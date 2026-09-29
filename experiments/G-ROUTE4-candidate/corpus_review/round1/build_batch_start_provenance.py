"""B10 provenance: bind the operator's original in-chat instructions for the adjudication period, verbatim.

Mechanical, with no selection or interpretation: every genuine operator message in the session transcript whose
timestamp falls between the audit-sample commit (the start of the adjudication stage) and the last record of the last
adjudication journal. Each is bound by transcript record id, timestamp, exact-text sha256 and the exact text, and is
filed against the adjudication run whose first journal record it precedes, or whose journal span contains it. Messages are never edited; a message that
contains key-like text would stop the build instead of being bound.

    python -B build_batch_start_provenance.py <session transcript .jsonl>
"""

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parents[1] / "adjudication" / "runs"
WINDOW_START = "2026-09-29T05:47:07Z"          # audit-sample commit 29f5a47 (01:47:07 -04:00)
KEYLIKE = re.compile(r"sk-ant|api[_-]?key\s*[:=]\s*\S{12,}", re.I)


def iso(ts):
    return ts.replace("+00:00", "Z")[:19] + "Z"


def main(transcript):
    raw = Path(transcript).read_bytes()
    runs = {}
    for r in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        lines = (r / "journal.jsonl").read_text(encoding="utf-8").splitlines()
        runs[r.name] = (iso(json.loads(lines[0])["utc"]), iso(json.loads(lines[-1])["utc"]))
    window_end = max(end for _, end in runs.values())
    order = sorted(runs.items(), key=lambda kv: kv[1][0])
    messages = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("type") != "user" or r.get("isMeta") or r.get("isCompactSummary") or r.get("isSidechain"):
            continue
        c = (r.get("message") or {}).get("content")
        if isinstance(c, list):
            if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                continue
            parts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
            if not parts:
                continue
            c = "\n".join(parts)
        if not isinstance(c, str) or c.startswith("<"):       # harness notices and command wrappers, not operator text
            continue
        ts = iso(r["timestamp"])
        if not (WINDOW_START <= ts <= window_end):
            continue
        if KEYLIKE.search(c):
            raise SystemExit(f"message {r['uuid']} contains key-like text; not bound")
        during = next((name for name, (start, end) in order if start <= ts <= end), None)
        before = None if during else next((name for name, (start, _) in order if ts < start), None)
        messages.append({"transcript_record_uuid": r["uuid"], "utc": r["timestamp"],
                         "text_sha256": hashlib.sha256(c.encode("utf-8")).hexdigest(), "chars": len(c),
                         "precedes_run": before, "during_run": during, "text": c})
    out = {"schema_version": "g-route4.batch-start-provenance.v1",
           "finding": "Reviewer B, B10 (NOTE): the operator's in-chat batch starts are not in the repository records",
           "rule": "every genuine operator message in the session transcript between the audit-sample commit and the last "
                   "adjudication journal record, bound verbatim; each filed against the run whose first journal record it "
                   "precedes, or the run whose journal span contains it. No selection, reconstruction or interpretation.",
           "transcript": {"session_id": Path(transcript).stem,
                          "note": "the transcript is still being appended to, so it is bound per record (uuid and text "
                                  "digest), not as a whole file"},
           "window_utc": [WINDOW_START, window_end],
           "runs_first_and_last_journal_record_utc": dict(order),
           "messages": messages}
    (HERE / "BATCH_START_PROVENANCE.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                     encoding="utf-8", newline="\n")
    for m in messages:
        print(m["utc"][:19], m["transcript_record_uuid"][:8], "before" if m["precedes_run"] else "during",
              m["precedes_run"] or m["during_run"], m["chars"])


if __name__ == "__main__":
    main(*sys.argv[1:])
