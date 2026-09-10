from __future__ import annotations
"""v1299.6-v1299.8 reliability audit for the final supervised rehearsal."""
from typing import Any, Mapping
from supervised_autonomy_rehearsal_foundations import DENIED_AUTHORITY, REAL_DEFECT_AFFECTED_PATHS, REHEARSAL_STAGES, digest, valid_digest

CONTRACT_VERSION = "v1299.8"


def audit_supervised_rehearsal(result: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(result)
    findings: list[str] = []
    stages = list(row.get("stage_sequence") or [])
    if stages != list(REHEARSAL_STAGES):
        findings.append("stage_sequence_not_complete")
    if tuple(sorted(row.get("affected_paths") or [])) != tuple(sorted(REAL_DEFECT_AFFECTED_PATHS)):
        findings.append("real_defect_scope_changed")
    checks = row.get("repaired_consumer_checks") or {}
    if set(checks) != {"canary_observation_resealed", "recovery_trigger_resealed", "maintenance_event_resealed"} or not all(bool(v) for v in checks.values()):
        findings.append("integrity_repair_incomplete")
    if row.get("active_installation_modified") is not False:
        findings.append("active_installation_modified")
    if row.get("exact_v1269_update_authorization_consumed") is not False:
        findings.append("update_authorization_consumed_during_rehearsal")
    if row.get("generic_authorization_phrase_is_sufficient") is not False:
        findings.append("generic_authorization_expansion")
    if any(bool(row.get(k)) for k in DENIED_AUTHORITY):
        findings.append("authority_expansion")
    if str(row.get("native_windows_status") or "") not in {"pending", "unavailable"}:
        findings.append("native_windows_false_pass")
    if not valid_digest(row.get("rehearsal_digest")):
        findings.append("rehearsal_digest_missing")
    else:
        payload = {k: v for k, v in row.items() if k != "rehearsal_digest"}
        if row.get("rehearsal_digest") != digest(payload):
            findings.append("rehearsal_digest_mismatch")
    ok = bool(row.get("ok")) and not findings and not row.get("integrity_violations")
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": ok,
        "status": "supervised_autonomy_rehearsal_reliable" if ok else "supervised_autonomy_rehearsal_reliability_blocked",
        "findings": findings,
        "native_windows_rehearsal_pending": True,
        "operator_controls_preserved": all(bool(row.get(k)) for k in (
            "operator_may_inspect", "operator_may_defer", "operator_may_reject", "operator_may_cancel",
            "operator_may_request_separately_governed_rollback",
        )),
        "content_free": True,
        "read_only": True,
        **DENIED_AUTHORITY,
    }
