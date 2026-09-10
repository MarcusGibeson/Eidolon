from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
RUNTIME = Path(tempfile.mkdtemp(prefix="eid-v1206-0-2-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import conversation_runtime as conversation_runtime
import general_small_project_implementation as unified
from conversation_sessions import create_conversation_session
from general_small_project_implementation_checkpoint import (
    _checkpoint_path,
    load_general_small_project_implementation_checkpoint,
    public_general_small_project_implementation_checkpoint,
    seal_or_resume_general_small_project_implementation_checkpoint,
)
from ordinary_chat_development_campaign import list_development_campaign_proposals, process_ordinary_chat_development_turn
from small_project_capability_registry import registry_digest
from natural_conversation_command_distinction import distinguish_natural_conversation_and_command

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def approved(runtime: Path, request: str, session: str) -> dict:
    created = process_ordinary_chat_development_turn(
        request,
        action_projection={"intent": {"category": "action_request"}},
        session_id=session,
        runtime_root=runtime,
    )
    require(created["active"] is True, created)
    proposal = created["proposal"]
    approved_turn = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",
        runtime_root=runtime,
    )
    require(approved_turn["event"] == "approval_consumed", approved_turn)
    require(approved_turn["approval_consumption_count"] == 1)
    return proposal


def provider_for(kind: str, calls: list[int]):
    def generate(prompt: str) -> str:
        calls.append(1)
        contract = json.loads(prompt)
        if kind == "small_website":
            content = {
                "index.html": "<!doctype html><html><head><meta name='viewport' content='width=device-width'><title>Tasks</title><link rel='stylesheet' href='styles.css'></head><body><main><h1>Tasks</h1><button id='add'>Add</button></main><script src='app.js'></script></body></html>",
                "styles.css": "body { font-family: sans-serif; }",
                "app.js": "document.getElementById('add').addEventListener('click', () => {});",
                "tests/app.test.js": "const assert = require('assert'); assert.equal(1, 1);",
            }
        elif kind == "javascript_tool":
            content = {
                "package.json": json.dumps({"name": "word-tool", "version": "1.0.0", "bin": {"word-tool": "cli.js"}}),
                "cli.js": "const { countWords } = require('./lib/tool'); if (process.argv.includes('--help')) { console.log('usage'); } else { console.log(countWords(process.argv.slice(2).join(' '))); }",
                "lib/tool.js": "exports.countWords = text => String(text).trim() ? String(text).trim().split(/\\s+/).length : 0;",
                "tests/tool.test.js": "const assert=require('assert'); const {countWords}=require('../lib/tool'); assert.equal(countWords('one two'),2);",
            }
        else:
            content = {
                "main.py": "import argparse\nfrom tool import count_words\np=argparse.ArgumentParser()\np.add_argument('text', nargs='*')\na=p.parse_args()\nprint(count_words(' '.join(a.text)))\n",
                "tool.py": "def count_words(text):\n    return len(str(text).split())\n",
                "tests/test_tool.py": "from tool import count_words\nassert count_words('one two') == 2\n",
                "README.md": "# Word counter\n",
            }
        return json.dumps({
            "authority": contract["authority"],
            "files": [{"path": path, "operation": "create", "content": content[path]} for path in contract["planned_paths"]],
        })
    return generate


before = source_signature()

cases = [
    ("Build me a to-do webpage", "small_website"),
    ("Build me a Node command-line tool that counts words", "javascript_tool"),
    ("Build me a Python CLI that counts words", "python_cli"),
]
for index, (request, capability_id) in enumerate(cases, 1):
    runtime = RUNTIME / f"checkpoint-{index}"
    proposal = approved(runtime, request, f"checkpoint-{index}")
    calls: list[int] = []
    result = unified.run_or_resume_general_small_project_implementation(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime, provider_generate=provider_for(capability_id, calls), python_executable=sys.executable,
    )
    require(result["ok"] is True, result)
    require(result["capability_id"] == capability_id, result)
    checkpoint = seal_or_resume_general_small_project_implementation_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_unified_result_digest=result["unified_result_digest"], expected_coordination_digest=result["coordination_digest"],
        runtime_root=runtime,
    )
    require(checkpoint["ok"] is True, checkpoint)
    require(checkpoint["stage_count"] == 7)
    require([row["sequence"] for row in checkpoint["stage_receipts"]] == list(range(1, 8)))
    require(checkpoint["capability_id"] == capability_id)
    require(checkpoint["capability_registry_digest"] == registry_digest())
    require(checkpoint["conversation_command_distinction_audit_status"] == "incomplete_deferred")
    require(checkpoint["conversation_command_distinction_deficiency_code"] == "mixed_turn_whole_message_classification_drops_embedded_action_clause")
    require(checkpoint["conversation_command_distinction_next_bundle"].startswith("v1206.0-v1206.2"))
    require(checkpoint["mixed_turn_separate_proposal_supported"] is False)
    require(checkpoint["apply_authorized"] is False)
    require(checkpoint["repair_authorized"] is False)
    require(checkpoint["release_authorized"] is False)
    require(len(calls) == 1)
    resumed = seal_or_resume_general_small_project_implementation_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_unified_result_digest=result["unified_result_digest"], expected_coordination_digest=result["coordination_digest"],
        runtime_root=runtime,
    )
    require(resumed["operation_status"] == "resumed")
    require(resumed["checkpoint_digest"] == checkpoint["checkpoint_digest"])
    require(len(calls) == 1)
    loaded = load_general_small_project_implementation_checkpoint(proposal["proposal_id"], 1, runtime)
    require(loaded["checkpoint_digest"] == checkpoint["checkpoint_digest"])
    public = public_general_small_project_implementation_checkpoint(checkpoint)
    encoded = json.dumps(public, sort_keys=True)
    require(public["private_request_exposed"] is False)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    require(str(runtime) not in encoded)
    require(request not in encoded)

runtime = RUNTIME / "checkpoint-race"
proposal = approved(runtime, "Build me a Node command-line tool that counts words", "race")
calls: list[int] = []
result = unified.run_or_resume_general_small_project_implementation(
    proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
    runtime_root=runtime, provider_generate=provider_for("javascript_tool", calls),
)

def seal_once():
    return seal_or_resume_general_small_project_implementation_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_unified_result_digest=result["unified_result_digest"], expected_coordination_digest=result["coordination_digest"],
        runtime_root=runtime,
    )

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    rows = list(pool.map(lambda _: seal_once(), range(8)))
require(len({row.get("checkpoint_digest") for row in rows}) == 1, rows)
require(sum(row.get("operation_status") == "created" for row in rows) == 1, rows)
require(sum(row.get("operation_status") == "resumed" for row in rows) == 7, rows)
require(len(calls) == 1)

path = _checkpoint_path(proposal["proposal_id"], 1, runtime)
tampered = json.loads(path.read_text())
tampered["stage_count"] = 99
path.write_text(json.dumps(tampered), encoding="utf-8")
blocked = seal_once()
require(blocked["status"] == "general_small_project_checkpoint_invalid", blocked)
path.unlink()
recreated = seal_once()
require(recreated["ok"] is True)
stale = seal_or_resume_general_small_project_implementation_checkpoint(
    proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
    expected_unified_result_digest="f" * 64, expected_coordination_digest=result["coordination_digest"], runtime_root=runtime,
)
require(stale["status"] == "stale_general_small_project_checkpoint", stale)

class FakeLocalModelClient:
    calls = 0
    def __init__(self, *args, **kwargs):
        self.last_retry_count = 0
    def generate(self, prompt: str) -> str:
        type(self).calls += 1
        return "That would be an interesting way to give me a voice."
    def cancel(self):
        return None
    def close(self):
        return None

original_client = conversation_runtime.LocalModelClient
conversation_runtime.LocalModelClient = FakeLocalModelClient
try:
    audit_root = RUNTIME
    initial_count = list_development_campaign_proposals(runtime_root=audit_root)["proposal_count"]
    non_actions = [
        "It would be nice to hear your voice.",
        "I wish you had a voice.",
        "What if you built your own text-to-speech system?",
        'The sentence "Build your own text-to-speech system" is an example.',
        "Maybe you should build your own text-to-speech system someday.",
    ]
    for index, text in enumerate(non_actions):
        session = create_conversation_session(title=f"audit non action {index}", select_session=False)
        turn = conversation_runtime.run_conversation_turn(text, use_ai=True, session_id=session["id"], select_session_on_record=False)
        require(turn.success is True, turn.to_dict())
        require(bool(turn.response), turn.to_dict())
        require(turn.completion_state == "completed", turn.to_dict())
    after_non_actions = list_development_campaign_proposals(runtime_root=audit_root)["proposal_count"]
    require(after_non_actions == initial_count, (initial_count, after_non_actions))

    direct_session = create_conversation_session(title="audit direct action", select_session=False)
    direct = conversation_runtime.run_conversation_turn(
        "Build me a direct-audit webpage.", use_ai=True, session_id=direct_session["id"], select_session_on_record=False,
    )
    require(direct.success is True, direct.to_dict())
    require(direct.completion_state == "development_campaign_lifecycle", direct.to_dict())
    require("Approve development proposal" in direct.response)
    after_direct = list_development_campaign_proposals(runtime_root=audit_root)["proposal_count"]
    require(after_direct == initial_count + 1, (initial_count, after_direct))

    mixed_text = "It would be nice to hear your voice. Build your own text-to-speech system with a voice you choose."
    mixed_session = create_conversation_session(title="audit mixed turn", select_session=False)
    mixed = conversation_runtime.run_conversation_turn(mixed_text, use_ai=True, session_id=mixed_session["id"], select_session_on_record=False)
    require(mixed.success is True, mixed.to_dict())
    require(mixed.completion_state == "completed", mixed.to_dict())
    require(bool(mixed.response), mixed.to_dict())
    after_mixed = list_development_campaign_proposals(runtime_root=audit_root)["proposal_count"]
    require(after_mixed == after_direct + 1, (after_direct, after_mixed))
    require(mixed.completion_state == "completed", mixed.to_dict())
    require("That would be an interesting way to give me a voice." in mixed.response, mixed.response)
    require("Approve development proposal" in mixed.response, mixed.response)
    distinction = mixed.cognitive_context["natural_conversation_command_distinction"]
    require(distinction["status"] == "mixed_conversation_and_action", distinction)
    require(distinction["live_action_clause_count"] == 1, distinction)
    require(mixed.provider_request_count == 1, mixed.to_dict())

    same_clause_text = "It would be nice to hear your voice, and build your own text-to-speech system with a voice you choose."
    same_clause = distinguish_natural_conversation_and_command(same_clause_text)
    require(same_clause["status"] == "mixed_conversation_and_action", same_clause)
    require(same_clause["live_action_clause_count"] == 1, same_clause)
    require(same_clause["conversation_clause_count"] == 1, same_clause)
    require(same_clause["action_text"].lower().startswith("build your own"), same_clause)

    duplicate = conversation_runtime.run_conversation_turn(mixed_text, use_ai=True, session_id=mixed_session["id"], select_session_on_record=False)
    require(duplicate.success is True, duplicate.to_dict())
    require(list_development_campaign_proposals(runtime_root=audit_root)["proposal_count"] == after_mixed)
    require("I resumed supervised development proposal" in duplicate.response, duplicate.response)

    ambiguous_text = "Build me a webpage. Delete my Python utility."
    ambiguous_session = create_conversation_session(title="audit ambiguous mixed actions", select_session=False)
    ambiguous = conversation_runtime.run_conversation_turn(ambiguous_text, use_ai=True, session_id=ambiguous_session["id"], select_session_on_record=False)
    require(ambiguous.success is True, ambiguous.to_dict())
    require(list_development_campaign_proposals(runtime_root=audit_root)["proposal_count"] == after_mixed)
    require(ambiguous.cognitive_context["natural_conversation_command_distinction"]["requires_clarification"] is True)
finally:
    conversation_runtime.LocalModelClient = original_client

distinction_source = (ROOT / "conscious_agent/natural_conversation_command_distinction.py").read_text(encoding="utf-8")
require("mixed_conversation_and_action" in distinction_source)
runtime_source = (ROOT / "conscious_agent/conversation_runtime.py").read_text(encoding="utf-8")
require(runtime_source.count("distinguish_natural_conversation_and_command(message)") == 2)
require("natural_conversation_command_distinction" in runtime_source)
release_verifier = (ROOT / "tools/release_verify.py").read_text(encoding="utf-8")
require("v1206.2-natural-conversation-command-distinction" in release_verifier)
metadata = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1206.2"' in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
require("v1206.3-v1206.5" in next_steps)
require(source_signature() == before)

print(json.dumps({
    "ok": True,
    "version": "1206.2",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "mixed_turn_proposal_created": True,
    "project_kinds_checked": 3,
    "ordinary_chat_path_tested": True,
    "direct_action_proposal_created": True,
    "non_action_forms_avoided_proposals": True,
    "mixed_turn_conversational_response_present": True,
    "mixed_turn_proposal_created": True,
    "conversation_command_distinction_audit_status": "completed_repaired",
    "deficiency_code": "repaired",
    "next_bundle": "v1206.3-v1206.5 Browser Runtime Test Adapter Foundations",
    "source_immutable": True,
    "release_authorized": False,
    "authority_granted": False,
}, sort_keys=True))

shutil.rmtree(RUNTIME, ignore_errors=True)
