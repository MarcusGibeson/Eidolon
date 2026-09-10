from __future__ import annotations
from typing import Any
REQUEST = "Build a release label helper using the configured local provider with offline fallback."
TASK_ID = "gamma_139713971397"
CONFIG = {"provider_id": "provider_ollama_local", "provider_class": "local", "privacy_tier": "local_only", "configured": True, "endpoint": "http://127.0.0.1:11434"}
def local_provider(payload):
    assert payload["private_project_content_included"] is False
    assert payload["filesystem_path_included"] is False
    return {"label_prefix": "gamma", "empty_label": "none"}
def require(condition: Any, message: str) -> None:
    if not condition: raise AssertionError(message)
