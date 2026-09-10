from __future__ import annotations

"""CLI for the v1250 segmented broad verifier."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from segmented_release_verifier import (  # noqa: E402
    DEFAULT_STAGES,
    build_segmented_verifier_manifest,
    run_segmented_verification,
)


def _text_manifest(report: dict) -> None:
    print(f"Eidolon segmented verifier ({report.get('contract_version')})")
    print(f"Status: {report.get('status')}")
    for row in report.get("stages", []):
        print(
            f"{row.get('ordinal'):>2}. {row.get('stage_id')}: "
            f"{row.get('label')} [{row.get('budget_seconds')}s, {len(row.get('suites') or [])} suites]"
        )
    print("Safety: verification evidence never authorizes release or independent action.")


def _text_run(report: dict) -> None:
    print(f"Eidolon segmented verification: {report.get('status')}")
    for row in report.get("stage_receipts", []):
        print(f"[{str(row.get('status')).upper()}] {row.get('stage_id')} ({row.get('elapsed_seconds')}s)")
    if report.get("resumable_next_stage"):
        print(f"Resume stage: {report.get('resumable_next_stage')}")
    print(f"Source unchanged: {report.get('source_unchanged')}")
    print("Safety: this report verifies evidence; it does not authorize release.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the segmented Eidolon broad verifier.")
    parser.add_argument("--list-stages", action="store_true", help="List the ten stage definitions without executing them.")
    parser.add_argument("--stage", action="append", dest="stages", help="Run one stage. Repeat to run several in the requested order.")
    parser.add_argument("--receipt", help="Write an atomic partial/final receipt outside the source tree.")
    parser.add_argument("--resume-receipt", help="Reuse unchanged passed stages from a prior receipt.")
    parser.add_argument("--continue-on-failure", action="store_true")
    parser.add_argument("--no-snapshot", action="store_true", help="Diagnostic only: execute in the selected source instead of an external snapshot.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list_stages:
        report = build_segmented_verifier_manifest(source_root=ROOT)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True, default=str))
        else:
            _text_manifest(report)
        return 0 if report.get("ok") else 1

    report = run_segmented_verification(
        source_root=ROOT,
        stage_ids=args.stages,
        receipt_path=args.receipt,
        resume_receipt=args.resume_receipt,
        stop_on_failure=not args.continue_on_failure,
        snapshot=not args.no_snapshot,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        _text_run(report)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
