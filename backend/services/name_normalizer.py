import re

_TITLE_PATTERN = re.compile(
    r"\b(?:mr|mrs|ms|miss|master|dr|prof|shri|smt|kumari)\.?\b",
    re.IGNORECASE,
)


def normalize_person_name(name: str) -> str:
    if not name:
        return ""

    normalized = _TITLE_PATTERN.sub(" ", name)
    normalized = re.sub(r"[^a-zA-Z\s]", " ", normalized)
    return " ".join(normalized.lower().split())
