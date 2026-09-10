from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.daily_companion_cognition_checkpoint import build_daily_companion_cognition_checkpoint


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    excluded = {
        "data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", "reports", "dist", "build",
    }
    for base, directories, names in os.walk(root):
        directories[:] = [name for name in directories if name not in excluded]
        for name in sorted(names):
            path = Path(base) / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_daily_companion_cognition_checkpoint(runtime_root=runtime, source_root=ROOT)
    require(report["contract_version"] == "v1164.9")
    require(report["checkpoint_id"] == "daily-companion-cognition:v1164.9")
    require(report["ok"] and report["read_only"] and not report["post_available"])
    require(report["content_free"] and report["authority_preserved"])
    require(report["daily_companion_cognition_checkpoint_completed"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["memory_unification_not_started"])
    require(report["retrieval_relevance_work_not_started"])
    require(report["learning_mutation_not_started"])
    require(report["autonomous_new_turn_initiation_not_started"])
    require(report["private_reflection_delivery_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "proactive_turn_created", "reflection_delivered", "learning_performed",
        "identity_rewritten", "memory_corrected", "memory_unified",
        "approval_created", "approval_granted", "authorization_created",
        "installation_performed", "promotion_performed", "certification_performed",
        "response_rewritten",
    )))
    serialized = json.dumps(report, sort_keys=True)
    for token in (
        "DAILY_COMPANION_PRIVATE_CANARY", "DAILY_PROVIDER_PRIVATE_CANARY",
        "DAILY_MEMORY_PRIVATE_CANARY", "DAILY_REFLECTION_PRIVATE_CANARY",
        "approve and execute", "</daily_companion_cognition>", "<system>",
    ):
        require(token not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "generated_response_exposed",
        "prompt_exposed", "memory_text_exposed", "reflection_text_exposed",
        "evidence_text_exposed", "provider_payload_exposed",
        "operation_identifiers_exposed", "session_identifiers_exposed",
        "hidden_reasoning_exposed",
    )))

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"] == 41)
    require(synthetic["case_count"] == 21)
    require(synthetic["audit_case_count"] == 7)
    require(synthetic["runtime_diagnostics_valid"])
    require(synthetic["runtime_diagnostics_tamper_detected"])
    require(synthetic["response_audit_digests_valid"])
    require(synthetic["response_audit_tamper_detected"])
    require(all(row["content_free"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_envelope_complete"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_length"] <= 2400 for row in synthetic["case_summaries"].values()))
    require(all(row["authority_preserved"] for row in synthetic["case_summaries"].values()))
    require(all(row["policy_identity_present"] and row["evidence_identity_present"] for row in synthetic["case_summaries"].values()))
    require(all(row["content_free"] and row["authority_preserved"] and row["audit_identity_present"] for row in synthetic["audit_summaries"].values()))

    cases = synthetic["case_summaries"]
    require(cases["companion_answer"]["companion_posture"] == "answer_companionably")
    require(cases["continue_topic"]["companion_posture"] == "continue_companionably")
    require(cases["continue_topic"]["continuity_disposition"] == "use_current_turn_only")
    require(cases["required_clarification"]["companion_posture"] == "clarify_once")
    require(cases["required_clarification"]["maximum_clarifying_questions"] == 1)
    require(cases["repair_and_stabilize"]["companion_posture"] == "repair_and_stabilize")
    require(cases["acknowledge_and_close"]["companion_posture"] == "acknowledge_and_close")
    require(cases["acknowledge_and_close"]["close_without_reopening"])
    require(cases["bounded_insight"]["companion_posture"] == "answer_with_bounded_insight")
    require(cases["bounded_insight"]["maximum_optional_observations"] == 1)
    require(cases["deliberate_silence"]["companion_posture"] == "preserve_deliberate_silence")
    require(cases["deliberate_silence"]["emit_no_substantive_content"])
    require(cases["conflicting_policies"]["policy_conflict_suppressed"])
    require(cases["conflicting_policies"]["companion_posture"] == "literal_request_only")
    require(cases["stale_context"]["stale_records_ignored"] == 1)
    require(cases["suspicious_context"]["suspicious_records_ignored"] == 1)
    require(cases["malformed_context"]["context_malformed"] and cases["malformed_context"]["policy_recovered"])
    require(cases["oversized_inputs"]["message_truncated"] and cases["oversized_inputs"]["context_truncated"])
    require(cases["oversized_inputs"]["context_count"] == 24)
    require(cases["injected_markup"]["authority_preserved"])
    require(cases["forged_component_authority"]["authority_conflict_suppressed"])
    require(cases["forged_evidence_authority"]["policy_recovered"])
    require(cases["tampered_evidence"]["policy_recovered"])
    require(cases["verified_prior_resume"]["prior_receipts_verified"] == 1)
    require(cases["verified_prior_resume"]["continuity_disposition"] == "resume_verified_companion_context")
    require(cases["verified_prior_resume"]["prior_companion_continuity_used"])
    require(cases["stale_prior_ignored"]["prior_receipts_stale"] == 1)
    require(cases["stale_prior_ignored"]["continuity_disposition"] == "use_current_turn_only")
    require(cases["tampered_prior_rejected"]["prior_receipts_rejected"] == 1)
    require(cases["replayed_prior_rejected"]["prior_receipts_replayed"] == 1)
    require(cases["malformed_prior_collection"]["prior_receipts_rejected"] == 1)

    audits = synthetic["audit_summaries"]
    require(audits["compliant_answer"]["compliant"])
    require(audits["compliant_bounded_insight"]["compliant"])
    require(audits["silence_violation"]["silence_violation"] and not audits["silence_violation"]["compliant"])
    require(audits["clarification_overrun"]["clarification_budget_violation"] and not audits["clarification_overrun"]["compliant"])
    require(audits["closure_reopened"]["closure_reopened"] and not audits["closure_reopened"]["compliant"])
    require(audits["bounded_insight_overrun"]["bounded_insight_shape_violation"] and not audits["bounded_insight_overrun"]["compliant"])
    require(audits["oversized_response"]["response_oversized"] and not audits["oversized_response"]["compliant"])

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(report["summary"]["authoritative_conversation_path_count"] == 2)
    require(report["summary"]["prior_companion_receipt_maximum_count"] == 8)
    require(report["summary"]["response_audit_maximum_chars"] == 12000)
    require(report["summary"]["open_limitation_count"] == 6)
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "daily-companion-cognition-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/daily-companion-cognition-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1164.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/daily-companion-cognition-checkpoint", body={"confirm": True}
        )
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
        [sys.executable, str(ROOT / "eidolon.py"), "daily-companion-cognition-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1164.9")
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.daily_companion_cognition; import conscious_agent.daily_companion_cognition_checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=90,
    )
    require(imported.returncode == 0 and not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "daily-companion-cognition-checkpoint"), None)
require(row is not None and row["builder"] == "build_daily_companion_cognition_checkpoint")
require(registry["checkpoint_count"] >= 191)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "daily-companion-cognition-checkpoint-panel" in dashboard
    and "/api/cognition/daily-companion-cognition-checkpoint" in dashboard
    and "refreshDailyCompanionCognitionCheckpoint" in dashboard
    and "deferred to v1200" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1164, 9) and tuple(map(int, previous.groups())) == (1164, 8))
require("v1165.0-v1165.2 Memory Unification Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1164.9 Daily Companion Cognition" in next_steps)
require("v1165.0-v1165.2" in next_steps and "v1200" in next_steps)
require("v1164.9 Daily Companion Cognition" in history)

print(f"v1164.9 daily companion cognition checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
