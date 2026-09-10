from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1217-c-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repaired_candidate_apply as repaired_apply
import operator_repair_result_review as result_review
from ordinary_chat_development_campaign import _atomic_json, _read_json
from v1217_repaired_candidate_apply_fixture import (
    build_repaired_candidate_apply_fixture,
    tree_digest,
)

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


def prepare(fixture: dict) -> dict:
    return repaired_apply.prepare_supervised_repaired_candidate_apply(
        fixture["proposal"]["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_apply_proposal_digest=fixture["apply_proposal"]["apply_proposal_digest"],
        runtime_root=fixture["runtime"],
    )


def seed_running(fixture: dict, *, state: str, live: bool = False) -> dict:
    prepared = prepare(fixture)
    require(prepared["ok"] is True, prepared)
    proposal_id = fixture["proposal"]["proposal_id"]
    runtime = fixture["runtime"]
    source_root = fixture["source_workspace_root"]
    repaired_root = fixture["repaired_workspace_root"]
    manifest = repaired_apply._prepare_rollback_manifest(prepared, source_root)
    _atomic_json(repaired_apply._rollback_manifest_path(proposal_id, 1, 2, runtime), manifest)
    auth = repaired_apply._seal({
        "schema_version": repaired_apply.SCHEMA_VERSION,
        "contract_version": repaired_apply.CONTRACT_VERSION,
        "ok": True,
        "status": "supervised_repaired_candidate_apply_authorization_consumed",
        "proposal_id": proposal_id,
        "proposal_revision": 1,
        "failed_attempt_number": 2,
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "supervised_repaired_candidate_apply_digest": prepared["supervised_repaired_candidate_apply_digest"],
        "apply_proposal_digest": prepared["apply_proposal_digest"],
        "authorization_phrase_digest": hashlib.sha256(
            fixture["apply_proposal"]["authorization_phrase"].casefold().encode()
        ).hexdigest(),
        "consumption_count": 1,
        "rollback_manifest_digest": manifest["rollback_manifest_digest"],
    }, "authorization_receipt_digest")
    _atomic_json(repaired_apply._authorization_path(proposal_id, 1, 2, runtime), auth)
    repaired_apply._write_journal(
        repaired_apply._journal_path(proposal_id, 1, 2, runtime),
        proposal_id=proposal_id,
        proposal_revision=1,
        failed_attempt_number=2,
        authorization_receipt_digest=auth["authorization_receipt_digest"],
        phase="applying",
        completed_count=0,
        operation_count=prepared["operation_count"],
    )
    if state == "repaired":
        for row in prepared["operations"]:
            target = source_root / row["relative_path"]
            if row["operation"] == "delete":
                target.unlink(missing_ok=True)
            else:
                target.write_bytes((repaired_root / row["relative_path"]).read_bytes())
    elif state == "conflict":
        (source_root / prepared["operations"][0]["relative_path"]).write_text(
            "private C:\\Users\\Marcus\\external edit\n", encoding="utf-8"
        )
    current = _read_json(repaired_apply._execution_path(proposal_id, 1, 2, runtime))
    current.update({
        "status": "supervised_repaired_candidate_apply_running",
        "phase": "running",
        "lease_token": "lease-token",
        "lease_expires_unix": time.time() + 120 if live else time.time() - 1,
        "authorization_receipt_digest": auth["authorization_receipt_digest"],
        "rollback_manifest_digest": manifest["rollback_manifest_digest"],
        "rollback_prepared": True,
        **repaired_apply._authority(authorized=True),
    })
    current = repaired_apply._seal(
        current, "supervised_repaired_candidate_apply_record_digest"
    )
    _atomic_json(repaired_apply._execution_path(proposal_id, 1, 2, runtime), current)
    return current


def authorize(fixture: dict) -> dict:
    return repaired_apply.authorize_and_apply_repaired_candidate(
        fixture["proposal"]["proposal_id"],
        expected_revision=1,
        expected_failed_attempt_number=2,
        expected_apply_proposal_digest=fixture["apply_proposal"]["apply_proposal_digest"],
        authorization_phrase=fixture["apply_proposal"]["authorization_phrase"],
        runtime_root=fixture["runtime"],
    )


# A live lease blocks a duplicate before any second authorization or write.
fixture = build_repaired_candidate_apply_fixture("c-live")
try:
    before = tree_digest(fixture["source_workspace_root"])
    seed_running(fixture, state="source", live=True)
    blocked = authorize(fixture)
    require(blocked["status"] == "supervised_repaired_candidate_apply_in_progress")
    require(blocked["apply_authorized"] is False)
    require(tree_digest(fixture["source_workspace_root"]) == before)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

# An expired lease with a fully repaired target seals one recovered result and
# never re-enters the write loop.
fixture = build_repaired_candidate_apply_fixture("c-repaired")
try:
    seed_running(fixture, state="repaired")
    recovered = authorize(fixture)
    require(recovered["ok"] is True, recovered)
    require(recovered["status"] == "supervised_repaired_candidate_apply_completed_recovered")
    require(recovered["operation_status"] == "recovered")
    require(recovered["authorization_consumption_count"] == 1)
    require(recovered["recovery_count"] == 1)
    require(recovered["rollback_prepared"] is True)
    require(recovered["rollback_executed"] is False)
    replay = authorize(fixture)
    require(replay["operation_status"] == "resumed")
    require(replay["supervised_repaired_candidate_apply_result_digest"] == recovered["supervised_repaired_candidate_apply_result_digest"])
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

# An expired authorization that never changed the source is recovered by an
# explicit manifest restore and seals a non-success result for operator review.
fixture = build_repaired_candidate_apply_fixture("c-source")
try:
    before = tree_digest(fixture["source_workspace_root"])
    seed_running(fixture, state="source")
    recovered = authorize(fixture)
    require(recovered["ok"] is False)
    require(recovered["status"] == "interrupted_repaired_candidate_apply_recovered_by_rollback")
    require(recovered["rollback_executed"] is True)
    require(recovered["selected_project_modified"] is False)
    require(tree_digest(fixture["source_workspace_root"]) == before)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

# A third-state operator edit blocks recovery and remains untouched.
fixture = build_repaired_candidate_apply_fixture("c-conflict")
try:
    seed_running(fixture, state="conflict")
    target = fixture["source_workspace_root"] / "tool.py"
    conflict_content = target.read_text(encoding="utf-8")
    blocked = authorize(fixture)
    require(blocked["status"] == "supervised_repaired_candidate_apply_recovery_conflict")
    require(target.read_text(encoding="utf-8") == conflict_content)
    require(blocked["rollback_authorized"] is False)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

# Tampered execution and proposal records fail closed before a project write.
fixture = build_repaired_candidate_apply_fixture("c-record-tamper")
try:
    prepared = prepare(fixture)
    path = repaired_apply._execution_path(fixture["proposal"]["proposal_id"], 1, 2, fixture["runtime"])
    row = _read_json(path)
    row["operation_count"] = 9
    _atomic_json(path, row)
    blocked = authorize(fixture)
    require(blocked["status"] == "supervised_repaired_candidate_apply_record_invalid")
    require(blocked["selected_project_modified"] is False)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

fixture = build_repaired_candidate_apply_fixture("c-proposal-tamper")
try:
    path = result_review._apply_proposal_path(
        fixture["proposal"]["proposal_id"], 1, 2, fixture["runtime"]
    )
    row = _read_json(path)
    row["maximum_apply_attempts"] = 2
    _atomic_json(path, row)
    blocked = prepare(fixture)
    require(blocked["status"] == "supervised_repaired_candidate_apply_proposal_invalid")
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

# Candidate changes after preparation are rejected before authorization is
# consumed; private path/error details are reduced to a type-only digest.
fixture = build_repaired_candidate_apply_fixture("c-candidate-tamper")
try:
    prepared = prepare(fixture)
    (fixture["repaired_workspace_root"] / "tool.py").write_text("tampered\n", encoding="utf-8")
    blocked = authorize(fixture)
    require(blocked["status"] == "supervised_repaired_candidate_apply_candidate_changed")
    require(blocked["apply_authorized"] is False)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

fixture = build_repaired_candidate_apply_fixture("c-private")
try:
    with patch.object(
        repaired_apply,
        "_workspace_descriptor",
        side_effect=ValueError("C:\\Users\\Marcus\\secret\\candidate.py"),
    ):
        blocked = prepare(fixture)
    encoded = json.dumps(repaired_apply.public_supervised_repaired_candidate_apply(blocked))
    require(blocked["status"] == "supervised_repaired_candidate_apply_workspace_invalid")
    require(len(blocked["reason"]) == 64)
    require("Marcus" not in encoded)
    require("C:\\Users" not in encoded)
    require("candidate.py" not in encoded)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

# Attempt expansion is recognized as an exact control and rejected rather than
# being reinterpreted as conversation or a second apply.
fixture = build_repaired_candidate_apply_fixture("c-limit")
try:
    expanded = fixture["apply_proposal"]["authorization_phrase"].replace(
        "repair attempt 1.", "repair attempt 2."
    )
    turn = repaired_apply.process_supervised_repaired_candidate_apply_control(
        expanded, runtime_root=fixture["runtime"]
    )
    require(turn["active"] is True)
    require(turn["event"] == "supervised_repaired_candidate_apply_attempt_limit_exceeded")
    require(turn["supervised_repaired_candidate_apply"]["apply_authorized"] is False)
finally:
    shutil.rmtree(fixture["runtime"], ignore_errors=True)

module = (ROOT / "conscious_agent" / "conversational_supervised_repaired_candidate_apply.py").read_text(encoding="utf-8")
require("APPLY_LEASE_SECONDS" in module)
require("supervised_repaired_candidate_apply_recovery_conflict" in module)
require("rollback_manifest_digest" in module)
require('"rollback_authorized": True' not in module)
require('"install_authorized": True' not in module)
require('"promotion_authorized": True' not in module)
require('"release_authorized": True' not in module)
require('"authority_granted": True' not in module)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require(release.count('"v1217.8-supervised-repaired-candidate-apply-reliability"') == 2)
require(release.count("tools/v1217_6_8_supervised_repaired_candidate_apply_reliability_tests.py") == 1)
require("v1217.6-v1217.8 Repaired-Candidate Apply Reliability and Recovery" in metadata)

print(json.dumps({
    "ok": True,
    "version": "1217.8",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "live_duplicate_blocking": True,
    "expired_lease_recovery": True,
    "tamper_and_conflict_rejection": True,
    "private_error_suppression": True,
    "release_authorized": False,
}, sort_keys=True))
