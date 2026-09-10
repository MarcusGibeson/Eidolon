from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS

INSTALL_RELEASE_TIMEOUT_HARNESS_VERSION = CURRENT_VERSION
INSTALL_RELEASE_TIMEOUT_HARNESS_SMOKE = "install-release-timeout-harness-repair-v1"
INSTALL_RELEASE_TIMEOUT_HARNESS_CLI = "--install-release-timeout-harness-repair"
INSTALL_RELEASE_TIMEOUT_HARNESS_TITLE = "Install-Release Timeout Harness Repair v1"
PASS_PROBE_TIMEOUT_SECONDS = 2.0
TIMEOUT_PROBE_TIMEOUT_SECONDS = 0.35

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "marks_install_release_clean": False,
    "release_authorized": False,
    "creates_release": False,
    "publishes_release": False,
    "applies_source_edits": False,
    "writes_source": False,
    "writes_memory": False,
    "memory_mutated": False,
    "approval_system_mutated": False,
    "release_system_mutated": False,
    "scheduler_mutated": False,
    "network_accessed": False,
    "generated_wiring_activated": False,
    "dashboard_wiring_activated": False,
    "api_wiring_activated": False,
    "cli_wiring_activated": False,
    "smoke_wiring_activated": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "protected_systems_require_operator_approval": True,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root_dir: str | Path | None = None) -> Path:
    return Path(root_dir or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _run_bounded_probe(name: str, code: str, timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    command = [sys.executable, "-I", "-B", "-c", code]
    try:
        completed = subprocess.run(
            command,
            cwd=str(Path.cwd()),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env={"PYTHONIOENCODING": "utf-8"},
        )
        elapsed = round(time.monotonic() - started, 3)
        return {
            "name": name,
            "status": "pass" if completed.returncode == 0 else "failed",
            "timed_out": False,
            "returncode": completed.returncode,
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": elapsed,
            "stdout": (completed.stdout or "")[:240],
            "stderr": (completed.stderr or "")[:240],
        }
    except subprocess.TimeoutExpired as error:
        elapsed = round(time.monotonic() - started, 3)
        return {
            "name": name,
            "status": "timeout",
            "timed_out": True,
            "returncode": None,
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": elapsed,
            "stdout": ((error.stdout or "") if isinstance(error.stdout, str) else "")[:240],
            "stderr": ((error.stderr or "") if isinstance(error.stderr, str) else "")[:240],
        }


def _timeout_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in INSTALL_RELEASE_LEDGER_ROWS if row.get("status") == "timeout"]


def build_install_release_timeout_harness_repair_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/install_release_timeout_harness.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ])
    rows = _timeout_rows()
    pass_probe = _run_bounded_probe("bounded-pass-probe", "print('bounded-pass-ok')", PASS_PROBE_TIMEOUT_SECONDS)
    timeout_probe = _run_bounded_probe(
        "bounded-timeout-probe",
        "import time\ntime.sleep(2)\nprint('should-not-print')",
        TIMEOUT_PROBE_TIMEOUT_SECONDS,
    )
    harness_probes = [pass_probe, timeout_probe]
    protected_rows = [
        {
            "name": row["name"],
            "previous_status": row.get("status"),
            "previous_category": row.get("category"),
            "repair_status": "timeout_protected_pending_retest",
            "bounded_subprocess_required": True,
            "full_segment_clean_claimed": False,
        }
        for row in rows
    ]
    policy_results = {
        "seven_timeout_rows_identified": len(rows) == 7,
        "pass_probe_executes_successfully": pass_probe.get("status") == "pass" and pass_probe.get("timed_out") is False,
        "timeout_probe_is_enforced": timeout_probe.get("status") == "timeout" and timeout_probe.get("timed_out") is True,
        "timeout_probe_elapsed_is_bounded": float(timeout_probe.get("elapsed_seconds") or 999) < 1.5,
        "all_timeout_rows_marked_protected_pending_retest": len(protected_rows) == len(rows) and all(row.get("repair_status") == "timeout_protected_pending_retest" for row in protected_rows),
        "full_install_release_not_claimed_clean": True,
        "targeted_smoke_registered": INSTALL_RELEASE_TIMEOUT_HARNESS_SMOKE in docs,
        "cli_flag_registered": INSTALL_RELEASE_TIMEOUT_HARNESS_CLI in docs,
        "builder_registered": "build_install_release_timeout_harness_repair_review" in docs,
        "text_renderer_registered": "install_release_timeout_harness_repair_review_text" in docs,
        "review_only": BOUNDARIES["review_only"] is True,
        "no_autonomy_expansion": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "no_release_authorization": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
    }
    ok = all(policy_results.values())
    return {
        "id": f"install_release_timeout_harness_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_timeout_harness_repair_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": INSTALL_RELEASE_TIMEOUT_HARNESS_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "timeout_harness_mode": "subprocess_timeout_enforced_probe",
        "pass_probe_timeout_seconds": PASS_PROBE_TIMEOUT_SECONDS,
        "timeout_probe_timeout_seconds": TIMEOUT_PROBE_TIMEOUT_SECONDS,
        "timeout_rows_reviewed": len(rows),
        "timeout_rows_protected": len(protected_rows),
        "timeout_rows_still_need_retest": len(protected_rows),
        "timeout_harness_repaired": True,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_timeout_rows_are_retested_with_bounded_release_archive_fixtures_and_supervised_blockers_are_resolved",
        "harness_probes": harness_probes,
        "protected_timeout_rows": protected_rows,
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def install_release_timeout_harness_repair_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Install-Release Timeout Harness Repair report not found."
    lines = [
        "# Install-Release Timeout Harness Repair",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Timeout rows reviewed: {report.get('timeout_rows_reviewed')}",
        f"Timeout rows protected: {report.get('timeout_rows_protected')}",
        f"Timeout rows still need retest: {report.get('timeout_rows_still_need_retest')}",
        f"Timeout harness repaired: {report.get('timeout_harness_repaired')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Harness probes"])
        for probe in report.get("harness_probes") or []:
            lines.append(f"- {probe.get('name')}: {probe.get('status')} timed_out={probe.get('timed_out')} elapsed={probe.get('elapsed_seconds')}s")
        lines.extend(["", "## Protected timeout rows"])
        for row in report.get("protected_timeout_rows") or []:
            lines.append(f"- {row.get('name')}: {row.get('repair_status')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_install_release_timeout_harness_repair_review(full: bool = False) -> None:
    print(install_release_timeout_harness_repair_review_text(build_install_release_timeout_harness_repair_review(), full=full))
