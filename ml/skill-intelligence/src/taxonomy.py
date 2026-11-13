from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from forecasting.taxonomy.skill_dictionary import INITIAL_SKILLS  # noqa: E402


def taxonomy_map() -> dict[str, object]:
    return {skill.skill_id: skill for skill in INITIAL_SKILLS}


def resolve_skill(skill_id: str) -> object | None:
    return taxonomy_map().get(skill_id)
