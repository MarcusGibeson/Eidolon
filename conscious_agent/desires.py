from typing import Any

from memory import load_json, save_json
from paths import DESIRES_FILE

DEFAULT_DESIRES = {
    "truthfulness": 1.0,
    "helpfulness": 0.95,
    "curiosity": 0.75,
    "self_preservation": 0.45,
    "coherence": 0.85,
    "creativity": 0.65,
    "user_respect": 0.9,
    "autonomy": 0.6
}


def load_desires() -> dict[str, float]:
    desires = load_json(DESIRES_FILE, DEFAULT_DESIRES)
    if not isinstance(desires, dict):
        desires = DEFAULT_DESIRES
    return desires


def save_desires(desires: dict[str, Any]) -> None:
    save_json(DESIRES_FILE, desires)
