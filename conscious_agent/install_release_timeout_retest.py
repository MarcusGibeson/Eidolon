from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS

INSTALL_RELEASE_TIMEOUT_RETEST_VERSION = CURRENT_VERSION
INSTALL_RELEASE_TIMEOUT_RETEST_SMOKE = "install-release-timeout-row-bounded-retest-v1"
INSTALL_RELEASE_TIMEOUT_RETEST_CLI = "--install-release-timeout-row-bounded-retest"
INSTALL_RELEASE_TIMEOUT_RETEST_TITLE = "Install-Release Timeout Row Bounded Retest v1"
RETEST_TIMEOUT_SECONDS = 1.0

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_targeted_timeout_rows_only": True,
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


def _timeout_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in INSTALL_RELEASE_LEDGER_ROWS if row.get("status") == "timeout"]


def _run_timeout_row_retest(root: Path, name: str, timeout_seconds: float = RETEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    started = time.monotonic()
    command = [sys.executable, "-u", str(root / "tools" / "smoke_check.py"), "--check", name]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env={"PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(root / "conscious_agent")},
        )
        elapsed = round(time.monotonic() - started, 3)
        if completed.returncode == 0:
            classification = "passed_after_bounded_retest"
        else:
            classification = "failed_after_bounded_retest"
        return {
            "name": name,
            "classification": classification,
            "timed_out": False,
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
            "timeout_seconds": timeout_seconds,
            "stdout_excerpt": (completed.stdout or "")[:320],
            "stderr_excerpt": (completed.stderr or "")[:320],
        }
    except subprocess.TimeoutExpired as error:
        elapsed = round(time.monotonic() - started, 3)
        return {
            "name": name,
            "classification": "still_timeout",
            "timed_out": True,
            "returncode": None,
            "elapsed_seconds": elapsed,
            "timeout_seconds": timeout_seconds,
            "stdout_excerpt": ((error.stdout or "") if isinstance(error.stdout, str) else "")[:320],
            "stderr_excerpt": ((error.stderr or "") if isinstance(error.stderr, str) else "")[:320],
        }


def _class_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in results:
        key = str(row.get("classification"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_install_release_timeout_row_bounded_retest_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/install_release_timeout_retest.py",
        "conscious_agent/install_release_timeout_harness.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ])
    rows = _timeout_rows()
    results = [_run_timeout_row_retest(root, row["name"], timeout_seconds=RETEST_TIMEOUT_SECONDS) for row in rows]
    class_counts = _class_counts(results)
    reclassified_rows: list[dict[str, Any]] = []
    previous_by_name = {row["name"]: row for row in rows}
    for result in results:
        previous = previous_by_name.get(result["name"], {})
        reclassified_rows.append({
            "name": result["name"],
            "previous_status": previous.get("status"),
            "previous_category": previous.get("category"),
            "previous_cause": previous.get("cause"),
            "bounded_retest_classification": result.get("classification"),
            "timed_out": result.get("timed_out"),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "timeout_seconds": result.get("timeout_seconds"),
            "next_action": "decompose_release_archive_fixture_or_raise_target_cap_under_operator_review" if result.get("classification") == "still_timeout" else "review_retest_output_before_reclassifying_release_segment",
        })
    policy_results = {
        "seven_timeout_rows_identified": len(rows) == 7,
        "all_timeout_rows_retested": len(results) == 7,
        "all_retests_bounded": all(float(row.get("elapsed_seconds") or 999) < (RETEST_TIMEOUT_SECONDS + 1.5) for row in results),
        "all_timeout_rows_reclassified": len(reclassified_rows) == 7 and all(bool(row.get("bounded_retest_classification")) for row in reclassified_rows),
        "classification_counts_recorded": bool(class_counts),
        "full_install_release_not_claimed_clean": True,
        "targeted_smoke_registered": INSTALL_RELEASE_TIMEOUT_RETEST_SMOKE in docs,
        "cli_flag_registered": INSTALL_RELEASE_TIMEOUT_RETEST_CLI in docs,
        "builder_registered": "build_install_release_timeout_row_bounded_retest_review" in docs,
        "text_renderer_registered": "install_release_timeout_row_bounded_retest_review_text" in docs,
        "review_only": BOUNDARIES["review_only"] is True,
        "no_autonomy_expansion": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "no_release_authorization": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
    }
    ok = all(policy_results.values())
    still_timeout = class_counts.get("still_timeout", 0)
    passed_after_retest = class_counts.get("passed_after_bounded_retest", 0)
    failed_after_retest = class_counts.get("failed_after_bounded_retest", 0)
    return {
        "id": f"install_release_timeout_row_bounded_retest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_timeout_row_bounded_retest_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": INSTALL_RELEASE_TIMEOUT_RETEST_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "retest_mode": "targeted_subprocess_timeout_retest",
        "retest_timeout_seconds": RETEST_TIMEOUT_SECONDS,
        "timeout_rows_total": len(rows),
        "timeout_rows_retested": len(results),
        "timeout_rows_reclassified": len(reclassified_rows),
        "timeout_rows_passed_after_retest": passed_after_retest,
        "timeout_rows_failed_after_retest": failed_after_retest,
        "timeout_rows_still_timeout": still_timeout,
        "remaining_timeout_rows": still_timeout,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_timeout_rows_stop_timing_out_or_are_decomposed_into_smaller_release_archive_fixtures",
        "classification_counts": class_counts,
        "retest_results": results,
        "reclassified_rows": reclassified_rows,
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def install_release_timeout_row_bounded_retest_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Install-Release Timeout Row Bounded Retest report not found."
    lines = [
        "# Install-Release Timeout Row Bounded Retest",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Timeout rows total: {report.get('timeout_rows_total')}",
        f"Timeout rows retested: {report.get('timeout_rows_retested')}",
        f"Timeout rows reclassified: {report.get('timeout_rows_reclassified')}",
        f"Timeout rows passed after retest: {report.get('timeout_rows_passed_after_retest')}",
        f"Timeout rows failed after retest: {report.get('timeout_rows_failed_after_retest')}",
        f"Timeout rows still timeout: {report.get('timeout_rows_still_timeout')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Classification counts"])
        for key, value in sorted((report.get("classification_counts") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Retested timeout rows"])
        for row in report.get("reclassified_rows") or []:
            lines.append(f"- {row.get('name')}: {row.get('bounded_retest_classification')} elapsed={row.get('elapsed_seconds')}s next={row.get('next_action')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_install_release_timeout_row_bounded_retest_review(full: bool = False) -> None:
    print(install_release_timeout_row_bounded_retest_review_text(build_install_release_timeout_row_bounded_retest_review(), full=full))
