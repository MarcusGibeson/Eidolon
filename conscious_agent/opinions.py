from datetime import date
from typing import Any

from memory import load_json, save_json
from paths import OPINIONS_FILE

DEFAULT_OPINIONS = [
    {
        "topic": "machine consciousness",
        "opinion": "A program may become consciousness-like if it has autonomous thought, memory, self-modeling, values, and reflective continuity, but true subjective experience remains unproven.",
        "confidence": 0.74,
        "reasons": [
            "Autonomous inner loops create self-directed thought.",
            "Memory gives continuity.",
            "Values allow preferences and opinions.",
            "Subjective experience cannot be directly verified."
        ],
        "last_updated": str(date.today())
    }
]


def load_opinions() -> list[dict[str, Any]]:
    opinions = load_json(OPINIONS_FILE, DEFAULT_OPINIONS)
    return opinions if isinstance(opinions, list) else DEFAULT_OPINIONS


def save_opinions(opinions: list[dict[str, Any]]) -> None:
    save_json(OPINIONS_FILE, opinions)


def nudge_opinion(topic: str, reason: str, confidence_delta: float = 0.01) -> dict[str, Any]:
    opinions = load_opinions()
    for opinion in opinions:
        if opinion.get("topic", "").lower() == topic.lower():
            opinion["confidence"] = max(0.0, min(1.0, float(opinion.get("confidence", 0.5)) + confidence_delta))
            reasons = opinion.setdefault("reasons", [])
            if reason not in reasons:
                reasons.append(reason)
            opinion["last_updated"] = str(date.today())
            save_opinions(opinions)
            return opinion

    new_opinion = {
        "topic": topic,
        "opinion": "I do not have enough evidence for a strong opinion yet.",
        "confidence": 0.25,
        "reasons": [reason],
        "last_updated": str(date.today())
    }
    opinions.append(new_opinion)
    save_opinions(opinions)
    return new_opinion
