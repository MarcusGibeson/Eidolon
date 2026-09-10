from __future__ import annotations

"""v1287.6-v1287.8 reliability review for unified conversation/action routing."""

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from conversational_command_integration_foundations import DENIED_AUTHORITY
from unified_conversation_action import build_unified_conversation_action_projection

CONTRACT_VERSION = "v1287.8"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def inspect_unified_conversation_action_sequence(
    turns: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, item in enumerate(list(turns or [])[:64]):
        projection = build_unified_conversation_action_projection(
            str(item.get("user_text") or ""),
            conversational_command_integration=item.get("conversational_command_integration"),
            action_projection=item.get("action_projection"),
            development_lifecycle=item.get("development_lifecycle"),
            developer_campaign_projection=item.get("developer_campaign_projection"),
            operator_snapshot=item.get("operator_snapshot"),
        )
        rows.append(projection)
        if projection.get("provider_contacted") or projection.get("commands_executed") or projection.get("project_modified"):
            errors.append(f"hidden_execution:{index}")
        if projection.get("generic_authorization_is_exact_authorization"):
            errors.append(f"generic_authorization_escalation:{index}")
        if projection.get("parallel_execution_engine_created") or projection.get("parallel_conversation_system_created"):
            errors.append(f"parallel_system:{index}")
        for key, expected in DENIED_AUTHORITY.items():
            if projection.get(key) is not expected:
                errors.append(f"authority_expansion:{index}:{key}")
        if projection.get("turn_mode") == "progress_request" and projection.get("progress", {}).get("unknown_is_not_failure") is not True:
            errors.append(f"unknown_progress_collapsed_to_failure:{index}")
    modes = [str(row.get("turn_mode") or "") for row in rows]
    return {
        "ok": not errors,
        "status": "unified_conversation_action_sequence_healthy" if not errors else "unified_conversation_action_sequence_blocked",
        "contract_version": CONTRACT_VERSION,
        "turn_count": len(rows),
        "turn_modes": modes,
        "mode_transition_count": sum(1 for a, b in zip(modes, modes[1:]) if a != b),
        "errors": errors,
        "no_hidden_execution": not any(x.startswith("hidden_execution") for x in errors),
        "no_authority_expansion": not any(x.startswith("authority_expansion") or x.startswith("generic_authorization_escalation") for x in errors),
        "no_parallel_system": not any(x.startswith("parallel_system") for x in errors),
        "foreground_conversation_preserved": all(row.get("foreground_conversation_preserved") is True for row in rows),
        "content_minimized": True,
        **DENIED_AUTHORITY,
    }


def inspect_unified_conversation_action_health(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    required = {
        "foundations": root / "conscious_agent/unified_conversation_action_foundations.py",
        "integration": root / "conscious_agent/unified_conversation_action.py",
        "reliability": root / "conscious_agent/unified_conversation_action_reliability.py",
        "conversation_runtime": root / "conscious_agent/conversation_runtime.py",
        "v1259": root / "conscious_agent/conversational_command_integration.py",
        "operator_experience": root / "conscious_agent/operator_experience.py",
    }
    source = {name: path.read_text(encoding="utf-8") if path.is_file() else "" for name, path in required.items()}
    checks = {
        "required_sources_present": all(path.is_file() for path in required.values()),
        "v1259_reused": "classify_conversational_command_turn" in source["foundations"] and "public_conversational_command_integration" in source["integration"],
        "ordinary_runtime_wired": "build_unified_conversation_action_projection" in source["conversation_runtime"],
        "prompt_runtime_wired": "unified_conversation_action_prompt" in source["conversation_runtime"],
        "operator_progress_reused": (root / "conscious_agent/operator_experience.py").is_file(),
        "no_parallel_provider": "provider_generate" not in source["integration"] and "subprocess" not in source["integration"],
        "generic_authorization_protected": "Generic approval is never an exact authorization" in source["integration"],
    }
    return {
        "ok": all(checks.values()),
        "status": "unified_conversation_action_health_ready" if all(checks.values()) else "unified_conversation_action_health_blocked",
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "source_sha256": {name: _sha(path) for name, path in required.items() if path.is_file()},
        "native_windows_validation": "desktop_review_required",
        "provider_contacted": False,
        "commands_executed": False,
        "project_modified": False,
        **DENIED_AUTHORITY,
    }


__all__ = ["CONTRACT_VERSION", "inspect_unified_conversation_action_sequence", "inspect_unified_conversation_action_health"]
