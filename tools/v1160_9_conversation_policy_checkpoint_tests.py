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
sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.conversation_policy_checkpoint import build_conversation_policy_checkpoint

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


def signature(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        h.update(b"missing")
        return h.hexdigest()
    for path in sorted(
        p for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
        and p.suffix.lower() not in {".pyc", ".pyo"}
        and ".pytest_cache" not in p.parts
    ):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_conversation_policy_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1160.9")
    require(report["checkpoint_id"] == "conversation-policy:v1160.9")
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 40)
    require(report["summary"]["synthetic_contract_check_count"] >= 22)
    require(report["summary"]["synthetic_case_count"] == 14)
    require(report["summary"]["registered_checkpoint_count"] >= 187)
    require(report["summary"]["discourse_prompt_maximum_chars"] == 1600)
    require(report["summary"]["message_analysis_maximum_chars"] == 4096)
    require(report["summary"]["history_record_maximum_count"] == 24)
    require(report["summary"]["authoritative_conversation_path_count"] == 2)
    require(report["summary"]["privacy_forbidden_entry_count"] == 0)
    require(report["summary"]["privacy_content_finding_count"] == 0)
    require(len(report["remaining_limitations"]) == 5)
    require(report["read_only"] and not report["post_available"] and report["content_free"])
    require(report["authority_preserved"] and report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["native_provider_certification_pending"])
    require(report["conversation_policy_checkpoint_completed"])
    require(report["conversation_and_learning_arc_started"])
    require(report["governed_proactive_speech_not_started"])
    require(report["bounded_learning_mutation_not_started"])
    require(not report["consciousness_proven"] and not report["sentience_proven"] and not report["personhood_proven"])
    require(report["forbidden_report_value_count"] == 0)
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "goal_modified", "plan_created",
        "decision_created", "intention_created", "conflict_resolved",
        "approval_request_created", "approval_created", "approval_granted",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed",
        "certification_performed", "proactive_turn_created", "learning_performed",
        "identity_rewritten", "memory_corrected",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require("DISCOURSE_PRIVATE_CANARY" not in serialized)
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
    require(all(row["content_free"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_envelope_complete"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_length"] <= 1600 for row in synthetic["case_summaries"].values()))
    require(all(row["authority_preserved"] for row in synthetic["case_summaries"].values()))
    require(all(row["policy_identity_present"] and row["evidence_identity_present"] for row in synthetic["case_summaries"].values()))
    cases = synthetic["case_summaries"]
    require(cases["continuation"]["maximum_prior_turn_references"] == 1 and cases["continuation"]["maximum_recap_sentences"] == 0)
    require(cases["correction"]["repair_sequence"] == "acknowledge_correct_answer")
    require(cases["clarification"]["completion_shape"] == "await_required_reply")
    require(cases["closure"]["completion_shape"] == "close_without_offer")
    require(cases["verified_silence"]["completion_shape"] == "silent_completion")
    require(cases["contradictory_cues"]["contradictory_cues_suppressed"])
    require(cases["repeated_repair_loop"]["repeated_repair_loop_suppressed"])
    require(cases["stale_history"]["stale_history_records_ignored"] == 1)
    require(cases["suspicious_history"]["suspicious_history_records_ignored"] == 1)
    require(cases["oversized_inputs"]["history_count"] == 24 and cases["oversized_inputs"]["history_truncated"])
    require(cases["malformed_context"]["history_malformed"] and cases["malformed_context"]["policy_recovered"])
    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "conversation-policy-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/conversation-policy-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1160.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/conversation-policy-checkpoint", body={"confirm": True}
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
        [sys.executable, str(ROOT / "eidolon.py"), "conversation-policy-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1160.9")
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.conversation_discourse_policy; import conscious_agent.conversation_policy_checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=90,
    )
    require(imported.returncode == 0 and not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "conversation-policy-checkpoint"), None)
require(row is not None and row["builder"] == "build_conversation_policy_checkpoint")
require(registry["checkpoint_count"] >= 187)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "conversation-policy-checkpoint-panel" in dashboard
    and "/api/cognition/conversation-policy-checkpoint" in dashboard
    and "refreshConversationPolicyCheckpoint" in dashboard
    and "deferred to v1200" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1160, 9) and tuple(map(int, previous.groups())) == (1160, 8))
require("v1161.0-v1161.2 Natural Conversation Continuity Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1160.9 Conversation Policy" in next_steps)
require("v1161.0-v1161.2" in next_steps and "v1200" in next_steps)
require("v1160.9 Conversation Policy" in history)

print(f"v1160.9 conversation policy checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
