"""Preserve the round-1 reviewer outputs exactly as produced, before any comparison or disposition.

- Reviewer B's report is the verbatim `message` of its single SubagentHandback call (the sub-session harness refused
  a report file), written as its exact UTF-8 bytes.
- Reviewer A produced no report: its session ended on a provider rate-limit error (HTTP 429) mid-review. Its only
  text outputs are recorded verbatim, and its scratch folder is inventoried by digest (not opened).
- For both: session metadata, model ids, timestamps, tool counts and the transcript digest.

    python -B preserve_outputs.py <transcripts dir> <scratch corpus_review_r1 dir>
"""

import collections
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
SESSIONS = {"A": "adb1b2921bfb6f038", "B": "ab702346d4c6e8293"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(transcripts, scratch):
    transcripts, scratch = Path(transcripts), Path(scratch)
    OUT.mkdir(exist_ok=True)
    record = {"schema_version": "g-route4.corpus-review-outputs.v1", "round": 1,
              "review_package_commit": "97afe8a93def2c1eb572e38f567f68ab5cb53b4b",
              "launched": "2026-09-29T21:17Z, both in parallel, as background sub-sessions of the operator's Claude Code "
                          "session; each prompt pointed only to its committed brief and the brief's LF sha256",
              "reviewers": {}}
    for name, sid in SESSIONS.items():
        raw = (transcripts / f"agent-{sid}.jsonl").read_bytes()
        meta = json.loads((transcripts / f"agent-{sid}.meta.json").read_text(encoding="utf-8"))
        recs = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        models = collections.Counter((r.get("message") or {}).get("model") for r in recs if r.get("type") == "assistant")
        tools = collections.Counter(c["name"] for r in recs if r.get("type") == "assistant"
                                    for c in (r.get("message") or {}).get("content", []) if isinstance(c, dict) and c.get("type") == "tool_use")
        texts = [c["text"] for r in recs if r.get("type") == "assistant"
                 for c in (r.get("message") or {}).get("content", []) if isinstance(c, dict) and c.get("type") == "text"]
        handbacks = [c["input"]["message"] for r in recs if r.get("type") == "assistant"
                     for c in (r.get("message") or {}).get("content", [])
                     if isinstance(c, dict) and c.get("type") == "tool_use" and c["name"] == "SubagentHandback"]
        errors = [((r.get("message") or {}).get("content") or [{}])[0].get("text") for r in recs if r.get("isApiErrorMessage")]
        entry = {"session_type": meta.get("agentType"), "description": meta.get("description"),
                 "fresh_session": True, "spawn_depth": meta.get("spawnDepth"),
                 "models": {k: v for k, v in models.items() if k}, "first_record_utc": recs[0].get("timestamp"),
                 "last_record_utc": recs[-1].get("timestamp"), "tool_calls": dict(tools),
                 "transcript_sha256": sha(raw), "transcript_records": len(recs),
                 "terminal_api_errors": errors}
        if handbacks:
            assert len(handbacks) == 1
            data = handbacks[0].encode("utf-8")
            (OUT / f"REVIEWER_{name}_REPORT.md").write_bytes(data)
            entry.update(status="REPORT DELIVERED (via the sub-session hand-back; the report-file write was refused by "
                                "the harness), then the session ended on the provider error above",
                         report_file=f"outputs/REVIEWER_{name}_REPORT.md", report_sha256_exact_bytes=sha(data),
                         report_chars=len(handbacks[0]),
                         verdict_line=next(l for l in handbacks[0].splitlines() if l.startswith("VERDICT:")))
        else:
            inv = {str(p.relative_to(scratch / f"reviewer_{name}")).replace("\\", "/"): sha(p.read_bytes())
                   for p in sorted((scratch / f"reviewer_{name}").rglob("*")) if p.is_file()
                   and "export" not in p.relative_to(scratch / f"reviewer_{name}").parts}
            entry.update(status="NO REPORT: the session ended on the provider error above before its review was complete",
                         text_outputs_verbatim=texts,
                         scratch_inventory_sha256=inv,
                         scratch_note="inventoried by digest only (the exported repository copy under export/ is omitted); "
                                      "not opened, not used")
        record["reviewers"][name] = entry
    (OUT / "REVIEW_OUTPUTS_RECORD.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                                                   encoding="utf-8", newline="\n")
    for name, e in record["reviewers"].items():
        print(name, e["status"][:60], "|", e.get("verdict_line"), "|", e.get("report_sha256_exact_bytes"), "|",
              e["models"], e["first_record_utc"], e["last_record_utc"])


if __name__ == "__main__":
    main(*sys.argv[1:])
