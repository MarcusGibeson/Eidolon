from __future__ import annotations
"""Strictly read-only v1134.2 Prospective Planning intake checkpoint."""
import hashlib
import os
from pathlib import Path
from prospective_planning_signals import build_prospective_planning_signal_inspection, SOURCE_CATEGORIES, PURPOSE_CATEGORIES
from prospective_planning_candidates import build_prospective_planning_candidate_inspection, STATES

CONTRACT_VERSION = "v1134.2"

def _root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition"

def _signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc"):
        stat = path.stat()
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(str(stat.st_size).encode())
        digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()

def build_prospective_planning_intake_checkpoint(runtime_root: Path | str | None = None, *, source_root: Path | str | None = None) -> dict:
    runtime = Path(runtime_root).resolve() if runtime_root else _root()
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    runtime_before = _signature(runtime)
    source_before = _signature(source)
    signals = build_prospective_planning_signal_inspection(runtime)
    candidates = build_prospective_planning_candidate_inspection(runtime)
    checks = [
        ("signal_contract", signals.get("contract_version") == "v1134.0"),
        ("candidate_contract", candidates.get("contract_version") == "v1134.1"),
        ("source_coverage", {"accepted_goal_outcome", "world_model_outcome", "inquiry_outcome", "perception_outcome"}.issubset(SOURCE_CATEGORIES)),
        ("purpose_coverage", {"project_path", "risk_mitigation", "deliberate_no_action_review"}.issubset(PURPOSE_CATEGORIES)),
        ("candidate_states", len(STATES) == 12),
        ("goal_lineage", all(row.get("goal_ids") for row in signals.get("recent_signals", []))),
        ("evidence_lineage", all(row.get("evidence_ids") for row in signals.get("recent_signals", []))),
        ("value_not_urgency", all(row.get("expected_value") is not None and row.get("urgency") is not None for row in signals.get("recent_signals", []))),
        ("alternatives_visible", all(row.get("alternative_ids") is not None for row in candidates.get("recent_candidates", []))),
        ("counterfactuals_visible", all(row.get("counterfactual_ids") is not None for row in candidates.get("recent_candidates", []))),
        ("risks_visible", all(row.get("risk") is not None and row.get("reversibility") is not None for row in candidates.get("recent_candidates", []))),
        ("stop_conditions_visible", all(row.get("stop_condition_ids") is not None for row in candidates.get("recent_candidates", []))),
        ("no_action_path", all(row.get("deliberate_no_action_eligible") is not None for row in candidates.get("recent_candidates", []))),
        ("false_pressure", all(row.get("false_pressure_suppressed") is not None for row in candidates.get("recent_candidates", []))),
        ("privacy_boundary", not signals.get("raw_content_exposed") and not candidates.get("plan_text_exposed") and not signals.get("hidden_reasoning_exposed")),
        ("no_provider", not signals.get("provider_contacted") and not candidates.get("provider_contacted")),
        ("authority_separation", not any(signals.get("authority_boundary", {}).values()) and not any(candidates.get("authority_boundary", {}).values())),
        ("read_only", runtime_before == _signature(runtime) and source_before == _signature(source)),
    ]
    return {
        "ok": all(value for _, value in checks),
        "contract_version": CONTRACT_VERSION,
        "checks": [{"id": check_id, "status": "pass" if value else "fail"} for check_id, value in checks],
        "signals": signals,
        "candidates": candidates,
        "runtime_mutated": runtime_before != _signature(runtime),
        "source_modified": source_before != _signature(source),
        "raw_content_exposed": False,
        "goal_text_exposed": False,
        "plan_text_exposed": False,
        "counterfactual_text_exposed": False,
        "evidence_text_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
        "provider_contacted": False,
        "goal_activated": False,
        "plan_created": False,
        "initiative_created": False,
        "message_sent": False,
        "notification_created": False,
        "approval_created": False,
        "authorization_created": False,
        "external_action_executed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "desktop_verification": "pending",
    }
