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
from conscious_agent.natural_conversation_continuity_checkpoint import build_natural_conversation_continuity_checkpoint


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    excluded = {"data", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "reports", "dist", "build"}
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
    report = build_natural_conversation_continuity_checkpoint(runtime_root=runtime, source_root=ROOT)
    require(report["contract_version"] == "v1161.9")
    require(report["checkpoint_id"] == "natural-conversation-continuity:v1161.9")
    require(report["ok"] and report["read_only"] and not report["post_available"])
    require(report["content_free"] and report["authority_preserved"])
    require(report["natural_conversation_continuity_checkpoint_completed"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["forbidden_report_value_count"] == 0)
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "proactive_turn_created", "learning_performed", "identity_rewritten", "memory_corrected",
        "approval_created", "approval_granted", "authorization_created", "installation_performed",
        "promotion_performed", "certification_performed",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require("CONTINUITY_PRIVATE_CANARY" not in serialized)
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
    require(synthetic["case_count"] == 15)
    require(all(row["content_free"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_envelope_complete"] for row in synthetic["case_summaries"].values()))
    require(all(row["prompt_length"] <= 1650 for row in synthetic["case_summaries"].values()))
    require(all(row["authority_preserved"] for row in synthetic["case_summaries"].values()))
    require(all(row["policy_identity_present"] and row["evidence_identity_present"] for row in synthetic["case_summaries"].values()))
    cases = synthetic["case_summaries"]
    require(cases["fresh_turn"]["continuity_relation"] == "fresh_turn" and cases["fresh_turn"]["maximum_prior_turn_references"] == 0)
    require(cases["answer_prior_question"]["consume_prior_question"] and cases["answer_prior_question"]["avoid_reasking_answered_question"])
    require(cases["continue_thread"]["resume_at_next_unfinished_point"] and cases["continue_thread"]["maximum_recap_sentences"] == 0)
    require(cases["repair_thread"]["replace_only_corrected_element"] and cases["repair_thread"]["avoid_repeating_prior_answer"])
    require(cases["close_thread"]["continuity_relation"] == "close_thread")
    require(cases["verified_silence"]["thread_posture"] == "silent_completion")
    require(cases["duplicate_question"]["prior_question_ambiguity_suppressed"] and not cases["duplicate_question"]["consume_prior_question"])
    require(cases["contradictory_linkage"]["contradictory_linkage_suppressed"] and cases["contradictory_linkage"]["continuity_relation"] == "fresh_turn")
    require(cases["stale_history"]["stale_records_ignored"] == 1)
    require(cases["suspicious_history"]["suspicious_records_ignored"] == 1)
    require(cases["oversized_inputs"]["history_count"] == 24 and cases["oversized_inputs"]["history_truncated"])
    require(cases["malformed_history"]["history_malformed"] and cases["malformed_history"]["policy_recovered"])
    require(cases["tampered_evidence"]["policy_recovered"] and cases["tampered_evidence"]["evidence_integrity"] == "degraded")
    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "natural-conversation-continuity-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/natural-conversation-continuity-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1161.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/natural-conversation-continuity-checkpoint", body={"confirm": True}
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
        [sys.executable, str(ROOT / "eidolon.py"), "natural-conversation-continuity-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1161.9")
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.natural_conversation_continuity; import conscious_agent.natural_conversation_continuity_checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=90,
    )
    require(imported.returncode == 0 and not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "natural-conversation-continuity-checkpoint"), None)
require(row is not None and row["builder"] == "build_natural_conversation_continuity_checkpoint")
require(registry["checkpoint_count"] >= 188)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "natural-conversation-continuity-checkpoint-panel" in dashboard
    and "/api/cognition/natural-conversation-continuity-checkpoint" in dashboard
    and "refreshNaturalConversationContinuityCheckpoint" in dashboard
    and "deferred to v1200" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1161, 9) and tuple(map(int, previous.groups())) == (1161, 8))
require("v1162.0-v1162.2 Governed Proactive Speech Foundations" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1161.9 Natural Conversation Continuity" in next_steps)
require("v1162.0-v1162.2" in next_steps and "v1200" in next_steps)
require("v1161.9 Natural Conversation Continuity" in history)

print(f"v1161.9 natural conversation continuity checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
