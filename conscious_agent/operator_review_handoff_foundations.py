from __future__ import annotations

"""v1268.0-v1268.2 operator review handoff foundations.

Builds one content-minimized, digest-bound review packet for a verified v1267
self-candidate.  Review is interpretation only: no application, installation,
release, self-update, provider, command, test, or mutation authority is created.
"""

import hashlib, json, os, re, tempfile
from pathlib import Path
from typing import Any, Mapping

from isolated_self_modification_foundations import load_self_modification, source_only_manifest
from intelligent_test_selection_foundations import load_test_selection, validate_test_selection
from iterative_self_repair_foundations import load_iterative_self_repair
from ordinary_chat_development_campaign import _proposal_lock

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1268.2"
MAX_RUNTIME_RECORD_BYTES = 4 * 1024 * 1024
REVIEW_DECISIONS = frozenset({"approve_for_v1269_consideration", "defer", "reject"})

REVIEW_DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "active_source_mutation_authorized": False,
    "source_application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "self_update_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _runtime_root(runtime_root: str | Path | None) -> Path:
    if runtime_root is None:
        raise ValueError("operator_review_handoff_runtime_root_required")
    return Path(runtime_root).expanduser().resolve()


def _record_path(review_id: str, runtime_root: str | Path | None) -> Path:
    if not re.fullmatch(r"selfreview_[a-f0-9]{24}", str(review_id or "")):
        raise ValueError("invalid_operator_review_id")
    return _runtime_root(runtime_root) / "operator_review_handoff" / "packets" / f"{review_id}.json"


def _decision_path(review_id: str, runtime_root: str | Path | None) -> Path:
    return _runtime_root(runtime_root) / "operator_review_handoff" / "decisions" / f"{review_id}.json"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    data=(json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=True)+"\n").encode()
    if len(data)>MAX_RUNTIME_RECORD_BYTES:
        raise ValueError("operator_review_record_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=None
    try:
        with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent, suffix=".tmp") as h:
            h.write(data); h.flush(); os.fsync(h.fileno()); tmp=Path(h.name)
        os.replace(tmp, path); tmp=None
    finally:
        if tmp is not None: tmp.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists(): return {}
    if path.stat().st_size>MAX_RUNTIME_RECORD_BYTES: raise ValueError("operator_review_record_too_large")
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("operator_review_record_invalid")
    return value


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({k:v for k,v in record.items() if k not in {"record_digest","operation_status"}})


def _manifest_map(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("relative_path") or ""): dict(row) for row in manifest.get("files") or []}


def _changed_files(active: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    a=_manifest_map(active); b=_manifest_map(candidate); rows=[]
    for rel in sorted(set(a)|set(b), key=str.casefold):
        before=a.get(rel); after=b.get(rel)
        if (before or {}).get("content_digest") == (after or {}).get("content_digest"): continue
        action="create" if before is None else "delete" if after is None else "modify"
        rows.append({
            "relative_path": rel,
            "action": action,
            "before_digest": (before or {}).get("content_digest", ""),
            "after_digest": (after or {}).get("content_digest", ""),
            "before_size_bytes": int((before or {}).get("size_bytes") or 0),
            "after_size_bytes": int((after or {}).get("size_bytes") or 0),
            "content_exposed": False,
        })
    return rows


def _surface_codes(paths: list[str]) -> list[str]:
    from intelligent_test_selection_foundations import _classify_surfaces
    return _classify_surfaces(paths)


def _risk_rows(surfaces: list[str], attempts: list[Mapping[str, Any]], changed_count: int) -> list[dict[str, Any]]:
    rows=[]
    if "self_modification" in surfaces: rows.append({"risk_code":"self_modification_boundary","severity":"high","basis":"changed_surface"})
    if "release_control" in surfaces: rows.append({"risk_code":"release_control_surface","severity":"high","basis":"changed_surface"})
    if "privacy_security" in surfaces: rows.append({"risk_code":"privacy_security_surface","severity":"high","basis":"changed_surface"})
    if "operator_surface" in surfaces: rows.append({"risk_code":"operator_surface_change","severity":"medium","basis":"changed_surface"})
    if changed_count>8: rows.append({"risk_code":"broad_change_set","severity":"medium","basis":"changed_file_count"})
    if attempts: rows.append({"risk_code":"candidate_required_repair","severity":"medium","basis":"repair_history"})
    if not rows: rows.append({"risk_code":"bounded_candidate_change","severity":"low","basis":"limited_changed_surface"})
    return rows


def _uncertainty_rows(repair: Mapping[str, Any], selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"uncertainty_code":"selected_tests_not_comprehensive_proof","state":"unresolved","severity":"medium","basis_digest":_digest(selection.get("selected_tests") or [])},
        {"uncertainty_code":"native_windows_behavior_requires_desktop_review","state":"unresolved","severity":"medium","basis_digest":_digest("desktop_windows_review")},
        {"uncertainty_code":"active_update_not_exercised","state":"unresolved","severity":"high","basis_digest":_digest("v1269_not_started")},
        {"uncertainty_code":"provider_generated_change_requires_human_judgment","state":"unresolved","severity":"medium","basis_digest":_digest(len(repair.get("attempts") or []))},
    ]


def validate_operator_review_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    digest_ok=bool(packet.get("record_digest")) and packet.get("record_digest")==_record_digest(packet)
    authority_ok=all(packet.get(k) is v for k,v in REVIEW_DENIED_AUTHORITY.items())
    semantic=(str(packet.get("review_id") or "").startswith("selfreview_") and packet.get("phase")=="review_ready"
              and bool(packet.get("source_manifest_digest")) and bool(packet.get("candidate_manifest_digest"))
              and packet.get("active_source_modified") is False and packet.get("candidate_verified") is True
              and isinstance(packet.get("changed_files"), list) and isinstance(packet.get("risks"), list)
              and isinstance(packet.get("unresolved_uncertainty"), list) and packet.get("operator_decision_required") is True)
    ok=digest_ok and authority_ok and semantic
    return {"ok":ok,"status":"operator_review_packet_valid" if ok else "operator_review_packet_invalid","digest_valid":digest_ok,"authority_contained":authority_ok,"semantic_valid":semantic}


def prepare_operator_review_handoff(
    repair_id: str,
    source_root: str | Path,
    *,
    self_modification_runtime_root: str | Path | None,
    test_selection_runtime_root: str | Path | None,
    repair_runtime_root: str | Path | None,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    source=Path(source_root).expanduser().resolve(strict=True)
    repair=load_iterative_self_repair(repair_id, runtime_root=repair_runtime_root)
    if not repair or repair.get("phase")!="passed" or not (repair.get("verification") or {}).get("passed"):
        raise ValueError("verified_v1267_repair_required")
    self_record=load_self_modification(str(repair.get("source_operation_id") or ""), runtime_root=self_modification_runtime_root)
    if not self_record or self_record.get("phase")!="sealed": raise ValueError("sealed_v1265_candidate_required")
    selection=load_test_selection(str(repair.get("selection_id") or ""), runtime_root=test_selection_runtime_root)
    if not selection or not validate_test_selection(selection).get("ok"): raise ValueError("valid_v1266_selection_required")
    workspace=Path(str(self_record.get("workspace_path") or "")).expanduser().resolve(strict=True)
    active_manifest=source_only_manifest(source); candidate_manifest=source_only_manifest(workspace)
    if active_manifest["source_manifest_digest"]!=repair.get("source_manifest_digest"): raise ValueError("operator_review_stale_active_source")
    if candidate_manifest["source_manifest_digest"]!=repair.get("candidate_manifest_digest"): raise ValueError("operator_review_candidate_manifest_mismatch")
    changed=_changed_files(active_manifest,candidate_manifest)
    if not changed: raise ValueError("operator_review_candidate_has_no_changes")
    surfaces=_surface_codes([r["relative_path"] for r in changed]); attempts=list(repair.get("attempts") or [])
    review_id="selfreview_"+hashlib.sha256(f"{repair_id}:{repair.get('record_digest')}:{candidate_manifest['source_manifest_digest']}".encode()).hexdigest()[:24]
    path=_record_path(review_id,runtime_root)
    with _proposal_lock("devc_"+review_id.split("_",1)[1], _runtime_root(runtime_root)):
        existing=_read_json(path)
        if existing:
            if not validate_operator_review_packet(existing).get("ok"): raise ValueError("stored_operator_review_packet_invalid")
            return {**existing,"operation_status":"restored"}
        packet={
            "ok":True,"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"status":"operator_review_handoff_ready","phase":"review_ready",
            "review_id":review_id,"repair_id":repair_id,"source_operation_id":repair.get("source_operation_id",""),"selection_id":repair.get("selection_id",""),
            "source_manifest_digest":active_manifest["source_manifest_digest"],"candidate_manifest_digest":candidate_manifest["source_manifest_digest"],
            "changed_files":changed,"changed_file_count":len(changed),"changed_files_digest":_digest(changed),"affected_surfaces":surfaces,
            "verification":{"passed":True,"selected_test_count":int((repair.get("verification") or {}).get("selected_test_count") or repair.get("selected_test_count") or 0),"test_run_count":int((repair.get("verification") or {}).get("test_run_count") or 0),"result_digest":(repair.get("verification") or {}).get("result_digest",""),"content_minimized":True},
            "repair_history":[{"attempt_number":a.get("attempt_number"),"strategy_code":a.get("strategy_code"),"failure_fingerprint":a.get("failure_fingerprint"),"repair_diff_digest":a.get("repair_diff_digest"),"candidate_manifest_digest":a.get("candidate_manifest_digest"),"content_minimized":True} for a in attempts],
            "risks":_risk_rows(surfaces,attempts,len(changed)),"unresolved_uncertainty":_uncertainty_rows(repair,selection),
            "limitations":["selected_verification_is_bounded_not_exhaustive","native_windows_review_pending","active_update_not_attempted","operator_must_review_changed_paths_and_risks"],
            "rollback_instructions":{"current_state":"active_source_unchanged","abandon_candidate":"discard_disposable_v1265_workspace","active_rollback_needed_now":False,"future_update_requires":"v1269_exact_backup_update_health_verification_and_recovery_authorization"},
            "operator_choices":["approve_for_v1269_consideration","defer","reject"],"operator_decision_required":True,"candidate_verified":True,"active_source_modified":False,"content_minimized":True,
            **REVIEW_DENIED_AUTHORITY,
        }
        packet["record_digest"]=_record_digest(packet); _write_json(path,packet)
        return {**packet,"operation_status":"created"}


def load_operator_review_packet(review_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    return _read_json(_record_path(review_id,runtime_root))


def public_operator_review_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {k:packet.get(k) for k in ("ok","status","phase","review_id","repair_id","source_operation_id","source_manifest_digest","candidate_manifest_digest","changed_files","changed_file_count","affected_surfaces","verification","repair_history","risks","unresolved_uncertainty","limitations","rollback_instructions","operator_choices","operator_decision_required","candidate_verified","active_source_modified","content_minimized")} | REVIEW_DENIED_AUTHORITY


__all__=["CONTRACT_VERSION","REVIEW_DECISIONS","REVIEW_DENIED_AUTHORITY","prepare_operator_review_handoff","load_operator_review_packet","public_operator_review_packet","validate_operator_review_packet","_digest","_record_digest","_record_path","_decision_path","_write_json","_read_json","_runtime_root"]
