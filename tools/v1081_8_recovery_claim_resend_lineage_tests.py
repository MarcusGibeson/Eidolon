from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import conversation_operations as ops
import conversation_resend_lineage as lineage
import conversation_retry_evidence as retry_evidence
import post_review_development_verify as isolated_verify
import release_metadata

SESSION_ID = "conversation_session_20260719T120000_abcdef1234"
SOURCE_KEY = "chat_accept_source_12345678"
RESEND_KEY = "chat_accept_resend_12345678"
OTHER_RESEND_KEY = "chat_accept_other_12345678"
OPERATION_ID = "conversation_20260719T120000_123456789abc"


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class IsolatedRuntime:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1081-8-")
        base = Path(self.temp.name)
        ops.CONVERSATION_OPERATION_DIR = base / "conversation_runtime" / "operations"
        ops.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR = base / "conversation_runtime" / "operation_acknowledgements"
        retry_evidence.CONVERSATION_RETRY_EVIDENCE_DIR = base / "conversation_runtime" / "retry_evidence"
        lineage.CONVERSATION_RESEND_LINEAGE_DIR = base / "conversation_runtime" / "resend_lineage"
        self.base = base

    def evidence(self) -> dict:
        return retry_evidence.persist_non_acceptance_evidence(
            SESSION_ID, SOURCE_KEY, reason="acceptance_validation_failed"
        )

    def close(self) -> None:
        self.temp.cleanup()


def test_release_metadata_reaches_v1081_8() -> None:
    require(tuple(map(int, release_metadata.RUNTIME_VERSION.split("."))) >= (1081, 8), "runtime predates v1081.8")
    require("v1081.8" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1081.8 history missing")


def test_non_acceptance_evidence_has_stable_content_free_token() -> None:
    runtime = IsolatedRuntime()
    try:
        first = runtime.evidence()
        second = retry_evidence.load_non_acceptance_evidence(SESSION_ID, SOURCE_KEY)
        require(first["evidence_token"] == second["evidence_token"], "evidence token is not stable")
        forbidden = {"message", "user_message", "assistant_response", "prompt", "provider_payload", "credentials"}
        require(not (forbidden & set(first)), "non-acceptance evidence leaked private fields")
    finally:
        runtime.close()


def test_unclaimed_candidate_requires_one_fresh_identity() -> None:
    runtime = IsolatedRuntime()
    try:
        runtime.evidence()
        candidate = lineage.resend_candidate_for_session(SESSION_ID)
        require(candidate and candidate["claim_state"] == "unclaimed", "unclaimed candidate missing")
        require(candidate["fresh_acceptance_identity_required"] is True, "fresh identity requirement missing")
        require(candidate["automatic_resend"] is False, "automatic resend was enabled")
    finally:
        runtime.close()


def test_claim_binds_source_to_fresh_identity() -> None:
    runtime = IsolatedRuntime()
    try:
        evidence = runtime.evidence()
        claim = lineage.claim_explicit_resend(
            SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token=evidence["evidence_token"]
        )
        require(claim["state"] == "claimed", "resend claim not persisted")
        require(claim["source_acceptance_key"] == SOURCE_KEY, "source lineage missing")
        require(claim["resend_acceptance_key"] == RESEND_KEY, "resend identity missing")
        require(claim["resume_same_acceptance_identity"] is True, "interrupted claim cannot resume")
    finally:
        runtime.close()


def test_same_claim_is_idempotent() -> None:
    runtime = IsolatedRuntime()
    try:
        evidence = runtime.evidence()
        lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token=evidence["evidence_token"])
        duplicate = lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token=evidence["evidence_token"])
        require(duplicate["duplicate_claim"] is True, "duplicate claim not identified")
        require(duplicate["resend_acceptance_key"] == RESEND_KEY, "duplicate changed acceptance identity")
    finally:
        runtime.close()


def test_competing_identity_is_rejected() -> None:
    runtime = IsolatedRuntime()
    try:
        evidence = runtime.evidence()
        lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token=evidence["evidence_token"])
        try:
            lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, OTHER_RESEND_KEY, source_evidence_token=evidence["evidence_token"])
        except ValueError as error:
            require("another resend identity" in str(error), "wrong competing-claim error")
        else:
            raise AssertionError("competing resend identity was accepted")
    finally:
        runtime.close()


def test_stale_evidence_token_is_rejected() -> None:
    runtime = IsolatedRuntime()
    try:
        runtime.evidence()
        try:
            lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token="0" * 64)
        except ValueError as error:
            require("evidence changed" in str(error), "wrong stale evidence error")
        else:
            raise AssertionError("stale evidence token was accepted")
    finally:
        runtime.close()


def test_accepted_original_blocks_resend_claim() -> None:
    runtime = IsolatedRuntime()
    try:
        evidence = runtime.evidence()
        ops.create_operation_marker(OPERATION_ID, SESSION_ID, acceptance_key=SOURCE_KEY)
        try:
            lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token=evidence["evidence_token"])
        except ValueError as error:
            require("original request is accepted" in str(error), "wrong accepted-source error")
        else:
            raise AssertionError("accepted source was allowed to resend")
    finally:
        runtime.close()


def test_finalization_binds_accepted_operation() -> None:
    runtime = IsolatedRuntime()
    try:
        evidence = runtime.evidence()
        lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token=evidence["evidence_token"])
        ops.create_operation_marker(OPERATION_ID, SESSION_ID, acceptance_key=RESEND_KEY)
        final = lineage.finalize_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, OPERATION_ID)
        require(final["state"] == "accepted", "lineage did not finalize")
        require(final["operation_id"] == OPERATION_ID, "accepted operation missing")
        require(lineage.resend_candidate_for_session(SESSION_ID) is None, "accepted lineage remains resendable")
    finally:
        runtime.close()


def test_interrupted_claim_restores_same_acceptance_identity() -> None:
    runtime = IsolatedRuntime()
    try:
        evidence = runtime.evidence()
        lineage.claim_explicit_resend(SESSION_ID, SOURCE_KEY, RESEND_KEY, source_evidence_token=evidence["evidence_token"])
        candidate = lineage.resend_candidate_for_session(SESSION_ID)
        require(candidate and candidate["claim_pending"] is True, "pending claim not restored")
        require(candidate["resend_acceptance_key"] == RESEND_KEY, "reload would create another identity")
        require(candidate["resume_same_acceptance_identity"] is True, "same-identity resume missing")
    finally:
        runtime.close()


def test_cross_process_competing_claim_is_exactly_once() -> None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-8-cross-") as raw:
        data = Path(raw)
        retry_dir = data / "conversation_runtime" / "retry_evidence"
        operation_dir = data / "conversation_runtime" / "operations"
        acknowledgement_dir = data / "conversation_runtime" / "operation_acknowledgements"
        old_retry, old_ops, old_ack, old_lineage = (
            retry_evidence.CONVERSATION_RETRY_EVIDENCE_DIR,
            ops.CONVERSATION_OPERATION_DIR,
            ops.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR,
            lineage.CONVERSATION_RESEND_LINEAGE_DIR,
        )
        try:
            retry_evidence.CONVERSATION_RETRY_EVIDENCE_DIR = retry_dir
            ops.CONVERSATION_OPERATION_DIR = operation_dir
            ops.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR = acknowledgement_dir
            lineage.CONVERSATION_RESEND_LINEAGE_DIR = data / "conversation_runtime" / "resend_lineage"
            evidence = retry_evidence.persist_non_acceptance_evidence(SESSION_ID, SOURCE_KEY)
            env = dict(os.environ)
            env["EIDOLON_DATA_DIR"] = str(data)
            base = [sys.executable, str(TOOLS / "conversation_resend_lineage_claim_worker.py"), "--session-id", SESSION_ID, "--source-key", SOURCE_KEY, "--evidence-token", evidence["evidence_token"]]
            processes = [
                subprocess.Popen(base + ["--resend-key", RESEND_KEY], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env),
                subprocess.Popen(base + ["--resend-key", OTHER_RESEND_KEY], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env),
            ]
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=30)
                require(stdout.strip(), f"claim worker produced no report: {stderr}")
                results.append(json.loads(stdout))
            require(sum(bool(item.get("ok")) for item in results) == 1, f"cross-process claims did not choose one winner: {results}")
            stored = lineage.load_resend_lineage(SESSION_ID, SOURCE_KEY)
            require(stored and stored["resend_acceptance_key"] in {RESEND_KEY, OTHER_RESEND_KEY}, "winning lineage missing")
            require(not list((data / "conversation_runtime" / "resend_lineage" / SESSION_ID).glob("*.lock")), "claim lock leaked")
        finally:
            retry_evidence.CONVERSATION_RETRY_EVIDENCE_DIR = old_retry
            ops.CONVERSATION_OPERATION_DIR = old_ops
            ops.CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR = old_ack
            lineage.CONVERSATION_RESEND_LINEAGE_DIR = old_lineage


def test_dashboard_wires_lineage_without_automatic_send() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    dashboard = (AGENT / "dashboard.py").read_text(encoding="utf-8")
    require("resend_source_acceptance_key" in source and "resend_evidence_token" in source, "stream does not carry lineage proof")
    require("claim_explicit_resend" in source and "finalize_explicit_resend" in source, "server operation path omits lineage claim")
    require("Review restored draft" in source, "explicit review control missing")
    require("automaticResend = 'false'" in source, "automatic resend boundary missing")
    require("resend_source_acceptance_key=str(body.get" in dashboard, "dashboard endpoint drops lineage fields")


def test_core_and_release_registration() -> None:
    selected = {suite.name for suite in isolated_verify.select_suites("core")}
    require("v1081.8-recovery-claim-lineage" in selected, "v1081.8 absent from core profile")
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(source.count("tools/v1081_8_recovery_claim_resend_lineage_tests.py") == 1, "v1081.8 release registration count wrong")


def test_source_only_privacy() -> None:
    require(not (ROOT / "data/projects.json").exists(), "data/projects.json present")
    forbidden = (
        "data/conversation_runtime", "data/conversation_sessions", "data/dashboard_chat", "data/approvals",
        "data/tasks.json", "data/memories.json", ".venv",
    )
    paths = [
        path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ]
    for token in forbidden:
        require(not any(token in path for path in paths), f"forbidden runtime path {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = tuple(
    (name[5:], value) for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1081.8-recovery-claim-resend-lineage",
        "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed, "total": len(TESTS), "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
