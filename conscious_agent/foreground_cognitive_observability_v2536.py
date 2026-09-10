from __future__ import annotations

"""v2536 durable foreground observability bridge.

Persists only minimized activity/voice projection metadata from foreground
conversation work. Raw prompts, response text, voice text, provider output, and
action arguments are deliberately excluded.
"""

import os
from pathlib import Path
from typing import Any, Mapping

from mental_activity_timeline_v2511 import MentalActivityTimeline

CONTRACT_VERSION = "v2536.0"


def _root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    base = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return base / "cognition"


def record_foreground_observability_event(
    projection: Mapping[str, Any],
    *,
    operation_id: str,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    event = str(projection.get("event") or "").strip().lower()
    op = str(operation_id or "").strip()[:160]
    if not op:
        raise ValueError("operation_id_required")
    if event == "activity":
        digest = str(projection.get("activity_digest") or "").strip().lower()
        stage = str(projection.get("stage") or "working").strip().lower()[:60]
        kind = "action" if stage.startswith("action") or stage == "governed_action" else "cognitive"
        transition = f"foreground_{stage}"[:80]
        source_ref = str(projection.get("operation_id") or op)[:120]
    elif event == "internal_voice":
        digest = str(projection.get("voice_digest") or "").strip().lower()
        kind = "voice"
        transition = "foreground_projection"
        source_ref = op[:120]
    else:
        raise ValueError("unsupported_projection_event")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("projection_digest_required")
    event_id = f"foreground:{op}:{event}:{digest[:20]}"
    result = MentalActivityTimeline(_root(runtime_root)).append(
        event_id,
        event_kind=kind,
        transition=transition,
        source_digest=digest,
        subject_ref=source_ref,
        outcome_code="FOREGROUND_OBSERVABILITY",
    )
    result["contract_version"] = CONTRACT_VERSION
    result["raw_prompt_stored"] = False
    result["response_text_stored"] = False
    result["voice_text_stored"] = False
    result["provider_output_stored"] = False
    result["read_only_observability_only"] = True
    return result


__all__ = ["CONTRACT_VERSION", "record_foreground_observability_event"]
