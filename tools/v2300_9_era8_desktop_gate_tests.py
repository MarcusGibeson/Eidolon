from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2300-data-")

from audit_incident_governance_v2200 import build_audit_lineage, inspect_incidents, open_incident, validate_audit_lineage
from fine_grained_authority_v2200 import build_permission_policy, evaluate_policy_ceiling, public_policy_state, revoke_policy
from transactional_recovery_v2200 import append_recovery_journal, build_recovery_checkpoint, inspect_recovery_journal
from trust_zone_defense_v2200 import classify_trust_zone

checks: list[str] = []


def require(value: object, name: str) -> None:
    checks.append(name)
    assert value, name


digest = "a" * 64
policy = build_permission_policy(
    policy_id="desktop-gate",
    capability="file_read",
    target_digest=digest,
    scope=["workspace"],
    mode="read_only",
    duration_seconds=60,
    file_budget=1,
    issued_epoch=100,
)
request = {
    "capability": "file_read",
    "target_digest": digest,
    "scope": ["workspace"],
    "environment": "isolated_workspace",
    "effect": "read",
}

bad_usage = evaluate_policy_ceiling(policy, {**request, "files": "not-a-number"}, now_epoch=101)
require(not bad_usage["allowed_by_policy_ceiling"] and "files_usage_invalid" in bad_usage["reason_codes"], "malformed_usage_fails_closed")
nan_usage = evaluate_policy_ceiling(policy, {**request, "files": float("nan")}, now_epoch=101)
require(not nan_usage["allowed_by_policy_ceiling"] and "files_usage_invalid" in nan_usage["reason_codes"], "nonfinite_usage_fails_closed")
nan_time = evaluate_policy_ceiling(policy, {**request, "files": 1}, now_epoch=float("nan"))
require(not nan_time["allowed_by_policy_ceiling"] and "evaluation_time_invalid" in nan_time["reason_codes"], "nonfinite_time_fails_closed")
bad_scope = evaluate_policy_ceiling(policy, {**request, "scope": "workspace", "files": 1}, now_epoch=101)
require(not bad_scope["allowed_by_policy_ceiling"] and "scope_shape_invalid" in bad_scope["reason_codes"], "malformed_scope_fails_closed")

authority_runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2300-authority-"))
revocation = revoke_policy(policy_digest=policy["policy_digest"], reason_code="test", event_id="one", runtime_root=authority_runtime)
require(revocation["ok"], "revocation_fixture_created")
authority_file = authority_runtime / "authority" / "era8_authority_policy.json"
authority_file.write_text("{broken", encoding="utf-8")
corrupt_authority = evaluate_policy_ceiling(policy, {**request, "files": 1}, now_epoch=101, runtime_root=authority_runtime)
require(not corrupt_authority["allowed_by_policy_ceiling"] and "authority_state_integrity_invalid" in corrupt_authority["reason_codes"], "corrupt_authority_state_fails_closed")
require(not public_policy_state(runtime_root=authority_runtime)["ok"], "corrupt_authority_state_visible")
require(not revoke_policy(policy_digest=policy["policy_digest"], reason_code="retry", event_id="two", runtime_root=authority_runtime)["ok"], "corrupt_authority_state_not_overwritten")

receipt_label = classify_trust_zone("web_content", authoritative_receipt=True)
require(receipt_label["treated_as_data"] and not receipt_label["may_define_authority"], "bare_receipt_flag_cannot_launder_web_content")
system_label = classify_trust_zone("system_policy")
require(not system_label["may_define_authority"] and system_label["classification_is_not_authority_validation"], "source_label_is_not_authority_validation")

event = {
    "session_id": "s",
    "event": "result",
    "intent_digest": digest,
    "authority_digest": digest,
    "attempt_digest": digest,
    "result_digest": digest,
    "rollback_digest": "",
    "operator_decision_digest": digest,
    "side_effect_digest": "",
}
lineage = build_audit_lineage([event])
require(validate_audit_lineage(lineage)["ok"], "valid_lineage_accepted")
tampered = copy.deepcopy(lineage)
tampered["event_count"] = 999
tampered["event_digests"] = ["b" * 64]
tampered["lineage_digest"] = "c" * 64
validation = validate_audit_lineage(tampered)
require(not validation["ok"] and {"event_count_mismatch", "event_digests_mismatch", "lineage_digest_mismatch"}.issubset(validation["reason_codes"]), "top_level_audit_tampering_detected")

incident_runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2300-incident-"))
opened = open_incident(incident_id="incident", signals=[{"code": "approval_forgery", "severity": "high"}], event_id="one", runtime_root=incident_runtime)
require(opened["ok"], "incident_fixture_created")
incident_file = incident_runtime / "security" / "era8_incidents.json"
incident_file.write_text("{broken", encoding="utf-8")
require(not inspect_incidents(runtime_root=incident_runtime)["ok"], "corrupt_incident_state_visible")
require(not open_incident(incident_id="incident-two", signals=[], event_id="two", runtime_root=incident_runtime)["ok"], "corrupt_incident_state_not_overwritten")

checkpoint = build_recovery_checkpoint(checkpoint_id="checkpoint", source_manifest_digest=digest)
recovery_runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2300-recovery-"))
entry = append_recovery_journal(operation_id="operation", checkpoint_digest=checkpoint["checkpoint_digest"], signal_digest=digest, runtime_root=recovery_runtime)
require(entry["ok"], "recovery_fixture_created")
recovery_file = recovery_runtime / "recovery" / "era8_recovery_journal.json"
recovery_file.write_text("{broken", encoding="utf-8")
require(not inspect_recovery_journal(runtime_root=recovery_runtime)["ok"], "corrupt_recovery_journal_visible")
require(not append_recovery_journal(operation_id="operation-two", checkpoint_digest=checkpoint["checkpoint_digest"], signal_digest=digest, runtime_root=recovery_runtime)["ok"], "corrupt_recovery_journal_not_overwritten")

for invalid in ("z" * 64, "a" * 63):
    try:
        build_recovery_checkpoint(checkpoint_id="bad", source_manifest_digest=invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("non_hex_recovery_digest_rejected")
require(True, "non_hex_recovery_digest_rejected")

print(json.dumps({"suite": "v2300.9-era8-desktop-gate", "ok": True, "passed": len(checks), "failed": 0, "checks": checks}, sort_keys=True))
