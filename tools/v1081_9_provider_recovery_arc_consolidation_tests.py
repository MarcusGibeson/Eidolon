from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import conversation_recovery_contract as contract
import conversation_resend_lineage as lineage
import dashboard_chat_console
import post_review_development_verify as isolated_verify
import release_metadata

SESSION_ID = "conversation_session_20260719T120000_abcdef1234"
OPERATION_ID = "conversation_20260719T120000_123456789abc"


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class ContractPatch:
    def __init__(self, *, marker=None, recovery=None, candidate=None, provider=None) -> None:
        self.original = (
            contract.latest_operation_marker,
            contract.recovery_state,
            contract.resend_candidate_for_session,
            contract.provider_resume_cue,
        )
        contract.latest_operation_marker = lambda _session: marker
        contract.recovery_state = lambda _session, _operation: recovery
        contract.resend_candidate_for_session = lambda _session: candidate
        contract.provider_resume_cue = lambda: provider or {"visible": False, "state": "unknown", "can_resume_composition": False}

    def close(self) -> None:
        (
            contract.latest_operation_marker,
            contract.recovery_state,
            contract.resend_candidate_for_session,
            contract.provider_resume_cue,
        ) = self.original


def test_release_metadata_closes_v1081_arc() -> None:
    current = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current >= (1081, 9), "runtime regressed below v1081.9")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1081.9 Provider Recovery Arc Consolidation" in history, "v1081.9 arc history missing")
    require("v1081.8" in history, "v1081.8 lineage history missing")


def test_accepted_running_contract_never_replays() -> None:
    patch = ContractPatch(marker={"operation_id": OPERATION_ID, "public_state": "running"})
    try:
        value = contract.conversation_recovery_contract(SESSION_ID)
        require(value["state"] == "accepted_reconciling", "running accepted state mismatch")
        require(value["acceptance_proven"] is True, "accepted state not proven")
        require(value["provider_request_replayed"] is False, "accepted request replay enabled")
    finally:
        patch.close()


def test_accepted_failure_uses_linked_recovery_vocabulary() -> None:
    marker = {"operation_id": OPERATION_ID, "public_state": "failed", "final_session_turn_recorded": True}
    patch = ContractPatch(marker=marker, recovery={"retryable": True, "successful_recovery_turn_id": ""})
    try:
        value = contract.conversation_recovery_contract(SESSION_ID)
        require(value["state"] == "accepted_recovery_available", "accepted recovery state mismatch")
        require(value["action"] == "linked_recovery", "linked recovery action missing")
        require(value["explicit_resend"] is False, "accepted failure exposed resend")
    finally:
        patch.close()


def test_successful_linked_recovery_is_canonical() -> None:
    marker = {"operation_id": OPERATION_ID, "public_state": "failed", "final_session_turn_recorded": True}
    patch = ContractPatch(marker=marker, recovery={"retryable": False, "successful_recovery_turn_id": "conversation_recovery"})
    try:
        value = contract.conversation_recovery_contract(SESSION_ID)
        require(value["state"] == "accepted_recovered", "successful recovery state mismatch")
        require("not replayed" in value["detail"], "no-replay explanation missing")
    finally:
        patch.close()


def test_unclaimed_resend_contract_is_explicit_only() -> None:
    candidate = {"resend_allowed": True, "claim_pending": False}
    patch = ContractPatch(candidate=candidate)
    try:
        value = contract.conversation_recovery_contract(SESSION_ID)
        require(value["state"] == "explicit_resend_available", "explicit resend state mismatch")
        require(value["action"] == "review_draft", "draft review action missing")
        require(value["automatic_resend"] is False, "automatic resend enabled")
    finally:
        patch.close()


def test_interrupted_resend_contract_resumes_same_claim() -> None:
    candidate = {"resend_allowed": True, "claim_pending": True}
    patch = ContractPatch(candidate=candidate)
    try:
        value = contract.conversation_recovery_contract(SESSION_ID)
        require(value["state"] == "explicit_resend_claimed", "pending resend state mismatch")
        require("same claimed acceptance identity" in value["detail"], "same-identity resume not explained")
    finally:
        patch.close()


def test_provider_unavailable_contract_preserves_truth() -> None:
    provider = {
        "visible": True,
        "state": "temporarily_unavailable",
        "can_resume_composition": False,
        "label": "Configured provider temporarily unavailable",
        "detail": "Generation is unavailable. Local history and drafts still work.",
    }
    patch = ContractPatch(provider=provider)
    try:
        value = contract.conversation_recovery_contract(SESSION_ID)
        require(value["state"] == "provider_unavailable", "provider state mismatch")
        require(value["provider_state"] == "temporarily_unavailable", "provider detail lost")
        require(value["action"] == "check_provider", "manual provider check action missing")
    finally:
        patch.close()


def test_verified_provider_return_does_not_claim_replay() -> None:
    provider = {"visible": True, "state": "ready", "can_resume_composition": True}
    patch = ContractPatch(provider=provider)
    try:
        value = contract.conversation_recovery_contract(SESSION_ID)
        require(value["state"] == "provider_recovered", "verified provider return missing")
        require(value["provider_request_replayed"] is False, "provider return claimed replay")
    finally:
        patch.close()


def test_contract_and_lineage_are_content_free() -> None:
    value = contract._contract(SESSION_ID, "ready", "Ready", "No recovery needed")
    require(contract.recovery_contract_contains_private_fields(value) is False, "contract privacy checker failed")
    sample = {
        "type": "conversation_resend_lineage", "session_id": SESSION_ID,
        "source_acceptance_key": "chat_accept_source_12345678",
        "resend_acceptance_key": "chat_accept_resend_12345678", "state": "claimed",
    }
    require(lineage.resend_lineage_contains_private_fields(sample) is False, "lineage privacy checker failed")
    require(lineage.resend_lineage_contains_private_fields({**sample, "user_message": "private"}) is True, "lineage private field not detected")


def test_chat_snapshot_and_operation_share_contract() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require(source.count('"recovery_contract": conversation_recovery_contract') >= 2, "snapshot and operation do not share the contract")
    require("applyRecoveryContract(snapshot.recovery_contract || null)" in source, "restored snapshot does not apply contract")
    require("payload && payload.recovery_contract" in source, "operation reconciliation does not apply contract")


def test_attention_center_uses_canonical_contract() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("contract = conversation_recovery_contract(session_id)" in source, "attention center ignores recovery contract")
    require('kind = "conversation_recovery"' in source, "canonical recovery attention kind missing")


def test_local_ui_is_not_presented_as_model_output() -> None:
    source = (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")
    require("deterministic local notices are not model responses" in source, "local/model distinction missing")
    require("chat-recovery-contract" in source, "dedicated operational recovery surface missing")
    require("appendExplicitResendPresentation" in source and "Review restored draft" in source, "explicit resend presentation missing")


def test_rendered_javascript_syntax() -> None:
    html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    expected = f"data-chat-version='{release_metadata.RUNTIME_VERSION_TAG}-{release_metadata.RUNTIME_UI_CONTRACT}'"
    require(expected in html, "rendered current UI contract mismatch")
    require("chat-recovery-contract" in html, "v1081.9 canonical recovery surface missing")
    scripts = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "unclosed rendered script")
        scripts.append(html[start + len("<script>"):end])
        cursor = end + len("</script>")
    require(scripts, "no rendered JavaScript found")
    node = shutil.which("node")
    if not node:
        return
    with tempfile.TemporaryDirectory(prefix="eidolon-v1081-9-js-") as raw:
        for index, script in enumerate(scripts):
            path = Path(raw) / f"script-{index}.js"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
            require(result.returncode == 0, result.stderr or "rendered JavaScript syntax failed")


def test_narrow_layout_contains_recovery_surfaces() -> None:
    styles = dashboard_chat_console.COMPANION_CHAT_STYLES
    require(".chat-recovery-contract" in styles, "recovery contract style missing")
    require("overflow-wrap:anywhere" in styles, "recovery text can overflow")
    require(".chat-explicit-resend-presentation > *" in styles, "narrow resend controls do not wrap")


def test_profile_and_release_registration() -> None:
    core = {suite.name for suite in isolated_verify.select_suites("core")}
    require("v1081.9-provider-recovery-arc-consolidation" in core, "v1081.9 absent from core")
    require("v1081.8-recovery-claim-lineage" in core, "v1081.8 retained suite missing")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(release_source.count("tools/v1081_9_provider_recovery_arc_consolidation_tests.py") == 1, "v1081.9 release registration wrong")
    require(release_source.count("tools/v1081_8_recovery_claim_resend_lineage_tests.py") == 1, "v1081.8 release registration wrong")


def test_docs_workspace_and_privacy() -> None:
    for relative in (
        "README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md",
        "data/settings.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ):
        require((ROOT / relative).exists(), f"{relative} missing")
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("# v1081.9 Provider Recovery Arc Consolidation" in history, "v1081.9 history missing")
    require("v1081.8" in history and "v1081.7" in history, "arc history was not retained")
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
        "suite": "v1081.9-provider-recovery-arc-consolidation",
        "ok": passed == len(TESTS), "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed, "total": len(TESTS), "checks": checks,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
