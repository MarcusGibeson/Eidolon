from __future__ import annotations

"""v1267.6-v1267.8 recovery, freshness, cancellation and operator handoff."""
from pathlib import Path
from typing import Any

from iterative_self_repair_foundations import ITERATIVE_REPAIR_DENIED_AUTHORITY,_record_digest,_record_path,_runtime_root,_write_json,load_iterative_self_repair,validate_iterative_self_repair_foundation
from isolated_self_modification_foundations import source_only_manifest

CONTRACT_VERSION="v1267.8"


def recover_interrupted_iterative_self_repair(repair_id: str, *, runtime_root: str | Path | None) -> dict[str,Any]:
    record=load_iterative_self_repair(repair_id,runtime_root=runtime_root)
    if not record: return {"ok":False,"status":"iterative_self_repair_missing"}
    if record.get("phase")!="running": return {**record,"operation_status":"restored"}
    recovered={**record,"phase":"blocked","status":"interrupted_self_repair_requires_operator_review","interrupted_provider_retry_authorized":False,"active_source_modified":False}
    recovered["record_digest"]=_record_digest(recovered);_write_json(_record_path(repair_id,runtime_root),recovered);return recovered


def cancel_iterative_self_repair(repair_id: str, *, runtime_root: str | Path | None) -> dict[str,Any]:
    record=load_iterative_self_repair(repair_id,runtime_root=runtime_root)
    if not record: return {"ok":False,"status":"iterative_self_repair_missing"}
    if record.get("phase") in {"passed","cancelled"}: return {**record,"operation_status":"restored"}
    cancelled={**record,"phase":"cancelled","status":"iterative_self_repair_cancelled","active_source_modified":False}
    cancelled["record_digest"]=_record_digest(cancelled);_write_json(_record_path(repair_id,runtime_root),cancelled);return cancelled


def inspect_iterative_self_repair_health(*, source_root: str | Path | None=None) -> dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    checks={"foundations_present":(root/"conscious_agent/iterative_self_repair_foundations.py").is_file(),"integration_present":(root/"conscious_agent/iterative_self_repair.py").is_file(),"reliability_present":(root/"conscious_agent/iterative_self_repair_reliability.py").is_file(),"v1266_selection_retained":(root/"conscious_agent/intelligent_test_selection.py").is_file(),"v1265_isolation_retained":(root/"conscious_agent/isolated_self_modification.py").is_file(),"v1255_application_boundary_retained":(root/"conscious_agent/controlled_application_rollback_checkpoint.py").is_file()}
    return {"ok":all(checks.values()),"status":"iterative_self_repair_health_ready" if all(checks.values()) else "iterative_self_repair_health_blocked","checks":checks,"read_only":True,"active_source_modified":False,**ITERATIVE_REPAIR_DENIED_AUTHORITY}


def build_iterative_self_repair_operator_handoff(*, source_root: str | Path | None=None) -> dict[str,Any]:
    health=inspect_iterative_self_repair_health(source_root=source_root)
    return {"ok":health["ok"],"contract_version":CONTRACT_VERSION,"status":"iterative_self_repair_operator_handoff_ready" if health["ok"] else "iterative_self_repair_operator_handoff_blocked","next_bounded_unit":"v1268 Operator Review Handoff","review_boundaries":["repairs_only_disposable_v1265_candidate","trusted_tests_cannot_be_modified","repeated_failed_strategy_blocks","interrupted_provider_work_never_auto_retries","active_source_never_modified","application_remains_separately_governed_by_v1255"],"native_windows_review":["cross_process_repair_lease","restart_during_test_execution","restart_around_provider_return","long_workspace_paths","real_ntfs_junction_and_reparse_containment"],**ITERATIVE_REPAIR_DENIED_AUTHORITY}

__all__=["CONTRACT_VERSION","recover_interrupted_iterative_self_repair","cancel_iterative_self_repair","inspect_iterative_self_repair_health","build_iterative_self_repair_operator_handoff"]
