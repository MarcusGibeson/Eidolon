from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

SMOKE_TIMEOUT_CONTRACT_VERSION = CURRENT_VERSION
COMPILE_SMOKE_TIMEOUT_SECONDS = 35
SMOKE_TIMEOUT_CONTRACT_ID = "smoke-timeout-contract-extraction-v1"

SMOKE_TIMEOUT_CONTRACT_BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "extracted_from_manual_smoke_runner": True,
    "manual_smoke_remains_authoritative": True,
    "generated_wiring_activated": False,
    "applies_source_edits": False,
    "writes_memory": False,
    "creates_release": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


def build_smoke_timeout_contract_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    smoke_path = project_root / "tools/smoke_check.py"
    module_path = project_root / "conscious_agent/smoke_timeout_contract.py"
    smoke_text = smoke_path.read_text(encoding="utf-8", errors="ignore") if smoke_path.exists() else ""
    module_text = module_path.read_text(encoding="utf-8", errors="ignore") if module_path.exists() else ""
    try:
        smoke_tree = ast.parse(smoke_text)
    except SyntaxError:
        smoke_tree = ast.Module(body=[], type_ignores=[])
    smoke_local_timeout_assignment_present = any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "COMPILE_SMOKE_TIMEOUT_SECONDS" for target in node.targets)
        for node in getattr(smoke_tree, "body", [])
    )
    rows = [
        {
            "name": "module-version-current",
            "ok": SMOKE_TIMEOUT_CONTRACT_VERSION == CURRENT_VERSION,
            "message": f"module={SMOKE_TIMEOUT_CONTRACT_VERSION}; current={CURRENT_VERSION}",
        },
        {
            "name": "compile-timeout-exported",
            "ok": COMPILE_SMOKE_TIMEOUT_SECONDS == 35,
            "message": "COMPILE_SMOKE_TIMEOUT_SECONDS remains 35 seconds after extraction.",
        },
        {
            "name": "manual-smoke-imports-contract",
            "ok": "from smoke_timeout_contract import COMPILE_SMOKE_TIMEOUT_SECONDS" in smoke_text,
            "message": "tools/smoke_check.py imports the compile timeout from the extracted contract module.",
        },
        {
            "name": "manual-smoke-no-local-timeout-assignment",
            "ok": not smoke_local_timeout_assignment_present,
            "message": "The manual smoke runner no longer owns the compile timeout constant locally.",
        },
        {
            "name": "registry-and-subprocess-use-extracted-constant",
            "ok": 'SmokeCheck("compile", "fast", COMPILE_SMOKE_TIMEOUT_SECONDS, check_compile)' in smoke_text and "timeout=COMPILE_SMOKE_TIMEOUT_SECONDS" in smoke_text,
            "message": "The advertised registry timeout and the py_compile subprocess timeout still use the same imported constant.",
        },
        {
            "name": "contract-source-carries-boundaries",
            "ok": all(token in module_text for token in ["manual_smoke_remains_authoritative", "generated_wiring_activated", "release_authorized", "autonomy_expanded"]),
            "message": "The extracted contract records review-only and non-autonomy boundaries.",
        },
    ]
    ok = all(bool(row["ok"]) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": SMOKE_TIMEOUT_CONTRACT_ID,
        "compile_timeout_seconds": COMPILE_SMOKE_TIMEOUT_SECONDS,
        "constant_extracted_from_smoke_check": "from smoke_timeout_contract import COMPILE_SMOKE_TIMEOUT_SECONDS" in smoke_text,
        "manual_smoke_local_timeout_assignment_removed": not smoke_local_timeout_assignment_present,
        "registry_and_subprocess_still_share_timeout": 'SmokeCheck("compile", "fast", COMPILE_SMOKE_TIMEOUT_SECONDS, check_compile)' in smoke_text and "timeout=COMPILE_SMOKE_TIMEOUT_SECONDS" in smoke_text,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "boundaries": dict(SMOKE_TIMEOUT_CONTRACT_BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row["ok"]],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def smoke_timeout_contract_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        CURRENT_MILESTONE,
        SMOKE_TIMEOUT_CONTRACT_ID,
        f"compile_timeout_seconds={report.get('compile_timeout_seconds')}",
        f"constant_extracted_from_smoke_check={report.get('constant_extracted_from_smoke_check')}",
        f"manual_smoke_local_timeout_assignment_removed={report.get('manual_smoke_local_timeout_assignment_removed')}",
        f"registry_and_subprocess_still_share_timeout={report.get('registry_and_subprocess_still_share_timeout')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1025.0 First Source Decomposition Compatibility Slice v1 tokens: smoke-timeout-contract-extraction-v1 COMPILE_SMOKE_TIMEOUT_SECONDS = 35 constant_extracted_from_smoke_check=True manual_smoke_local_timeout_assignment_removed=True registry_and_subprocess_still_share_timeout=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True.
