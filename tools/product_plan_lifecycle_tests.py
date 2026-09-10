from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_to_candidate_planner import build_evidence_to_candidate_plans
from product_plan_lifecycle import (
    prepare_isolated_product_repair,
    process_product_plan_control,
    register_product_candidate_plan,
    review_product_candidate_plan,
)
from isolated_coding_execution_foundations import MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES, load_coding_work_plan
from isolated_coding_execution import _authorization_text_matches
from ordinary_chat_development_campaign import MAX_FILE_BYTES as MAX_RUNTIME_RECORD_BYTES


checks: list[str] = []


def require(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    checks.append(label)


def tree_digest(root: Path) -> str:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows).encode("utf-8")).hexdigest()


require(
    MAX_FILES >= 6000 and MAX_FILE_BYTES >= 8 * 1024 * 1024 and MAX_TOTAL_BYTES >= 128 * 1024 * 1024,
    "current_eidolon_source_fits_bounded_inspection_budget",
)
require(MAX_RUNTIME_RECORD_BYTES >= 4 * 1024 * 1024, "current_eidolon_manifest_fits_sealed_runtime_record_budget")
authority = "Authorize isolated coding execution for request devc_" + "a" * 24 + " execution " + "b" * 64
require(_authorization_text_matches(authority, authority + "."), "authorization_terminal_punctuation_is_optional")
require(not _authorization_text_matches(authority[:-1] + "c", authority + "."), "authorization_digest_remains_exact")


with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    source = base / "source"
    runtime = base / "runtime"
    (source / "conscious_agent").mkdir(parents=True)
    (source / "tools").mkdir()
    (source / "conscious_agent" / "discourse_response_planning.py").write_text("def target():\n    return 'current'\n", encoding="utf-8")
    (source / "conscious_agent" / "conversation_context.py").write_text("def context():\n    return []\n", encoding="utf-8")
    (source / "conscious_agent" / "context_assembly_architecture.py").write_text("def assemble():\n    return []\n", encoding="utf-8")
    (source / "tools" / "conversation_target_tests.py").write_text("print('ok')\n", encoding="utf-8")
    evidence = {
        "evidence_id": "initev_" + "a" * 24,
        "evidence_digest": "b" * 64,
        "evidence_class": "conversation_quality_finding",
        "issue_domain": "model_quality",
        "impact_score": 0.8,
        "confidence": 0.9,
        "freshness": "current",
        "structural_only": False,
    }
    planning = build_evidence_to_candidate_plans({"records": [evidence]}, source_root=source)
    plan = planning["plans"][0]
    before = tree_digest(source)

    registered = register_product_candidate_plan(plan, source_root=source, runtime_root=runtime)
    require(registered["ok"] and registered["status"] == "product_plan_registered", "exact_plan_is_registered")
    restored = register_product_candidate_plan(plan, source_root=source, runtime_root=runtime)
    require(restored.get("operation_status") == "restored", "duplicate_registration_is_idempotent")
    require(not registered["provider_contacted"] and not registered["tests_executed"], "registration_executes_nothing")

    stale_digest = review_product_candidate_plan(plan["candidate_plan_id"], "0" * 16, source_root=source, runtime_root=runtime)
    require(not stale_digest["ok"] and stale_digest["status"] == "product_plan_missing_or_stale", "stale_review_digest_is_rejected")

    reviewed = review_product_candidate_plan(
        plan["candidate_plan_id"], plan["candidate_plan_digest"][:16], source_root=source, runtime_root=runtime
    )
    require(reviewed["ok"] and reviewed["status"] == "product_plan_reviewed", "current_scope_is_reviewed")
    require("Prepare isolated product repair" in reviewed["next_phrase"], "review_returns_exact_prepare_phrase")
    require(not reviewed["provider_contacted"] and not reviewed["tests_executed"], "review_executes_nothing")

    prepared = prepare_isolated_product_repair(
        plan["candidate_plan_id"], plan["candidate_plan_digest"][:16], source_root=source, runtime_root=runtime
    )
    require(prepared["ok"] and prepared["status"] == "product_repair_workspace_prepared", "isolated_product_workspace_is_prepared")
    require(str(prepared["isolated_coding_execution"].get("request_id") or "").startswith("devc_"), "retained_coding_executor_is_reused")
    prepared_plan = load_coding_work_plan(
        str(prepared["isolated_coding_execution"].get("request_id") or ""), runtime_root=runtime
    )
    require(
        set(prepared_plan.get("context_paths") or ()) == set([*plan["target_files"], *plan["test_files"]]),
        "provider_context_is_confined_to_product_plan",
    )
    require("Authorize isolated coding execution" in prepared["next_phrase"], "prepare_returns_exact_execution_phrase")
    require(not prepared["provider_contacted"] and not prepared["tests_executed"], "preparation_executes_nothing")
    require(before == tree_digest(source), "active_source_remains_unchanged")
    first_request_id = str(prepared["isolated_coding_execution"].get("request_id") or "")
    (source / "README.md").write_text("new source snapshot\n", encoding="utf-8")
    rebound = prepare_isolated_product_repair(
        plan["candidate_plan_id"], plan["candidate_plan_digest"][:16], source_root=source, runtime_root=runtime
    )
    require(
        rebound["ok"] and str(rebound["isolated_coding_execution"].get("request_id") or "") != first_request_id,
        "legitimate_source_drift_rebinds_fresh_request",
    )
    require(not rebound["provider_contacted"] and not rebound["source_modified"], "source_rebinding_preserves_authority_boundary")

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    source = base / "source"
    runtime = base / "runtime"
    (source / "conscious_agent").mkdir(parents=True)
    (source / "tools").mkdir()
    for relative in ("discourse_response_planning.py", "conversation_context.py", "context_assembly_architecture.py"):
        (source / "conscious_agent" / relative).write_text("value = 1\n", encoding="utf-8")
    (source / "tools" / "conversation_target_tests.py").write_text("print('ok')\n", encoding="utf-8")
    plan = build_evidence_to_candidate_plans({"records": [evidence]}, source_root=source)["plans"][0]
    register_product_candidate_plan(plan, source_root=source, runtime_root=runtime)
    (source / "conscious_agent" / "conversation_context.py").write_text("value = 2\n", encoding="utf-8")
    stale = process_product_plan_control(
        f"Review product plan {plan['candidate_plan_id']} digest {plan['candidate_plan_digest'][:16]}.",
        source_root=source,
        runtime_root=runtime,
    )
    require(stale["active"] and stale["status"] == "product_plan_source_stale", "source_drift_blocks_review")
    require(not stale["source_modified"] and not stale["authority_granted"], "blocked_review_grants_no_authority")

print(json.dumps({"ok": True, "suite": "product-plan-lifecycle", "passed": len(checks), "failed": 0, "checks": checks}, indent=2))
