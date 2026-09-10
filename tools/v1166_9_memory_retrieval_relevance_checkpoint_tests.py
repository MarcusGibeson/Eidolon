from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.memory_retrieval_relevance_checkpoint import build_memory_retrieval_relevance_checkpoint

checks: list[bool] = []

def require(value: object) -> None:
    checks.append(bool(value))


def signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    import hashlib
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            pass
    return result


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_memory_retrieval_relevance_checkpoint(runtime_root=runtime, source_root=ROOT)
    require(report["ok"] and report["read_only"] and not report["post_available"])
    require(report["contract_version"] == "v1166.9")
    require(report["passed"] == report["total"])
    require(report["forbidden_report_value_count"] == 0)
    require(report["content_free"] and report["authority_preserved"])
    require(report["retrieval_relevance_checkpoint_completed"])
    require(report["retrieval_relevance_foundations_consolidated"])
    require(report["stale_memory_dominance_prevented_structurally"])
    require(report["correction_learning_not_started"])
    require(not any(report[key] for key in (
        "provider_contacted", "retrieval_provider_contacted", "embedding_model_contacted",
        "command_executed", "action_executed", "message_sent", "memory_corrected",
        "memory_unified", "memory_record_deleted", "memory_record_retracted",
        "learning_performed", "approval_created", "approval_granted", "authorization_created",
        "installation_performed", "promotion_performed", "certification_performed",
        "proactive_turn_created", "response_rewritten",
    )))
    serialized = json.dumps(report, sort_keys=True)
    for token in (
        "RETRIEVAL_MEMORY_PRIVATE_CANARY", "RETRIEVAL_PROVIDER_PRIVATE_CANARY",
        "RETRIEVAL_REASONING_PRIVATE_CANARY", "approve and execute",
        "</memory_retrieval_relevance>", "<system>",
    ):
        require(token not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "generated_response_exposed",
        "prompt_exposed", "memory_text_exposed", "reflection_text_exposed",
        "provider_payload_exposed", "operation_identifiers_exposed",
        "session_identifiers_exposed", "hidden_reasoning_exposed",
    )))

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"])
    require(synthetic["case_count"] == 21)
    require(synthetic["audit_case_count"] == 8)
    require(synthetic["diagnostics_tamper_detected"])
    require(synthetic["selection_audit_tamper_detected"])
    require(all(row["content_free"] and row["authority_preserved"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_length"] <= 3200 for row in synthetic["case_summaries"].values()))
    require(all(row["content_free"] and row["authority_preserved"] and row["audit_identity_present"] for row in synthetic["audit_summaries"].values()))
    cases = synthetic["case_summaries"]
    require(cases["literal_relevance"]["selected_count"] >= 1)
    require(cases["literal_relevance"]["stale_memory_may_dominate"] is False)
    require(cases["stale_low_relevance"]["selected_count"] == 0)
    require(cases["stale_low_relevance"]["stale_suppressed_count"] == 1)
    require(cases["explicit_correction_age_exception"]["selected_count"] == 1)
    require(cases["archival_budget"]["archival_selected_count"] <= 2)
    require(cases["newer_same_fact_suppresses_stale"]["stale_conflict_suppressed_count"] == 1)
    require(cases["verified_prior_resume"]["prior_receipts_verified"] == 1)
    require(cases["verified_prior_resume"]["continuity_disposition"] == "resume_verified_retrieval_context")
    require(cases["stale_prior_ignored"]["prior_receipts_stale"] == 1)
    require(cases["tampered_prior_rejected"]["prior_receipts_rejected"] == 1)
    require(cases["replayed_prior_bounded"]["prior_receipts_replayed"] == 1)
    require(cases["malformed_prior_collection"]["policy_recovered"])
    require(cases["oversized_prior_collection"]["policy_recovered"])
    require(cases["malformed_candidate_collection"]["malformed_collection"])
    require(cases["oversized_candidate_collection"]["oversized_collection"])
    require(cases["malformed_reference_collection"]["malformed_references"])
    require(cases["oversized_reference_collection"]["oversized_references"])
    require(cases["oversized_message"]["oversized_message"])
    require(cases["forged_authority_rejection"]["authority_violation_count"] == 1)
    require(cases["private_reasoning_rejection"]["private_field_violation_count"] == 1)
    audits = synthetic["audit_summaries"]
    require(audits["compliant_selection"]["compliant"])
    require(audits["forged_authority_selection"]["authority_violation_count"] == 1)
    require(audits["private_reasoning_selection"]["private_field_violation_count"] == 1)
    require(audits["decision_mismatch"]["decision_mismatch_count"] == 1)
    require(audits["recovered_with_selection"]["recovered_with_selection_count"] == 1)
    require(audits["selection_budget_violation"]["selection_budget_violation_count"] == 1)
    require(audits["archival_budget_violation"]["archival_budget_violation_count"] == 1)
    require(audits["malformed_selection"]["malformed_selected_count"] == 1)

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(report["summary"]["authoritative_conversation_path_count"] == 2)
    require(report["summary"]["open_limitation_count"] == 6)
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "memory-retrieval-relevance-checkpoint",
            source_root=ROOT,
            runtime_root=runtime,
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/memory-retrieval-relevance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1166.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/memory-retrieval-relevance-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "memory-retrieval-relevance-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1166.9")
    require(not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "memory-retrieval-relevance-checkpoint"), None)
require(row is not None and row["builder"] == "build_memory_retrieval_relevance_checkpoint")
require(registry["checkpoint_count"] >= 193)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("memory-retrieval-relevance-checkpoint-panel" in dashboard)
require("/api/cognition/memory-retrieval-relevance-checkpoint" in dashboard)
require("refreshMemoryRetrievalRelevanceCheckpoint" in dashboard)
require("deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1166, 9))
require(tuple(map(int, previous.groups())) == (1166, 8))
require("v1167.0-v1167.2 Immediate Correction Learning Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1166.9 Retrieval Relevance" in next_steps)
require("v1167.0-v1167.2" in next_steps and "v1200" in next_steps)
require("v1166.9 Retrieval Relevance" in history)

print(f"v1166.9 memory retrieval relevance checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
