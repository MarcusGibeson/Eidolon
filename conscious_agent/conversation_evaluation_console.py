from __future__ import annotations

"""v1087.7 provider-free state assembly for the Desktop Alpha evaluation console."""

from typing import Any
import hashlib
import json

from conversation_daily_evaluation import DailyEvaluationError, load_daily_evaluation
from conversation_daily_evaluation_protocol import build_daily_evaluation_protocol
from conversation_evaluation_long_session import build_long_session_evaluation
from conversation_evaluation_recovery_scenarios import build_restart_outage_evaluation
from conversation_evaluation_reproduction import build_reproduction_packet
from conversation_evaluation_trends import build_daily_evaluation_trends

EVALUATION_CONSOLE_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_evaluation_console_state(*, evaluation_id: str = "", session_id: str = "") -> dict[str, Any]:
    protocol = build_daily_evaluation_protocol(session_id=session_id)
    trends = build_daily_evaluation_trends()
    token = str(evaluation_id or "").strip()
    selected: dict[str, Any] | None = None
    reproduction: dict[str, Any] | None = None
    recovery: dict[str, Any] | None = None
    long_session: dict[str, Any] | None = None
    selection_status = "none_selected"
    if token:
        try:
            selected = load_daily_evaluation(token)
            reproduction = build_reproduction_packet(token)
            recovery = build_restart_outage_evaluation(token)
            long_session = build_long_session_evaluation(token)
            selection_status = "available"
        except DailyEvaluationError:
            selection_status = "not_found"
    evidence = {
        "protocol_digest": str(protocol.get("readiness_contract_digest") or ""),
        "trends_digest": str(trends.get("evidence_digest") or ""),
        "selected_evaluation_digest": str((selected or {}).get("observation_evidence_digest") or ""),
        "selection_status": selection_status,
    }
    return {
        "type": "desktop_alpha_daily_evaluation_console_state",
        "schema_version": EVALUATION_CONSOLE_SCHEMA_VERSION,
        "selection_status": selection_status,
        "selected_evaluation_id": token if selection_status == "available" else "",
        "protocol": protocol,
        "trends": trends,
        "selected_evaluation": selected,
        "reproduction": reproduction,
        "restart_outage": recovery,
        "long_session": long_session,
        "console_digest": _digest(evidence),
        "operator_confirmation_required_for_mutation": True,
        "mutation_route": "/api/dashboard-chat/daily-evaluation",
        "read_routes_only": True,
        "provider_invoked": False,
        "generation_invoked": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }
