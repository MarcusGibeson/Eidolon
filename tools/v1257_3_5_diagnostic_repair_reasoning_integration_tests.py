from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from diagnostic_repair_reasoning import public_diagnostic_result
from diagnostic_repair_reasoning_foundations import DENIED_AUTHORITY, load_diagnostic_plan, load_diagnostic_result
from isolated_coding_execution import authorize_and_run_isolated_coding_execution, load_isolated_coding_review, prepare_isolated_coding_execution
from isolated_coding_execution_foundations import (
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    materialize_or_restore_isolated_coding_workspace,
)
from persistent_development_sessions_foundations import (
    create_or_restore_persistent_development_session,
    refresh_persistent_development_session,
)
from v1255_test_support import make_project, tree_signature

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel or rel.endswith((".pyc", ".pyo")) or rel.startswith("data/"):
            continue
        rows.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def prepare(project: Path, runtime: Path) -> tuple[dict, dict]:
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add subtract(a,b).", "Preserve add(a,b)."],
        acceptance_criteria=["subtract(7,2) is 5", "add(2,3) is 5"],
        constraints=["Keep current Python layout."],
        prohibited_actions=["Do not install dependencies."],
        assumptions=["Existing tests are authoritative."],
        expected_artifacts=["Reviewable diff", "Passing tests"],
        verification=["Compile Python", "Run project tests"],
        runtime_root=runtime,
    )
    assert inspect_coding_project(request["request_id"], runtime_root=runtime)["ok"]
    assert create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)["ok"]
    assert materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)["ok"]
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    assert prepared["ok"]
    return request, prepared


class DiagnosticAwareProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.prompts: list[dict] = []

    def __call__(self, prompt: str) -> str:
        payload = json.loads(prompt)
        self.calls += 1
        self.prompts.append(payload)
        authority = payload["authority"]
        if self.calls == 1:
            body = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a + b\n"
        else:
            diagnostic = payload.get("previous_outcome", {}).get("diagnostic_context", {})
            if diagnostic.get("repair_posture") != "repair_supported" or diagnostic.get("preferred_hypothesis_code") != "implementation_behavior_defect":
                raise AssertionError("repair prompt missing diagnostic reasoning")
            body = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
        return json.dumps({
            "authority": {
                "request_id": authority["request_id"],
                "execution_digest": authority["execution_digest"],
                "attempt": authority["attempt"],
            },
            "files": [{"path": "main.py", "operation": "modify", "content": body}],
        })


class CapabilityBlockedProvider:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        payload = json.loads(prompt); self.calls += 1
        authority = payload["authority"]
        body = "import socket\n\ndef add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
        return json.dumps({
            "authority": {"request_id": authority["request_id"], "execution_digest": authority["execution_digest"], "attempt": authority["attempt"]},
            "files": [{"path": "main.py", "operation": "modify", "content": body}],
        })


SOURCE_BEFORE = source_signature()
with tempfile.TemporaryDirectory(prefix="eid-v1257-3-5-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base)
    project_before = tree_signature(project)
    request, prepared = prepare(project, runtime)
    session = create_or_restore_persistent_development_session(request["request_id"], runtime_root=runtime)
    provider = DiagnosticAwareProvider()
    result = authorize_and_run_isolated_coding_execution(
        request["request_id"],
        expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(result["ok"] and result["status"] == "isolated_coding_execution_completed", "failed_attempt_diagnosed_then_repaired_successfully")
    require(result["attempt_count"] == 2 and result["repair_attempt_count"] == 1, "exactly_one_repair_attempt_needed")
    require(result["diagnostic_cycle_count"] == 1 and result["diagnostic_reasoning_used"] is True, "one_diagnostic_cycle_recorded")
    require(provider.calls == 2, "one_initial_and_one_repair_provider_call")
    require(provider.prompts[0]["mode"] == "initial_implementation" and provider.prompts[1]["mode"] == "repair_failed_isolated_attempt", "provider_modes_distinguish_initial_and_repair")
    diagnostic_context = provider.prompts[1]["previous_outcome"]["diagnostic_context"]
    require(diagnostic_context["repair_posture"] == "repair_supported", "repair_prompt_receives_supported_posture")
    require(diagnostic_context["preferred_hypothesis_code"] == "implementation_behavior_defect", "repair_prompt_receives_best_supported_hypothesis")
    require(len(diagnostic_context["failing_test_path_digests"]) == 1, "repair_prompt_receives_content_free_failing_test_identity")
    require(diagnostic_context["raw_test_output_included"] is False and "AssertionError" not in json.dumps(diagnostic_context), "repair_prompt_excludes_raw_test_output")
    require(all("output_digest" in row for row in diagnostic_context["probe_outcomes"] if row["probe_code"] == "individual_test_file_isolation"), "focused_diagnostic_uses_output_digests")

    plan = load_diagnostic_plan(request["request_id"], 1, runtime_root=runtime)
    diagnosis = load_diagnostic_result(request["request_id"], 1, runtime_root=runtime)
    require(plan["diagnostic_plan_digest"] == diagnostic_context["diagnostic_result_digest"] or bool(plan["diagnostic_plan_digest"]), "diagnostic_plan_persisted")
    require(diagnosis["repair_supported"] and diagnosis["preferred_hypothesis_code"] == "implementation_behavior_defect", "diagnostic_result_persisted")
    require(any(row["probe_code"] == "individual_test_file_isolation" and row["passed"] is False for row in diagnosis["probe_results"]), "focused_test_failure_reproduced")
    require(any(row["probe_code"] == "changed_source_syntax_guard" and row["passed"] is True for row in diagnosis["probe_results"]), "syntax_explanation_disproved_before_behavior_repair")
    require(diagnosis["root_cause_proven"] is False, "diagnosis_remains_calibrated_not_proven")
    public = public_diagnostic_result(diagnosis)
    for key, expected in DENIED_AUTHORITY.items():
        require(public.get(key) is expected, f"diagnostic_result_{key}_denied")
    require(public["raw_test_output_exposed"] is False and public["raw_provider_output_exposed"] is False, "public_diagnosis_content_minimized")

    refreshed = refresh_persistent_development_session(session["session_id"], runtime_root=runtime)
    evidence = refreshed["snapshot"]["attempt_evidence"]
    require(evidence[0]["diagnostic_result_digest"] == diagnosis["diagnostic_result_digest"], "persistent_session_links_diagnostic_evidence")
    require(evidence[0]["diagnostic_repair_posture"] == "repair_supported", "persistent_session_preserves_repair_posture")
    require(evidence[0]["diagnostic_preferred_hypothesis"] == "implementation_behavior_defect", "persistent_session_preserves_preferred_hypothesis")
    require(evidence[0]["passed"] is False and evidence[1]["passed"] is True, "session_preserves_failed_then_passing_attempts")
    require(tree_signature(project) == project_before, "diagnosis_and_repair_remain_in_disposable_workspace")
    review = load_isolated_coding_review(request["request_id"], runtime_root=runtime)
    require(review["ok"] and review["reviewable_diff_available"] and review["source_fresh_at_review"], "repaired_candidate_still_requires_operator_review")

# A capability/environment blocker stops after the initial provider attempt and does not
# waste the remaining repair budget on code changes.
with tempfile.TemporaryDirectory(prefix="eid-v1257-3-5-blocked-") as directory:
    base = Path(directory); runtime = base / "runtime"; project = make_project(base)
    project_before = tree_signature(project)
    request, prepared = prepare(project, runtime)
    provider = CapabilityBlockedProvider()
    result = authorize_and_run_isolated_coding_execution(
        request["request_id"], expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
        provider_generate=provider, python_executable=sys.executable,
    )
    require(result["ok"] is False and "blocked_environment" in result["status"], "environment_capability_failure_becomes_genuine_blocker")
    require(result["attempt_count"] == 1 and provider.calls == 1, "environment_blocker_does_not_burn_repair_attempts")
    require(result["diagnostic_cycle_count"] == 1, "blocked_failure_still_has_diagnostic_evidence")
    diagnosis = load_diagnostic_result(request["request_id"], 1, runtime_root=runtime)
    require(diagnosis["repair_posture"] == "blocked_environment" and diagnosis["repair_supported"] is False, "environment_failure_not_mislabeled_repairable")
    require(diagnosis["preferred_hypothesis_code"] == "verification_environment_unavailable", "environment_explanation_ranked_first")
    require(tree_signature(project) == project_before, "blocked_diagnosis_preserves_selected_project")

require(source_signature() == SOURCE_BEFORE, "integration_suite_preserves_source_immutability")
print(json.dumps({
    "ok": True,
    "suite": "v1257.3-v1257.5-diagnostic-repair-reasoning-integration",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_calls_success_case": 2,
    "provider_calls_blocked_case": 1,
    "selected_project_modified": False,
    "application_authorized": False,
}, indent=2, sort_keys=True))
