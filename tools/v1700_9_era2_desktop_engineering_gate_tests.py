from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1700-9-"))

from checkpoint_registry import lookup_checkpoint  # noqa: E402
from dashboard_first_use import render_first_use_shell  # noqa: E402
from dashboard_performance import optimize_dashboard_html_assets  # noqa: E402
from release_authority import (  # noqa: E402
    AUTHORITY_FLAGS,
    CODEX_REVIEW_STATE,
    MILESTONE,
    NEXT_BOUNDED_UNIT,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
)


checks: dict[str, bool] = {}
toolchains: dict[str, dict[str, object]] = {}


def require(name: str, value: object) -> None:
    checks[name] = bool(value)
    assert checks[name], name


def run_tool(name: str, command: list[str]) -> None:
    executable = shutil.which(command[0])
    if not executable:
        toolchains[name] = {"available": False, "passed": False}
        return
    completed = subprocess.run(
        [executable, *command[1:]],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        check=False,
    )
    toolchains[name] = {
        "available": True,
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
    }
    require(f"native_{name}", completed.returncode == 0)


require("version", WORKING_SOURCE_VERSION == "1700.9")
require("previous", PREVIOUS_WORKING_SOURCE_VERSION == "1699.9")
require("milestone", MILESTONE == "v1700.9 Era 2 Desktop Engineering Gate")
require("next", NEXT_BOUNDED_UNIT == "v1701.0 - Requirements and Problem Framing foundations")
require("review_state", CODEX_REVIEW_STATE == "v1700_9_desktop_gate_reviewed_unpromoted")
require("authority_denied", not any(bool(value) for value in AUTHORITY_FLAGS.values()))
checkpoint = lookup_checkpoint("1700.9")
require("canonical_registry_selector", checkpoint is not None and checkpoint.test_selector == f"tools/{Path(__file__).name}")

first_use = optimize_dashboard_html_assets(render_first_use_shell())
require("first_use_css_retained", "#conversation-log { min-height:48vh; max-height:58vh; overflow:auto;" in first_use)
require("first_use_not_hybrid", "/assets/dashboard.css?v=1396.9-r3" not in first_use)

readiness = (ROOT / "conscious_agent/local_model_readiness.py").read_text(encoding="utf-8")
upgrade = (ROOT / "conscious_agent/portable_release_upgrade_engineering.py").read_text(encoding="utf-8")
first_runtime = (ROOT / "conscious_agent/first_use_runtime.py").read_text(encoding="utf-8")
packaging = (ROOT / "conscious_agent/release_packaging.py").read_text(encoding="utf-8")
require("provider_identity_config", "identity_config" in readiness)
require("source_only_upgrade_manifest", "_source_only_manifest" in upgrade and "_source_only_paths" in upgrade)
require("fast_private_runtime_startup", "inspect_runtime_inventory=False" in first_runtime)
require("settings_schema_release_role_separation", "settings_schema_coherent" in packaging and "schema identity is independent from product release" in packaging)

with tempfile.TemporaryDirectory(prefix="eidolon-v1700-native-") as directory:
    temp = Path(directory)
    py = temp / "probe.py"
    js = temp / "probe.js"
    ps = temp / "probe.ps1"
    java = temp / "Probe.java"
    php = temp / "probe.php"
    py.write_text("value = 1700\n", encoding="utf-8")
    js.write_text("const value = 1700;\n", encoding="utf-8")
    ps.write_text("$value = 1700\n", encoding="utf-8")
    java.write_text("final class Probe { static int value() { return 1700; } }\n", encoding="utf-8")
    php.write_text("<?php $value = 1700;\n", encoding="utf-8")

    run_tool("python", [sys.executable, "-m", "py_compile", str(py)])
    run_tool("node", ["node", "--check", str(js)])
    run_tool("powershell", ["pwsh", "-NoProfile", "-NonInteractive", "-Command", f"[void][ScriptBlock]::Create((Get-Content -Raw -LiteralPath '{ps}'))"])
    run_tool("java", ["javac", "-d", str(temp / "java-out"), str(java)])
    run_tool("php", ["php", "-l", str(php)])
    if shutil.which("dotnet"):
        run_tool("dotnet", ["dotnet", "--info"])

require("required_native_tools", all(toolchains[name]["passed"] for name in ("python", "node", "powershell")))

ledger = ROOT / "docs/roadmaps/EIDOLON_V1700_9_DESKTOP_ENGINEERING_GATE_LEDGER.md"
require("gate_ledger", ledger.is_file())
require("ledger_digest", len(hashlib.sha256(ledger.read_bytes()).hexdigest()) == 64)

result = {
    "suite": "v1700.9-era2-desktop-engineering-gate",
    "ok": all(checks.values()),
    "passed": sum(checks.values()),
    "total": len(checks),
    "checks": checks,
    "native_toolchains": toolchains,
    "source_modified": False,
    "provider_model_changed": False,
    "installed": False,
    "promoted": False,
    "authority_expanded": False,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
