"""Build A_MAIN_CLOSURE.json: the A′ counterpart of B_MAIN_CLOSURE.json, plus the design step-13 records for all cells.

Reads only committed records: the A′ batch run and its fix-round run (journals re-verified by hash chain), the operator
decisions, the fix records, the audit sample, B_MAIN_CLOSURE.json, and the latent-defect reports. Nothing is
re-scored and no verdict is changed.

    python -B build_a_closure.py        # writes experiments/G-ROUTE4-candidate/adjudication/A_MAIN_CLOSURE.json
"""

import collections
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
sys.path.insert(0, str(ADJ))
import g4_adjudicate as H  # noqa: E402

RUN, FIX_RUN = "g4adj-amain-20260929T180225Z", "g4adj-amain-fix1-20260929T185315Z"
B_RUN, B_FIX_RUN = "g4adj-bmain-20260929T155837Z", "g4adj-bmain-fix1-20260929T171651Z"
A, F = ADJ / "runs" / RUN, ADJ / "runs" / FIX_RUN
FD, FDB = ADJ / "fixes" / "round1_amain", ADJ / "fixes" / "round1_bmain"
OUT = ADJ / "A_MAIN_CLOSURE.json"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def commit_of(path):
    return subprocess.run(["git", "log", "-1", "--format=%H", "--", str(path)], cwd=H.ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def record(path):
    return {"path": str(Path(path).relative_to(ADJ)).replace("\\", "/"), "commit": commit_of(path),
            "lf_sha256": H.lf_sha256(path)}


def journal(p):
    H.Journal(p / "journal.jsonl")                                   # re-verifies the hash chain
    recs = [json.loads(line) for line in (p / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    res = [r for r in recs if r["type"] == "result"]
    intents = collections.Counter((r["fixture_id"], r["slot"]) for r in recs if r["type"] == "intent")
    finals = collections.Counter((r["fixture_id"], r["slot"]) for r in res if r["kind"] == "final_message")
    reclass = [r for r in recs if r["type"] == "operator_reclassification"]
    repeated = sorted(f"{fid} slot {s}" for (fid, s), n in intents.items() if n > 1)
    return {"slots": len(intents), "invocations": sum(intents.values()),
            "one_binding_final_message_per_slot": all(finals[k] == 1 for k in intents) and len(finals) == len(intents),
            "slots_with_a_second_invocation": repeated,
            "second_invocations_justified_by_reclassified_no_answer": sorted(
                f"{r['fixture_id']} slot {r['slot']}" for r in reclass if r["to"] == "no_answer") == repeated,
            "final_messages": sum(r["kind"] == "final_message" for r in res),
            "results_by_kind": dict(collections.Counter(r["kind"] for r in res)),
            "refusal_stop_reasons": sorted(f"{r['fixture_id']} slot {r['slot']}" for r in res if r.get("stop_reason") == "refusal"),
            "in_doubt": sum(r["type"] == "in_doubt" for r in recs), "stops": sum(r["type"] == "stop" for r in recs),
            "operator_resolutions": sum(r["type"] == "operator_resolution" for r in recs),
            "operator_reclassifications": len(reclass),
            "preflights": sum(r["type"] == "preflight" for r in recs),
            "input_tokens": sum((r.get("usage") or {}).get("input_tokens", 0) for r in res),
            "output_tokens": sum((r.get("usage") or {}).get("output_tokens", 0) for r in res),
            "models": sorted({r.get("model") for r in res if r.get("model")}),
            "config_digests": sorted({r["config_sha256"] for r in recs if "config_sha256" in r}),
            "journal_lf_sha256": H.lf_sha256(p / "journal.jsonl")}


def cell(fid):
    return fid.rsplit("-", 1)[0]


def main():
    dec_a, dec_f = load(A / "decisions.json"), load(F / "decisions.json")
    op_a, op_f = load(A / "OPERATOR_DECISIONS.json"), load(F / "OPERATOR_DECISIONS.json")
    scores_a, scores_f = load(A / "scores_phase1.json")["slots"], load(F / "scores_phase1.json")["slots"]
    boundary, fix_report = load(A / "A_MAIN_BOUNDARY_REPORT.json"), load(F / "FIX_ROUND_REPORT.json")
    fixed = sorted(r["fixture_id"] for r in load(FD / "FIX_RECORD.json")["fixes"])
    a_ids = sorted(H.model_facing_a())
    sample = set(H.audit_sample())

    kept_direct = sorted(f for f, v in dec_a.items() if v["decision"] == "keep")
    kept_op = sorted(d["fixture_id"] for d in op_a["decisions"] if d["outcome"].startswith("gold right"))
    to_fix = sorted(d["fixture_id"] for d in op_a["decisions"] if d["outcome"].startswith("input ambiguous"))
    fixed_kept_readj = sorted(f for f, v in dec_f.items() if v["decision"] == "keep")
    fixed_kept_op = sorted(d["fixture_id"] for d in op_f["decisions"] if d["outcome"].startswith("gold right"))
    assert sorted(dec_a) == a_ids and len(a_ids) == 80
    assert to_fix == fixed and sorted(dec_f) == fixed
    assert len(kept_direct) + len(kept_op) + len(fixed) == 80
    assert sorted(fixed_kept_readj + fixed_kept_op) == fixed
    assert not set(kept_direct) & (set(kept_op) | set(fixed)) and not set(kept_op) & set(fixed)
    assert not sample & set(a_ids), "the audit sample is B′ only"
    for f in fixed_kept_op:                                          # recorded verdicts are carried unchanged
        d = next(x for x in op_f["decisions"] if x["fixture_id"] == f)
        assert d["verdicts"] == [dec_f[f]["a1"], dec_f[f]["a2"], dec_f[f]["a3"]]

    ja, jf = journal(A), journal(F)

    # disagreement causes, as recorded: the batch's per-slot causes (A_MAIN_BOUNDARY_REPORT) and the fix round's
    causes_a = collections.Counter(c for slots in boundary["escalations"]["per_slot_causes"].values() for c in slots.values())
    assert sum(causes_a.values()) == sum(r["agree"] is False for r in scores_a) == 52
    causes_f = collections.Counter("fence" if r["operational_reasons"] == ["malformed_json"] else "other"
                                   for r in scores_f if r["agree"] is False)
    assert causes_f == {"fence": 8}

    disputed = {r["fixture_id"] for r in scores_a if r["agree"] is False}
    untouched = sorted(f for f in a_ids if f not in disputed and f not in fixed)
    disputed_unchanged = sorted(f for f in a_ids if f in disputed and f not in fixed)
    per_cell = collections.defaultdict(lambda: {"fixtures": 0, "kept_directly": 0, "kept_by_operator": 0, "fixed": 0,
                                                "replaced": 0, "slots": 0, "disagreeing_slots": 0,
                                                "fix_round_slots": 0, "fix_round_disagreeing_slots": 0})
    for f in a_ids:
        c = per_cell[cell(f)]
        c["fixtures"] += 1
        c["kept_directly"] += f in kept_direct
        c["kept_by_operator"] += f in kept_op
        c["fixed"] += f in fixed
    for r in scores_a:
        per_cell[cell(r["fixture_id"])]["slots"] += 1
        per_cell[cell(r["fixture_id"])]["disagreeing_slots"] += r["agree"] is False
    for r in scores_f:
        per_cell[cell(r["fixture_id"])]["fix_round_slots"] += 1
        per_cell[cell(r["fixture_id"])]["fix_round_disagreeing_slots"] += r["agree"] is False
    per_cell_a = {k: dict(v, disagreement_rate=round(v["disagreeing_slots"] / v["slots"], 3))
                  for k, v in sorted(per_cell.items())}

    b_closure_path = ADJ / "B_MAIN_CLOSURE.json"
    b_closure = load(b_closure_path)
    final_a, final_ga = H.model_facing_a(FD), H.gold_path_overlay(FD, gold_file="gold_a.json")
    final_b, final_gb = H.model_facing_b(FDB), H.gold_path_overlay(FDB)
    b_fixed = sorted(r["fixture_id"] for r in load(FDB / "FIX_RECORD.json")["fixes"])
    assert b_closure["final_b_main_corpus"]["model_facing_sha256"] == H.sha256(H.canonical(sorted(final_b.values(), key=lambda x: x["fixture_id"])))

    def digest(items):
        return H.sha256(H.canonical(sorted(items.values(), key=lambda x: x["fixture_id"])))

    sealed_reserve_a = load(H.SEALED / "reserve_corpus_a.json")["fixtures"]
    sealed_reserve_b = load(H.SEALED / "reserve_corpus_b.json")["fixtures"]
    runs_dir = ADJ / "runs"
    contacted = set()
    for run in runs_dir.iterdir():
        if run.is_dir():
            contacted |= {json.loads(line)["fixture_id"] for line in (run / "journal.jsonl").read_text(encoding="utf-8").splitlines()
                          if json.loads(line)["type"] == "intent"}
    reserve_ids = {f["fixture_id"] for f in sealed_reserve_a + sealed_reserve_b}
    assert not contacted & reserve_ids, "a reserve fixture was sent to an adjudicator"

    closure = {
        "schema_version": "g-route4.a-main-closure.v1", "status": "CLOSED", "closed_on": "2026-09-29", "batch": "A′ main",
        "seal_commit": "50e6b46994299ffd71c97aa3f81f30637efaba1c",
        "audit_sample_commit": "29f5a477693d703699af62f9fc0e0945c9c66be2",
        "o2": b_closure["o2"],
        "runs": {RUN: ja, FIX_RUN: jf},
        "totals": {"a_main_fixtures": 80,
                   "kept_directly_by_the_frozen_rule_all_three_agree": len(kept_direct),
                   "kept_unchanged_by_operator_decision_gold_right": len(kept_op),
                   "fixed_then_kept": len(fixed),
                   "fixed_then_kept_by_re_adjudication_all_three_agree": len(fixed_kept_readj),
                   "fixed_then_kept_by_operator_decision_gold_right": len(fixed_kept_op),
                   "replaced": 0, "unresolved": 0,
                   "automatic_keep": len(kept_direct) + len(fixed_kept_readj),
                   "operator_keep": len(kept_op) + len(fixed_kept_op),
                   "final_kept": len(kept_direct) + len(kept_op) + len(fixed)},
        "provider": {"messages_api_invocations": ja["invocations"] + jf["invocations"],
                     "slots": ja["slots"] + jf["slots"],
                     "provider_rejections": ja["results_by_kind"].get("request_rejected", 0) + jf["results_by_kind"].get("request_rejected", 0),
                     "rejection_handling": boundary["contact"]["rejection"],
                     "refusal_stop_reasons_bound_as_answers": ja["refusal_stop_reasons"] + jf["refusal_stop_reasons"],
                     "in_doubt": ja["in_doubt"] + jf["in_doubt"],
                     "tokens": {"input": ja["input_tokens"] + jf["input_tokens"], "output": ja["output_tokens"] + jf["output_tokens"]}},
        "disagreements": {"batch": {"slots": len(scores_a), "disagreeing": sum(r["agree"] is False for r in scores_a),
                                    "by_recorded_cause": dict(sorted(causes_a.items()))},
                          "fix_round": {"slots": len(scores_f), "disagreeing": sum(r["agree"] is False for r in scores_f),
                                        "by_recorded_cause": {"fence (malformed_json)": causes_f["fence"]}},
                          "verdicts": "recorded verdicts are unchanged; every malformed-JSON answer remains a disagreement"},
        "decisions": {"batch_keep": kept_direct, "batch_operator_gold_right_keep": kept_op,
                      "batch_operator_input_ambiguous_fix": to_fix,
                      "fix_round_keep_all_three_agree": fixed_kept_readj,
                      "fix_round_operator_gold_right_keep": fixed_kept_op},
        "audit_sample": {"a_prime_fixtures_sampled": 0,
                         "note": "the O1 audit sample is drawn from B′ cells only (38 fixtures); every A′ fixture had the "
                                 "full three-adjudicator treatment, so step 11 does not apply to A′",
                         "b_prime_outcome": b_closure["audit_sample"]},
        "reserve_usage": {"a_prime_reserve_fixtures": len(sealed_reserve_a), "b_prime_reserve_fixtures": len(sealed_reserve_b),
                          "drawn": 0, "adjudicated": 0,
                          "note": "no fixture was replaced, so no reserve was drawn; no reserve fixture appears in any "
                                  "adjudication journal (checked)"},
        "flagged": {"fixed": fixed, "replaced": []},
        "descriptive_subsets_step_12_never_gating": {
            "untouched": {"count": len(untouched), "fixtures": untouched},
            "disputed_but_kept_unchanged": {"count": len(disputed_unchanged), "fixtures": disputed_unchanged}},
        "per_cell": per_cell_a,
        "step_13_records_all_cells": {
            "note": "design step 13: per-cell fix and replacement counts, disagreement rates and audit-sample "
                    "outcomes; A′ from this record, B′ from B_MAIN_CLOSURE.json (bound by digest below)",
            "a_prime": {k: {x: v[x] for x in ("fixtures", "fixed", "replaced", "slots", "disagreeing_slots", "disagreement_rate")}
                        for k, v in per_cell_a.items()},
            "b_prime": b_closure["per_cell"],
            "b_prime_audit_sample": b_closure["audit_sample"],
            "b_main_closure_lf_sha256": H.lf_sha256(b_closure_path)},
        "final_corpus": {
            "definition": "the sealed corpus with the 20 recorded round-1 fixes overlaid (6 A′ in fixes/round1_amain, 14 B′ "
                          "in fixes/round1_bmain); no replacement; reserves unchanged and unused; the seal is not modified",
            "a_main": {"fixtures": sorted(final_a), "fixed": fixed, "model_facing_sha256": digest(final_a),
                       "gold_sha256": digest(final_ga), "fix_record_lf_sha256": H.lf_sha256(FD / "FIX_RECORD.json")},
            "b_main": {"fixtures": sorted(final_b), "fixed": b_fixed, "model_facing_sha256": digest(final_b),
                       "gold_sha256": digest(final_gb), "fix_record_lf_sha256": H.lf_sha256(FDB / "FIX_RECORD.json")},
            "reserve_a_sha256_sealed_unchanged": digest({f["fixture_id"]: f for f in sealed_reserve_a}),
            "reserve_b_sha256_sealed_unchanged": digest({f["fixture_id"]: f for f in sealed_reserve_b})},
        "sealed_records": {
            RUN: {k: record(A / f"{k}.json") for k in ("answers_phase1", "scores_phase1", "decisions", "A_MAIN_BOUNDARY_REPORT", "OPERATOR_DECISIONS")},
            FIX_RUN: {k: record(F / f"{k}.json") for k in ("answers_phase1", "scores_phase1", "decisions", "FIX_ROUND_REPORT", "OPERATOR_DECISIONS")},
            "fixes": {k: record(FD / f"{k}.json") for k in ("FIX_RECORD", "FIX_CHECK_REPORT", "corpus_fixed", "gold_fixed", "ledger_fixed")},
            "B_MAIN_CLOSURE": record(b_closure_path)},
        "latent_defects": {
            "reports": ["fixes/LATENT_DEFECTS.md", "fixes/round1_amain/LATENT_DEFECTS_ADDENDUM.md"],
            "fixed_in_a_prime_round_1": ["A4-RSRCH-R2-02", "A4-RSRCH-R4-03", "A4-SYNTH-R2-03", "A4-SYNTH-R4-01",
                                         "A4-RSRCH-R2-01 (weak weekend paraphrase, newly identified)"],
            "in_the_final_main_corpus_unfixed": {
                "A4-SYNTH-R1-01": "SY1 cause under role 'diagnosis'; kept by operator decision (all three answers reached "
                                  "the gold conclusion; the only disagreement was a code fence)",
                "B4-SYNTH-R1-02": "SY1 cause under role 'diagnosis'; kept (first adjudicator agreed)",
                "B4-SYNTH-R2-15": "SY1 cause under role 'diagnosis'; kept (first adjudicator agreed)",
                "B4-SYNTH-R3-08": "SY1 cause under role 'diagnosis'; kept (first adjudicator agreed)"},
            "in_unused_reserves_unfixed": {
                "P6 'only'": ["A4-RSRCH-R2-X02", "A4-RSRCH-R4-X03", "B4-RSRCH-R1-X06", "B4-RSRCH-R1-X14", "B4-RSRCH-R2-X06",
                              "B4-RSRCH-R2-X14", "B4-RSRCH-R3-X06", "B4-RSRCH-R3-X14"],
                "SY1 diagnosis role": ["A4-SYNTH-R1-X01", "A4-SYNTH-R2-X03", "A4-SYNTH-R4-X01", "B4-SYNTH-R1-X01", "B4-SYNTH-R3-X03"],
                "weak anonymity paraphrase": ["B4-RSRCH-R3-X03"],
                "weak weekend (courier) paraphrase": ["B4-RSRCH-R2-X04"]},
            "what_the_protocol_permits": "kept main fixtures change only through the external corpus review (step 10: a "
                                         "fix counted as the fixture's one fix, or a replacement, with re-adjudication); "
                                         "reserves are used only when drawn as replacements"},
        "residual_limitations": [
            "Code-fence behavior: the adjudicator often wraps valid JSON in a ```json fence, which the frozen validator "
            f"rejects as malformed_json. A′ batch: of 52 disagreeing slots, {causes_a['fence']} were fenced only, "
            f"{causes_a['fence+content']} fenced with a content difference, {causes_a['malformed (not a fence)']} malformed "
            f"(refusals) and {sum(v for k, v in causes_a.items() if k.startswith('content'))} content-only; fix round: all "
            f"{causes_f['fence']} fenced only. The format-only escalations were resolved only by operator "
            "'gold right -> keep' decisions.",
            "A4-PLAN-R3-04: all three adjudicator answers ended with stop_reason 'refusal' and bound as disagreements "
            "(malformed, not a fence); the operator kept the fixture unchanged ('gold right -> keep').",
            "A4-PLAN-R1-03 slot 3: the provider rejected invocation 1 (HTTP 400, credit balance exhausted); by operator "
            "decision (option b) it was reclassified as a no-answer and its single frozen retry bound.",
            "Operator decisions (25 'gold right -> keep') were made by a non-blind operator, as the design declares, on "
            "diagnostic content comparisons of fenced answers.",
            "The SY1 fixes relabelled roles; gold roles follow the input roles (conclusions and required terms unchanged). "
            "The extraction fix renamed one schema key; the gold value is unchanged.",
            "Adjudication used the O2 amendment (thinking omitted, temperature omitted, effort high, 32000 output tokens); "
            "the sealed configuration is preserved unchanged.",
        ],
        "unchanged": "sealed corpus, gold, rationales, ledger, reserves, audit sample, blueprint, validators and thresholds",
        "not_started": ["external corpus review", "implementation", "execution freeze", "Phase A′", "Phase B′",
                        "qualification-table construction"],
    }
    assert closure["totals"]["automatic_keep"] + closure["totals"]["operator_keep"] == 80
    OUT.write_text(json.dumps(closure, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: closure[k] for k in ("totals", "provider", "disagreements")}, indent=1, ensure_ascii=False))
    print("subsets: untouched", len(untouched), "| disputed kept unchanged", len(disputed_unchanged))
    for run, j in closure["runs"].items():
        print(run, {k: j[k] for k in ("slots", "invocations", "one_binding_final_message_per_slot",
                                      "second_invocations_justified_by_reclassified_no_answer", "in_doubt", "models", "config_digests")})
    print("final corpus:", closure["final_corpus"]["a_main"]["model_facing_sha256"][:16], closure["final_corpus"]["b_main"]["model_facing_sha256"][:16])


if __name__ == "__main__":
    main()
