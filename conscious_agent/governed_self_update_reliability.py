from __future__ import annotations
"""v1269.6-v1269.8 recovery, freshness, health and Windows handoff."""
import time
from pathlib import Path
from typing import Any
from isolated_self_modification_foundations import source_only_manifest
from governed_self_update_foundations import DENIED_AUTHORITY,load_governed_self_update,validate_governed_self_update_packet,_read_json,_backup_path

def inspect_governed_self_update_health(update_id:str,source_root:str|Path,*,runtime_root=None)->dict[str,Any]:
    source=Path(source_root).resolve(strict=True);rec=load_governed_self_update(update_id,runtime_root=runtime_root)
    if not rec or not validate_governed_self_update_packet(rec).get("ok"):return {"ok":False,"status":"governed_self_update_record_invalid_or_missing","read_only":True,**DENIED_AUTHORITY}
    digest=source_only_manifest(source)["source_manifest_digest"];state="baseline" if digest==rec.get("source_manifest_digest") else "candidate" if digest==rec.get("candidate_manifest_digest") else "other";backup=bool(_read_json(_backup_path(update_id,runtime_root)));phase=str(rec.get("phase") or "");lease_active=phase=="running" and float(rec.get("lease_expires_unix") or 0)>time.time()
    recovery="none"
    if phase=="running" and lease_active:recovery="in_progress_do_not_duplicate"
    elif phase=="running" and state=="candidate" and backup:recovery="same_exact_authorization_restores_then_retries"
    elif state=="other":recovery="manual_review_required"
    elif phase=="applied_verified":recovery="separate_exact_rollback_available"
    elif phase=="rolled_back":recovery="terminal_rolled_back"
    return {"ok":state in {"baseline","candidate"},"status":"governed_self_update_health_ready" if state in {"baseline","candidate"} else "governed_self_update_health_attention_required","update_id":update_id,"phase":phase,"target_state":state,"backup_present":backup,"lease_active":lease_active,"recovery_disposition":recovery,"read_only":True,"active_source_modified_by_inspection":False,**DENIED_AUTHORITY}

def inspect_governed_self_update_surface_health(*,source_root:str|Path|None=None)->dict[str,Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();checks={"foundations_present":(root/'conscious_agent/governed_self_update_foundations.py').is_file(),"integration_present":(root/'conscious_agent/governed_self_update.py').is_file(),"reliability_present":(root/'conscious_agent/governed_self_update_reliability.py').is_file(),"v1268_review_retained":(root/'conscious_agent/operator_review_handoff.py').is_file(),"v1267_repair_retained":(root/'conscious_agent/iterative_self_repair.py').is_file(),"v1265_isolation_retained":(root/'conscious_agent/isolated_self_modification.py').is_file(),"v1255_application_boundary_retained":(root/'conscious_agent/controlled_application_rollback_checkpoint.py').is_file()}
    return {"ok":all(checks.values()),"status":"governed_self_update_surface_health_ready" if all(checks.values()) else "governed_self_update_surface_health_blocked","checks":checks,"read_only":True,**DENIED_AUTHORITY}

def build_governed_self_update_operator_handoff(*,source_root:str|Path|None=None)->dict[str,Any]:
    h=inspect_governed_self_update_surface_health(source_root=source_root);return {"ok":h['ok'],"status":"governed_self_update_operator_handoff_ready" if h['ok'] else "governed_self_update_operator_handoff_blocked","next_bounded_unit":"v1270 Self-Development Alpha Checkpoint","boundaries":["v1268_approval_is_not_update_authority","fresh_v1269_preflight_and_exact_authorization","backup_before_first_write","transactional_reviewed_paths_only","restart_health_verification_required","automatic_rollback_on_failure","successful_update_rollback_requires_separate_exact_authorization","promotion_certification_release_remain_denied"],"native_windows_review":["external_supervisor_restart","cross_process_update_lock","ntfs_atomic_replace","junction_reparse_containment","long_paths","interrupted_update_recovery"],**DENIED_AUTHORITY}

__all__=["inspect_governed_self_update_health","inspect_governed_self_update_surface_health","build_governed_self_update_operator_handoff"]
