from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "conscious_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "conscious_agent"))

from javascript_tool_implementation_foundations import run_or_resume_javascript_tool_implementation
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def runtime(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=f"eid-v1207-{prefix}-"))


def approved(runtime_root: Path, *, session_id: str = "v1207") -> dict:
    turn = process_ordinary_chat_development_turn(
        "Build me a Node command-line tool that counts words",
        action_projection={"intent": {"category": "action_request"}},
        session_id=session_id,
        runtime_root=runtime_root,
    )
    proposal = turn["proposal"]
    approval = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",
        runtime_root=runtime_root,
    )
    if approval.get("event") != "approval_consumed":
        raise AssertionError(approval)
    return proposal


def provider(mode: str = "pass", calls: list[int] | None = None) -> Callable[[str], str]:
    calls = calls if calls is not None else []

    def generate(prompt: str) -> str:
        calls.append(1)
        payload = json.loads(prompt)
        script = "node --test"
        test = (
            "const test=require('node:test');const assert=require('node:assert');"
            "const {countWords}=require('../lib/tool');"
            "test('counts',()=>assert.equal(countWords('one two'),2));\n"
        )
        tool = "exports.countWords=t=>String(t).trim()?String(t).trim().split(/\\s+/).length:0;\n"
        if mode == "fail":
            test = test.replace("),2));", "),3));")
        elif mode == "network":
            test = "const http=require('node:http');\n" + test
        elif mode == "unsupported_script":
            script = "npm run actual-tests"
        elif mode == "selected_script":
            script = "node --test tests/tool.test.js"
        elif mode == "timeout":
            test = "const test=require('node:test');test('hang',async()=>{setInterval(()=>{},1000);await new Promise(()=>{});});\n"
        elif mode == "output":
            test = "const test=require('node:test');test('output',()=>{process.stdout.write('x'.repeat(700000));});\n"
        elif mode == "dynamic_import":
            test = "const test=require('node:test');test('dynamic',async()=>{const n='node:'+'http';await import(n);});\n"
        elif mode == "filesystem_write":
            test = "const fs=require('node:fs');fs.writeFileSync('forbidden-node.txt','x');\n" + test
        elif mode == "no_test":
            test = "exports.notATest=true;\n"
        content = {
            "package.json": json.dumps({"name": "word-counter", "private": True, "type": "commonjs", "scripts": {"test": script}}),
            "cli.js": (
                "const {countWords}=require('./lib/tool');"
                "if(process.argv.includes('--help')){console.log('usage');process.exit(0)}"
                "console.log(countWords(process.argv.slice(2).join(' ')));\n"
            ),
            "lib/tool.js": tool,
            "tests/tool.test.js": test,
        }
        return json.dumps({
            "authority": payload["authority"],
            "files": [
                {"path": path, "operation": "create", "content": content[path]}
                for path in payload["planned_paths"]
            ],
        })

    return generate


def campaign(runtime_root: Path, *, mode: str = "pass", calls: list[int] | None = None, session_id: str = "v1207"):
    proposal = approved(runtime_root, session_id=session_id)
    implementation = run_or_resume_javascript_tool_implementation(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime_root,
        provider_generate=provider(mode, calls),
    )
    if not implementation.get("workspace_digest"):
        raise AssertionError(implementation)
    return proposal, implementation


def cleanup(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
