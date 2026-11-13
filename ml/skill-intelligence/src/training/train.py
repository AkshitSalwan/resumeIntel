
from __future__ import annotations

import json
import hashlib
import platform
from pathlib import Path
from typing import Any

from .hardware import require_training_hardware


def _load_training_examples(path: Path, tokenizer: Any, max_length: int) -> list[dict[str, list[int]]]:
    import json as json_module

    examples: list[dict[str, list[int]]] = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue

        record = json_module.loads(line)
        messages = record.get("messages")

        if not isinstance(messages, list) or len(messages) != 3:
            raise ValueError(f"Line {line_number}: expected system, user and assistant messages.")

        if [message.get("role") for message in messages] != ["system", "user", "assistant"]:
            raise ValueError(f"Line {line_number}: unexpected chat message roles.")

        full_ids = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=False,
        )
        prompt_ids = tokenizer.apply_chat_template(
            messages[:-1],
            tokenize=True,
            add_generation_prompt=True,
        )

        if full_ids[:len(prompt_ids)] != prompt_ids:
            raise ValueError(
                f"Line {line_number}: chat template prompt is not a prefix of the full conversation."
            )

        answer_ids = full_ids[len(prompt_ids):]
        if not answer_ids:
            raise ValueError(f"Line {line_number}: assistant response contains no tokens.")

        if len(answer_ids) >= max_length:
            raise ValueError(
                f"Line {line_number}: assistant response exceeds max sequence length."
            )

        # Preserve the assistant target and the most recent job-description context.
        prompt_budget = max_length - len(answer_ids)
        if len(prompt_ids) > prompt_budget:
            system_ids = tokenizer.apply_chat_template(
                messages[:1],
                tokenize=True,
                add_generation_prompt=False,
            )

            if prompt_ids[:len(system_ids)] == system_ids and len(system_ids) < prompt_budget:
                prompt_ids = system_ids + prompt_ids[-(prompt_budget - len(system_ids)):]
            else:
                prompt_ids = prompt_ids[-prompt_budget:]

        input_ids = prompt_ids + answer_ids
        labels = ([-100] * len(prompt_ids)) + answer_ids

        examples.append({
            "input_ids": input_ids,
            "labels": labels,
        })

    if not examples:
        raise RuntimeError(f"No examples were loaded from {path}.")

    return examples


class _AssistantOnlyDataset:
    def __init__(self, examples: list[dict[str, list[int]]]) -> None:
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.examples[index]


class _AssistantOnlyCollator:
    def __init__(self, pad_token_id: int) -> None:
        self.pad_token_id = pad_token_id

    def __call__(self, features: list[dict[str, list[int]]]) -> dict[str, Any]:
        import torch

        max_length = max(len(item["input_ids"]) for item in features)
        max_length = ((max_length + 7) // 8) * 8

        input_ids = []
        attention_mask = []
        labels = []

        for item in features:
            padding = max_length - len(item["input_ids"])
            input_ids.append(item["input_ids"] + [self.pad_token_id] * padding)
            attention_mask.append([1] * len(item["input_ids"]) + [0] * padding)
            labels.append(item["labels"] + [-100] * padding)

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def _load_reference_records(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        messages = row["messages"]
        target = json.loads(messages[-1]["content"])
        records.append({
            "canonical_skill_ids": row.get("canonical_skill_ids", []),
            "skills": target.get("skills", []),
            "user_text": next(message["content"] for message in messages if message["role"] == "user"),
        })
    return records


def _generate_predictions(model: Any, tokenizer: Any, path: Path, max_length: int, hardware: dict[str, Any]) -> list[dict[str, Any]]:
    import torch

    predictions = []
    model.eval()
    with torch.inference_mode():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            messages = row["messages"]
            prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=True, add_generation_prompt=True, return_tensors="pt")
            prompt = prompt.to(model.device)
            generated = model.generate(prompt, max_new_tokens=min(512, max_length), do_sample=False, pad_token_id=tokenizer.pad_token_id)
            text = tokenizer.decode(generated[0][prompt.shape[-1]:], skip_special_tokens=True)
            try:
                output = json.loads(text)
            except json.JSONDecodeError:
                output = {}
            skills = output.get("skills", []) if isinstance(output, dict) else []
            predictions.append({
                "skills": skills if isinstance(skills, list) else [],
                "canonical_skill_ids": [str(item["canonical_id"]) for item in skills if isinstance(item, dict) and item.get("canonical_id")],
            })
    model.train()
    return predictions


def train(
    train_file: str | Path,
    validation_file: str | Path,
    output_dir: str | Path,
    *,
    config_path: str | Path | None = None,
    resume_from_checkpoint: str | Path | None = None,
) -> dict[str, Any]:
    hardware = require_training_hardware()

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoConfig,
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    from .config import load_config

    train_path = Path(train_file)
    if not train_path.is_file() or not train_path.read_text(encoding="utf-8").strip():
        raise RuntimeError("Training JSONL is missing or empty.")

    validation_path = Path(validation_file)
    if not validation_path.is_file() or not validation_path.read_text(encoding="utf-8").strip():
        raise RuntimeError("Reviewed validation JSONL is missing or empty.")
    if train_path.resolve() == validation_path.resolve():
        raise ValueError("Training and validation datasets must be separate files.")

    config = load_config(config_path)

    if config.get("base_model") != "Qwen/Qwen3-4B-Instruct-2507":
        raise ValueError("Unexpected base model. Check config/training.json before training.")

    device_memory = min(
        device["memory_gb"] for device in hardware["devices"]
    )
    low_memory = device_memory <= 20

    max_length = int(
        config["low_memory_max_seq_length"] if low_memory
        else config["max_seq_length"]
    )
    gradient_accumulation = int(
        config["low_memory_gradient_accumulation_steps"] if low_memory
        else config["gradient_accumulation_steps"]
    )

    set_seed(int(config["seed"]))

    compute_dtype = (
        torch.bfloat16
        if hardware.get("bf16_supported")
        else torch.float16
    )

    model_config = AutoConfig.from_pretrained(config["base_model"], revision=config.get("revision"))
    if model_config.model_type != "qwen3":
        raise ValueError(f"Expected Qwen3 model architecture, received {model_config.model_type!r}.")

    tokenizer = AutoTokenizer.from_pretrained(config["base_model"], revision=config.get("revision"))
    if not getattr(tokenizer, "chat_template", None):
        raise ValueError("The base model tokenizer does not provide a chat template.")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    examples = _load_training_examples(train_path, tokenizer, max_length)
    validation_examples = _load_training_examples(validation_path, tokenizer, max_length)
    print(f"Loaded {len(examples)} training and {len(validation_examples)} validation examples; maximum sequence length: {max_length}")

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )

    model_kwargs: dict[str, Any] = {
        "quantization_config": quantization_config,
        "device_map": "auto",
        "torch_dtype": compute_dtype,
    }
    if config.get("revision"):
        model_kwargs["revision"] = config["revision"]

    model = AutoModelForCausalLM.from_pretrained(
        config["base_model"],
        **model_kwargs,
    )
    model.config.use_cache = False

    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=bool(config["gradient_checkpointing"]),
    )

    lora_config = LoraConfig(
        r=int(config["lora_r"]),
        lora_alpha=int(config["lora_alpha"]),
        lora_dropout=float(config["lora_dropout"]),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )
    model = get_peft_model(model, lora_config)
    if not any(parameter.requires_grad for parameter in model.parameters()):
        raise RuntimeError("PEFT configuration produced no trainable parameters.")
    model.print_trainable_parameters()

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    resume_checkpoint = resume_from_checkpoint or config.get("resume_from_checkpoint")
    if resume_checkpoint:
        resume_path = Path(resume_checkpoint)
        if not resume_path.is_dir() or not (resume_path / "trainer_state.json").is_file():
            raise ValueError(f"Checkpoint is not a resumable Transformers Trainer checkpoint: {resume_path}")
        resume_checkpoint = str(resume_path)
    (destination / "training_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    training_args = TrainingArguments(
        output_dir=str(destination / "checkpoints"),
        logging_dir=str(destination / "logs"),
        per_device_train_batch_size=int(config["per_device_train_batch_size"]),
        gradient_accumulation_steps=gradient_accumulation,
        num_train_epochs=float(config["num_train_epochs"]),
        learning_rate=float(config["learning_rate"]),
        warmup_ratio=float(config["warmup_ratio"]),
        weight_decay=float(config["weight_decay"]),
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit",
        logging_steps=1,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        bf16=bool(hardware.get("bf16_supported")),
        fp16=not bool(hardware.get("bf16_supported")),
        gradient_checkpointing=bool(config["gradient_checkpointing"]),
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_grad_norm=0.3,
        group_by_length=False,
        report_to="none",
        remove_unused_columns=False,
        dataloader_pin_memory=True,
        seed=int(config["seed"]),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=_AssistantOnlyDataset(examples),
        eval_dataset=_AssistantOnlyDataset(validation_examples),
        data_collator=_AssistantOnlyCollator(tokenizer.pad_token_id),
    )

    result = trainer.train(resume_from_checkpoint=resume_checkpoint)

    adapter_dir = destination / "adapter"
    trainer.model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    validation_predictions = _generate_predictions(trainer.model, tokenizer, validation_path, max_length, hardware)
    validation_gold = _load_reference_records(validation_path)
    from src.evaluation.metrics import extraction_metrics
    validation_structured = extraction_metrics(
        [{"canonical_skill_ids": row["canonical_skill_ids"], "skills": row["skills"]} for row in validation_gold],
        validation_predictions,
        [row["user_text"] for row in validation_gold],
    )
    validation_loss = trainer.evaluate().get("eval_loss")

    metrics = dict(result.metrics)
    metrics.update({
        "validation_metrics": validation_structured,
        "validation_loss": validation_loss,
        "training_examples": len(examples),
        "base_model": config["base_model"],
        "max_seq_length": max_length,
        "gradient_accumulation_steps": gradient_accumulation,
        "gpu": hardware["devices"],
        "validation_loss_is_extraction_quality": False,
    })

    (destination / "training_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    (destination / "training_log_history.json").write_text(
        json.dumps(trainer.state.log_history, indent=2),
        encoding="utf-8",
    )

    metadata = {
        "status": "trained_with_validation",
        "base_model": config["base_model"],
        "adapter_path": str(adapter_dir),
        "training_examples": len(examples),
        "epochs": config["num_train_epochs"],
        "seed": config["seed"],
        "resume_from_checkpoint": str(resume_checkpoint) if resume_checkpoint else None,
        "max_seq_length": max_length,
        "gold_evaluation_performed": False,
        "validation_evaluation_performed": True,
        "validation_metrics": validation_structured,
        "dataset_counts": {"train": len(examples), "validation": len(validation_examples)},
        "split_information": {"training": "train", "validation": "validation", "gold": "test held out for final evaluation", "companies": {"train": sorted({row["source_companies"][0] for row in _read_dataset_rows(train_path) if row.get("source_companies")}), "validation": sorted({row["source_companies"][0] for row in _read_dataset_rows(validation_path) if row.get("source_companies")})}},
        "dataset_sha256": {"train": hashlib.sha256(train_path.read_bytes()).hexdigest(), "validation": hashlib.sha256(validation_path.read_bytes()).hexdigest()},
        "config": config,
        "reproducibility": {"seed": config["seed"], "python_version": platform.python_version(), "torch_version": str(torch.__version__), "transformers_version": __import__("transformers").__version__, "peft_version": __import__("peft").__version__},
    }
    (destination / "training_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    model.config.use_cache = True
    return metadata


def _read_dataset_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def preflight_model_loading(config_path: str | Path | None = None) -> dict[str, Any]:
    """Check CUDA, pinned libraries, tokenizer, model weights, NF4, and PEFT without training."""
    hardware = require_training_hardware()
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    from .config import load_config

    config = load_config(config_path)
    model_id = config["base_model"]
    model_config = AutoConfig.from_pretrained(model_id, revision=config.get("revision"))
    if model_config.model_type != "qwen3":
        raise ValueError(f"Expected Qwen3 model architecture, received {model_config.model_type!r}.")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=config.get("revision"))
    if not getattr(tokenizer, "chat_template", None):
        raise ValueError("The base model tokenizer does not provide a chat template.")

    compute_dtype = torch.bfloat16 if hardware.get("bf16_supported") else torch.float16
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=compute_dtype,
        **({"revision": config["revision"]} if config.get("revision") else {}),
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=bool(config["gradient_checkpointing"]))
    lora_config = LoraConfig(
        r=int(config["lora_r"]),
        lora_alpha=int(config["lora_alpha"]),
        lora_dropout=float(config["lora_dropout"]),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    if not trainable:
        raise RuntimeError("PEFT configuration produced no trainable parameters.")
    del model
    torch.cuda.empty_cache()
    return {"status": "preflight_passed", "model": model_id, "model_type": model_config.model_type, "tokenizer_chat_template": True, "trainable_parameters": trainable, "hardware": hardware}
