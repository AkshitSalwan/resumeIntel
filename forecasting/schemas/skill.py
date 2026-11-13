from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    canonical_name: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    taxonomy_source: str = "resumeintel-initial"
    taxonomy_version: str = "1.0.0"
    external_ids: dict[str, str] = Field(default_factory=dict)


class SkillMention(BaseModel):
    posting_id: str
    skill_id: str
    canonical_name: str
    matched_text: str
    extraction_method: str = "dictionary"
    confidence: float | None = None
    evidence: str
