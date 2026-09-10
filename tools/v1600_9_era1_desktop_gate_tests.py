from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1600-9-"))

from release_authority import (  # noqa: E402
    AUTHORITY_FLAGS,
    CODEX_REVIEW_STATE,
    MILESTONE,
    NEXT_BOUNDED_UNIT,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
)


checks: dict[str, bool] = {}


def require(name: str, value: object) -> None:
    checks[name] = bool(value)
    assert checks[name], name


readme = (ROOT / "README.md").read_text(encoding="utf-8")
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
ledger = (ROOT / "docs/roadmaps/EIDOLON_V1600_9_DESKTOP_GATE_LEDGER.md").read_text(encoding="utf-8")

require("version", WORKING_SOURCE_VERSION == "1600.9")
require("previous_version", PREVIOUS_WORKING_SOURCE_VERSION == "1599.9")
require("milestone", MILESTONE == "v1600.9 Era 1 Desktop Acceptance Gate")
require("next_arc", NEXT_BOUNDED_UNIT == "v1601.0 - Deep Project Understanding foundations")
require("review_state", CODEX_REVIEW_STATE == "v1600_9_desktop_gate_operator_installed")
require("authority_denied", not any(bool(value) for value in AUTHORITY_FLAGS.values()))
require("dashboard_command", "python eidolon.py dashboard" in readme)
require("verify_command", "python eidolon.py verify" in readme)
require("windows_setup", "setup.ps1" in readme)
require("portable_setup", "setup.sh" in readme)
require("quick_verify", "tools/release_verify.py --profile quick" in next_steps)
require("full_verify", "tools/release_verify.py --profile full" in next_steps)
require("history_milestone", MILESTONE in history)
require("registry_smoke", "registry-navigation-smoke-consolidation-v1" in history)
require("gate_ledger", "operator-invoked Windows gate" in ledger)
desktop_checkpoint = (ROOT / "tools/v1450_9_desktop_alpha_checkpoint_tests.py").read_text(encoding="utf-8")
require("historical_runtime_external", 'Path(os.environ["EIDOLON_DATA_DIR"])' in desktop_checkpoint)
require("historical_source_data_not_read", 'ROOT / "data" / "settings.json"' not in desktop_checkpoint)
multi_tab_fixture = (ROOT / "tools/multi_tab_conversation_coordination_tests.py").read_text(encoding="utf-8")
require("multi_tab_disposable_runtime", 'tempfile.mkdtemp(prefix="multi-tab-fixture-"' in multi_tab_fixture)
require("multi_tab_no_whole_tree_hash", 'ROOT.rglob("*")' not in multi_tab_fixture)
require("campaign_module", (ROOT / "conscious_agent/supervised_initiative_campaign.py").is_file())
require("repair_module", (ROOT / "conscious_agent/supervised_repair_intelligence.py").is_file())

for relative in (
    "conscious_agent/release_authority.py",
    "conscious_agent/release_metadata.py",
    "conscious_agent/supervised_initiative_campaign.py",
    "conscious_agent/supervised_repair_intelligence.py",
):
    source_path = ROOT / relative
    compile(source_path.read_text(encoding="utf-8"), str(source_path), "exec")
require("focused_compile", True)

result = {
    "ok": all(checks.values()),
    "version": WORKING_SOURCE_VERSION,
    "passed": sum(checks.values()),
    "total": len(checks),
    "checks": checks,
    "source_modified": False,
    "provider_contacted": False,
    "authority_expanded": False,
}
print(json.dumps(result, sort_keys=True))
