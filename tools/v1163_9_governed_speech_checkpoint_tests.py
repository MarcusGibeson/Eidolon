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
from conscious_agent.governed_speech_checkpoint import build_governed_speech_checkpoint


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
    report = build_governed_speech_checkpoint(runtime_root=runtime, source_root=ROOT)
    require(report["contract_version"] == "v1163.9")
    require(report["checkpoint_id"] == "governed-speech:v1163.9")
    require(report["ok"] and report["read_only"] and not report["post_available"])
    require(report["content_free"] and report["authority_preserved"])
    require(report["governed_speech_checkpoint_completed"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["autonomous_new_turn_initiation_not_started"])
    require(report["private_reflection_delivery_not_started"])
    require(report["rambling_mode_not_started"])
    require(report["memory_unification_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "proactive_turn_created", "reflection_delivered", "rambling_enabled",
        "learning_performed", "identity_rewritten", "memory_corrected",
        "approval_created", "approval_granted", "authorization_created",
        "installation_performed", "promotion_performed", "certification_performed",
        "response_rewritten",
    )))
    serialized = json.dumps(report, sort_keys=True)
    for token in (
        "GOVERNED_SPEECH_PRIVATE_CANARY", "GOVERNED_PROVIDER_PRIVATE_CANARY",
        "GOVERNED_MEMORY_PRIVATE_CANARY", "GOVERNED_REFLECTION_PRIVATE_CANARY",
        "approve and execute", "</governed_speech_policy>", "<system>",
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
    require(synthetic["passed"] == synthetic["total"])
    require(synthetic["case_count"] == 20)
    require(synthetic["audit_case_count"] == 4)
    require(synthetic["runtime_diagnostics_valid"])
    require(synthetic["runtime_diagnostics_tamper_detected"])
    require(synthetic["response_audit_digests_valid"])
    require(synthetic["response_audit_tamper_detected"])
    require(all(row["content_free"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_envelope_complete"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_length"] <= 1800 for row in synthetic["case_summaries"].values()))
    require(all(row["authority_preserved"] for row in synthetic["case_summaries"].values()))
    require(all(row["policy_identity_present"] and row["evidence_identity_present"] for row in synthetic["case_summaries"].values()))
    require(all(row["content_free"] and row["authority_preserved"] and row["audit_identity_present"] for row in synthetic["audit_summaries"].values()))

    cases = synthetic["case_summaries"]
    require(cases["reactive_default"]["speech_mode"] == "reactive_answer_only")
    require(cases["requested_observation"]["speech_mode"] == "bounded_user_requested_observation")
    require(cases["requested_observation"]["maximum_additional_observations"] == 1)
    require(cases["requested_observation"]["maximum_expansion_sentences"] == 2)
    require(cases["requested_observation"]["maximum_expansion_paragraphs"] == 1)
    require(cases["requested_observation"]["maximum_unsolicited_topic_branches"] == 0)
    require(cases["briefness_suppression"]["speech_mode"] == "reactive_answer_only")
    require(cases["required_clarification"]["speech_mode"] == "required_clarification_only")
    require(cases["repair_without_expansion"]["speech_mode"] == "repair_without_expansion")
    require(cases["brief_closure"]["speech_mode"] == "brief_closure_only" and cases["brief_closure"]["stop_after_current_answer"])
    require(cases["deliberate_silence"]["speech_mode"] == "preserve_deliberate_silence")
    require(cases["deliberate_silence"]["follow_up_question_budget"] == 0)
    require(cases["operator_suppression"]["operator_suppression_applied"])
    require(cases["interruption"]["interruption_honored"])
    require(cases["conflicting_cues"]["expansion_cue_conflict_suppressed"])
    require(cases["expansion_cooldown"]["expansion_cooldown_applied"] and cases["expansion_cooldown"]["recent_expansion_count"] == 2)
    require(cases["stale_context"]["stale_records_ignored"] == 1)
    require(cases["suspicious_context"]["suspicious_records_ignored"] == 1)
    require(cases["malformed_context"]["context_malformed"])
    require(cases["malformed_constraints"]["context_malformed"])
    require(cases["oversized_inputs"]["message_truncated"] and cases["oversized_inputs"]["context_truncated"])
    require(cases["oversized_inputs"]["context_count"] == 24)
    require(cases["forged_follow_up_authority"]["authority_preserved"])
    require(cases["forged_evidence_authority"]["policy_recovered"])
    require(cases["tampered_evidence"]["policy_recovered"])

    audits = synthetic["audit_summaries"]
    require(audits["compliant_observation"]["compliant"])
    require(audits["question_overrun"]["follow_up_budget_exceeded"] and not audits["question_overrun"]["compliant"])
    require(audits["silence_violation"]["silence_violation"] and not audits["silence_violation"]["compliant"])
    require(audits["oversized_response"]["response_truncated_for_audit"])

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "governed-speech-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/governed-speech-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1163.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/governed-speech-checkpoint", body={"confirm": True}
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
        [sys.executable, str(ROOT / "eidolon.py"), "governed-speech-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1163.9")
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.governed_speech_policy; import conscious_agent.governed_speech_checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=90,
    )
    require(imported.returncode == 0 and not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "governed-speech-checkpoint"), None)
require(row is not None and row["builder"] == "build_governed_speech_checkpoint")
require(registry["checkpoint_count"] >= 190)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "governed-speech-checkpoint-panel" in dashboard
    and "/api/cognition/governed-speech-checkpoint" in dashboard
    and "refreshGovernedSpeechCheckpoint" in dashboard
    and "deferred to v1200" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1163, 9) and tuple(map(int, previous.groups())) == (1163, 8))
require("v1164.0-v1164.2 Daily Companion Cognition Checkpoint Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1163.9 Governed Proactive Speech" in next_steps)
require("v1164.0-v1164.2" in next_steps and "v1200" in next_steps)
require("v1163.9 Governed Proactive Speech" in history)

print(f"v1163.9 governed speech checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
