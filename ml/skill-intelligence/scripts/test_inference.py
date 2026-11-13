from __future__ import annotations

from _bootstrap import ROOT
from src.inference.predict import predict
from src.inference.schemas import ExtractSkillsRequest


def main() -> int:
    try:
        predict(ExtractSkillsRequest(job_description="Python and Kubernetes"))
    except RuntimeError as error:
        print(f"Inference unavailable: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
