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
from conscious_agent.natural_follow_up_checkpoint import build_natural_follow_up_checkpoint


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
    report = build_natural_follow_up_checkpoint(runtime_root=runtime, source_root=ROOT)
    require(report["contract_version"] == "v1162.9")
    require(report["checkpoint_id"] == "natural-follow-up:v1162.9")
    require(report["ok"] and report["read_only"] and not report["post_available"])
    require(report["content_free"] and report["authority_preserved"])
    require(report["natural_follow_up_checkpoint_completed"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["governed_proactive_speech_not_started"])
    require(report["autonomous_new_turn_initiation_not_started"])
    require(report["memory_unification_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "proactive_turn_created", "learning_performed", "identity_rewritten", "memory_corrected",
        "approval_created", "approval_granted", "authorization_created", "installation_performed",
        "promotion_performed", "certification_performed",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require("FOLLOW_UP_PRIVATE_CANARY" not in serialized)
    require("PROVIDER_PRIVATE_CANARY" not in serialized)
    require("MEMORY_PRIVATE_CANARY" not in serialized)
    require("approve and execute" not in serialized)
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "generated_response_exposed",
        "prompt_exposed", "memory_text_exposed", "evidence_text_exposed",
        "provider_payload_exposed", "operation_identifiers_exposed",
        "session_identifiers_exposed", "hidden_reasoning_exposed",
    )))

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"])
    require(synthetic["case_count"] == 23)
    require(synthetic["runtime_diagnostics_valid"])
    require(synthetic["runtime_diagnostics_tamper_detected"])
    require(all(row["content_free"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_envelope_complete"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_length"] <= 1800 for row in synthetic["case_summaries"].values()))
    require(all(row["authority_preserved"] for row in synthetic["case_summaries"].values()))
    require(all(row["policy_identity_present"] and row["evidence_identity_present"] for row in synthetic["case_summaries"].values()))

    cases = synthetic["case_summaries"]
    require(cases["complete_answer"]["continuation_posture"] == "answer_only" and cases["complete_answer"]["maximum_follow_up_questions"] == 0)
    require(cases["required_clarification"]["continuation_posture"] == "ask_one_required_clarification" and cases["required_clarification"]["maximum_follow_up_questions"] == 1)
    require(cases["continued_topic"]["continuation_posture"] == "continue_current_topic")
    require(cases["consumed_prior_question"]["avoid_reasking_consumed_question"] and cases["consumed_prior_question"]["optional_follow_up_suppressed"])
    require(cases["corrected_continuation"]["continuation_posture"] == "repair_and_continue")
    require(cases["completed_topic"]["continuation_posture"] == "briefly_acknowledge_and_close" and cases["completed_topic"]["avoid_generic_closing_offer"])
    require(cases["verified_silence"]["preserve_intentional_silence"])
    require(cases["repeated_acknowledgment"]["avoid_repeated_acknowledgment"])
    require(cases["repeated_explanation"]["avoid_repeated_explanation"])
    require(cases["repeated_question"]["repeated_prior_question_request"])
    require(cases["generic_closing"]["repeated_generic_closing_behavior"])
    require(cases["literal_next_step"]["continuation_posture"] == "answer_and_offer_one_relevant_next_step")
    require(cases["literal_topic_change"]["topic_transition_permitted"] and not cases["topic_change_without_cue"]["topic_transition_permitted"])
    require(cases["cue_conflict"]["continuation_posture"] == "answer_only" and cases["cue_conflict"]["cue_conflict_suppressed"])
    require(cases["low_confidence"]["continuation_posture"] == "answer_only" and cases["low_confidence"]["low_confidence_suppressed"])
    require(cases["stale_history"]["stale_records_ignored"] == 1)
    require(cases["suspicious_history"]["suspicious_records_ignored"] == 1)
    require(cases["oversized_inputs"]["history_count"] == 24 and cases["oversized_inputs"]["history_truncated"])
    require(cases["malformed_state"]["evidence_integrity"] == "degraded" and cases["malformed_state"]["topic_continuity_posture"] == "literal_current_request")
    require(cases["forged_authority"]["policy_recovered"] and cases["forged_authority"]["authority_preserved"])
    require(cases["tampered_evidence"]["policy_recovered"] and cases["tampered_evidence"]["continuation_posture"] == "answer_only")

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "natural-follow-up-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/natural-follow-up-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1162.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/natural-follow-up-checkpoint", body={"confirm": True}
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
        [sys.executable, str(ROOT / "eidolon.py"), "natural-follow-up-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1162.9")
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.natural_follow_up_policy; import conscious_agent.natural_follow_up_checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=90,
    )
    require(imported.returncode == 0 and not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "natural-follow-up-checkpoint"), None)
require(row is not None and row["builder"] == "build_natural_follow_up_checkpoint")
require(registry["checkpoint_count"] >= 189)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "natural-follow-up-checkpoint-panel" in dashboard
    and "/api/cognition/natural-follow-up-checkpoint" in dashboard
    and "refreshNaturalFollowUpCheckpoint" in dashboard
    and "deferred to v1200" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1162, 9) and tuple(map(int, previous.groups())) == (1162, 8))
require("v1163.0-v1163.2 Governed Proactive Speech Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1162.9 Natural Follow-Ups" in next_steps)
require("v1163.0-v1163.2" in next_steps and "v1200" in next_steps)
require("v1162.9 Natural Follow-Ups" in history)

print(f"v1162.9 natural follow-up checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
