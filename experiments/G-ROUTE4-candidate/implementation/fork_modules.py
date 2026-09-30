"""Mechanical identity fork of the G-ROUTE3 R7 stack into g_route4_* (design "Identity and separation").

This is only the first, mechanical step: every forked module is copied from its G-ROUTE3 source (LF-normalized) and
the identity table below is applied; nothing else. The design-driven changes (coding exclusion, 8/8 qualification,
the G-ROUTE4 gates, denominators, D9 composition, prefixes, seeds, the dropped modules) are made afterwards in
separate commits, so the difference between this output and the final module is exactly the design change.

- Forked (design table): platform, fs, contract, qualification, validation, scorer, lifecycle, journal, evidence,
  launch, freeze, runner, independence (already forked separately: not touched here), campaign; tests: tests ->
  tests, r7_tests -> r7_tests.
- Imported unchanged, never renamed: g_route3_conversation, g_route3_semantics, g_route3_operational,
  g_route3_triggers, g_route3_routing, and their contract ids (carried by module attribute).
- Not forked: g_route3_worker (coding runner), g_route3_r7_differential (an R6-versus-R7 test).

    python -B fork_modules.py        # writes tools/g_route4_<m>.py (refuses to overwrite) and FORK_RECORD.json
"""

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TOOLS = ROOT / "tools"
FORKED = ["platform", "fs", "contract", "qualification", "validation", "scorer", "lifecycle", "journal", "evidence",
          "launch", "freeze", "runner", "campaign", "tests", "r7_tests"]
IMPORTED_UNCHANGED = ["conversation", "semantics", "operational", "triggers", "routing"]
CARRIED_CONTRACT_IDS = ["g-route3.conversation-frame.v3", "g-route3.semantics.v1", "g-route3.operational-validator.v2",
                        "g-route3.triggers.v1", "g-route3.routing.v1"]
KEEP = [f"g_route3_{m}" for m in IMPORTED_UNCHANGED] + CARRIED_CONTRACT_IDS + ["g_route3_worker", "g_route3_r7_differential"]
# Ordered identity substitutions (design "Identity constants" table)
TABLE = [
    ("G-ROUTE3-candidate", "G-ROUTE4-candidate"),
    ("G-ROUTE3", "G-ROUTE4"),
    ("g-route3", "g-route4"),
    ("GROUTE3", "GROUTE4"),
    ("groute3", "groute4"),
    ("g_route3", "g_route4"),
    ("RouteThree", "RouteFour"),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fork(text):
    placeholders = {}
    for i, k in enumerate(sorted(KEEP, key=len, reverse=True)):
        token = f"\x00KEEP{i}\x00"
        placeholders[token] = k
        text = text.replace(k, token)
    counts = {}
    for old, new in TABLE:
        counts[old] = text.count(old)
        text = text.replace(old, new)
    for token, k in placeholders.items():
        text = text.replace(token, k)
    return text, counts


def main():
    record = {"schema_version": "g-route4.fork-record.v1", "table": TABLE, "kept_unchanged": KEEP, "modules": {}}
    for m in FORKED:
        src = TOOLS / f"g_route3_{m}.py"
        dst = TOOLS / f"g_route4_{m}.py"
        if dst.exists():
            raise SystemExit(f"refusing to overwrite {dst.name}")
        raw = src.read_bytes().replace(b"\r\n", b"\n")
        text, counts = fork(raw.decode("utf-8"))
        text = f"# forked from g_route3_{m}\n" + text
        dst.write_bytes(text.encode("utf-8"))
        record["modules"][m] = {"source": f"tools/g_route3_{m}.py", "source_lf_sha256": sha(raw),
                                "mechanical_fork_lf_sha256": sha(text.encode("utf-8")), "substitutions": counts}
    (HERE / "FORK_RECORD.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    for m, r in record["modules"].items():
        print(f"{m:14s} {sum(r['substitutions'].values()):4d} substitutions")


if __name__ == "__main__":
    main()
