from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from symbol_level_refactoring import (
    build_symbol_extraction_changes,
    build_symbol_inventory,
    build_symbol_selection_prompt,
    parse_symbol_selection,
)


checks: list[str] = []


def require(condition: bool, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


PROPOSAL = {
    "proposal_id": "improvement-1234567890abcdef1234",
    "proposal_digest": "b" * 64,
    "improvement_class": "approval_record_boundary_extraction",
    "proposed_change": "Extract approval-record discovery and validation helpers behind retained imports.",
    "expected_benefit": "Reduce coupling while preserving behavior.",
}

FIXTURE = '''from __future__ import annotations

from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR, path_reference

FACTOR = 2


def _approval_record_value(value: int = 1) -> int:
    return value * FACTOR


def _approval_record_summary(value: int = 1) -> dict[str, Any]:
    return {"value": _approval_record_value(value), "root": str(ROOT_DIR)}
'''

inventory = build_symbol_inventory(FIXTURE, PROPOSAL)
require({row["name"] for row in inventory} == {"_approval_record_value", "_approval_record_summary"}, "private symbol inventory exact")

revocation_fixture = """
def _approval_record_summary():
    return {}

def _revocation_record_files():
    return []

def _read_revocation_payload():
    return {}

def _revocation_record_id():
    return 'id'
"""
revocation_proposal = {
    **PROPOSAL,
    "improvement_class": "approval_revocation_boundary_extraction",
    "proposed_change": "Extract approval-revocation lookup and validation helpers behind retained imports.",
}
revocation_inventory = build_symbol_inventory(revocation_fixture, revocation_proposal)
require(
    {"_revocation_record_files", "_read_revocation_payload", "_revocation_record_id"}.issubset(
        {row["name"] for row in revocation_inventory}
    ),
    "revocation objective retains distinct private family",
)
prompt, prompt_inventory = build_symbol_selection_prompt(
    FIXTURE,
    PROPOSAL,
    source_path="conscious_agent/self_maintenance.py",
    destination_path="conscious_agent/self_maintenance_approval_records.py",
)
require(len(prompt) < 8_000 and prompt_inventory == inventory, "selection prompt bounded")
raw = json.dumps(
    {
        "authority": {"proposal_id": PROPOSAL["proposal_id"], "proposal_digest": PROPOSAL["proposal_digest"]},
        "symbols": ["_approval_record_value", "_approval_record_summary"],
        "reason_code": "cohesive_record_family",
    }
)
selection = parse_symbol_selection(raw, PROPOSAL, inventory)
require(selection["symbols"] == ["_approval_record_value", "_approval_record_summary"], "bound symbol selection accepted")

wrapped = "Selected family:\n```json\n" + raw + "\n```"
require(parse_symbol_selection(wrapped, PROPOSAL, inventory)["selection_digest"] == selection["selection_digest"], "wrapped selection accepted")
bad = json.loads(raw); bad["symbols"] = ["_approval_record_value", "not_allowed"]
try:
    parse_symbol_selection(json.dumps(bad), PROPOSAL, inventory)
    raise AssertionError("outside symbol unexpectedly accepted")
except ValueError:
    require(True, "outside symbol rejected")

wide_inventory = [{"name": f"_approval_record_{index}", "line": line} for index, line in enumerate([10, 20, 200, 210, 220, 230, 240, 250, 500, 700, 900])]
wide_raw = json.dumps({"authority": {"proposal_id": PROPOSAL["proposal_id"], "proposal_digest": PROPOSAL["proposal_digest"]}, "symbols": [row["name"] for row in wide_inventory], "reason_code": "broad_family"})
wide = parse_symbol_selection(wide_raw, PROPOSAL, wide_inventory)
require(wide["symbols"] == [f"_approval_record_{index}" for index in range(2, 8)], "broad model selection narrows to unique adjacent family")
single_raw = json.dumps({"authority": {"proposal_id": PROPOSAL["proposal_id"], "proposal_digest": PROPOSAL["proposal_digest"]}, "symbols": ["_approval_record_4"], "reason_code": "anchor"})
single = parse_symbol_selection(single_raw, PROPOSAL, wide_inventory)
require(single["symbols"] == [f"_approval_record_{index}" for index in range(2, 8)], "single anchor expands to adjacent family")
tie_inventory = [
    {"name": "_family_a_one", "line": 100},
    {"name": "_family_a_two", "line": 110},
    {"name": "_family_b_one", "line": 300},
    {"name": "_family_b_two", "line": 310},
]
tie_raw = json.dumps({"authority": {"proposal_id": PROPOSAL["proposal_id"], "proposal_digest": PROPOSAL["proposal_digest"]}, "symbols": [row["name"] for row in tie_inventory], "reason_code": "equal_families"})
tie = parse_symbol_selection(tie_raw, PROPOSAL, tie_inventory)
require(tie["symbols"] == ["_family_a_one", "_family_a_two"], "equal families use deterministic source-order tiebreak")
require(tie["normalization_code"] == "largest_adjacent_family_source_order_tiebreak", "family tiebreak is recorded")
require(wide["selection_normalized"] is True, "selection normalization recorded")

result = build_symbol_extraction_changes(
    FIXTURE,
    source_path="conscious_agent/self_maintenance.py",
    destination_path="conscious_agent/self_maintenance_approval_records.py",
    symbols=selection["symbols"],
)
require(result["dependencies"] == ["FACTOR", "ROOT_DIR"], "external dependency closure exact")
require("_deps=_deps" in result["destination_content"], "internal calls forward dependency context")
require("def _approval_record_value(value: int=1)" in result["source_content"], "public signature wrapper retained")
require("_build_self_maintenance_approval_records_dependencies" in result["source_content"], "dependency factory generated")
require("_SelfMaintenanceApprovalRecordsSymbolDependencies" in result["source_content"], "dependency alias is destination specific")
ast.parse(result["source_content"]); ast.parse(result["destination_content"])
require(True, "transformed modules parse")

with tempfile.TemporaryDirectory(prefix="eidolon-symbol-refactor-") as td:
    root = Path(td)
    agent = root / "conscious_agent"
    agent.mkdir()
    (agent / "__init__.py").write_text("", encoding="utf-8")
    (agent / "paths.py").write_text(
        "from pathlib import Path\nDATA_DIR=Path('.')\nROOT_DIR=Path('fixture-root')\ndef path_reference(value): return str(value)\n",
        encoding="utf-8",
    )
    (agent / "self_maintenance.py").write_text(result["source_content"], encoding="utf-8")
    (agent / "self_maintenance_approval_records.py").write_text(result["destination_content"], encoding="utf-8")
    command = [
        sys.executable,
        "-c",
        "import sys;sys.path.insert(0,'conscious_agent');import self_maintenance as m;assert m._approval_record_value(3)==6;assert m._approval_record_summary(4)=={'value':8,'root':'fixture-root'}",
    ]
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=30, check=False)
    require(completed.returncode == 0, "transformed wrappers preserve behavior")

actual = (ROOT / "conscious_agent" / "self_maintenance.py").read_text(encoding="utf-8")
installed_helper = ROOT / "conscious_agent" / "self_maintenance_approval_records.py"
actual_symbols = [
    "_approval_record_files",
    "_safe_approval_record_from_path",
    "_approval_record_id",
    "_approval_record_summary",
    "_read_approval_record_summaries",
]
if installed_helper.exists():
    helper_text = installed_helper.read_text(encoding="utf-8")
    ast.parse(helper_text)
    require("_SymbolDependencies" in actual and "_build_self_maintenance_approval_records_dependencies" in actual, "candidate retains dependency wrappers")
    require(all(f"def {name}" in actual for name in actual_symbols[:5]), "candidate retains public symbol names")
    require(len(helper_text) < 12_000, "candidate extracted helper remains bounded")
else:
    actual_result = build_symbol_extraction_changes(
        actual,
        source_path="conscious_agent/self_maintenance.py",
        destination_path="conscious_agent/self_maintenance_approval_records.py",
        symbols=actual_symbols,
    )
    require(actual_result["symbols"] == actual_symbols, "real approval family transforms")
    require(actual_result["dependencies"] == ["RELEASE_APPROVALS_DIR", "ROOT_DIR", "_approval_record_validator_rows", "_report_path", "_sha256_text", "_status_from"], "real approval dependencies exact")
    require(len(actual_result["destination_content"]) < 12_000, "real extracted helper remains bounded")

print(json.dumps({"ok": True, "suite": "v1489-symbol-level-refactoring", "passed": len(checks), "failed": 0, "checks": checks}, sort_keys=True))
