# validator.py - Keyword heuristics to audit AI scores
HIGH_IMPACT_KEYWORDS = ["fire", "weapon", "active", "medical", "unconscious"]


def validate_score(text: str, ai_score: int) -> int:
    """
    Override AI score if high-impact keywords are present but score is low.
    """
    if any(keyword in text.lower() for keyword in HIGH_IMPACT_KEYWORDS) and ai_score < 4:
        return 5
    return ai_score
