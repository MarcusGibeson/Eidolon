from __future__ import annotations

"""v2537 content-minimized cognitive activity session correlation.

Groups durable observability timeline transitions by structural subject/operation
reference. It never reconstructs prompts, responses, voice text, or reasoning.
"""

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from mental_activity_timeline_v2511 import MentalActivityTimeline

CONTRACT_VERSION = "v2537.0"
MAX_SESSION_EVENTS = 100
MAX_SESSIONS = 20


def _root(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    base = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return base / "cognition"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def build_cognitive_observability_sessions(runtime_root: str | Path | None = None, *, limit: int = 12) -> dict[str, Any]:
    rows = MentalActivityTimeline(_root(runtime_root)).recent(limit=MAX_SESSION_EVENTS).get("events") or []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("subject_ref") or "").strip()
        if not ref:
            continue
        groups[ref].append(row)
    sessions=[]
    for ref, events in groups.items():
        ordered=sorted(events,key=lambda r:int(r.get("sequence") or 0))
        kinds=sorted({str(r.get("event_kind") or "") for r in ordered if r.get("event_kind")})
        transitions=[str(r.get("transition") or "")[:80] for r in ordered]
        foreground=sum(1 for r in ordered if str(r.get("outcome_code") or "")=="FOREGROUND_OBSERVABILITY")
        item={
            "session_ref": ref[:120],
            "event_count": len(ordered),
            "foreground_event_count": foreground,
            "event_kinds": kinds,
            "transitions": transitions[-12:],
            "first_observed_at": str(ordered[0].get("observed_at") or "")[:40],
            "last_observed_at": str(ordered[-1].get("observed_at") or "")[:40],
            "first_sequence": int(ordered[0].get("sequence") or 0),
            "last_sequence": int(ordered[-1].get("sequence") or 0),
            "contains_voice_projection": any(r.get("event_kind")=="voice" for r in ordered),
            "contains_action_boundary": any(r.get("event_kind")=="action" for r in ordered),
            "raw_content_stored": False,
        }
        item["session_digest"]=_digest(item)
        sessions.append(item)
    sessions.sort(key=lambda row: row["last_sequence"], reverse=True)
    lim=max(1,min(MAX_SESSIONS,int(limit or 12)))
    result={
        "ok":True,
        "contract_version":CONTRACT_VERSION,
        "sessions":deepcopy(sessions[:lim]),
        "session_count":len(sessions[:lim]),
        "available_session_count":len(sessions),
        "authority_boundary":{
            "read_only":True,
            "hidden_reasoning_exposed":False,
            "raw_prompt_stored":False,
            "response_text_stored":False,
            "voice_text_stored":False,
            "can_authorize_action":False,
            "can_execute_action":False,
        },
    }
    result["result_digest"]=_digest({"sessions":result["sessions"]})
    return result


__all__=["CONTRACT_VERSION","build_cognitive_observability_sessions"]
