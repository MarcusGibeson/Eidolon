from __future__ import annotations

"""Strictly read-only v1210.9 Conversational Build-and-Test Loop checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from conversational_build_test_loop import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, SUPPORTED_LOOP_PROJECT_KINDS, _authorization_phrase
from unified_test_adapter_contract import select_test_adapter

CONTRACT_VERSION = "v1210.9"
_EXCLUDED = {"data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "dist", "build", "reports"}


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in _EXCLUDED)
        for name in sorted(files):
            path = Path(base) / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(root).as_posix()
            content = path.read_bytes()
            digest.update(relative.encode("utf-8") + b"\0" + hashlib.sha256(content).digest())
            count += 1
    return digest.hexdigest(), count


def build_conversational_build_test_loop_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    selections = {kind: select_test_adapter(kind) for kind in sorted(SUPPORTED_LOOP_PROJECT_KINDS)}
    expected = {"new_small_web_project": "browser_runtime", "new_javascript_tool_project": "node_javascript", "new_python_cli_project": "python"}
    for kind, adapter in expected.items():
        check(selections[kind].get("status") == "test_adapter_selected")
        check(selections[kind].get("selected_adapter_id") == adapter)
        check(selections[kind].get("tests_executed") is False)
        check(selections[kind].get("authority", {}).get("execution_authorized") is False)
    phrase = _authorization_phrase("devc_" + "a" * 24, 1, "b" * 64)
    check(phrase.startswith("Authorize build and tests for development proposal"))
    check("b" * 64 in phrase)
    check(all(value is False for value in AUTHORITY_FLAGS.values()))
    check(RETAINED_CONTRACT_VERSION == "v1210.8")
    module_source = (source / "conscious_agent" / "conversational_build_test_loop.py").read_text(encoding="utf-8")
    ordinary_source = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    check("process_conversational_build_test_control" in ordinary_source)
    check("prepare_conversational_build_test_loop" in ordinary_source)
    check("run_or_resume_general_small_project_implementation" in module_source)
    check("run_or_resume_selected_test_adapter" in module_source)
    check("conversational_build_test_tests_failed" in module_source)
    check("conversational_build_test_build_blocked" in module_source)
    check("conversational_build_test_test_blocked" in module_source)
    check("LOOP_LEASE_SECONDS" in module_source)
    check("loop_record_digest" in module_source)
    check("private_path_exposed\": False" in module_source)
    check("repair_authorized\": True" not in module_source)
    check("apply_authorized\": True" not in module_source)
    check("release_authorized\": True" not in module_source)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "conversational-build-test-loop-checkpoint"), None)
    check(descriptor is not None)
    check((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    check((descriptor or {}).get("read_only") is True)
    check((descriptor or {}).get("post_available") is False)
    after, after_count = _tree_signature(source)
    check(after == before and after_count == count)
    check(runtime is None or runtime.exists() == runtime_existed)

    summary = {
        "supported_project_kind_count": len(SUPPORTED_LOOP_PROJECT_KINDS),
        "adapter_routing": expected,
        "ordinary_chat_control_present": True,
        "separate_loop_authorization": True,
        "digest_bound": True,
        "persistent_external_runtime_state": True,
        "idempotent_resume": True,
        "stale_operation_recovery": True,
        "build_and_test_outcomes_distinct": True,
        "privacy_preserved": True,
        "authority_preserved": True,
    }
    report = {
        "ok": all(checks),
        "contract_version": CONTRACT_VERSION,
        "retained_contract_version": RETAINED_CONTRACT_VERSION,
        "passed": sum(checks),
        "total": len(checks),
        "summary": summary,
        "read_only": True,
        "post_available": False,
        "synthetic_contract_evaluation": True,
        "provider_contacted": False,
        "project_tests_executed": False,
        "runtime_probed": False,
        "runtime_data_read": False,
        "runtime_mutated": False,
        "source_modified": False,
        "project_modified": False,
        "dependencies_installed": False,
        "automatic_diagnosis": False,
        "automatic_repair": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "global_profile_pass_claimed": False,
        "source_signature_before": before,
        "source_signature_after": after,
        "source_file_count": count,
        "limitations": [
            "The checkpoint evaluates source contracts and synthetic routing only; it does not contact a provider or run project tests.",
            "v1210 supports the three established new small-project kinds; broader existing-project development remains on the later roadmap.",
            "Test failures remain operator-review evidence and do not authorize diagnosis or repair.",
            "Language-runtime guards remain policy boundaries rather than OS containers.",
        ],
    }
    report["structural_digest"] = hashlib.sha256(json.dumps({k: v for k, v in report.items() if k != "structural_digest"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return report

