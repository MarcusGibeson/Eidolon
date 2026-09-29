"""Preserve Reviewer A's report after its resumption (operator decision 1a), before any comparison or disposition.

The report is the verbatim `message` of the session's single SubagentHandback call, written as its exact UTF-8 bytes.
The record also binds the resumption: the resume message, both session segments, the transcript digest, the
post-resume tool calls checked against the three resume instructions, and the reviewer's sealed derivation files
compared with the digest inventory committed at the interruption (REVIEW_OUTPUTS_RECORD.json). The earlier record is
not changed.

    python -B preserve_reviewer_a_resumed.py <transcripts dir> <scratch corpus_review_r1 dir>
"""

import collections
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
SID = "adb1b2921bfb6f038"
INTERRUPTED_AT = "2026-09-29T21:35:54.179Z"
FORBIDDEN = ("corpus_review/round1/outputs", "corpus_review\\round1\\outputs", "reviewer_B", "errata",
             "OPERATOR_RULINGS", "BATCH_START_PROVENANCE", "b7ac00f", "ae62dba", "REVIEWER_B")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(transcripts, scratch):
    transcripts, scratch = Path(transcripts), Path(scratch)
    raw = (transcripts / f"agent-{SID}.jsonl").read_bytes()
    recs = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    after = [r for r in recs if r.get("timestamp", "") > INTERRUPTED_AT]
    resume_msgs = [r for r in after if r.get("type") == "user" and isinstance((r.get("message") or {}).get("content"), str)]
    tool_inputs = [json.dumps(c["input"], ensure_ascii=False) for r in after if r.get("type") == "assistant"
                   for c in (r.get("message") or {}).get("content", []) if isinstance(c, dict) and c.get("type") == "tool_use"
                   and c["name"] != "SubagentHandback"]         # the report itself names the paths it did not open
    violations = [t[:200] for t in tool_inputs if any(f in t for f in FORBIDDEN)]
    handbacks = [c["input"]["message"] for r in recs if r.get("type") == "assistant"
                 for c in (r.get("message") or {}).get("content", [])
                 if isinstance(c, dict) and c.get("type") == "tool_use" and c["name"] == "SubagentHandback"]
    assert len(handbacks) == 1, len(handbacks)
    data = handbacks[0].encode("utf-8")
    (OUT / "REVIEWER_A_REPORT.md").write_bytes(data)

    earlier = json.loads((OUT / "REVIEW_OUTPUTS_RECORD.json").read_text(encoding="utf-8"))["reviewers"]["A"]
    inv_then = earlier["scratch_inventory_sha256"]
    folder = scratch / "reviewer_A"
    derivation_files = {k: v for k, v in inv_then.items() if k.startswith("derivations/")}
    changed = {k: "missing" if not (folder / k).exists() else "changed"
               for k, v in derivation_files.items() if not (folder / k).exists() or sha((folder / k).read_bytes()) != v}
    models = collections.Counter((r.get("message") or {}).get("model") for r in after if r.get("type") == "assistant")
    record = {
        "schema_version": "g-route4.corpus-review-resumption.v1", "round": 1, "reviewer": "A",
        "operator_decision": "1(a): resume the same session (corpus_review/round1/OPERATOR_RULINGS_R1.json)",
        "interrupted_at_utc": INTERRUPTED_AT,
        "resume_message_verbatim": [(r["message"]["content"]) for r in resume_msgs],
        "resumed_segment_utc": [after[0].get("timestamp"), after[-1].get("timestamp")] if after else None,
        "resumed_segment_models": {k: v for k, v in models.items() if k},
        "resumed_segment_tool_calls": len(tool_inputs),
        "resume_instruction_check": {"forbidden_path_markers": list(FORBIDDEN), "tool_calls_touching_them": violations},
        "derivations_unchanged_since_interruption": {"files": len(derivation_files), "changed_or_missing": changed},
        "transcript_sha256": sha(raw), "transcript_records": len(recs),
        "report_file": "outputs/REVIEWER_A_REPORT.md", "report_sha256_exact_bytes": sha(data), "report_chars": len(handbacks[0]),
        "verdict_line": next(l for l in handbacks[0].splitlines() if l.startswith("VERDICT:")),
        "reviewed_commit": "97afe8a93def2c1eb572e38f567f68ab5cb53b4b",
    }
    (OUT / "REVIEWER_A_RESUMPTION_RECORD.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                                                          encoding="utf-8", newline="\n")
    print(record["verdict_line"], "|", record["report_sha256_exact_bytes"], "|", record["resumed_segment_utc"],
          record["resumed_segment_models"], "| tool calls", len(tool_inputs), "| violations", len(violations),
          "| derivations", len(derivation_files), "changed", changed)


if __name__ == "__main__":
    main(*sys.argv[1:])
