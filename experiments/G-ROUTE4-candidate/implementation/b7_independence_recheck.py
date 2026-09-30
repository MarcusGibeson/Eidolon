"""B7: the final pre-freeze independence re-check with the forked module, against the reviewed 26-fix corpus.

Freeze condition B7 (operator ruling, corpus_review/round1/CORPUS_REVIEW_R1_CLOSURE.json), verbatim: "After
"g_route4_independence" is implemented from the frozen design, the final pre-freeze independence re-check using that
forked module must reproduce the required frozen values and satisfy the same bounds. Failure of that check blocks
freeze and cannot be waived by the successful pinned-tool result."

- The forked module `tools/g_route4_independence.py` computes the standard over the final pool (seal + 26 recorded
  fixes). Its result is compared value by value with the frozen values in INDEPENDENCE_REPORT.json (and, for the
  values that report does not carry for the 26-fix corpus, N8, with INDEPENDENCE_REPORT_CR1.json).
- A maximum pair is compared as an unordered pair (overlap is symmetric; list order reflects only pool iteration).
  Everything else is compared exactly. Any difference, any bound violation or any finding fails B7.
- The pinned-tool result is not used as evidence here; it is only the source of the frozen values.

    python -B b7_independence_recheck.py    # writes B7_INDEPENDENCE_RECHECK.json next to this script; exit 1 on failure
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parent
ROOT = CAND.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import g_route4_independence as G4I  # noqa: E402

B7_TEXT = ('After "g_route4_independence" is implemented from the frozen design, the final pre-freeze independence '
           're-check using that forked module must reproduce the required frozen values and satisfy the same bounds. '
           'Failure of that check blocks freeze and cannot be waived by the successful pinned-tool result.')


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    frozen_path, succ_path = CAND / "INDEPENDENCE_REPORT.json", CAND / "INDEPENDENCE_REPORT_CR1.json"
    closure = load(CAND / "corpus_review/round1/CORPUS_REVIEW_R1_CLOSURE.json")
    assert closure["freeze_conditions_carried_forward"]["B7"]["condition_verbatim"] == B7_TEXT
    frozen, succ = load(frozen_path)["result_final"], load(succ_path)
    report = G4I.audit()

    comparisons = {}

    def cmp(name, want, got, unordered=False):
        same = (sorted(want) == sorted(got)) if unordered else (want == got)
        comparisons[name] = {"frozen": want, "forked": got, "equal": bool(same),
                             **({"compared_as": "unordered pair"} if unordered else {})}

    for key in ("trigram", "trigram_task_relevant"):
        for tc in frozen[key]:
            for m in ("pool", "boilerplate_trigrams", "max_jaccard", "pairs_over_bound"):
                cmp(f"{key}.{tc}.{m}", frozen[key][tc][m], report[key][tc][m])
            cmp(f"{key}.{tc}.max_pair", frozen[key][tc]["max_pair"], report[key][tc]["max_pair"], unordered=True)
        if key == "trigram":
            for tc in frozen[key]:
                cmp(f"o5.{tc}.single_family_boilerplate", frozen[key][tc]["o5_single_family_boilerplate"],
                    report[key][tc]["o5_single_family_boilerplate"])
                cmp(f"o5.{tc}.boilerplate_in_family_templates", [], report[key][tc]["o5_boilerplate_in_family_templates"])
    for m in ("g4_fixtures", "g4_entities", "g3_entities_compared", "shared"):
        cmp(f"o3_entities.{m}", frozen["o3_entities"][m], report["o3_entities"][m])
    for m in ("g4_identifiers", "g3_identifiers", "shared", "pattern_sha256"):
        cmp(f"o3_identifier_gate.{m}", frozen["o3_identifier_gate"][m], report["o3_identifier_gate"][m])
    cmp("o6.g4_values_compared_by_class", frozen["o6"]["g4_values_compared_by_class"], report["o6"]["g4_values_compared_by_class"])
    cmp("o6.collisions", frozen["o6"]["collisions"], report["o6"]["collisions"])
    for m in ("n1_duplicates", "fine_signature_clashes", "canonical_signature_clashes"):
        cmp(m, frozen[m], report[m])
    cmp("research.unique_lineages", frozen["research"]["unique_lineages"], report["unique_lineages"])
    cmp("research.cross_fixture_lineage_repeats", frozen["research"]["cross_fixture_lineage_repeats"],
        report["research_lineage_repeats"])
    cmp("planning.g4_action_names", frozen["planning"]["g4_action_names"], report["planning"]["g4_action_names"])
    cmp("planning.repeated_action_names", frozen["planning"]["repeated_action_names"], report["planning"]["repeated_action_names"])
    cmp("conversation.fixtures_with_four_options", frozen["conversation"]["fixtures_with_four_options"],
        report["conversation"]["fixtures_with_four_options"])
    cmp("conversation.gold_positions", frozen["conversation"]["gold_positions"], report["conversation"]["gold_positions"])
    for cell, want in succ["n8_same_family_a_b_max_jaccard_per_cell"].items():
        got = report["n8_same_family_a_b_max_jaccard_per_cell"][cell]
        for m in ("same_family_pairs", "max_jaccard", "family"):
            cmp(f"n8.{cell}.{m}", want[m], got[m])
        if want["max_pair"] is not None:
            cmp(f"n8.{cell}.max_pair", want["max_pair"], got["max_pair"], unordered=True)

    differing = sorted(k for k, v in comparisons.items() if not v["equal"])
    bounds = {"trigram_pairs_over_0.20": sum(v["pairs_over_bound"] for v in report["trigram"].values()),
              "task_relevant_pairs_over_0.20": sum(v["pairs_over_bound"] for v in report["trigram_task_relevant"].values()),
              "o3_shared_entities": report["o3_entities"]["shared"], "o3_shared_identifiers": report["o3_identifier_gate"]["shared"],
              "o6_collisions": report["o6"]["collisions"], "n1_duplicates": report["n1_duplicates"],
              "fine_signature_clashes": report["fine_signature_clashes"],
              "canonical_signature_clashes": report["canonical_signature_clashes"],
              "lineage_repeats": report["research_lineage_repeats"],
              "repeated_planning_actions": report["planning"]["repeated_action_names"],
              "o5_single_family_boilerplate": sum(v["o5_single_family_boilerplate"] for v in report["trigram"].values())}
    bounds_met = all(v == 0 for v in bounds.values())
    passed = report["valid"] and not differing and bounds_met
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    out = {
        "schema_version": "g-route4.b7-recheck.v1", "condition": "B7", "condition_verbatim": B7_TEXT,
        "result": "PASS" if passed else "FAIL", "blocks_freeze": not passed,
        "forked_module": {"path": "tools/g_route4_independence.py", "contract_version": G4I.CONTRACT_VERSION,
                          "lf_sha256": G4I.lf_sha256(Path(G4I.__file__))},
        "generated_at_parent_commit": head,
        "corpus": {"fixes_applied": report["fixes_applied"], "fixes": sum(len(v) for v in report["fixes_applied"].values()),
                   "pool": report["pool"]},
        "frozen_values_source": {"INDEPENDENCE_REPORT.json": G4I.lf_sha256(frozen_path),
                                 "INDEPENDENCE_REPORT_CR1.json (N8 for the 26-fix corpus)": G4I.lf_sha256(succ_path)},
        "compared": len(comparisons), "differing": differing, "comparisons": comparisons,
        "bounds": bounds, "bounds_met": bounds_met,
        "forked_findings": report["findings"],
        "declared": "a maximum pair is compared as an unordered pair; all other values exactly",
    }
    (HERE / "B7_INDEPENDENCE_RECHECK.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                      encoding="utf-8", newline="\n")
    print(f"B7 {out['result']}: {len(comparisons)} values compared, {len(differing)} differing {differing}; "
          f"bounds met {bounds_met}; forked findings {len(report['findings'])}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
