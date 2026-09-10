from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from windows_startup_soak import DEFAULT_SOAK_RUNS, run_windows_startup_soak


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded content-free Eidolon startup soak evidence.")
    parser.add_argument("--runs", type=int, default=DEFAULT_SOAK_RUNS)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--include-provider-probe", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_windows_startup_soak(
        ROOT,
        runs=args.runs,
        timeout_seconds=args.timeout,
        include_provider_probe=args.include_provider_probe,
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
