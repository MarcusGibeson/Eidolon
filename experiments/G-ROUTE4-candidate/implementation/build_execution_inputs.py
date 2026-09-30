"""Materialize the G-ROUTE4 execution inputs from the reviewed final corpus (seal + 26 recorded fixes).

Writes, into experiments/G-ROUTE4-candidate/ (the design's artifact folder):
- corpus_a.json / corpus_b.json: model-facing fixtures of A′ main (80) and B′ main (305), in sealed order;
- gold_a.json / gold_b.json: their gold (evaluator-only);
- model_bindings.json: G-ROUTE3's bindings, generation configuration and provider version, unchanged, under renamed
  ids (design "Scope": g-route4.model-bindings.v1, G-ROUTE4-MODEL-BINDINGS-R1).

Every corpus and gold digest is asserted equal to the final-corpus digests bound in the round-1 closure addenda, and
each file carries its provenance (seal, fix records, closure). Reserves are not execution inputs. Refuses to overwrite a
file with different content.

    python -B build_execution_inputs.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parent
ROOT = CAND.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import g_route4_independence as G4I  # noqa: E402  (the final-pool loader: seal + pinned fix records)

TIERS = ["small", "mid", "large"]
RISKS = ["R1", "R2", "R3", "R4"]
CLASSES = ["ordinary_conversation", "structured_extraction", "grounded_research_synthesis",
           "hierarchical_semantic_synthesis", "reflective_planning"]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def digest(items):
    return G4I.sha256(G4I.canonical_json(sorted(items, key=lambda x: x["fixture_id"])))


def write(path, doc):
    rendered = json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise FileExistsError(f"conflicting_execution_input_exists:{path.name}")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return G4I.lf_sha256(path)


def main():
    pool = G4I.load_final_pool()
    aa = load(CAND / "adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json")["final_corpus"]["a_main"]
    ba = load(CAND / "adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json")["final_corpus"]["b_main"]
    closure = load(CAND / "corpus_review/round1/CORPUS_REVIEW_R1_CLOSURE.json")
    assert closure["status"] == "CLOSED"
    provenance = {"seal_commit": "50e6b46994299ffd71c97aa3f81f30637efaba1c",
                  "fix_records_lf_sha256": {sub: pinned for sub, _, _, pinned in G4I.FIX_ROUNDS},
                  "fixes_applied": pool["fixes_applied"], "replacements": 0,
                  "corpus_review_closure": "experiments/G-ROUTE4-candidate/corpus_review/round1/CORPUS_REVIEW_R1_CLOSURE.json",
                  "corpus_review_closure_commit": "30b488a3434f69ffb1edb9b46533e4ecc1e19eba",
                  "builder": "experiments/G-ROUTE4-candidate/implementation/build_execution_inputs.py"}
    out = {}
    for corpus, sealed_name, bound in (("A", "corpus_a.json", aa), ("B", "corpus_b.json", ba)):
        order = [f["fixture_id"] for f in load(G4I.SEALED / sealed_name)["fixtures"]]
        fixtures = [pool["fixtures"][fid] for fid in order]
        gold = [pool["gold"][fid] for fid in order]
        assert order == bound["fixtures"] or sorted(order) == bound["fixtures"]
        assert digest(fixtures) == bound["model_facing_sha256"], corpus
        assert digest(gold) == bound["gold_sha256"], corpus
        lower = corpus.lower()
        corpus_doc = {
            "schema_version": "g-route4.fixture-corpus.v1", "corpus_id": f"G-ROUTE4-CORPUS-{corpus}",
            "corpus_role": "qualification" if corpus == "A" else "validation",
            "fixture_count": len(fixtures), "fixtures": fixtures, "model_input_contains_gold": False,
            "model_tiers": TIERS, "risk_classes": RISKS, "task_classes": CLASSES,
            "fixtures_per_cell": 4 if corpus == "A" else None,
            "cell_composition": ("4 per cell, 20 cells" if corpus == "A" else
                                 "D9: 28 per conversation cell R1-R3, 18 per other eligible cell, 1 per R4 cell"),
            "final_corpus_sha256": digest(fixtures), "provenance": provenance}
        gold_doc = {"schema_version": "g-route4.gold.v1", "gold_id": f"G-ROUTE4-GOLD-{corpus}",
                    "corpus_id": f"G-ROUTE4-CORPUS-{corpus}", "item_count": len(gold), "items": gold,
                    "model_input": False, "ambiguity_count": 0, "final_gold_sha256": digest(gold),
                    "adjudication": ("gold adjudicated per design step 6-13; see adjudication/A_MAIN_CLOSURE.json and its "
                                     "addendum" if corpus == "A" else
                                     "gold adjudicated per design step 6-13; see adjudication/B_MAIN_CLOSURE.json, its "
                                     "errata and addendum"),
                    "provenance": provenance}
        out[f"corpus_{lower}.json"] = write(CAND / f"corpus_{lower}.json", corpus_doc)
        out[f"gold_{lower}.json"] = write(CAND / f"gold_{lower}.json", gold_doc)
    g3 = load(ROOT / "experiments/G-ROUTE3-candidate/model_bindings.json")
    bindings = {"schema_version": "g-route4.model-bindings.v1", "binding_id": "G-ROUTE4-MODEL-BINDINGS-R1",
                "provider": g3["provider"], "provider_version": g3["provider_version"],
                "bindings": g3["bindings"], "generation_configuration": g3["generation_configuration"],
                "metadata_inspected_without_generation": g3["metadata_inspected_without_generation"],
                "provider_generation_calls": 0, "belief_effects": "none",
                "rationale": ("Model identities, provider version and every generation option are carried unchanged "
                              "(design 'Scope'); only the ids are renamed. A test asserts equality of bindings, "
                              "generation_configuration and provider_version across the three experiments' files."),
                "verification_limitations": g3["verification_limitations"],
                "source": "experiments/G-ROUTE3-candidate/model_bindings.json (read-only)"}
    out["model_bindings.json"] = write(CAND / "model_bindings.json", bindings)
    for name, d in out.items():
        print(f"{name:20s} {d}")


if __name__ == "__main__":
    main()
