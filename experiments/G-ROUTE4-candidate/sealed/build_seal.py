"""Build the G-ROUTE4 seal folder (experiments/G-ROUTE4-candidate/sealed/) from a staging export. Contacts nothing.

Uses the prepared, tested seal layout (corpus/seal_layout.py) unchanged, and adds only what the operator's seal
requirements name: the frozen O2 configuration, the O3 identifier decision and gate specification, the committed
name-stream artifact, the seal notes (placement, O1 runbook, carried note N4), and a manifest with every pinned digest
(frozen blueprint, accepted design, obligations, approved sentences, validators, authoring toolchain, sealed files).
Every pinned digest is verified before anything is written; any mismatch aborts.

    python -B build_seal.py <repository export root at the staging checkpoint> <output folder>
"""

import hashlib
import json
import re
import sys
from pathlib import Path

SEAL_PARENT = "1156d0645b1b113b91c65e4a485b7f75ffa10061"
STAGING_COMMIT = "dd8193bfcf1db05c752635dc4f8911a58098c97b"
STAGING_TREE = "e4cc9469cfd6f90e916d624a4a9c0ac4b11cfe96"
SEAL_BRANCH = "g-route4/seal"
OPERATOR_DECISION_DATE = "2026-09-29"
CLASSES = ("extraction", "synthesis", "planning", "conversation", "research")
VALIDATORS = ["tools/g_route1_validators.py", "tools/g_route3_semantics.py", "tools/g_route3_operational.py",
              "tools/g_route3_conversation.py", "tools/g_route3_independence.py", "tools/g_route3_contract.py",
              "experiments/G-ROUTE1-candidate/prompt_profiles.json",
              "experiments/G-ROUTE1-candidate/model_bindings.json"]


def lf_sha(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def main(root, out):
    root, out = Path(root).resolve(), Path(out).resolve()
    corpus = root / "experiments/G-ROUTE4-candidate/corpus"
    bp_dir = root / "experiments/G-ROUTE4-candidate/blueprint"
    sys.path.insert(0, str(corpus))
    sys.path.insert(0, str(root / "tools"))
    import seal_layout as SL
    import adjudicator_config as AC
    import check_corpus as CC
    import name_stream as NS

    problems = []
    # ---- pinned digests of the frozen inputs (BLUEPRINT_FREEZE.json is the authority)
    freeze = json.loads((bp_dir / "BLUEPRINT_FREEZE.json").read_text(encoding="utf-8"))
    frozen_files = {}
    for rel, want in freeze["files"].items():
        got = lf_sha(root / rel)
        frozen_files[rel] = got
        if got != want:
            problems.append(f"frozen blueprint file digest mismatch: {rel}")
    design_sha = lf_sha(root / freeze["design"]["path"])
    obligations_sha = lf_sha(root / freeze["obligations"]["path"])
    if design_sha != freeze["design"]["sha256"]:
        problems.append("accepted design digest mismatch")
    if obligations_sha != freeze["obligations"]["sha256"]:
        problems.append("obligations digest mismatch")
    blueprint = json.loads((bp_dir / "BLUEPRINT.json").read_text(encoding="utf-8"))
    templates = {}
    for tc, pinned in freeze["templates"].items():
        t = blueprint["templates"][tc]
        got = {"assembled_template_sha256": text_sha(t["assembled_template"]),
               "rule_body_sha256": text_sha(t["rule_body"]),
               "disclosure_sentence_sha256": text_sha(t["disclosure_sentence"]) if t["disclosure_sentence"] else None}
        for key, value in got.items():
            if value != pinned[key]:
                problems.append(f"{tc} {key} mismatch")
        templates[tc] = dict(got, disclosure_status=pinned["disclosure_status"])
    absence_sha = text_sha(blueprint["templates"]["structured_extraction"]["absence_sentence"])
    if absence_sha != freeze["extraction_absence_sentence_sha256"]:
        problems.append("extraction absence sentence digest mismatch")
    sys.path.insert(0, str(bp_dir))
    import audit_sample as AS
    self_test = AS.self_test()["digest"]
    if self_test != freeze["audit_sample"]["self_test_digest"]:
        problems.append("audit-sample self-test digest mismatch")
    if CC.FROZEN_G3_INDEPENDENCE_SHA256 != lf_sha(root / "tools/g_route3_independence.py"):
        problems.append("frozen G-ROUTE3 independence checker digest mismatch")
    if CC.IDENT_GATE_PATTERN_SHA256 != text_sha(CC.IDENT_INTENDED.pattern):
        problems.append("O3 identifier gate pattern digest mismatch")

    # ---- the corpus, re-checked, and the name stream, replayed with no dictionary
    staged = [json.loads((corpus / "staging" / f"{c}.json").read_text(encoding="utf-8")) for c in CLASSES]
    check_problems, report = CC.check(staged)
    problems += [f"corpus: {p}" for p in check_problems]
    stream = NS.load_artifact(corpus / "name_stream.json")
    replay = NS.replay_without_dictionary(stream)

    # ---- O2: the prepared configuration, frozen with the operator's decisions (nothing else changes)
    prepared = AC.config()
    if prepared != json.loads((corpus / "staging/ADJUDICATOR_CONFIG.json").read_text(encoding="utf-8")):
        problems.append("prepared O2 configuration differs from its committed snapshot")
    frozen = {k: v for k, v in prepared.items() if k not in ("config_sha256", "operator_confirmation_required")}
    if prepared["adjudicator"]["model_id"] != "claude-opus-5-5" or \
            not prepared["adjudicator"]["channel"].startswith("Anthropic Messages API"):
        problems.append("prepared O2 model or channel differs from the operator decision")
    frozen["status"] = "FROZEN in the G-ROUTE4 seal commit; no adjudicator or model has been contacted"
    frozen["operator_decisions"] = [
        {"field": "adjudicator.model_id", "value": "claude-opus-5-5", "decided_by": "operator",
         "date": OPERATOR_DECISION_DATE},
        {"field": "adjudicator.channel", "value": "Anthropic Messages API", "decided_by": "operator",
         "date": OPERATOR_DECISION_DATE}]
    frozen["prepared_config_sha256"] = prepared["config_sha256"]
    frozen["config_sha256"] = hashlib.sha256(canonical(frozen).encode("utf-8")).hexdigest()

    # ---- the prepared layout
    layout = SL.build_layout(staged, frozen)
    blind = SL.verify_blind(layout)
    problems += [f"blind separation: {p}" for p in blind]
    facing = [f for name in SL.MODEL_FACING for f in layout[name]["fixtures"]]
    staged_fixtures = {f["fixture_id"]: f for d in staged for f in d["fixtures"]}
    if len(facing) != 584 or any(f != staged_fixtures[f["fixture_id"]] for f in facing):
        problems.append("model-facing fixtures differ from the staged fixtures or are not 584")
    toolchain = {p.name: lf_sha(p) for p in sorted(corpus.glob("*")) if p.is_file() and p.suffix in (".py", ".md", ".json")}
    layout["authoring_ledger.json"]["provenance"] = {
        "staging_branch": "g-route4/authoring-staging (authoring only; never merged)",
        "staging_commit": STAGING_COMMIT, "staging_tree": STAGING_TREE,
        "authoring_toolchain_sha256": toolchain,
        "staging_files_sha256": {f"staging/{c}.json": lf_sha(corpus / "staging" / f"{c}.json") for c in CLASSES},
        "check_report_sha256": lf_sha(corpus / "staging/CHECK_REPORT.json"),
        "digest_basis": "sha256 of file bytes with line endings normalized to LF (the git blob content)",
    }

    # ---- O3 gate specification
    gate = {
        "gate": "O3 identifier gate (G-ROUTE4, prospective, binding)",
        "decision_record": "O3_IDENTIFIER_DECISION.md",
        "pattern": CC.IDENT_INTENDED.pattern, "pattern_sha256": CC.IDENT_GATE_PATTERN_SHA256,
        "excluded": {"a single capital followed by one digit": r"[A-Z]\d",
                     "structural ids in structural fields": {"form": "[A-Z][0-9]+",
                                                             "fields": sorted(CC.STRUCTURAL_KEYS)}},
        "requires": ["0 identifiers shared between two G-ROUTE4 fixtures or with any G-ROUTE3 A or B fixture",
                     "every identifier found in a G-ROUTE4 fixture is declared in its design record"],
        "frozen_g3_checker": {"path": "tools/g_route3_independence.py",
                              "sha256": CC.FROZEN_G3_INDEPENDENCE_SHA256, "status": "byte-identical, unmodified"},
        "implementation": {"path_at_staging_commit": "experiments/G-ROUTE4-candidate/corpus/check_corpus.py",
                           "sha256": toolchain["check_corpus.py"],
                           "functions": ["structural_ids", "intended_identifiers"]},
        "result_at_seal": report["o3_identifier_gate"],
        "g_route3": "not rescored or reinterpreted",
    }

    files = {name: render(obj) for name, obj in layout.items() if name != "SEAL_MANIFEST.json"}
    files["o3_identifier_gate.json"] = render(gate)
    files["O3_IDENTIFIER_DECISION.md"] = (corpus / "O3_IDENTIFIER_DECISION.md").read_text(encoding="utf-8")
    files["SEAL_LAYOUT.md"] = (corpus / "SEAL_LAYOUT.md").read_text(encoding="utf-8")
    files["name_stream.json"] = (corpus / "name_stream.json").read_text(encoding="utf-8")
    files["SEAL_NOTES.md"] = SEAL_NOTES
    files["build_seal.py"] = Path(__file__).read_text(encoding="utf-8")

    manifest = {
        "schema_version": "g-route4.seal-manifest.v1", "layout_version": SL.LAYOUT_VERSION,
        "seal_parent": SEAL_PARENT, "seal_branch": SEAL_BRANCH,
        "source": {"staging_commit": STAGING_COMMIT, "staging_tree": STAGING_TREE},
        "counts": {"fixtures": len(facing), "main_A": len(layout["corpus_a.json"]["fixtures"]),
                   "main_B": len(layout["corpus_b.json"]["fixtures"]),
                   "reserve_A": len(layout["reserve_corpus_a.json"]["fixtures"]),
                   "reserve_B": len(layout["reserve_corpus_b.json"]["fixtures"])},
        "files": {name: {"file_sha256": text_sha(text),
                         **({"canonical_sha256": text_sha(canonical(layout[name])),
                             "count": len(layout[name].get("fixtures", layout[name].get("items", [])))}
                            if name in layout else {})}
                  for name, text in sorted(files.items())},
        "roles": {"model_facing": list(SL.MODEL_FACING), "gold_and_rationales": list(SL.GOLD_FILES),
                  "reserves": ["reserve_corpus_a.json", "reserve_corpus_b.json", "reserve_gold_a.json",
                               "reserve_gold_b.json"],
                  "ledger": "authoring_ledger.json", "o2": "adjudicator_config.json",
                  "o3": ["O3_IDENTIFIER_DECISION.md", "o3_identifier_gate.json"], "names": "name_stream.json"},
        "blind_separation": {"verified": not blind, "model_facing_keys": list(SL.FIXTURE_KEYS),
                             "gold_only_keys_absent": sorted(SL.GOLD_ONLY_KEYS),
                             "ledger_only_keys_absent": sorted(SL.LEDGER_ONLY_KEYS)},
        "frozen_inputs": {
            "blueprint_freeze_manifest": {"path": "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT_FREEZE.json",
                                          "sha256": lf_sha(bp_dir / "BLUEPRINT_FREEZE.json")},
            "blueprint_files": frozen_files,
            "design": {"path": freeze["design"]["path"], "sha256": design_sha, "accepted": freeze["design"]["accepted"]},
            "obligations": {"path": freeze["obligations"]["path"], "sha256": obligations_sha},
            "templates_and_approved_sentences": templates,
            "extraction_absence_sentence_sha256": absence_sha,
            "audit_sample": {"procedure": freeze["audit_sample"]["procedure"],
                             "procedure_sha256": frozen_files[freeze["audit_sample"]["procedure"]],
                             "self_test_digest": self_test, "total": freeze["audit_sample"]["total"]},
        },
        "validators_and_rendering_sha256": {rel: lf_sha(root / rel) for rel in VALIDATORS},
        "digests": {
            "o2_frozen_config_sha256": frozen["config_sha256"],
            "o2_prepared_config_sha256": prepared["config_sha256"],
            "o3_gate_pattern_sha256": CC.IDENT_GATE_PATTERN_SHA256,
            "o3_gate_spec_canonical_sha256": text_sha(canonical(gate)),
            "name_stream_names_sha256": stream["stream_sha256"],
            "name_stream_file_sha256": text_sha(files["name_stream.json"]),
        },
        "validation_at_seal": {
            "checker_problems": len(check_problems),
            "trigram_max_jaccard": {tc: v["max_jaccard"] for tc, v in report["trigram"].items()},
            "task_relevant_max_jaccard": {tc: v["max_jaccard"] for tc, v in report["trigram_task_relevant"].items()},
            "o3_shared_entities": report["o3_entities"]["shared"], "o3_shared_identifiers":
                report["o3_identifier_gate"]["shared"], "o6_collisions": report["o6"]["collisions"],
            "n1_duplicates": report["n1_duplicates"], "fine_signature_clashes": report["fine_signature_clashes"],
            "canonical_signature_clashes": report["canonical_signature_clashes"],
            "reply_length": report["reply_length"], "name_stream_replay": replay,
        },
        "excluded": "no runtime outputs, model responses, adjudication results, audit sample or other post-seal "
                    "derived artifacts",
        "digest_basis": "file_sha256 is over the exact committed bytes (LF); canonical_sha256 is over compact "
                        "sorted-key JSON; input digests are over LF-normalized file bytes (the git blob content)",
    }
    files["SEAL_MANIFEST.json"] = render(manifest)
    if problems:
        print("SEAL BUILD REFUSED:")
        for p in problems:
            print("  ", p)
        raise SystemExit(1)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"files": len(files), "manifest_file_sha256": text_sha(files["SEAL_MANIFEST.json"]),
                      "o2_frozen": frozen["config_sha256"], "counts": manifest["counts"]}, indent=1))


SEAL_NOTES = """# G-ROUTE4 seal notes

**What this is.** The single G-ROUTE4 seal commit (obligation O1): the complete authored corpus of 584 fixtures
(A′ 80 and B′ 305 main, 80 A′ and 119 B′ reserve), gold and rationales, the authoring and provenance ledger, the
frozen O2 adjudicator configuration, the O3 identifier decision and gate, the committed name stream, and a manifest
of every pinned digest. It is built by `build_seal.py` from staging checkpoint
`dd8193bfcf1db05c752635dc4f8911a58098c97b` with the prepared, tested seal layout. It contains no runtime outputs,
model responses or adjudication results. No model or adjudicator was contacted before or during the seal.

**Parent and placement.** The seal's parent is the frozen blueprint commit
`1156d0645b1b113b91c65e4a485b7f75ffa10061`. By operator instruction (2026-09-29) the seal is pushed to the branch
`g-route4/seal` and `main` is not moved. The frozen `seal_requirement` ("the single commit on main whose parent is
the commit adding this manifest") is met when `main` is fast-forwarded to this commit or its descendants; a
fast-forward does not change the seal id, and no other commit may be placed on `main` with that parent.
Disclosed: the authoring branch `g-route4/authoring-staging` begins with commit
`8d890b2fff9de7616e98cab71665025909647d21`, whose parent is also `1156d06`; it is authoring-only and never merged.

**Only one seal.** This seal commit id is recorded when it is pushed; any later re-seal is refused. If one ever
happens, both samples are disclosed and their union is audited.

**O1 audit sample (runbook).** Computed only after this commit is pushed to `origin`, by the frozen procedure
`experiments/G-ROUTE4-candidate/blueprint/audit_sample.py` (sha256
`8e5afc8478c913150fd9d4ac9564a829ae857e74d005ca4371d2b76937767524`, self-test
`75af7d1ad5d785b40c1a41f15e4d23fa7e987715530e8d9b64f4fec5a4b398c9`) with this commit's id, over the frozen
blueprint's B′ main cells: 38 fixtures. It is committed as a separate commit after the seal and before the first
adjudication session, with the local reflog around the seal disclosed.

**Carried note N4 (checked at SEAL), clarified.** For sampled fixtures that the first adjudicator agrees with, the
two further blind adjudicators always run, and the operator is involved only on disagreement. Any disagreement within
a sampled cell is also reported.

**After the seal.** Gold changes only through a recorded fix, with re-adjudication from scratch (design, gold
adjudication steps 3 and 7). The O2 configuration changes only by a recorded operator decision, after which every
fixture is re-adjudicated from scratch.
"""

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
