"""Erratum 1 to the closed B_MAIN_CLOSURE.json (operator ruling on corpus-review finding B2, 2026-09-29).

B_MAIN_CLOSURE.json is not edited. This erratum is bound to its exact digest and corrects one characterization: its
`disagreements.batch.by_cause` counted every fenced answer as "format (code fence)", but some fenced answers also
disagree on content. The split is re-derived here from the committed batch records, diagnostically: the one outer
code fence is stripped and the frozen validators are re-run against the batch's scoring gold (the sealed gold). The
recorded verdicts are not changed; every fenced answer remains a disagreement.

    python -B build_b_closure_erratum.py    # writes B_MAIN_CLOSURE_ERRATUM_1.json next to this script
"""

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

sys.path.insert(0, str(H.ROOT / "tools"))
from g_route3_operational import validate_operational  # noqa: E402
from g_route3_semantics import validate_fixture_output  # noqa: E402

RUN = "g4adj-bmain-20260929T155837Z"
FENCE = re.compile(r"^\s*```[A-Za-z0-9_-]*\s*\n(.*?)\n?```\s*$", re.S)


def main():
    run = ADJ / "runs" / RUN
    closure_path = ADJ / "B_MAIN_CLOSURE.json"
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    fixtures = H.model_facing_b()
    gold = {g["fixture_id"]: g for g in json.loads((H.SEALED / "gold_b.json").read_text(encoding="utf-8"))["items"]}
    rows = collections.defaultdict(list)
    for ph in (1, 2):
        answers = {(r["fixture_id"], r["slot"]): r for r in
                   json.loads((run / f"answers_phase{ph}.json").read_text(encoding="utf-8"))["slots"]}
        for r in json.loads((run / f"scores_phase{ph}.json").read_text(encoding="utf-8"))["slots"]:
            if r.get("agree") is not False:
                continue
            key = f"{r['fixture_id']} slot {r['slot']}"
            if "malformed_json" not in r.get("operational_reasons", []):
                rows["content_only"].append(key)
                continue
            a = answers[(r["fixture_id"], r["slot"])]
            body = run / "raw" / f"{r['fixture_id']}__s{r['slot']}__i{a['binding_invocation']}.body"
            text = H.binding_text(json.loads(body.read_bytes()))
            assert H.sha256(text) == a["binding_text_sha256"], key
            m = FENCE.match(text)
            if not m:
                rows["malformed_not_a_fence"].append(key)
                continue
            inner = m.group(1)
            ok = validate_operational(fixtures[r["fixture_id"]], inner).get("accepted") and \
                validate_fixture_output(fixtures[r["fixture_id"]], gold[r["fixture_id"]], inner).get("hard_gate_pass")
            rows["fenced_format_only" if ok else "fenced_and_content"].append(key)
    counts = {k: len(v) for k, v in rows.items()}
    stated = closure["disagreements"]["batch"]
    assert stated["disagreeing"] == sum(counts.values()) == 131
    assert counts.get("malformed_not_a_fence", 0) == 0
    assert counts["fenced_format_only"] + counts["fenced_and_content"] == stated["by_cause"]["format (code fence)"]
    fixed = {x["fixture_id"] for x in json.loads((ADJ / "fixes/round1_bmain/FIX_RECORD.json").read_text(encoding="utf-8"))["fixes"]}
    fc_fixtures = sorted({k.split(" slot ")[0] for k in rows["fenced_and_content"]})
    erratum = {
        "schema_version": "g-route4.erratum.v1",
        "erratum": 1,
        "corrects": {"file": "adjudication/B_MAIN_CLOSURE.json", "lf_sha256": H.lf_sha256(closure_path),
                     "commit": "f07b1a2fa211ec2c4109117e2b5f1b5c742df7e2", "field": "disagreements.batch.by_cause",
                     "unchanged": "the closed file itself is not edited"},
        "authority": "operator ruling on external corpus review round 1 finding B2 (MUST-FIX), 2026-09-29: issue a "
                     "separately bound erratum; do not edit the closed artifact",
        "as_stated": stated["by_cause"],
        "corrected": {"slots": 131,
                      "fenced_format_only": counts["fenced_format_only"],
                      "fenced_with_a_content_disagreement": counts["fenced_and_content"],
                      "content_only": counts["content_only"],
                      "involving_content_total": counts["fenced_and_content"] + counts["content_only"]},
        "fenced_with_a_content_disagreement_slots": rows["fenced_and_content"],
        "fenced_with_a_content_disagreement_fixtures": fc_fixtures,
        "all_within_the_14_fixed_fixtures": set(fc_fixtures) <= fixed,
        "method": "diagnostic only: strip the one outer code fence of each fenced binding answer (binding text re-verified "
                  "by digest) and re-run the frozen validate_operational and validate_fixture_output against the sealed "
                  "gold_b.json, which scored the batch. Recorded verdicts are unchanged.",
        "also_affects": "B_MAIN_CLOSURE.json residual_limitations[0] ('107 of 131 disagreeing answers were fenced ... the "
                        "fenced content matched gold in every format-only case') is accurate as worded; only the by_cause "
                        "partition understated content disagreements (40, not 24)",
        "bind_in": "the final external-review closure and freeze records",
    }
    out = HERE / "B_MAIN_CLOSURE_ERRATUM_1.json"
    out.write_text(json.dumps(erratum, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(erratum["corrected"]), erratum["all_within_the_14_fixed_fixtures"])


if __name__ == "__main__":
    main()
