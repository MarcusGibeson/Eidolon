from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from isolated_coding_execution_foundations import (
    create_or_restore_coding_work_plan,
    create_or_restore_coding_work_request,
    inspect_coding_project,
    materialize_or_restore_isolated_coding_workspace,
)
from isolated_coding_execution import prepare_isolated_coding_execution, authorize_and_run_isolated_coding_execution


def tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def make_project(base: Path, *, failing_after_apply: bool = False) -> Path:
    project = base / "project"
    (project / "tests").mkdir(parents=True)
    (project / "pyproject.toml").write_text('[project]\nname="calculator"\nversion="0.1.0"\n', encoding="utf-8")
    (project / "main.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    expected = "999" if failing_after_apply else "5"
    (project / "tests" / "test_main.py").write_text(
        "import unittest\n"
        "from main import add, subtract\n\n"
        "class CalculatorTests(unittest.TestCase):\n"
        "    def test_add(self): self.assertEqual(add(2, 3), 5)\n"
        f"    def test_subtract(self): self.assertEqual(subtract(7, 2), {expected})\n\n"
        "if __name__ == '__main__': unittest.main()\n",
        encoding="utf-8",
    )
    (project / "README.md").write_text("# Calculator\noperator notes\n", encoding="utf-8")
    (project / ".env").write_text("SECRET=fixture-private\n", encoding="utf-8")
    (project / "data").mkdir()
    (project / "data" / "projects.json").write_text('{"private":true}\n', encoding="utf-8")
    return project


class CandidateProvider:
    def __init__(self, *, create_extra: bool = False, delete_readme: bool = False) -> None:
        self.calls = 0
        self.create_extra = create_extra
        self.delete_readme = delete_readme

    def __call__(self, prompt: str) -> str:
        payload = json.loads(prompt)
        self.calls += 1
        authority = payload["authority"]
        files = [{
            "path": "main.py",
            "operation": "modify",
            "content": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
        }]
        if self.create_extra:
            files.append({"path": "helper.py", "operation": "create", "content": "VALUE = 42\n"})
        if self.delete_readme:
            files.append({"path": "README.md", "operation": "delete", "content": ""})
        return json.dumps({
            "authority": {
                "request_id": authority["request_id"],
                "execution_digest": authority["execution_digest"],
                "attempt": authority["attempt"],
            },
            "files": files,
        })


def prepare_v1254_candidate(project: Path, runtime: Path, *, provider: CandidateProvider | None = None) -> tuple[dict, dict, CandidateProvider]:
    provider = provider or CandidateProvider()
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add subtract(a, b) while preserving add(a, b)."],
        acceptance_criteria=["add(2,3) is 5", "subtract(7,2) is 5"],
        constraints=["Keep existing project layout."],
        prohibited_actions=["Do not install dependencies."],
        expected_artifacts=["Reviewable diff", "Passing tests"],
        verification=["Compile Python", "Run project tests"],
        runtime_root=runtime,
    )
    inspect = inspect_coding_project(request["request_id"], runtime_root=runtime)
    assert inspect["ok"], inspect
    plan = create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)
    assert plan["ok"], plan
    workspace = materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    assert workspace["ok"], workspace
    prepared = prepare_isolated_coding_execution(request["request_id"], runtime_root=runtime)
    assert prepared["ok"], prepared
    result = authorize_and_run_isolated_coding_execution(
        request["request_id"],
        expected_execution_digest=prepared["execution_digest"],
        authorization_phrase=prepared["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    assert result["ok"], result
    return request, result, provider


def prepare_fast_v1254_candidate(project: Path, runtime: Path, *, provider: CandidateProvider | None = None) -> tuple[dict, dict, CandidateProvider]:
    """Build a sealed v1254 lineage without provider/test execution.

    Reliability tests below v1255 are about the application transaction rather
    than re-testing v1254 provider generation on every fixture.  The full
    provider-backed v1254 path remains exercised by the v1255.3-.5 integration
    suite.  This helper creates the same sealed request/inspection/plan/workspace
    lineage, applies the deterministic candidate inside the disposable workspace,
    and seals the review/execution records expected by v1255.
    """
    import difflib
    from ordinary_chat_development_campaign import _atomic_json, _digest, _store_root
    from isolated_coding_execution import _execution_path, _review_path, _seal as seal_execution
    from isolated_coding_execution_foundations import _manifest_digest, _path_digest, _walk_project

    provider = provider or CandidateProvider()
    request = create_or_restore_coding_work_request(
        user_objective="Add subtraction while preserving addition.",
        target_project=project,
        requirements=["Add subtract(a, b) while preserving add(a, b)."],
        acceptance_criteria=["add(2,3) is 5", "subtract(7,2) is 5"],
        constraints=["Keep existing project layout."],
        prohibited_actions=["Do not install dependencies."],
        expected_artifacts=["Reviewable diff", "Passing tests"],
        verification=["Compile Python", "Run project tests"],
        runtime_root=runtime,
    )
    inspection = inspect_coding_project(request["request_id"], runtime_root=runtime)
    assert inspection["ok"], inspection
    plan = create_or_restore_coding_work_plan(request["request_id"], runtime_root=runtime)
    assert plan["ok"], plan
    workspace = materialize_or_restore_isolated_coding_workspace(request["request_id"], runtime_root=runtime)
    assert workspace["ok"], workspace

    workspace_record_path = _store_root(runtime) / "coding_workspace_records" / f"{request['request_id']}.json"
    workspace_record = json.loads(workspace_record_path.read_text(encoding="utf-8"))
    workspace_root = Path(workspace_record["workspace_path"])
    changed_paths = ["main.py"]
    before = (workspace_root / "main.py").read_text(encoding="utf-8")
    after = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n"
    (workspace_root / "main.py").write_text(after, encoding="utf-8")
    if provider.create_extra:
        (workspace_root / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
        changed_paths.append("helper.py")
    if provider.delete_readme:
        (workspace_root / "README.md").unlink()
        changed_paths.append("README.md")
    # Model one already-completed generation call so recovery assertions can
    # prove the v1255 transaction never recontacts it.
    provider.calls += 1

    diff_parts = []
    baseline_map = {row["relative_path"]: row for row in inspection.get("inventory") or []}
    for relative in sorted(changed_paths, key=str.casefold):
        baseline_exists = relative in baseline_map
        source_path = project / relative
        old = source_path.read_text(encoding="utf-8") if baseline_exists and source_path.is_file() else ""
        candidate_path = workspace_root / relative
        candidate_exists = candidate_path.is_file()
        new = candidate_path.read_text(encoding="utf-8") if candidate_exists else ""
        diff_parts.append("".join(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{relative}" if baseline_exists else "/dev/null",
            tofile=f"b/{relative}" if candidate_exists else "/dev/null",
            lineterm="\n",
        )))
    full_diff = "\n".join(part for part in diff_parts if part)
    files, _ = _walk_project(workspace_root)
    review = {
        "ok": True,
        "schema_version": "1",
        "contract_version": "v1254.5",
        "status": "isolated_coding_review_ready",
        "request_id": request["request_id"],
        "changed_paths": sorted(changed_paths, key=str.casefold),
        "changed_path_digests": [_path_digest(value) for value in sorted(changed_paths, key=str.casefold)],
        "added_file_count": int(provider.create_extra),
        "modified_file_count": 1,
        "deleted_file_count": int(provider.delete_readme),
        "diff": full_diff,
        "diff_digest": hashlib.sha256(full_diff.encode("utf-8")).hexdigest(),
        "diff_bytes": len(full_diff.encode("utf-8")),
        "diff_truncated": False,
        "workspace_manifest_digest": _manifest_digest(files),
        "workspace_file_count": len(files),
        "source_fresh_at_review": True,
        "source_freshness_digest": _digest({"request_id": request["request_id"], "source_manifest_digest": inspection.get("source_manifest_digest", "")}),
        "reviewable_diff_available": bool(full_diff),
        "operator_review_required": True,
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "permanent_approval_granted": False,
        "independent_authority_granted": False,
    }
    review = seal_execution(review, "review_record_digest")
    _atomic_json(_review_path(request["request_id"], runtime), review)

    execution_digest = _digest({
        "request_id": request["request_id"],
        "review_record_digest": review["review_record_digest"],
        "workspace_manifest_digest": review["workspace_manifest_digest"],
        "fixture": "v1255_reliability_sealed_v1254_lineage",
    })
    result = {
        "ok": True,
        "schema_version": "1",
        "contract_version": "v1254.5",
        "status": "isolated_coding_execution_completed",
        "request_id": request["request_id"],
        "execution_digest": execution_digest,
        "project_type": inspection.get("project_type", "python"),
        "attempt_count": 1,
        "repair_attempt_count": 0,
        "attempts": [],
        "provider_contacted": True,
        "tests_executed": True,
        "test_passed": True,
        "cleanup_confirmed": True,
        "source_fresh_at_review": True,
        "review_digest": review["review_record_digest"],
        "diff_digest": review["diff_digest"],
        "reviewable_diff_available": True,
        "changed_file_count": len(changed_paths),
        "recovery_count": 0,
        "operator_review_required": True,
        "runtime_records_external": True,
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "permanent_approval_granted": False,
        "independent_authority_granted": False,
        "execution_authority_consumed": True,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        "private_content_exposed": False,
    }
    result["execution_result_digest"] = _digest(result)
    execution = {
        "ok": True,
        "schema_version": "1",
        "contract_version": "v1254.5",
        "status": "isolated_coding_execution_completed",
        "phase": "sealed",
        "request_id": request["request_id"],
        "execution_digest": execution_digest,
        "authorization_phrase": "",
        "lease_token": "",
        "lease_expires_unix": 0.0,
        "attempt_count": 1,
        "repair_attempt_count": 0,
        "provider_contacted": True,
        "tests_executed": True,
        "reviewable_diff_available": True,
        "result": result,
        "result_digest": _digest(result),
        "selected_project_modified": False,
        "source_modified": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "release_authorized": False,
        "permanent_approval_granted": False,
        "independent_authority_granted": False,
        "execution_authority_consumed": True,
    }
    execution = seal_execution(execution, "execution_record_digest")
    _atomic_json(_execution_path(request["request_id"], runtime), execution)
    return request, result, provider
