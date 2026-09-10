from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from isolated_self_modification_foundations import source_only_manifest
from v1489_generic_self_development_execution import (
    GenericSelfDevelopmentError,
    _parse_response,
    execute_generic_isolated_proposal,
)
from v1489_product_capability_integration import (
    _PREPARE_SELF_PROPOSAL,
    _prepare_isolated_proposal,
)


checks: list[str] = []


def require(condition: bool, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def fixture(base: Path) -> Path:
    root = base / "Eidolon"
    (root / "conscious_agent").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "conscious_agent" / "__init__.py").write_text("", encoding="utf-8")
    (root / "conscious_agent" / "app.py").write_text(
        "def value():\n    return 1\n", encoding="utf-8"
    )
    (root / "tools" / "v1489_product_capability_integration_tests.py").write_text(
        "from pathlib import Path\nimport sys\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\nfrom conscious_agent.app import value\nassert value() == 2\n",
        encoding="utf-8",
    )
    (root / "tools" / "v1489_generic_self_development_execution_tests.py").write_text(
        "print('fixture generic execution check passed')\n",
        encoding="utf-8",
    )
    (root / "tools" / "v1489_symbol_level_refactoring_tests.py").write_text(
        "print('fixture symbol refactoring check passed')\n",
        encoding="utf-8",
    )
    return root


def proposal(scope: list[str] | None = None) -> dict[str, object]:
    base: dict[str, object] = {
        "proposal_id": "improvement-1234567890abcdef1234",
        "proposal_digest": "a" * 64,
        "improvement_class": "generic_test_boundary",
        "proposed_change": "Extract a tiny value helper behind a retained import.",
        "expected_benefit": "Prove bounded structured coding.",
        "affected_scope": scope or ["conscious_agent/app.py", "conscious_agent/value_helper.py"],
    }
    return base


def response(p: dict[str, object]) -> str:
    return json.dumps(
        {
            "authority": {
                "proposal_id": p["proposal_id"],
                "proposal_digest": p["proposal_digest"],
            },
            "changes": [
                {
                    "path": "conscious_agent/app.py",
                    "action": "modify",
                    "edits": [
                        {
                            "find": "def value():\n    return 1\n",
                            "replace": "from conscious_agent.value_helper import VALUE\n\n\ndef value():\n    return VALUE\n",
                        }
                    ],
                },
                {
                    "path": "conscious_agent/value_helper.py",
                    "action": "create",
                    "content": "VALUE = 2\n",
                },
            ],
        }
    )


wrapped = "I prepared the bounded change.\n```json\n" + response(proposal()) + "\n```\nNo files were applied."
require(_parse_response(wrapped)["authority"]["proposal_id"] == proposal()["proposal_id"], "single wrapped JSON object accepted")
ambiguous = response(proposal()) + "\n" + response(proposal())
try:
    _parse_response(ambiguous)
    raise AssertionError("multiple provider objects unexpectedly accepted")
except ValueError:
    require(True, "multiple structured objects rejected")
python_literal = "Here is the result:\n```python\n" + repr(json.loads(response(proposal()))) + "\n```"
require(_parse_response(python_literal)["authority"]["proposal_id"] == proposal()["proposal_id"], "single Python-style literal accepted")


with tempfile.TemporaryDirectory(prefix="eidolon-v1489-generic-") as td:
    workspace = fixture(Path(td))
    p = proposal()
    calls: list[str] = []
    baseline = source_only_manifest(workspace)
    before = baseline["source_manifest_digest"]
    baseline_content_digests = {row["relative_path"]: row["content_digest"] for row in baseline["files"]}
    result = execute_generic_isolated_proposal(
        workspace, p, provider_generate=lambda prompt: calls.append(prompt) or response(p),
        baseline_content_digests=baseline_content_digests,
    )
    require(result["baseline_manifest_digest"] == before, "preverified baseline digest reused exactly")
    require(result["checks_passed"] is True, "valid structured candidate passes")
    require(result["provider_request_count"] == 1 and len(calls) == 1, "provider called exactly once")
    require(len(calls[0]) < 20_000, "provider prompt fits bounded local context budget")
    require(result["changed_file_count"] == 2, "exact bounded file count")
    require(source_only_manifest(workspace)["source_manifest_digest"] != before, "workspace changed")
    require((workspace / "conscious_agent" / "app.py").read_text(encoding="utf-8").endswith("return VALUE\n"), "exact edit applied")

with tempfile.TemporaryDirectory(prefix="eidolon-v1500-dynamic-refactor-") as td:
    workspace = fixture(Path(td))
    (workspace / "paths.py").write_text("DATA_DIR = None\nROOT_DIR = None\ndef path_reference(x): return x\n", encoding="utf-8")
    (workspace / "conscious_agent" / "app.py").write_text(
        "from paths import DATA_DIR, ROOT_DIR, path_reference\n\nVALUE = 2\n\ndef value():\n    return VALUE\n\ndef double():\n    return value() * VALUE\n", encoding="utf-8"
    )
    (workspace / "tools" / "v1489_product_capability_integration_tests.py").write_text(
        "from pathlib import Path\nimport sys\nroot=Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(root))\nsys.path.insert(0, str(root/'conscious_agent'))\nfrom conscious_agent.app import value\nassert value() == 2\n", encoding="utf-8"
    )
    dynamic = {
        "proposal_id": "improvement-fedcba0987654321fedc",
        "proposal_digest": "d" * 64,
        "improvement_class": "dynamic_symbol_refactoring",
        "proposed_change": "Extract exact discovered value and double symbol family behind retained wrappers.",
        "expected_benefit": "Prove deterministic dynamic discovery implementation.",
        "affected_scope": ["conscious_agent/app.py", "conscious_agent/dynamic_helpers.py"],
        "source_symbols": ["value", "double"],
    }
    result = execute_generic_isolated_proposal(
        workspace, dynamic, provider_generate=lambda _: (_ for _ in ()).throw(AssertionError("provider contacted"))
    )
    require(result["checks_passed"] is True, "dynamic discovered symbol family verifies")
    require(result["provider_request_count"] == 0, "dynamic exact-symbol refactor is provider free")
    require(result["selected_symbols"] == ["value", "double"], "dynamic exact symbols remain bound")
    require((workspace / "conscious_agent" / "dynamic_helpers.py").is_file(), "dynamic destination module created")

with tempfile.TemporaryDirectory(prefix="eidolon-v1489-repair-") as td:
    workspace = fixture(Path(td))
    p = proposal()
    calls = []

    def repaired(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return "not-json"
        if "Create the new bounded helper module" in prompt:
            return "```python\nVALUE = 2\n```"
        full = json.loads(response(p))
        full["changes"] = [row for row in full["changes"] if row["path"] == "conscious_agent/app.py"]
        return json.dumps(full)

    result = execute_generic_isolated_proposal(workspace, p, provider_generate=repaired)
    require(result["repair_attempt_count"] == 1, "one bounded repair recorded")
    require(result["provider_request_count"] == 3 and len(calls) == 3, "staged repair requests bounded")
    require("provider_output_not_object" not in calls[-1], "private output not echoed unnecessarily")

with tempfile.TemporaryDirectory(prefix="eidolon-v1489-reject-") as td:
    workspace = fixture(Path(td))
    before = source_only_manifest(workspace)["source_manifest_digest"]
    rejected = False
    try:
        execute_generic_isolated_proposal(
            workspace,
            proposal(["data/projects.json"]),
            provider_generate=lambda _: (_ for _ in ()).throw(AssertionError("provider contacted")),
        )
    except GenericSelfDevelopmentError as exc:
        rejected = exc.code == "generic_self_development_private_path_rejected"
    require(rejected, "private runtime path rejected before provider")
    require(source_only_manifest(workspace)["source_manifest_digest"] == before, "rejected scope preserves workspace")

with tempfile.TemporaryDirectory(prefix="eidolon-v1489-exhaust-") as td:
    workspace = fixture(Path(td))
    before = source_only_manifest(workspace)["source_manifest_digest"]
    calls = []
    try:
        execute_generic_isolated_proposal(
            workspace, proposal(), provider_generate=lambda prompt: calls.append(prompt) or "not-json"
        )
        raise AssertionError("exhausted candidate unexpectedly passed")
    except GenericSelfDevelopmentError as exc:
        require(exc.code.startswith("generic_self_development_attempts_exhausted:"), "exhaustion classified")
        require(exc.provider_request_count == 2, "exhaustion request count retained")
        require(exc.failure_codes == ["provider_output_not_single_structured_object", "provider_created_python_module_has_no_definitions"], "failure classes retained")
    require(len(calls) == 2, "malformed staged output repair bounded")
    require(source_only_manifest(workspace)["source_manifest_digest"] == before, "exhaustion restores clean workspace")

with tempfile.TemporaryDirectory(prefix="eidolon-v1489-refresh-") as td:
    base = Path(td)
    source = fixture(base / "source")
    runtime = base / "runtime"
    old_runtime = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        p = proposal()
        p.update(
            {
                "state": "proposed",
                "isolated_workspace_created": False,
                "isolated_preparation_authorized": False,
                "source_modified": False,
            }
        )
        record_path = runtime / "self_development_proposals" / f"{p['proposal_id']}.json"
        record_path.parent.mkdir(parents=True)
        record_path.write_text(json.dumps(p), encoding="utf-8")
        phrase = f"Prepare isolated self-development proposal {p['proposal_id']} digest {str(p['proposal_digest'])[:16]}."
        control = _PREPARE_SELF_PROPOSAL.fullmatch(phrase)
        require(control is not None, "refresh fixture exact phrase parses")
        first = _prepare_isolated_proposal(control, source)
        require(first["event"] == "isolated_self_development_prepared", "initial workspace prepared")
        stored = json.loads(record_path.read_text(encoding="utf-8"))
        stored["state"] = "isolated_implementation_blocked"
        stored["implementation_blocker"] = "fixture_failure"
        record_path.write_text(json.dumps(stored), encoding="utf-8")
        (source / "conscious_agent" / "app.py").write_text("def value():\n    return 9\n", encoding="utf-8")
        refreshed = _prepare_isolated_proposal(control, source)
        require(refreshed["event"] == "isolated_self_development_preparation_refreshed", "stale failed workspace refreshed")
        require((runtime / "self_development_proposals" / "workspaces" / str(p["proposal_id"]) / "Eidolon" / "conscious_agent" / "app.py").read_text(encoding="utf-8").endswith("return 9\n"), "refreshed workspace uses current source")
        require(any((runtime / "self_development_proposals" / "workspaces" / str(p["proposal_id"])).glob("Eidolon.stale-*")), "stale clean workspace retained for audit")
    finally:
        if old_runtime is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_runtime

print(json.dumps({"ok": True, "suite": "v1489-generic-self-development-execution", "passed": len(checks), "failed": 0, "checks": checks}, sort_keys=True))
