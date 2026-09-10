from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import general_small_project_implementation as unified
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from small_project_capability_registry import (
    capability_by_id,
    capability_for_project_kind,
    list_small_project_capabilities,
    registry_digest,
    validate_registry,
)

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
            "files": [
                {"path": path, "operation": "create", "content": content[path]}
                for path in contract["planned_paths"]
            ],
        })
    return generate


before = source_signature()
registry = list_small_project_capabilities()
require(registry["status"] == "small_project_capability_registry_ready")
require(registry["capability_count"] == 3)
require(validate_registry())
require(registry["registry_digest"] == registry_digest())
require(set(row["capability_id"] for row in registry["capabilities"]) == {"small_website", "javascript_tool", "python_cli"})
require(capability_for_project_kind("new_small_web_project").capability_id == "small_website")
require(capability_for_project_kind("new_javascript_tool_project").capability_id == "javascript_tool")
require(capability_for_project_kind("new_python_cli_project").capability_id == "python_cli")
require(capability_for_project_kind("unsupported_project_type") is None)
require(capability_by_id("python_cli").preview_required is False)
require(all(row["authority_granted"] is False for row in registry["capabilities"]))
require(registry["private_request_included"] is False)
require(registry["private_path_included"] is False)

cases = [
    ("Build me a to-do webpage", "web", "small_website", "new_small_web_project"),
    ("Build me a Node command-line tool that counts words", "js", "javascript_tool", "new_javascript_tool_project"),
    ("Build me a Python CLI that counts words", "py", "python_cli", "new_python_cli_project"),
]
for request, session, capability_id, project_kind in cases:
    runtime = Path(tempfile.mkdtemp(prefix=f"eid-v1205-{session}-"))
    try:
        proposal = approved(runtime, request, session)
        calls: list[int] = []
        result = unified.run_or_resume_general_small_project_implementation(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            runtime_root=runtime,
            provider_generate=provider_for(capability_id, calls),
            python_executable=sys.executable,
        )
        require(result["ok"] is True, result)
        require(result["capability_id"] == capability_id, result)
        require(result["project_kind"] == project_kind, result)
        require(result["supported"] is True)
        require(result["coordinator"] == "general_small_project_implementation")
        require(result["capability_registry_digest"] == registry_digest())
        require(result["operator_review_required"] is True)
        require(result["apply_authorized"] is False)
        require(result["repair_authorized"] is False)
        require(result["release_authorized"] is False)
        require(len(calls) == 1)
        resumed = unified.run_or_resume_general_small_project_implementation(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            runtime_root=runtime,
            provider_generate=provider_for(capability_id, calls),
            python_executable=sys.executable,
        )
        require(resumed["unified_result_digest"] == result["unified_result_digest"])
        require(len(calls) == 1)
        public = unified.public_general_small_project_result(result)
        encoded = json.dumps(public, sort_keys=True)
        require(public["capability_id"] == capability_id)
        require(public["private_request_exposed"] is False)
        require(public["private_path_exposed"] is False)
        require(public["private_content_exposed"] is False)
        require(str(runtime) not in encoded)
        require("count_words" not in encoded)
    finally:
        shutil.rmtree(runtime, ignore_errors=True)

# Unsupported routing returns a content-free limitation and contacts no provider.
original_plan = unified.create_or_resume_grounded_plan
try:
    unified.create_or_resume_grounded_plan = lambda *args, **kwargs: {
        "planning_digest": "a" * 64,
        "project_kind": "mobile_application",
    }
    unsupported = unified.run_or_resume_general_small_project_implementation(
        "proposal-unsupported",
        expected_revision=1,
        expected_revision_digest="b" * 64,
        provider_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("provider contacted")),
    )
    require(unsupported["ok"] is False)
    require(unsupported["status"] == "unsupported_small_project_kind")
    require(unsupported["provider_contacted"] is False)
    require(unsupported["authority_granted"] is False)
    require(bool(unsupported["limitation_digest"]))
finally:
    unified.create_or_resume_grounded_plan = original_plan

# Registry validation rejects duplicate project-kind ownership.
rows = registry["capabilities"]
duplicate = [dict(rows[0]), dict(rows[1])]
duplicate[1]["project_kinds"] = list(rows[0]["project_kinds"])
require(validate_registry(duplicate) is False)

# Dashboard and release registration are present and POST-only.
dashboard = (ROOT / "conscious_agent/dashboard.py").read_text(encoding="utf-8")
require('/api/development-campaign/implement-small-project' in dashboard)
require('run_or_resume_general_small_project_implementation' in dashboard)
require('/api/development-campaign/small-project-capabilities' in dashboard)
verifier = (ROOT / "tools/post_review_development_verify.py").read_text(encoding="utf-8")
require('v1205.0-v1205.2 general small-project implementation consolidation' in verifier)
require('v1205_0_2_general_small_project_consolidation_tests.py' in verifier)
release_verifier = (ROOT / 'tools/release_verify.py').read_text(encoding='utf-8')
require(release_verifier.count('v1205.2-general-small-project-implementation-consolidation') == 2)
metadata = (ROOT / "release_metadata.py").read_text(encoding="utf-8")
require('1205.2' in metadata)
require(source_signature() == before)

print(json.dumps({
    "ok": True,
    "version": "1205.2",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "capability_count": 3,
    "provider_calls_per_project_kind": 1,
    "source_immutable": True,
    "selected_project_modified": False,
    "dependencies_installed": False,
    "network_allowed": False,
    "repair_authorized": False,
    "apply_authorized": False,
    "release_authorized": False,
}, sort_keys=True))
