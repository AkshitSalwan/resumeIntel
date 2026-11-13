import re
from collections.abc import Iterable

from forecasting.schemas.skill import Skill, SkillMention


class SkillNormalizer:
    """Extract explicit taxonomy terms while avoiding substring collisions."""

    def __init__(self, skills: Iterable[Skill]) -> None:
        self.skills = tuple(skills)
        patterns: list[tuple[Skill, re.Pattern[str]]] = []
        for skill in self.skills:
            aliases = sorted(skill.aliases + (skill.canonical_name,), key=len, reverse=True)
            alternatives = "|".join(re.escape(alias) for alias in aliases)
            if skill.skill_id == "go":
                # "Go" is ordinary English and appears in phrases such as
                # "go-to-market". Require local programming context unless the
                # unambiguous alias "Golang" occurs.
                pattern = re.compile(
                    r"(?<![\w+#])(?:golang|go(?!(?:[- ]to[- ]market|[- ]to[- ]markets)))(?![\w+#])",
                    re.IGNORECASE,
                )
            else:
                pattern = re.compile(rf"(?<![\w+#])(?:{alternatives})(?![\w+#])", re.IGNORECASE)
            patterns.append((skill, pattern))
        self._patterns = tuple(patterns)

    def extract(self, posting_id: str, text: str | None) -> list[SkillMention]:
        if not text:
            return []
        mentions: list[SkillMention] = []
        for skill, pattern in self._patterns:
            match = pattern.search(text)
            if not match:
                continue
            if skill.skill_id == "go" and match.group(0).lower() != "golang":
                context = text[max(0, match.start() - 70):min(len(text), match.end() + 70)]
                if not re.search(r"\b(programming|programmer|language|golang|software|developer|coding|codebase|backend|compiler)\b", context, re.IGNORECASE):
                    continue
            start = max(0, match.start() - 70)
            end = min(len(text), match.end() + 70)
            mentions.append(SkillMention(
                posting_id=posting_id,
                skill_id=skill.skill_id,
                canonical_name=skill.canonical_name,
                matched_text=match.group(0),
                evidence=" ".join(text[start:end].split()),
            ))
        return mentions
