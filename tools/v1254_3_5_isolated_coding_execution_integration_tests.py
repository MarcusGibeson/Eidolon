from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from isolated_coding_execution_foundations import (
    AUTHORITY_STATE,
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    materialize_or_restore_isolated_coding_workspace,
)
from isolated_coding_execution import (
    authorize_and_run_isolated_coding_execution,
    load_isolated_coding_execution,
    load_isolated_coding_review,
    prepare_isolated_coding_execution,
    public_isolated_coding_execution,
    public_isolated_coding_review,
)
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


SOURCE_BEFORE = source_signature()


def make_project(base: Path) -> Path:
    project = base / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="calculator"\nversion="0.1.0"\n', encoding="utf-8")
    (project / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (project / "tests").mkdir()
    (project / "tests" / "test_main.py").write_text(
        "import unittest\n"
        "from main import add, subtract\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n"
        "    def test_subtract(self):\n        self.assertEqual(subtract(7, 2), 5)\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n",
        encoding="utf-8",
    )
    (project / ".env").write_text("SECRET=DO_NOT_EXPOSE\n", encoding="utf-8")
    (project / "data").mkdir()
    (project / "data" / "projects.json").write_text('{"private":true}\n', encoding="utf-8")
    return project


def prepare_request(project: Path, runtime: Path) -> dict:
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction to the calculator while preserving addition.",
        target_project=project,
        requirements=["Add subtract(a, b) and preserve add(a, b)."],
        acceptance_criteria=["add(2,3) is 5", "subtract(7,2) is 5"],
        constraints=["Keep the existing Python layout."],
        prohibited_actions=["Do not install dependencies."],
        expected_artifacts=["Reviewable isolated diff", "Passing tests"],
        verification=["Compile Python", "Run project tests"],
        runtime_root=runtime,
    )
    require(request["ok"], "foundation_request_ready")
    require(inspect_coding_project(request["request_id"], runtime_root=runtime)["ok"], "foundation_inspection_ready")
    require(create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)["ok"], "foundation_plan_ready")
    require(materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)["ok"], "foundation_workspace_ready")
    return request


class RepairingProvider:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, prompt: str) -> str:
        payload = json.loads(prompt)
        self.calls.append(payload)
        authority = payload["authority"]
        attempt = int(authority["attempt"])
        subtract = "return a + b" if attempt == 1 else "return a - b"
        return json.dumps({
            "authority": {
                "request_id": authority["request_id"],
                "execution_digest": authority["execution_digest"],
                "attempt": attempt,
            },
            "files": [{
                "path": "main.py",
                "operation": "modify",
                "content": f"def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    {subtract}\n",
            }],
        })


with tempfile.TemporaryDirectory(prefix="eid-v1254-3-5-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    selected_before = tree_signature(project)
    request = prepare_request(project, runtime)
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    require(prepared["ok"] and prepared["status"] == "isolated_coding_execution_authorization_required", "execution_prepared")
    require(prepared["authorization_phrase"].startswith("Authorize isolated coding execution for request "), "exact_authorization_phrase_emitted")
    require(prepared["implementation_execution_authorized"] is False and prepared["source_application_authorized"] is False, "preparation_does_not_grant_execution_or_apply")

    provider = RepairingProvider()
    wrong = authorize_and_run_isolated_coding_execution(
        request["request_id"],
        expected_execution_digest="0" * 64,
        authorization_phrase=prepared["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(wrong["status"] == "isolated_coding_execution_stale_authorization", "stale_execution_authorization_rejected")
    require(len(provider.calls) == 0, "provider_not_contacted_on_stale_authorization")

    result = authorize_and_run_isolated_coding_execution(
        request["request_id"],
        expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(result["ok"] and result["status"] == "isolated_coding_execution_completed", "isolated_execution_completed")
    require(result["attempt_count"] == 2 and result["repair_attempt_count"] == 1, "failed_attempt_repaired_once")
    require(len(provider.calls) == 2, "provider_called_once_per_required_attempt")
    require(provider.calls[0]["mode"] == "initial_implementation" and provider.calls[1]["mode"] == "repair_failed_isolated_attempt", "provider_repair_mode_bounded")
    require(result["tests_executed"] and result["test_passed"] and result["cleanup_confirmed"], "bounded_tests_pass_after_repair")
    require(result["reviewable_diff_available"] and result["changed_file_count"] == 1, "reviewable_diff_ready")
    require(tree_signature(project) == selected_before, "selected_project_remains_immutable")
    require((project / "main.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n", "selected_project_content_unchanged")
    require((project / ".env").read_text(encoding="utf-8").startswith("SECRET="), "private_selected_data_unchanged")

    sealed = load_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    require(sealed["phase"] == "sealed" and sealed["execution_authority_consumed"] is True, "execution_authority_consumed_and_sealed")
    for key, expected in AUTHORITY_STATE.items():
        require(sealed.get(key) is expected, f"sealed_{key}_denied")
    public = public_isolated_coding_execution(sealed)
    require(public["source_application_authorized"] is False and public["release_authorized"] is False, "public_result_apply_release_denied")
    require(public["private_path_exposed"] is False and public["private_content_exposed"] is False, "public_execution_projection_private_safe")

    review = load_isolated_coding_review(request["request_id"], runtime_root=runtime)
    require(review["ok"] and review["source_fresh_at_review"], "review_source_fresh")
    require("subtract" in review["diff"] and "SECRET" not in review["diff"] and "projects.json" not in review["diff"], "review_diff_relevant_and_private_safe")
    public_review = public_isolated_coding_review(review)
    require(public_review["changed_paths"] == ["main.py"] and public_review["diff_exposed"] is False, "public_review_minimized")
    operator_review = public_isolated_coding_review(review, include_diff=True)
    require("subtract" in operator_review["diff"], "operator_review_diff_available")

    replay = authorize_and_run_isolated_coding_execution(
        request["request_id"],
        expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(replay["operation_status"] == "restored" and replay["execution_result_digest"] == result["execution_result_digest"], "execution_replay_idempotent")
    require(len(provider.calls) == 2, "execution_replay_does_not_recontact_provider")

# Stale selected source blocks execution before provider contact.
with tempfile.TemporaryDirectory(prefix="eid-v1254-3-5-stale-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    request = prepare_request(project, runtime)
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    (project / "main.py").write_text("VALUE = 'operator changed source'\n", encoding="utf-8")
    provider = RepairingProvider()
    stale = authorize_and_run_isolated_coding_execution(
        request["request_id"],
        expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(stale["status"] == "stale_source_detected", "stale_source_blocks_execution")
    require(len(provider.calls) == 0, "stale_source_blocks_provider_contact")

# Ordinary-chat integration bridges an approved selected-project proposal into
# the new isolated execution rather than requiring a parallel UI/product.
with tempfile.TemporaryDirectory(prefix="eid-v1254-3-5-chat-") as directory:
    base = Path(directory)
    runtime = base / "runtime"
    project = make_project(base)
    selected_before = tree_signature(project)
    projection = {"grounding": {"grounding_status": "matched", "capability_id": "software_development"}, "intent": {"category": "action_request"}}
    created = process_ordinary_chat_development_turn(
        "Add subtraction to this calculator and keep addition working.",
        action_projection=projection,
        session_id="fixture-session",
        project_state={"id": "calculator", "name": "Calculator", "path": str(project)},
        runtime_root=runtime,
    )
    require(created["active"] and created["event"] == "proposal_created", "ordinary_chat_development_request_recognized")
    proposal = created["proposal"]
    approved = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",
        runtime_root=runtime,
        python_executable=sys.executable,
    )
    require(approved["event"] == "approval_consumed", "ordinary_chat_proposal_approval_consumed")
    isolated = approved.get("isolated_coding_execution") or {}
    require(isolated.get("status") == "isolated_coding_execution_authorization_required", "approved_selected_project_bridged_to_isolated_execution")
    require("Authorize isolated coding execution" in approved["conversation_response"], "ordinary_chat_exposes_exact_execution_control")
    provider = RepairingProvider()
    executed = process_ordinary_chat_development_turn(
        isolated["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(executed["event"] == "isolated_coding_execution_completed", "ordinary_chat_exact_execution_control_runs")
    require(executed["isolated_coding_execution"]["test_passed"] is True, "ordinary_chat_execution_returns_passing_evidence")
    require(tree_signature(project) == selected_before, "ordinary_chat_execution_never_modifies_selected_project")
    require("application" in executed["conversation_response"].casefold() and "not modified" in executed["conversation_response"].casefold(), "ordinary_chat_response_preserves_apply_boundary")

require(source_signature() == SOURCE_BEFORE, "eidolon_source_immutable_during_bundle_b_suite")

report = {
    "ok": True,
    "suite": "v1254.3-v1254.5-isolated-coding-execution-integration",
    "passed": len(CHECKS),
    "total": len(CHECKS),
    "checks": CHECKS,
    "native_provider_contacted": False,
    "selected_project_modified": False,
    "source_application_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}
print(json.dumps(report, indent=2 if "--json" in sys.argv else None, sort_keys=True))
