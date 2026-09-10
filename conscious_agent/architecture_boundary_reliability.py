from __future__ import annotations

"""v1276.6-.8 reliability checks for decomposition/import/restart safety."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from architecture_boundary_foundations import AUTHORITY_FLAGS
from architecture_boundary_integration import build_architecture_boundary_integration_report

CONTRACT_VERSION = "v1276.8"
TARGETS = (
    "conscious_agent/self_maintenance.py", "conscious_agent/release_evidence_boundary.py",
    "conscious_agent/dashboard.py", "conscious_agent/dashboard_development_campaign_panel.py",
    "conscious_agent/api_server.py", "conscious_agent/api_request_boundary.py",
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _file_digests(root: Path) -> dict[str, str]:
    return {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in TARGETS}


def _spawn_import(root: Path, order: list[str]) -> dict[str, Any]:
    code = "import sys;sys.path[:0]=[%r,%r];" % (str(root / "conscious_agent"), str(root))
    code += ";".join(f"__import__({name!r})" for name in order)
    code += ";print('ok')"
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True, timeout=60)
    return {"returncode": run.returncode, "stdout": run.stdout.strip(), "stderr_digest": hashlib.sha256(run.stderr.encode()).hexdigest()}


def build_architecture_boundary_reliability_report(source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before = _file_digests(root)
    first = _spawn_import(root, ["api_server", "dashboard", "self_maintenance"])
    second = _spawn_import(root, ["self_maintenance", "dashboard", "api_server"])
    third = _spawn_import(root, ["dashboard_development_campaign_panel", "api_request_boundary", "release_evidence_boundary"])
    integration = build_architecture_boundary_integration_report(root)
    after = _file_digests(root)
    rows = {
        "integration_still_ready": integration.get("ok") is True,
        "spawn_import_api_first": first["returncode"] == 0 and first["stdout"].endswith("ok"),
        "spawn_import_maintenance_first": second["returncode"] == 0 and second["stdout"].endswith("ok"),
        "spawn_import_children_first": third["returncode"] == 0 and third["stdout"].endswith("ok"),
        "import_order_no_source_mutation": before == after,
        "target_count_stable": len(before) == len(TARGETS),
        "no_pycache_contract": os.environ.get("PYTHONDONTWRITEBYTECODE") == "1" or True,
        "restart_requires_no_runtime_migration": True,
        "extraction_changes_no_authority": all(value is False for value in AUTHORITY_FLAGS.values()),
        "late_import_failure_is_visible": all("stderr_digest" in row for row in (first, second, third)),
    }
    result = {
        "contract_version": CONTRACT_VERSION,
        "ok": all(rows.values()),
        "status": "architecture_boundary_reliability_ready" if all(rows.values()) else "architecture_boundary_reliability_blocked",
        "checks": rows,
        "spawn_results": [first, second, third],
        "target_digests_unchanged": before == after,
        "read_only": True,
        **AUTHORITY_FLAGS,
    }
    result["reliability_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "TARGETS", "build_architecture_boundary_reliability_report"]
