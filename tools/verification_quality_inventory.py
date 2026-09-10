from __future__ import annotations

"""Read-only inventory of likely verification styles in tools/.

This report is advisory. It deliberately does not turn heuristic classification
into release authority. Its purpose is to identify source-presence-heavy suites
for replacement by behavioral contracts.
"""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SOURCE_READ = re.compile(r"(?:read_text\(|\.read\(\)|Path\([^\n]+\.read_text)")
SOURCE_ASSERT = re.compile(r"(?:\bin\s+[A-Za-z_][A-Za-z0-9_]*|\.count\(|startswith\(|endswith\()")
RUNTIME_CUES = re.compile(r"(?:subprocess\.|HTTPConnection|ThreadingHTTPServer|create_connection|unittest\.mock|tempfile\.|_facts_from_text\(|execute_|run_|build_)")


def classify(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    sourceish = bool(SOURCE_READ.search(text) and SOURCE_ASSERT.search(text))
    runtimeish = bool(RUNTIME_CUES.search(text))
    if sourceish and not runtimeish:
        return "source_presence_candidate"
    if sourceish and runtimeish:
        return "mixed_candidate"
    if runtimeish:
        return "behavioral_or_integration_candidate"
    return "unclassified"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = []
    for path in sorted(TOOLS.glob("*.py")):
        if path.name == Path(__file__).name:
            continue
        rows.append({"path": str(path.relative_to(ROOT)), "classification": classify(path)})
    counts = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    payload = {"ok": True, "advisory_only": True, "total": len(rows), "counts": counts, "rows": rows if args.json else []}
    print(json.dumps(payload, sort_keys=True) if args.json else json.dumps({k:v for k,v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
