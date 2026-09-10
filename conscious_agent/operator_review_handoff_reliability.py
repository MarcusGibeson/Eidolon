from __future__ import annotations

"""v1268.6-v1268.8 freshness, tamper, restart and operator-surface hardening."""
from pathlib import Path
from typing import Any
from isolated_self_modification_foundations import load_self_modification,source_only_manifest
from operator_review_handoff_foundations import REVIEW_DENIED_AUTHORITY,load_operator_review_packet,validate_operator_review_packet

CONTRACT_VERSION="v1268.8"


def validate_operator_review_freshness(review_id: str, source_root: str | Path, *, self_modification_runtime_root: str | Path | None, runtime_root: str | Path | None) -> dict[str,Any]:
    packet=load_operator_review_packet(review_id,runtime_root=runtime_root)
    if not packet or not validate_operator_review_packet(packet).get("ok"): return {"ok":False,"status":"operator_review_packet_invalid_or_missing"}
    source=Path(source_root).expanduser().resolve(strict=True); active=source_only_manifest(source)
    self_record=load_self_modification(str(packet.get("source_operation_id") or ""),runtime_root=self_modification_runtime_root)
    try: workspace=Path(str(self_record.get("workspace_path") or "")).expanduser().resolve(strict=True); candidate=source_only_manifest(workspace)
    except Exception: return {"ok":False,"status":"operator_review_candidate_workspace_missing_or_invalid"}
    active_ok=active["source_manifest_digest"]==packet.get("source_manifest_digest"); candidate_ok=candidate["source_manifest_digest"]==packet.get("candidate_manifest_digest")
    return {"ok":active_ok and candidate_ok,"status":"operator_review_handoff_fresh" if active_ok and candidate_ok else "operator_review_handoff_stale","active_source_fresh":active_ok,"candidate_fresh":candidate_ok,"active_source_modified":False,**REVIEW_DENIED_AUTHORITY}


def inspect_operator_review_handoff_health(*, source_root: str | Path | None=None) -> dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); checks={"foundations_present":(root/'conscious_agent/operator_review_handoff_foundations.py').is_file(),"integration_present":(root/'conscious_agent/operator_review_handoff.py').is_file(),"reliability_present":(root/'conscious_agent/operator_review_handoff_reliability.py').is_file(),"v1267_repair_retained":(root/'conscious_agent/iterative_self_repair.py').is_file(),"v1266_selection_retained":(root/'conscious_agent/intelligent_test_selection.py').is_file(),"v1265_isolation_retained":(root/'conscious_agent/isolated_self_modification.py').is_file(),"v1255_application_boundary_retained":(root/'conscious_agent/controlled_application_rollback_checkpoint.py').is_file()}
    return {"ok":all(checks.values()),"status":"operator_review_handoff_health_ready" if all(checks.values()) else "operator_review_handoff_health_blocked","checks":checks,"read_only":True,"active_source_modified":False,**REVIEW_DENIED_AUTHORITY}


def build_operator_review_handoff_operator_handoff(*, source_root: str | Path | None=None) -> dict[str,Any]:
    health=inspect_operator_review_handoff_health(source_root=source_root)
    return {"ok":health['ok'],"contract_version":CONTRACT_VERSION,"status":"operator_review_handoff_operator_handoff_ready" if health['ok'] else "operator_review_handoff_operator_handoff_blocked","next_bounded_unit":"v1269 Governed Self-Update","review_boundaries":["review_packet_is_content_minimized","approve_means_v1269_consideration_only","fresh_v1269_preflight_required","fresh_v1269_authorization_required","active_source_unchanged","application_remains_separately_governed_by_v1255"],"native_windows_review":["cross_process_review_decision_lock","candidate_workspace_junction_reparse_containment","long_runtime_paths","restart_between_packet_and_decision","stale_source_after_review"],**REVIEW_DENIED_AUTHORITY}

__all__=["CONTRACT_VERSION","validate_operator_review_freshness","inspect_operator_review_handoff_health","build_operator_review_handoff_operator_handoff"]
