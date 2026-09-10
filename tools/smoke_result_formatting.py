from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any, Iterable, Mapping

SMOKE_RESULT_FORMATTING_VERSION = RUNTIME_VERSION

INSTALL_RELEASE_SUPERSEDED_TIMEOUT_PARENT_ROWS: set[str] = {
    "recovery-drill-and-release-closure-v1",
    "release-candidate-integrity-and-operator-handoff-v1",
    "release-decision-and-archive-ledger-v1",
    "release-archive-retrieval-and-continuity-index-v1",
    "release-archive-search-and-handoff-review-v1",
    "release-archive-export-and-decision-closure-v1",
    "release-archive-import-and-closure-recall-v1",
}

INSTALL_RELEASE_DECOMPOSED_LEGACY_PILOT_ROWS: set[str] = {
    "fast-install-release-isolation-gate-v1",
}

INSTALL_RELEASE_DECOMPOSED_SLOW_EVIDENCE_ROWS: set[str] = {
    "install-release-timeout-harness-repair-v1",
    "install-release-timeout-row-bounded-retest-v1",
    "install-release-fixture-decomposition-plan-v1",
    "installed-tree-cleanup-enforcement-v1",
    "installed-tree-cleanup-and-historical-verification-reconciliation-v1",
}

INSTALL_RELEASE_SUPERSEDED_REPLACEMENTS: dict[str, str] = {
    "recovery-drill-and-release-closure-v1": "recovery-closure-parent-replacement-overlay-v1",
    "release-candidate-integrity-and-operator-handoff-v1": "candidate-handoff-parent-replacement-overlay-v1",
    "release-decision-and-archive-ledger-v1": "decision-archive-ledger-parent-replacement-overlay-v1",
    "release-archive-retrieval-and-continuity-index-v1": "install-release-timeout-parent-row-replacement-pilot-v1",
    "release-archive-search-and-handoff-review-v1": "install-release-parent-replacement-expansion-v1",
    "release-archive-export-and-decision-closure-v1": "install-release-parent-replacement-expansion-v1",
    "release-archive-import-and-closure-recall-v1": "final-timeout-parent-overlay-closure-v1",
    "fast-install-release-isolation-gate-v1": "json-output-stability-gate-v1",
    "install-release-timeout-harness-repair-v1": "compile-timeout-historical-gate-harness-v1",
    "install-release-timeout-row-bounded-retest-v1": "install-release-segment-runner-timeout-decomposition-v1",
    "install-release-fixture-decomposition-plan-v1": "install-release-segment-runner-timeout-decomposition-v1",
    "installed-tree-cleanup-enforcement-v1": "installed-tree-cleanup-and-historical-verification-reconciliation-v1",
    "installed-tree-cleanup-and-historical-verification-reconciliation-v1": "current-version-staleness-and-post-patch-verification-v1",
}

SUPERSEDED_STATUS = "superseded-timeout-parent"


def is_install_release_superseded_row(name: str) -> bool:
    return name in INSTALL_RELEASE_SUPERSEDED_TIMEOUT_PARENT_ROWS or name in INSTALL_RELEASE_DECOMPOSED_LEGACY_PILOT_ROWS or name in INSTALL_RELEASE_DECOMPOSED_SLOW_EVIDENCE_ROWS


def superseded_reason_for(name: str) -> str:
    if name in INSTALL_RELEASE_SUPERSEDED_TIMEOUT_PARENT_ROWS:
        return "overlay evidence"
    if name in INSTALL_RELEASE_DECOMPOSED_SLOW_EVIDENCE_ROWS:
        return "bounded individual evidence"
    return "legacy pilot isolation evidence"


def build_segment_superseded_result(check: Any) -> dict[str, object]:
    name = str(getattr(check, "name", ""))
    reason = superseded_reason_for(name)
    replacement_check = INSTALL_RELEASE_SUPERSEDED_REPLACEMENTS.get(name, "documented-current-segment-evidence")
    print(
        f"[superseded] smoke {name} (install-release parent segment uses {reason}; replacement={replacement_check}; run --check {name} for individual historical verification)",
        flush=True,
    )
    return {
        "name": name,
        "tier": getattr(check, "tier", "install"),
        "status": SUPERSEDED_STATUS,
        "ok": True,
        "elapsed_seconds": 0.0,
        "timeout_seconds": getattr(check, "timeout", 0),
        "mode": "decomposed-install-release-parent",
        "superseded_reason": reason,
        "replacement_check": replacement_check,
        "parent_segment_runs_superseded_timeout_rows": False,
        "individual_parent_check_remains_available": True,
        "segment_runner_treats_superseded_parent_as_current_pass": False,
        "counts_as_parent_executed_pass": False,
        "release_authorized": False,
        "autonomy_expanded": False,
    }


def split_executed_and_superseded(results: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    executed: list[dict[str, Any]] = []
    superseded: list[dict[str, Any]] = []
    for row in results:
        normalized = dict(row)
        if str(normalized.get("status")) == SUPERSEDED_STATUS:
            superseded.append(normalized)
        else:
            executed.append(normalized)
    return executed, superseded


def summarize_executed_results(executed_results: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    rows = [dict(row) for row in executed_results]
    passed = sum(1 for row in rows if row.get("ok") is True)
    failed = sum(1 for row in rows if row.get("ok") is not True)
    forced_failed = sum(1 for row in rows if str(row.get("status")) in {"forced-failed", "forced_failed"})
    return {
        "executed_check_count": len(rows),
        "passed_executed_count": passed,
        "failed_executed_count": failed,
        "forced_failed_count": forced_failed,
    }


def build_smoke_summary(*, version: str, tier: str, segment: str | None, elapsed_seconds: float, results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    result_rows = [dict(row) for row in results]
    executed_results, superseded_results = split_executed_and_superseded(result_rows)
    executed_counts = summarize_executed_results(executed_results)
    failed_results = [row for row in executed_results if row.get("ok") is not True]
    ok = not failed_results and all(row.get("ok") is True for row in superseded_results)
    accounted_total = executed_counts["executed_check_count"] + len(superseded_results)
    return {
        "version": version,
        "tier": tier,
        "segment": segment,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "check_count": len(result_rows),
        **executed_counts,
        "superseded_check_count": len(superseded_results),
        "accounted_check_count": accounted_total,
        "summary_counts_match_results": accounted_total == len(result_rows),
        "parent_segment_counts_superseded_as_passed": False,
        "failed": failed_results,
        "superseded": superseded_results,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "results": result_rows,
    }


def validate_smoke_summary_honesty(summary: Mapping[str, Any]) -> dict[str, Any]:
    check_count = int(summary.get("check_count") or 0)
    executed_count = int(summary.get("executed_check_count") or 0)
    superseded_count = int(summary.get("superseded_check_count") or 0)
    failed = list(summary.get("failed") or [])
    superseded = list(summary.get("superseded") or [])
    results = list(summary.get("results") or [])
    violations: list[str] = []
    if executed_count + superseded_count != check_count:
        violations.append("executed_plus_superseded_must_equal_check_count")
    if len(results) != check_count:
        violations.append("result_row_count_must_equal_check_count")
    if any(row.get("ok") is not True for row in results if str(row.get("status")) != SUPERSEDED_STATUS) and not failed:
        violations.append("failed_executed_rows_must_be_disclosed")
    if any(str(row.get("status")) == SUPERSEDED_STATUS and row.get("counts_as_parent_executed_pass") is not False for row in superseded):
        violations.append("superseded_rows_must_not_count_as_executed_passes")
    if summary.get("parent_segment_counts_superseded_as_passed") is not False:
        violations.append("parent_segment_must_not_count_superseded_as_passed")
    return {
        "ok": not violations,
        "violations": violations,
        "check_count": check_count,
        "executed_check_count": executed_count,
        "superseded_check_count": superseded_count,
        "failed_count": len(failed),
        "result_count": len(results),
    }


def build_decomposition_extraction_report(project_root: str | Path, *, expected_version: str, previous_smoke_line_count: int = 22168) -> dict[str, Any]:
    root = Path(project_root)
    smoke_path = root / "tools" / "smoke_check.py"
    helper_path = root / "tools" / "smoke_result_formatting.py"
    smoke_text = smoke_path.read_text(encoding="utf-8")
    helper_text = helper_path.read_text(encoding="utf-8")
    smoke_lines = smoke_text.count("\n") + 1
    sample_summary = build_smoke_summary(
        version=expected_version,
        tier="install",
        segment="install-release",
        elapsed_seconds=0.001,
        results=[
            {"name": "sample-pass", "tier": "install", "status": "pass", "ok": True},
            {"name": "sample-fail", "tier": "install", "status": "blocked", "ok": False},
            build_segment_superseded_result(type("Check", (), {"name": "fast-install-release-isolation-gate-v1", "tier": "install", "timeout": 120})()),
        ],
    )
    honesty = validate_smoke_summary_honesty(sample_summary)
    required_helper_tokens = [
        "SMOKE_RESULT_FORMATTING_VERSION",
        "build_smoke_summary",
        "validate_smoke_summary_honesty",
        "build_segment_superseded_result",
        "INSTALL_RELEASE_SUPERSEDED_REPLACEMENTS",
    ]
    required_smoke_tokens = [
        "from smoke_result_formatting import",
        "build_smoke_summary",
        "validate_smoke_summary_honesty",
        "check_smoke_check_decomposition_extraction_v1",
    ]
    rows = [
        {"name": "helper-module-current", "ok": SMOKE_RESULT_FORMATTING_VERSION == expected_version},
        {"name": "helper-module-has-required-tokens", "ok": all(token in helper_text for token in required_helper_tokens)},
        {"name": "smoke-check-imports-helper", "ok": all(token in smoke_text for token in required_smoke_tokens)},
        {"name": "smoke-check-growth-bounded", "ok": smoke_lines <= previous_smoke_line_count + 200, "current_line_count": smoke_lines, "previous_line_count": previous_smoke_line_count, "successor_ceiling": previous_smoke_line_count + 200},
        {"name": "summary-counts-match-results", "ok": sample_summary.get("summary_counts_match_results") is True},
        {"name": "failed-rows-disclosed", "ok": len(sample_summary.get("failed") or []) == 1},
        {"name": "superseded-rows-disclosed-separately", "ok": len(sample_summary.get("superseded") or []) == 1 and sample_summary.get("parent_segment_counts_superseded_as_passed") is False},
        {"name": "summary-honesty-validation-passes", "ok": honesty.get("ok") is True},
    ]
    return {
        "version": expected_version,
        "check_id": "smoke-check-decomposition-extraction-v1",
        "ok": all(row.get("ok") is True for row in rows),
        "status": "pass" if all(row.get("ok") is True for row in rows) else "blocked",
        "helper_module": "tools/smoke_result_formatting.py",
        "extracted_helpers": required_helper_tokens,
        "smoke_check_line_count": smoke_lines,
        "previous_smoke_check_line_count": previous_smoke_line_count,
        "line_count_delta": smoke_lines - previous_smoke_line_count,
        "sample_summary": sample_summary,
        "honesty_validation": honesty,
        "rows": rows,
        "actual_fixture_execution_count": 0,
        "subprocess_spawn_count": 0,
        "source_write_count": 0,
        "source_delete_count": 0,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "manual_smoke_remains_authoritative": True,
    }
