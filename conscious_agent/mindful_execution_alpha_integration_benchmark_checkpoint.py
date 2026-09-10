from __future__ import annotations

"""Read-only v1230.9 Mindful Execution Alpha integration benchmark checkpoint."""

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from mindful_execution_alpha_integration_benchmark import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    RETAINED_CHECKPOINTS,
    ROADMAP_PATH,
    build_mindful_execution_alpha_contract,
)

CONTRACT_VERSION = "v1230.9"
CHECKPOINT_ID = "mindful-execution-alpha-integration-benchmark-checkpoint"


def _tree_signature(root: Path) -> tuple[str, int]:
    rows: list[str] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def build_mindful_execution_alpha_integration_benchmark_checkpoint(
    *, source_root: str | Path | None = None, runtime_root=None
) -> dict[str, Any]:
    del runtime_root
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before_signature, before_count = _tree_signature(source)
    contract = build_mindful_execution_alpha_contract(source_root=source)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == CHECKPOINT_ID),
        {},
    )
    metadata_text = (source / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    roadmap_text = (source / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
    release_verifier_text = (source / "tools" / "release_verify.py").read_text(encoding="utf-8")
    quick_stage_names: set[str] = set()
    try:
        tree = ast.parse(release_verifier_text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name)
                and target.id in {"QUICK_STAGE_NAMES", "LEGACY_QUICK_STAGE_NAMES"}
                for target in node.targets
            ):
                quick_stage_names.update(ast.literal_eval(node.value))
    except (SyntaxError, ValueError, TypeError):
        quick_stage_names = set()
    expected_v1230_stages = {
        "v1230.2-mindful-execution-alpha-integration-foundations",
        "v1230.5-mindful-execution-alpha-ordinary-path",
        "v1230.8-mindful-execution-alpha-adversarial-reliability",
        "v1230.9-mindful-execution-alpha-integration-benchmark-checkpoint",
    }
    progress = retained_checkpoint_progress(
        source,
        checkpoint_version="1230.9",
        successor_version="1231.0",
        successor_surface="conscious_agent/dynamic_execution_plan_revision.py",
    )

    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))
    for value in (
        contract.get("ok"),
        contract.get("status") == "mindful_execution_alpha_contract_ready",
        contract.get("contract_version") == "v1230.8",
        contract.get("milestone_name") == MILESTONE_NAME,
        contract.get("roadmap_path") == ROADMAP_PATH,
        contract.get("stage_count") == 5,
        contract.get("complete_stage_order") is True,
        contract.get("retained_versions_match") is True,
        contract.get("retained_checkpoints_pass") is True,
        contract.get("ordinary_chat_required") is True,
        contract.get("restart_recovery_required") is True,
        contract.get("adversarial_authority_testing_required") is True,
        contract.get("goal_alignment_preserved") is True,
        contract.get("uncertainty_preserved") is True,
        contract.get("operator_intervention_preserved") is True,
        contract.get("outcome_reflection_preserved") is True,
        contract.get("learning_revisable") is True,
        contract.get("historical_receipts_remain_authoritative") is True,
        RETAINED_CONTRACT_VERSION == "v1230.8",
        len(RETAINED_CHECKPOINTS) == 5,
        descriptor.get("contract_version") == CONTRACT_VERSION,
        descriptor.get("read_only") is True,
        descriptor.get("required_input_count") == 0,
        progress.get("checkpoint_retained") is True,
        progress.get("coherent") is True,
        progress.get("started") is True,
        "Balanced Mind-and-Action Path 3" in roadmap_text,
        "v1230.9 Mindful Execution Alpha Integration Benchmark" in roadmap_text,
        expected_v1230_stages.issubset(quick_stage_names),
    ):
        check(value)

    for row, retained in zip(contract.get("stages", []), RETAINED_CHECKPOINTS):
        for value in (
            row.get("stage_id") == retained[0],
            row.get("expected_contract_version") == retained[1],
            row.get("checkpoint_id") == retained[2],
            row.get("reported_contract_version") == retained[1],
            row.get("ok") is True,
            row.get("read_only") is True,
            row.get("content_free") is True,
            row.get("runtime_data_read") is False,
            row.get("source_modified") is False,
            row.get("authority_granted") is False,
            row.get("provider_contacted") is False,
            row.get("commands_executed") is False,
            row.get("tests_executed") is False,
            row.get("project_modified") is False,
            row.get("cognition_written") is False,
            int(row.get("passed_checks") or 0) > 0,
        ):
            check(value)

    for key, expected in AUTHORITY_FLAGS.items():
        check(contract.get(key) is expected)
    for value in (
        contract.get("runtime_data_read") is False,
        contract.get("runtime_data_written") is False,
        contract.get("source_modified") is False,
        contract.get("content_free") is True,
        contract.get("read_only") is True,
    ):
        check(value)

    serialized = json.dumps(contract, sort_keys=True)
    for forbidden in ("/tmp/", "\\AppData\\", "C:\\", "private_request", "raw_provider_output", "raw_test_output"):
        check(forbidden not in serialized)

    after_signature, after_count = _tree_signature(source)
    check(before_signature == after_signature)
    check(before_count == after_count)
    passed = sum(checks)
    total = len(checks)
    return {
        "ok": passed == total,
        "status": "mindful_execution_alpha_integration_benchmark_checkpoint_ready" if passed == total else "mindful_execution_alpha_integration_benchmark_checkpoint_blocked",
        "checkpoint_id": CHECKPOINT_ID,
        "contract_version": CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "passed": passed,
        "total": total,
        "checks": checks,
        "retained_contract": contract,
        "source_signature_unchanged": before_signature == after_signature,
        "source_file_count_before": before_count,
        "source_file_count_after": after_count,
        "read_only": True,
        "content_free": True,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "project_modified": False,
        "source_modified": False,
        "cognition_written": False,
        "authority_granted": False,
        "release_authorized": False,
    }
