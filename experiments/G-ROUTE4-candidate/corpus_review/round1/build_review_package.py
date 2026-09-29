"""G-ROUTE4 external corpus review (design order of work 3.7), round 1: the review package.

Materializes the FINAL main corpus exactly as the adjudication records bind it (the sealed corpus with the 20
recorded round-1 fixes overlaid; no replacement), in two separate files so a reviewer can derive answers from the
model-facing input before opening gold:

    FINAL_MAIN_MODEL_FACING.json   the 385 main fixtures (80 A′, 305 B′), model-facing only
    FINAL_MAIN_GOLD.json           their gold (expected, reference output, rationale)
    REVIEW_MANIFEST.json           every binding digest, and the digests of the two reviewer briefs

Each digest is asserted equal to the one recorded in A_MAIN_CLOSURE.json, B_MAIN_CLOSURE.json and
INDEPENDENCE_REPORT.json. Nothing sealed or adjudicated is read for writing; no model is contacted.

    python -B build_review_package.py
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parents[1]
ADJ = CAND / "adjudication"
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402


def digest(items):
    return H.sha256(H.canonical(sorted(items.values(), key=lambda x: x["fixture_id"])))


def write(path, obj):
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main():
    fa, fb = ADJ / "fixes/round1_amain", ADJ / "fixes/round1_bmain"
    mf = {**H.model_facing_a(fa), **H.model_facing_b(fb)}
    ga, gb = H.gold_path_overlay(fa, gold_file="gold_a.json"), H.gold_path_overlay(fb)
    gold = {**ga, **gb}
    a_clo = json.loads((ADJ / "A_MAIN_CLOSURE.json").read_text(encoding="utf-8"))
    b_clo = json.loads((ADJ / "B_MAIN_CLOSURE.json").read_text(encoding="utf-8"))
    ind = json.loads((CAND / "INDEPENDENCE_REPORT.json").read_text(encoding="utf-8"))
    a_ids = sorted(f for f in mf if f.startswith("A4-"))
    b_ids = sorted(f for f in mf if f.startswith("B4-"))
    assert len(a_ids) == 80 and len(b_ids) == 305 and sorted(gold) == sorted(mf)
    assert digest({f: mf[f] for f in a_ids}) == a_clo["final_corpus"]["a_main"]["model_facing_sha256"] \
        == ind["binding"]["final_pool"]["corpus_a.json"]["canonical_sha256"]
    assert digest({f: mf[f] for f in b_ids}) == a_clo["final_corpus"]["b_main"]["model_facing_sha256"] \
        == b_clo["final_b_main_corpus"]["model_facing_sha256"] == ind["binding"]["final_pool"]["corpus_b.json"]["canonical_sha256"]
    assert digest(ga) == a_clo["final_corpus"]["a_main"]["gold_sha256"]
    assert digest(gb) == a_clo["final_corpus"]["b_main"]["gold_sha256"] == b_clo["final_b_main_corpus"]["gold_sha256"]
    fixed = sorted(a_clo["final_corpus"]["a_main"]["fixed"] + a_clo["final_corpus"]["b_main"]["fixed"])
    assert len(fixed) == 20

    head = {"schema_version": "g-route4.corpus-review-package.v1",
            "definition": "final main corpus: sealed corpus (seal 50e6b46) with the 20 recorded round-1 fixes overlaid; "
                          "no replacement; reserves unchanged and unused",
            "fixed_fixtures": fixed}
    write(HERE / "FINAL_MAIN_MODEL_FACING.json", dict(head, fixtures=[mf[f] for f in a_ids + b_ids]))
    write(HERE / "FINAL_MAIN_GOLD.json", dict(head, items=[gold[f] for f in a_ids + b_ids]))

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=H.ROOT, capture_output=True, text=True, check=True).stdout.strip()
    manifest = {
        "schema_version": "g-route4.corpus-review-manifest.v1",
        "design_step": "order of work 3.7: the external corpus review (two fresh reviewers, safety-gated rule; accepted "
                       "at 0 BLOCKING with every MUST-FIX resolved; changes through fixes or replacements with re-adjudication)",
        "package_built_at_parent_commit": commit,
        "final_main_corpus": {
            "a_main_model_facing_sha256": a_clo["final_corpus"]["a_main"]["model_facing_sha256"],
            "a_main_gold_sha256": a_clo["final_corpus"]["a_main"]["gold_sha256"],
            "b_main_model_facing_sha256": a_clo["final_corpus"]["b_main"]["model_facing_sha256"],
            "b_main_gold_sha256": a_clo["final_corpus"]["b_main"]["gold_sha256"],
            "fixed_fixtures": fixed, "replaced": [],
            "package_files_lf_sha256": {n: H.lf_sha256(HERE / n) for n in ("FINAL_MAIN_MODEL_FACING.json", "FINAL_MAIN_GOLD.json")}},
        "reserves_unchanged_sha256": {"reserve_corpus_a": a_clo["final_corpus"]["reserve_a_sha256_sealed_unchanged"],
                                      "reserve_corpus_b": a_clo["final_corpus"]["reserve_b_sha256_sealed_unchanged"]},
        "seal": {"commit": "50e6b46994299ffd71c97aa3f81f30637efaba1c", "tag": "g-route4-seal",
                 "tag_object": "86ff773cf1dacd7d2e3a75cc9907ae436f739787",
                 "audit_sample_commit": "29f5a477693d703699af62f9fc0e0945c9c66be2",
                 "blueprint_commit": "1156d0645b1b113b91c65e4a485b7f75ffa10061",
                 "seal_manifest_lf_sha256": H.lf_sha256(H.SEALED / "SEAL_MANIFEST.json")},
        "o2": {"sealed_config_sha256": "1658b9a2a32fa176c8ca679d5407725b17379902610869fc3cdc91d03df88029",
               "amended_config_sha256": H.AMENDED_CONFIG_SHA256,
               "amendment_record": "adjudication/O2_AMENDMENT_2026-09-29.md"},
        "reports_lf_sha256": {p: H.lf_sha256(CAND / p) for p in
                              ("INDEPENDENCE_REPORT.json", "CONTAMINATION_ANALYSIS.md", "adjudication/A_MAIN_CLOSURE.json",
                               "adjudication/B_MAIN_CLOSURE.json", "adjudication/fixes/LATENT_DEFECTS.md",
                               "adjudication/fixes/round1_amain/LATENT_DEFECTS_ADDENDUM.md")},
        "checker": {"check_corpus_commit": "dd8193bfcf1db05c752635dc4f8911a58098c97b",
                    "check_corpus_lf_sha256": ind["binding"]["tool"]["check_corpus_lf_sha256"],
                    "frozen_g3_detector_lf_sha256": ind["binding"]["tool"]["frozen_g3_detector"]["lf_sha256"]},
        "briefs_lf_sha256": {n: H.lf_sha256(HERE / n) for n in ("REVIEWER_A_BRIEF.md", "REVIEWER_B_BRIEF.md")},
    }
    write(HERE / "REVIEW_MANIFEST.json", manifest)
    print(json.dumps(manifest["final_main_corpus"], indent=1, ensure_ascii=False))
    print("briefs:", manifest["briefs_lf_sha256"])


if __name__ == "__main__":
    main()
