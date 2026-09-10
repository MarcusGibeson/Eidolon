from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import conversational_build_test_loop as loop
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


provider_calls: list[int] = []


def provider(prompt: str) -> str:
    provider_calls.append(1)
    contract = json.loads(prompt)
    content = {
        "main.py": "import argparse\nfrom tool import count_words\np=argparse.ArgumentParser()\np.add_argument('text', nargs='*')\na=p.parse_args()\nprint(count_words(' '.join(a.text)))\n",
        "tool.py": "def count_words(text):\n    return len(str(text).split())\n",
        "tests/test_tool.py": "import unittest\nfrom tool import count_words\nclass Tests(unittest.TestCase):\n    def test_words(self): self.assertEqual(count_words('one two'), 2)\n",
        "README.md": "# Word counter\n",
    }
    return json.dumps({
        "authority": contract["authority"],
        "files": [{"path": path, "operation": "create", "content": content[path]} for path in contract["planned_paths"]],
    })


original_dispatch = loop.run_or_resume_selected_test_adapter


def passing_dispatch(request, **kwargs):
    require(request["status"] == "test_adapter_execution_prepared", request)
    require(request["authority"]["execution_authorized"] is True)
    return {
        "status": "test_adapter_execution_completed",
        "tests_executed": True,
        "outcome": {"state": "passed", "passed": True, "evidence_digest": "e" * 64},
        "cleanup": {"state": "confirmed", "cleanup_confirmed": True},
        "reliability": {"failure_class": None, "retry_disposition": "not_needed"},
        "authority": {"execution_authorized": True, "repair_authorized": False, "apply_authorized": False, "release_authorized": False, "authority_granted": False},
    }


loop.run_or_resume_selected_test_adapter = passing_dispatch
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1210-b-"))
try:
    created = process_ordinary_chat_development_turn(
        "Build me a Python CLI that counts words", action_projection={"intent": {"category": "action_request"}}, runtime_root=runtime,
    )
    proposal = created["proposal"]
    approved = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision 1.", runtime_root=runtime,
    )
    prepared = approved["build_test_loop"]
    phrase = prepared["authorization_phrase"]
    result = process_ordinary_chat_development_turn(
        phrase, runtime_root=runtime, provider_generate=provider, python_executable=sys.executable,
    )
    require(result["active"] is True)
    require(result["event"] == "conversational_build_test_completed", result)
    public = result["build_test_loop"]
    require(public["status"] == "conversational_build_test_completed")
    require(public["completed_stage"] == "complete")
    require(public["provider_contacted"] is True, public)
    require(public["tests_executed"] is True)
    require(public["test_passed"] is True)
    require(public["cleanup_confirmed"] is True)
    require(public["selected_project_modified"] is False)
    require(public["repair_authorized"] is False)
    require(public["apply_authorized"] is False)
    require(public["release_authorized"] is False)
    require(public["authority_granted"] is False)
    require(len(provider_calls) == 1)
    replay = process_ordinary_chat_development_turn(
        phrase, runtime_root=runtime, provider_generate=provider, python_executable=sys.executable,
    )
    require(replay["event"] == "conversational_build_test_completed")
    require(replay["build_test_loop"]["operation_status"] == "resumed")
    require(len(provider_calls) == 1)

    wrong = phrase.replace(prepared["loop_digest"], "0" * 64)
    rejected = process_ordinary_chat_development_turn(wrong, runtime_root=runtime, provider_generate=provider)
    require(rejected["active"] is True)
    require(rejected["event"] == "conversational_build_test_stale_authorization")
finally:
    loop.run_or_resume_selected_test_adapter = original_dispatch
    shutil.rmtree(runtime, ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1210.5-conversational-build-test-execution"') == 2)
require(release.count("tools/v1210_3_5_conversational_build_test_execution_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1210.5", "checks": len(checks), "passed": sum(checks), "provider_calls": len(provider_calls), "tests_executed": True, "selected_project_modified": False, "repair_authorized": False, "apply_authorized": False}, sort_keys=True))
