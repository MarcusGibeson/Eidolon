from __future__ import annotations

from release_metadata import RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

import ast
import json
from pathlib import Path
from typing import Any

MODULE_VERSION = "1078.6"
CHECK_ID = "runtime-compile-and-live-version-truth-repair-v1"
def build_runtime_compile_and_live_version_truth_repair_report(root: Path) -> dict[str, Any]:
    root = Path(root)
    rows: list[dict[str, Any]] = []
    py_files = sorted((root / "conscious_agent").rglob("*.py")) + sorted((root / "tools").rglob("*.py"))
    syntax_errors: list[dict[str, str]] = []
    for path in py_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            syntax_errors.append({"path": str(path.relative_to(root)), "error": str(exc)})
    rows.append({"name": "full-python-ast-compile", "ok": not syntax_errors, "actual": len(syntax_errors)})
    from release_metadata import RUNTIME_VERSION, RUNTIME_VERSION_TAG
    checks = {
        "conscious_agent/api_server.py": "API_VERSION",
        "conscious_agent/dashboard.py": "DASHBOARD_VERSION",
        "conscious_agent/current_version_staleness_audit.py": "CURRENT_VERSION",
        "conscious_agent/self_maintenance.py": "SELF_MAINTENANCE_VERSION",
        "conscious_agent/metadata_release_integrity.py": "CURRENT_VERSION",
    }

    def marker_uses_runtime_authority(text: str, marker: str) -> bool:
        """Accept either the historical exact literal or a release_metadata import binding."""
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return False
        runtime_aliases = {"RUNTIME_VERSION"}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module == "release_metadata":
                for imported in node.names:
                    if imported.name == "RUNTIME_VERSION":
                        bound_name = imported.asname or imported.name
                        runtime_aliases.add(bound_name)
                        if bound_name == marker:
                            return True
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(target, ast.Name) and target.id == marker for target in targets):
                continue
            value = node.value
            if isinstance(value, ast.Constant) and value.value == RUNTIME_VERSION:
                return True
            if isinstance(value, ast.Name) and value.id in runtime_aliases:
                return True
        return False

    for rel, marker in checks.items():
        text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        ok = marker_uses_runtime_authority(text, marker)
        rows.append({
            "name": f"live-version:{rel}",
            "ok": ok,
            "expected": f"{marker} resolves from release_metadata.RUNTIME_VERSION ({RUNTIME_VERSION})",
        })
    settings=json.loads((root/"data/settings.json").read_text(encoding="utf-8"))
    rows.append({"name":"settings-last-updated", "ok": settings.get("last_updated_for")==RUNTIME_VERSION_TAG, "actual":settings.get("last_updated_for")})
    dashboard=(root/"conscious_agent/dashboard.py").read_text(encoding="utf-8",errors="ignore")
    rows.append({"name":"f-string-fallback-precomputed", "ok": "detail_rows or empty_detail_row" in dashboard and "empty_detail_row =" in dashboard})
    
    from audited_sandbox_backend_evidence_interface import AUTHORITY_BOUNDARIES, sandbox_backend_admission_rows
    admission_rows = sandbox_backend_admission_rows()
    safety_ok = (
        AUTHORITY_BOUNDARIES.get("actual_fixture_execution_allowed") is False
        and AUTHORITY_BOUNDARIES.get("audited_os_sandbox_backend_integrated") is False
        and AUTHORITY_BOUNDARIES.get("subprocess_spawn_count_is_zero") is True
        and AUTHORITY_BOUNDARIES.get("source_write_count_is_zero") is True
        and AUTHORITY_BOUNDARIES.get("source_delete_count_is_zero") is True
        and admission_rows
        and all(row.get("passed") is False and row.get("blocks_fixture_execution") is True for row in admission_rows)
    )
    rows.append({"name":"safety-boundary-inspected", "ok": bool(safety_ok), "release_authorized":False, "autonomy_expanded":False, "fixture_execution_enabled":False, "admission_gate_count":len(admission_rows)})
    ok=all(bool(row.get("ok")) for row in rows)
    return {"version":MODULE_VERSION,"check_id":CHECK_ID,"status":"pass" if ok else "blocked","ok":ok,"rows":rows,"syntax_errors":syntax_errors,"release_authorized":False,"autonomy_expanded":False}

def runtime_compile_and_live_version_truth_repair_text(report: dict[str, Any]) -> str:
    return "\n".join([f"{CHECK_ID}: {report.get('status')}"]+[f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}" for row in report.get('rows',[])])
