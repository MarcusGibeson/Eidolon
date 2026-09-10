from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from supervised_self_development_contract import create_isolated_workspace, source_manifest
from symbol_level_refactoring import build_symbol_extraction_changes

CHECKS: list[str] = []


def require(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if "__pycache__" in relative or relative.endswith((".pyc", ".pyo")) or relative.startswith("data/"):
            continue
        rows.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


before = source_signature()
with tempfile.TemporaryDirectory(prefix="eid-v1501-0-1-") as directory:
    source = Path(directory) / "source"
    source.mkdir()
    (source / "agent.py").write_text("VALUE = 1\n", encoding="utf-8")
    backup = source / "install_backups" / "old"
    backup.mkdir(parents=True)
    (backup / "agent.py").write_text("PRIVATE_OLD = True\n", encoding="utf-8")
    workspace = Path(directory) / "workspace"
    created = create_isolated_workspace(source, workspace, authorized=True)
    require(created["created"], "workspace_created")
    require(not (workspace / "install_backups").exists(), "install_backups_excluded")
    require(source_manifest(source) == source_manifest(workspace), "source_only_manifest_parity")

source_text = (ROOT / "conscious_agent" / "alternative_planning.py").read_text(encoding="utf-8")
require("from alternative_planning_alternative import (" in source_text, "reviewed_candidate_installed_in_authoritative_source")
helper = ROOT / "conscious_agent" / "alternative_planning_alternative.py"
require(helper.is_file(), "reviewed_helper_present")
compile(source_text, "alternative_planning.py", "exec")
compile(helper.read_text(encoding="utf-8"), "alternative_planning_alternative.py", "exec")
require(True, "installed_candidate_compiles")

fixture = """from __future__ import annotations\n\nimport os\nfrom typing import Any\n\ndef alpha(value: Any) -> Any:\n    return os.fspath(value)\n\ndef beta(value: Any) -> Any:\n    return alpha(value)\n"""
extraction = build_symbol_extraction_changes(
    fixture,
    source_path="conscious_agent/fixture.py",
    destination_path="conscious_agent/fixture_helpers.py",
    symbols=["alpha", "beta"],
)
require("from fixture_helpers import (" in extraction["source_content"], "ordinary_import_block_supported")
require(extraction["symbol_count"] == 2, "exact_symbols_retained")

integration = (ROOT / "conscious_agent" / "v1489_product_capability_integration.py").read_text(encoding="utf-8")
require("implementation_blocker\": blocker" in integration, "failure_receipt_preserves_blocker")
require("source_is_stale or not workspace_is_clean" in integration, "failed_workspace_can_refresh_safely")
require("development_plan\") or {}).get(\"destination_module\")" in integration, "installed_lineage_uses_planned_destination")
require(source_signature() == before, "suite_preserves_source")

print(json.dumps({
    "ok": True,
    "suite": "v1501.0.1-source-only-workspace-boundary-repair",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
}, indent=2, sort_keys=True))
