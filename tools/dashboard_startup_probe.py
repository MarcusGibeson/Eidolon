from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

from dashboard_startup import DEFAULT_READY_ROUTE, build_dashboard_startup_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure fresh Eidolon dashboard startup without mutating source data.")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--route", default=DEFAULT_READY_ROUTE)
    parser.add_argument("--skip-import-profile", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_dashboard_startup_report(
        ROOT,
        runs=args.runs,
        route=args.route,
        profile_imports=not args.skip_import_profile,
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
