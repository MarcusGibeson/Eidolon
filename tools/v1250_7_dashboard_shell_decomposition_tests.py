from __future__ import annotations

import ast
import hashlib
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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-7-"))

import dashboard  # noqa: E402
import dashboard_layout  # noqa: E402
from checkpoint_registry import lookup_checkpoint, validate_checkpoint_report  # noqa: E402
from dashboard_shell_decomposition import (  # noqa: E402
    AUTHORITY_FLAGS,
    BASELINE_NORMALIZED_LAYOUT_SHA256,
    BASELINE_PARENT_LINE_COUNT,
    CONTRACT_VERSION,
    validate_dashboard_shell_decomposition,
)
from dashboard_shell_decomposition_checkpoint import build_dashboard_shell_decomposition_checkpoint  # noqa: E402

checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


validation = validate_dashboard_shell_decomposition(source_root=ROOT)
checkpoint = build_dashboard_shell_decomposition_checkpoint(source_root=ROOT)
checkpoint_validation = validate_checkpoint_report(checkpoint, source_root=ROOT)
parent_source = (ROOT / "conscious_agent/dashboard.py").read_text(encoding="utf-8")
child_source = (ROOT / "conscious_agent/dashboard_layout.py").read_text(encoding="utf-8")

require(CONTRACT_VERSION == "v1250.7")
require(dashboard_layout.CONTRACT_VERSION == "v1250.7")
require(BASELINE_PARENT_LINE_COUNT == 18432)
require(BASELINE_NORMALIZED_LAYOUT_SHA256 == "1872a65fa848863b814c84e2e60bb660bcf1c69d5ef7f397b92db355d1c68ee5")
require(validation["ok"] is True)
require(validation["status"] == "dashboard_shell_decomposed")
require(validation["passed"] == validation["total"] == 11)
require(all(validation["checks"].values()))
require(validation["parent_line_count"] < 17632)
require(900 <= validation["extracted_line_count"] <= 1000)
require(5 <= validation["wrapper_span"] <= 40)
require(validation["renderer_span"] >= 850)
require(validation["normalized_layout_sha256"] == BASELINE_NORMALIZED_LAYOUT_SHA256)
require(validation["normalized_layout_length"] > 200000)
require(len(validation["validation_digest"]) == 64)
require("def _layout(path: str, content: str)" in parent_source)
require("def render_dashboard_layout(" in child_source)
require("def handle_action(" in parent_source)
require("class EidolonDashboardHandler" in parent_source)
require("def handle_action(" not in child_source)
require("class EidolonDashboardHandler" not in child_source)
require("method='post'" not in child_source.lower())
require("/action" not in child_source or "form method='post' action='/action'" not in child_source)
require("shell=True" not in child_source)
require("import subprocess" not in child_source)
require("data-tip" in child_source)
require("no_native_title_tooltip" not in child_source)
require("<title>" in child_source)
require("_live_refresh_script(settings)" in child_source)
require("dashboard_route_registry_nav_items()" in child_source)
require("load_settings=load_settings" in parent_source)
require("DashboardState=DashboardState" in parent_source)
require("_render_nav=_render_nav" in parent_source)
require(dashboard._layout.__module__ == "dashboard")
require(dashboard_layout.render_dashboard_layout.__module__ == "dashboard_layout")
require(lookup_checkpoint("1250.7") is not None)
require(lookup_checkpoint("1250.7").title == "Dashboard Shell Decomposition")
require(checkpoint["ok"] is True)
require(checkpoint["checkpoint_version"] == "1250.7")
require(checkpoint["status"] == "dashboard_shell_decomposition_ready")
require(checkpoint["passed"] == checkpoint["total"] == 3)
require(checkpoint["details"]["parent_line_count"] == validation["parent_line_count"])
require(checkpoint["details"]["extracted_line_count"] == validation["extracted_line_count"])
require(checkpoint_validation["ok"] is True)
require(checkpoint_validation["passed"] == checkpoint_validation["total"])
require("v1250.7 Dashboard Shell Decomposition" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
for key, expected in AUTHORITY_FLAGS.items():
    require(expected is False)
    require(validation[key] is False)
    require(checkpoint.get(key, False) is False)

result = {"suite": "v1250.7-dashboard-shell-decomposition", "ok": all(checks), "passed": sum(checks), "total": len(checks)}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
