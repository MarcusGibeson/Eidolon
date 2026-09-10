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

from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.unified_memory_checkpoint import build_unified_memory_checkpoint

checks: list[bool] = []
def require(value: object) -> None:
    checks.append(bool(value))


def signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    result: dict[str, str] = {}
    import hashlib
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
    report = build_unified_memory_checkpoint(runtime_root=runtime, source_root=ROOT)
    require(report["ok"] and report["read_only"] and not report["post_available"])
    require(report["contract_version"] == "v1165.9")
    require(report["passed"] == report["total"])
    require(report["forbidden_report_value_count"] == 0)
    require(report["content_free"] and report["authority_preserved"])
    require(report["unified_memory_checkpoint_completed"])
    require(report["memory_stores_physically_merged"] is False)
    require(report["retrieval_relevance_work_not_started"])
    require(report["stale_memory_weighting_not_started"])
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "memory_corrected", "memory_unified", "memory_record_deleted", "memory_record_retracted",
        "learning_performed", "approval_created", "approval_granted", "authorization_created",
        "installation_performed", "promotion_performed", "certification_performed",
        "proactive_turn_created", "response_rewritten",
    )))
    serialized = json.dumps(report, sort_keys=True)
    for token in (
        "UNIFIED_MEMORY_PRIVATE_CANARY", "UNIFIED_PROVIDER_PRIVATE_CANARY",
        "UNIFIED_PROJECT_PRIVATE_CANARY", "UNIFIED_REASONING_PRIVATE_CANARY",
        "approve and execute", "</unified_memory_context>", "<system>",
    ):
        require(token not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "generated_response_exposed",
        "prompt_exposed", "memory_text_exposed", "project_text_exposed",
        "reflection_text_exposed", "provider_payload_exposed",
        "operation_identifiers_exposed", "session_identifiers_exposed", "hidden_reasoning_exposed",
    )))

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"])
    require(synthetic["case_count"] == 19)
    require(synthetic["audit_case_count"] == 8)
    require(synthetic["runtime_diagnostics_tamper_detected"])
    require(synthetic["selection_audit_tamper_detected"])
    require(all(row["content_free"] and row["authority_preserved"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_length"] <= 3000 for row in synthetic["case_summaries"].values()))
    require(all(row["content_free"] and row["authority_preserved"] and row["audit_identity_present"] for row in synthetic["audit_summaries"].values()))
    cases = synthetic["case_summaries"]
    require(cases["five_domain_coordination"]["domain_count"] == 5)
    require(cases["five_domain_coordination"]["coordination_posture"] == "cross_domain_grounded")
    require(cases["single_domain_coordination"]["coordination_posture"] == "single_domain_grounded")
    require(cases["current_request_without_memory"]["coordination_posture"] == "current_request_without_memory")
    require(cases["exact_duplicate_omission"]["duplicate_references_omitted"] == 1)
    require(cases["explicit_correction_conflict"]["conflict_groups_detected"] == 1)
    require(cases["explicit_correction_conflict"]["conflicting_references_suppressed"] == 1)
    require(cases["forged_authority_rejection"]["authority_conflict_suppressed"])
    require(cases["malformed_rows"]["policy_recovered"])
    require(cases["oversized_rows"]["oversized_rows_ignored"] == 10)
    require(cases["verified_prior_resume"]["prior_receipts_verified"] == 1)
    require(cases["verified_prior_resume"]["continuity_disposition"] == "resume_verified_cross_domain_context")
    require(cases["stale_prior_ignored"]["prior_receipts_stale"] == 1)
    require(cases["tampered_prior_rejected"]["prior_receipts_rejected"] == 1)
    require(cases["replayed_prior_rejected"]["prior_receipts_replayed"] == 1)
    require(cases["malformed_prior_collection"]["policy_recovered"])
    require(cases["oversized_prior_collection"]["prior_receipts_oversized"] == 1)
    require(cases["tampered_evidence"]["policy_recovered"])
    audits = synthetic["audit_summaries"]
    require(audits["compliant_selection"]["compliant"])
    require(audits["forged_authority_selection"]["authority_violation_count"] == 1)
    require(audits["private_reasoning_selection"]["private_field_violation_count"] == 1)
    require(audits["malformed_selection"]["malformed_count"] == 1)
    require(audits["oversized_selection"]["oversized_count"] == 2)
    require(audits["recovered_with_selection"]["recovered_with_selection"])
    require(audits["provenance_violation"]["provenance_violation"])
    require(audits["invalid_collection"]["invalid_collection"])

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(report["summary"]["authoritative_conversation_path_count"] == 2)
    require(report["summary"]["memory_domain_count"] == 5)
    require(report["summary"]["open_limitation_count"] == 6)
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint("unified-memory-checkpoint", source_root=ROOT, runtime_root=runtime)
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/unified-memory-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1165.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/unified-memory-checkpoint", body={"confirm": True})
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
    cli = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "unified-memory-checkpoint"], cwd=ROOT, env=env, text=True, capture_output=True, timeout=480)
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1165.9")
    require(not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "unified-memory-checkpoint"), None)
require(row is not None and row["builder"] == "build_unified_memory_checkpoint")
require(registry["checkpoint_count"] >= 192)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("unified-memory-checkpoint-panel" in dashboard)
require("/api/cognition/unified-memory-checkpoint" in dashboard)
require("refreshUnifiedMemoryCheckpoint" in dashboard)
require("deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1165, 9))
require(tuple(map(int, previous.groups())) == (1165, 8))
require("v1166.0-v1166.2 Retrieval Relevance Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1165.9 Unified Memory" in next_steps)
require("v1166.0-v1166.2" in next_steps and "v1200" in next_steps)
require("v1165.9 Unified Memory" in history)

print(f"v1165.9 unified memory checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
