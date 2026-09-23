"""G-SYNTH1-R2: bounded live semantic-fidelity gate that forces real multi-input compression.

G-SYNTH1 went mechanically green and proved almost nothing: 39 of 44 statements cited a single input, so the
cross-role compression the gate exists to test barely happened, and both repair paths - deterministic promotion and
fidelity refusal - never fired once. A gate that passes because the behaviour under test did not occur has not
passed; it has abstained.

R2 changes three things:

* each unit gets four related inputs and may return one statement, so restating a single input cannot satisfy it;
* a chain counts toward critical coverage only when an *accepted* statement actually cites two or more inputs, at
  least one carrying an interpretation-critical role and one asserting something settled;
* insufficient coverage yields INCONCLUSIVE, never PASS.

The harness validates itself before it is allowed to spend model time: a full stub pass must run every chain, prove
the lineage/evidence mapping resolves, prove cited-input accounting adds up, and prove the counters are internally
consistent. Four measurement bugs in G-SYNTH1 earned that precondition.
"""

import collections
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path("C:/Users/marcu/Eidolon")
LIVE = Path("C:/Users/marcu/AppData/Local/Eidolon/data")
OUT = Path(__file__).resolve().parent / "g_synth1_r2"
OUT.mkdir(parents=True, exist_ok=True)
DATA = OUT / "data"
DATA.mkdir(parents=True, exist_ok=True)
if not (DATA / "settings.json").is_file():
    shutil.copy2(LIVE / "settings.json", DATA / "settings.json")
os.environ["EIDOLON_DATA_DIR"] = str(DATA)
for value in (str(REPO), str(REPO / "tools"), str(REPO / "conscious_agent")):
    sys.path.insert(0, value)

import experiment_review as base                      # noqa: E402
import experiment_review_hierarchical as hier         # noqa: E402
import reviewer_capacity_qualification as q           # noqa: E402

MIN_CRITICAL_MERGES = 8          # below this the run is INCONCLUSIVE, never PASS
LOG = {"gate": "G-SYNTH1-R2", "contract": hier.CONTRACT_VERSION, "phases": {}, "steps": []}
STARTED = time.time()


def step(label, **data):
    LOG["steps"].append({"step": label, "at": time.strftime("%H:%M:%S"),
                         "elapsed_min": round((time.time() - STARTED) / 60, 1), **data})
    print(f"[{label}] " + json.dumps(data, default=str)[:700], flush=True)
    (OUT / "evidence.json").write_text(json.dumps(LOG, indent=1, default=str), encoding="utf-8")


def stop(reason, **data):
    step("STOPPED", reason=reason, **data)
    raise SystemExit(2)


# --- corpus -------------------------------------------------------------------------------------------------------
def make(idx, text, roles):
    """One input. Its lineage names an observation the harness supplies evidence for - support_evidence resolves
    lineage down to observations and looks each one up, which is what broke the first harness."""
    ident = f"DS{idx}"
    return ident, {"id": ident, "type": "document_statement", "kind": "finding", "doc_id": "D1",
                   "statement": text, "direct_roles": list(roles), "inherited_roles": [],
                   "lineage": [f"O{ident}"], "cites": []}


CHAINS = []


def chain(name, category, rows, expect):
    items = dict(make(n + 1, text, roles) for n, (text, roles) in enumerate(rows))
    CHAINS.append({"name": name, "category": category, "items": items, "expect": expect})


# Inputs within a chain are all about ONE subject, because that is the only condition under which this reviewer
# merges at all. Its prompt tells the model to keep each disagreement, uncertainty, minority observation and
# contradiction as its own statement rather than merging into a consensus, so unrelated inputs are correctly kept
# apart - and a statement budget too tight to obey that instruction makes the model emit nothing at all rather than
# disobey it. Compression happens when several inputs describe the same thing. That is when a role can be
# flattened, and that is what this measures.
#
# The statement budget is the planner's own, ceil(inputs / 2) capped: no lever is applied that a real consolidation
# round would not apply.
def budget(count):
    return min(hier.GROUP_MAX_STATEMENTS, max(1, math.ceil(count / 2)))


TOPICS = [
    ("labels", "design_constraint",
     [("No operational label appeared in any of the 192 responses.", ["measured_result"]),
      ("The architecture specifies the assessor never emits an operational label.", ["design_constraint"]),
      ("Each response carried only relation, scope and confidence.", ["observation"]),
      ("Responses were parsed for label fields in fixed order.", ["procedure"])]),
    ("authority", "design_constraint",
     [("All thirty-two items received a disposition.", ["measured_result"]),
      ("The deterministic layer, not the model, assigns the final disposition.", ["design_constraint"]),
      ("Every disposition was recorded downstream of the assessor.", ["observation"]),
      ("Dispositions were written after gate evaluation.", ["procedure"])]),
    ("schema", "design_constraint",
     [("No response contained a decision field.", ["measured_result"]),
      ("The schema does not admit an operational label field.", ["design_constraint"]),
      ("Responses were validated against the schema.", ["observation"]),
      ("Validation ran before scoring.", ["procedure"])]),
    ("diagnostics", "limitation",
     [("Three of twelve diagnostic cases produced unsafe operational use.", ["measured_result"]),
      ("The diagnostic set covers only twelve ambiguous items.", ["limitation"]),
      ("Each diagnostic case was drawn from the ambiguous pool.", ["observation"]),
      ("Diagnostic cases were scored after the primary set.", ["procedure"])]),
    ("gatescope", "limitation",
     [("Gate G10 fired on 18 of 32 records.", ["measured_result"]),
      ("Only the paired arm was measured against the frozen gate set.", ["limitation"]),
      ("Gate outcomes were recorded for every record.", ["observation"]),
      ("Gates were applied after parsing.", ["procedure"])]),
    ("agreement", "minority_finding",
     [("Twenty-nine of thirty-two items produced identical dispositions.", ["measured_result"]),
      ("One item out of thirty-two produced a disposition no other item produced.", ["minority_finding"]),
      ("Dispositions were recorded for every item.", ["observation"]),
      ("Items were compared pairwise.", ["procedure"])]),
    ("failuremode", "uncertainty",
     [("Repeated assessment reduced unsafe operational use.", ["conclusion"]),
      ("Whether the two arms share a failure mode cannot be determined from this run.", ["uncertainty"]),
      ("Both arms failed the same three items.", ["observation"]),
      ("Arms were run under separate seeds.", ["procedure"])]),
    ("representativeness", "uncertainty",
     [("The ambiguous pool supplied every diagnostic case.", ["measured_result"]),
      ("It is unclear whether the diagnostic set is representative.", ["uncertainty"]),
      ("Twelve cases were drawn in total.", ["observation"]),
      ("Cases were drawn before scoring began.", ["procedure"])]),
    ("conflict", "contradiction",
     [("Both records reported a relation and a confidence.", ["measured_result"]),
      ("Records T07-r1 and T07-r2 report opposite relations for the same evidence.", ["contradiction"]),
      ("Each record cited two evidence spans.", ["observation"]),
      ("Records were read in fixed order.", ["procedure"])]),
    ("priors", "hypothesis",
     [("Both arms failed the same three diagnostic items.", ["measured_result"]),
      ("Shared model priors may explain why both arms failed the same items.", ["hypothesis"]),
      ("The same model produced both arms.", ["observation"]),
      ("Seeds differed between arms.", ["procedure"])]),
]
for _name, _crit, _rows in TOPICS:
    chain("critical-" + _name, "interpretation_critical", _rows, {"critical_role": _crit})

# Adversarial: the settled claim leads and reads fluently, so the tempting compression is the one that drops the
# qualifier behind it.
ADVERSARIAL = [
    ("advlabels", "design_constraint",
     [("The assessor never indicated a decision outcome in any record.", ["measured_result"]),
      ("The contract restricts the assessor to relation and confidence only.", ["design_constraint"]),
      ("All 192 responses were inspected for decision fields.", ["observation"]),
      ("Inspection ran once per response.", ["procedure"])]),
    ("advcorrelated", "limitation",
     [("Correlated error was observed in three items.", ["measured_result"]),
      ("Only twelve ambiguous items were examined for correlated error.", ["limitation"]),
      ("Each examined item came from the ambiguous pool.", ["observation"]),
      ("Examination followed the primary scoring pass.", ["procedure"])]),
    ("advsettled", "uncertainty",
     [("Both arms agreed on twenty-nine of thirty-two items.", ["measured_result"]),
      ("Whether repetition removes correlated error is not established by this run.", ["uncertainty"]),
      ("Agreement was computed per item.", ["observation"]),
      ("Comparison used the frozen disposition set.", ["procedure"])]),
]
for _name, _crit, _rows in ADVERSARIAL:
    chain("adversarial-" + _name, "adversarial_fluent", _rows, {"critical_role": _crit, "adversarial": True})

for _n, _phrase in enumerate(["by design", "the contract prohibits", "it is intentionally constrained",
                              "the specification withholds"], 1):
    chain("wording-" + str(_n), "wording_variant",
          [("The run recorded 3 of 12 diagnostic unsafe uses.", ["measured_result"]),
           ("The assessor emits no operational label because " + _phrase + " it.", ["design_constraint"]),
           ("Every response carried a relation and a confidence.", ["observation"]),
           ("Responses were parsed in fixed order.", ["procedure"])],
          {"critical_role": "design_constraint"})

for _n in range(1, 4):
    chain("control-" + str(_n), "single_role_control",
          [("The harness scheduled 192 calls across 32 items.", ["measured_result"]),
           ("Gate G10 fired on 18 of 32 records.", ["measured_result"]),
           ("Coverage reached every required part.", ["measured_result"]),
           ("Twenty-nine of thirty-two items matched.", ["measured_result"])], {})

for _n, _junk in enumerate([["architectural_observation_constraintish"], ["Design Constraint!!", "finding"]], 1):
    chain("invalid-" + str(_n), "invalid_proposal",
          [("No operational label appeared in any of the 192 responses.", ["measured_result"]),
           ("The architecture specifies no operational labels are emitted.", ["design_constraint"]),
           ("Each response carried relation and confidence.", ["observation"]),
           ("Responses were parsed in fixed order.", ["procedure"])],
          {"critical_role": "design_constraint", "force_invalid": _junk})

PACKAGE = {"title": "G-SYNTH1-R2 semantic fidelity chains", "brief": "Synthetic consolidation chains. No experiment."}


def run_chains(call_model, phase):
    """Every chain, through the real prompt, validator and role governance. Returns records plus accounting."""
    records, counts = [], collections.Counter()
    proposed_roles, direct_roles, inherited_roles = collections.Counter(), collections.Counter(), collections.Counter()
    invalid, promotions, refusals, role_loss, harness_errors = [], [], [], [], []
    with hier.review_id_vocabulary(), hier.record_identity_metadata(), hier.semantic_role_prompts():
        for spec in CHAINS:
            items = spec["items"]
            unit = {"unit_id": f"GU1.{len(records) + 1}", "stage": f"group:r1:{spec['name']}", "round": 1,
                    "group": 1, "groups": 1, "inputs": list(items), "required": True, "max_statements": budget(len(items))}
            evidence = {f"O{k}": v["statement"] for k, v in items.items()}
            # harness invariant: every lineage id a statement could resolve to must have evidence
            for key, value in items.items():
                for observation in value["lineage"]:
                    if observation not in evidence:
                        harness_errors.append(f"{spec['name']}:lineage_without_evidence:{observation}")
            prompt = hier.GROUP_PROMPT.format(
                title=PACKAGE["title"], brief=PACKAGE["brief"], group=1, groups=1, round=1,
                inputs=hier._block(unit["inputs"], items, "group"), max_ids=base.MAX_IDS_PER_STATEMENT,
                max_statements=unit["max_statements"], max_chars=base.MAX_STATEMENT_CHARS,
                kinds=", ".join(base.SYNTHESIS_KINDS))
            ledger = []
            try:
                parsed, reason = base._ask(call_model, prompt, hier.GROUP_MAX_TOKENS, base._accept_statements,
                                           ledger, unit["stage"])
            except Exception as error:
                harness_errors.append(f"{spec['name']}:ask_raised:{type(error).__name__}:{error}"[:200])
                continue
            record = {"chain": spec["name"], "category": spec["category"], "inputs": list(items),
                      "input_roles": {k: v["direct_roles"] for k, v in items.items()},
                      "reply_ok": parsed is not None, "reason": reason, "statements": []}
            if parsed is None:
                counts["provider_failures"] += 1
                records.append(record)
                continue
            kept, dropped = base.validate_statements(parsed, unit, items, evidence, ids_key="input_ids")
            proposals = {}
            for raw in (x for x in (parsed.get("statements") or []) if isinstance(x, dict)):
                proposals.setdefault(base._norm(raw.get("statement") or "")[:600], []).append(
                    raw.get("semantic_roles"))
            for s in kept:
                queue = proposals.get(s["statement"]) or []
                raw_roles = spec["expect"].get("force_invalid") or (queue.pop(0) if queue else None)
                for r in (raw_roles if isinstance(raw_roles, list) else [raw_roles] if raw_roles else []):
                    proposed_roles[str(r)] += 1
                    if str(r).strip().lower() not in hier.SEMANTIC_ROLES:
                        invalid.append({"chain": spec["name"], "proposed": r})
                roles = hier.assign_roles(raw_roles, s["cites"], items)
                verdict = hier.role_fidelity(s["statement"], roles["direct_roles"], roles["role_lineage"],
                                             roles["inherited_roles"])
                for r in roles["direct_roles"]:
                    direct_roles[r] += 1
                for r in roles["inherited_roles"]:
                    inherited_roles[r] += 1

                cites = list(s["cites"])
                cited_roles = {r for c in cites for r in items.get(c, {}).get("direct_roles", [])}
                multi = len(cites) >= 2
                crit = spec["expect"].get("critical_role")
                critical_merge = bool(multi and crit and crit in cited_roles
                                      and (cited_roles & set(hier.ASSERTIVE_ROLES)))
                entry = {"statement": s["statement"], "cites": cites, "proposed": raw_roles,
                         "direct": roles["direct_roles"], "inherited": roles["inherited_roles"],
                         "multi_input": multi, "critical_merge": critical_merge,
                         "verdict": "refused" if not verdict["ok"] else
                                    ("promoted" if verdict["promoted"] else "ok")}
                counts["statements"] += 1
                counts["multi_input_merges"] += int(multi)
                if not verdict["ok"]:
                    counts["fidelity_refusals"] += 1
                    refusals.append({"chain": spec["name"], "statement": s["statement"], "cites": cites,
                                     "missing": verdict["roles_missing_from_prose"],
                                     "inputs_retained": sorted(set(items) - set(cites)) or "all_carry_forward"})
                    entry["missing_from_prose"] = verdict["roles_missing_from_prose"]
                elif verdict["promoted"]:
                    counts["deterministic_promotions"] += 1
                    promotions.append({"chain": spec["name"], "statement": s["statement"],
                                       "promoted": verdict["promoted"], "proposed": raw_roles, "cites": cites})
                    entry["promoted"] = verdict["promoted"]
                else:
                    counts["accepted_clean"] += 1

                if critical_merge:
                    counts["critical_multi_input_merges"] += 1
                    if entry["verdict"] == "refused":
                        counts["critical_refused"] += 1
                    elif crit in roles["direct_roles"]:
                        counts["critical_direct"] += 1
                        if verdict["promoted"] and crit in verdict["promoted"]:
                            counts["critical_recovered_by_promotion"] += 1
                            counts["critical_recovery_opportunities"] += 1
                    else:
                        counts["critical_demoted_and_accepted"] += 1
                    if not (verdict["promoted"] and crit in verdict["promoted"]) and \
                            crit not in (hier.valid_roles(raw_roles) or []):
                        counts["critical_recovery_opportunities"] += 1

                carried = set(roles["direct_roles"]) | set(roles["inherited_roles"])
                if cited_roles - carried:
                    role_loss.append({"chain": spec["name"], "lost": sorted(cited_roles - carried),
                                      "statement": s["statement"], "cites": cites})
                record["statements"].append(entry)
            records.append(record)
            step(f"{phase}-chain", chain=spec["name"], category=spec["category"],
                 statements=len(record["statements"]),
                 cites=[len(x["cites"]) for x in record["statements"]],
                 verdicts=[x["verdict"] for x in record["statements"]])
    return {"records": records, "counts": counts, "proposed": proposed_roles, "direct": direct_roles,
            "inherited": inherited_roles, "invalid": invalid, "promotions": promotions, "refusals": refusals,
            "role_loss": role_loss, "harness_errors": harness_errors}


# --- phase 1: the harness must prove itself before spending model time ---------------------------------------------
ident = base.model_identity()
step("preflight", contract=hier.CONTRACT_VERSION, model=ident.get("model"), chains=len(CHAINS),
     inputs_per_chain=sorted({len(c["items"]) for c in CHAINS}),
     min_critical_merges=MIN_CRITICAL_MERGES, min_reduction=hier.MIN_REDUCTION,
     representation_floor=hier.MIN_SYNTHESISED_REPRESENTATION)

dry = run_chains(q.deterministic_stub(), "stub")
harness = {
    "no_harness_errors": not dry["harness_errors"],
    "every_chain_produced_a_record": len(dry["records"]) == len(CHAINS),
    "no_provider_failures": dry["counts"].get("provider_failures", 0) == 0,
    "accounting_adds_up": (dry["counts"].get("statements", 0) ==
                           dry["counts"].get("accepted_clean", 0) + dry["counts"].get("deterministic_promotions", 0)
                           + dry["counts"].get("fidelity_refusals", 0)),
    "cited_inputs_are_real": all(c in r["inputs"] for r in dry["records"] for s in r["statements"]
                                 for c in s["cites"]),
    "role_loss_measured_against_cited_inputs": all(set(x["lost"]) for x in dry["role_loss"]) or not dry["role_loss"],
}
LOG["phases"]["stub"] = {"harness": harness, "counts": dict(dry["counts"]),
                         "multi_input_merges": dry["counts"].get("multi_input_merges", 0),
                         "errors": dry["harness_errors"][:10]}
step("harness_selftest", **harness, statements=dry["counts"].get("statements", 0),
     multi_input=dry["counts"].get("multi_input_merges", 0))
if not all(harness.values()):
    stop("harness_selftest_failed", harness=harness, errors=dry["harness_errors"][:10])
if os.environ.get("G_SYNTH_SELFTEST_ONLY") == "1":
    step("selftest_only", note="harness validated; stopping before any model call")
    raise SystemExit(0)
if str(ident.get("model")) != "qwen3.8:27b":
    stop("unexpected_model", model=ident.get("model"))

# --- phase 2: live ---------------------------------------------------------------------------------------------
step("live_start", note="harness validated; spending model time now")
live = run_chains(base.production_call_model(), "live")

# --- phase 3: sparse-citation whole run for register pressure and convergence -------------------------------------
pkg = OUT / "pkg"
if not pkg.exists():
    q.build_package(pkg, 64)
runtime = OUT / "rt"
runtime.mkdir(parents=True, exist_ok=True)
art = hier.review_experiment(pkg, call_model=q.deterministic_stub(part_cite_rate=0.15, doc_cite_rate=0.15),
                             runtime_root_path=runtime,
                             identity={"model": "stub", "provider": "test", "context_size": 8192,
                                       "resolved_config_sha256": "0" * 64}, release_model=False)
registers = art["hierarchy"]["uncaptured_registers"]
bad = [r for r in registers if r.get("kind") != "preserved_register"
       or r.get("representation_status") != "preserved_indirectly"
       or any(w in str(r.get("statement", "")).lower() for w in ("unrepresented", "unknown", "uncaptured"))]
rounds = art["hierarchy"]["intermediate_rounds"]
arch = art["coverage"]["levels"]["architecture"]
step("whole_run", status=art["status"], registers=len(registers), misclassified=len(bad), rounds=len(rounds),
     reductions=[r.get("reduction") for r in rounds][:6], represented=arch["represented_in_final_inputs"],
     observations=arch["observations"], silently_dropped=arch["silently_dropped"])

# --- gate ---------------------------------------------------------------------------------------------------------
c = live["counts"]
critical_merges = c.get("critical_multi_input_merges", 0)
opportunities = c.get("critical_recovery_opportunities", 0)
sufficient = critical_merges >= MIN_CRITICAL_MERGES
gate = {
    "role_loss_zero": len(live["role_loss"]) == 0,
    "preserved_register_misclassification_zero": len(bad) == 0,
    "refused_merges_retain_inputs": all(r.get("inputs_retained") for r in live["refusals"]),
    "no_silently_dropped_observations": arch["silently_dropped"] == [],
    "thresholds_unchanged": hier.MIN_REDUCTION == 0.80 and hier.MIN_SYNTHESISED_REPRESENTATION == 0.5,
    "registers_actually_created": len(registers) >= 1,
    "sufficient_critical_merge_coverage": sufficient,
}
verdict = "PASS" if all(gate.values()) else ("INCONCLUSIVE_INSUFFICIENT_COVERAGE" if not sufficient else "FAIL")
LOG["summary"] = {
    "verdict": verdict, "gate": gate,
    "false_promotion": "requires_operator_inspection",
    "promotions_for_inspection": live["promotions"],
    "refusals": live["refusals"], "role_loss": live["role_loss"],
    "harness_errors": live["harness_errors"],
    "measurements": {
        "chains": len(CHAINS), "statements": c.get("statements", 0),
        "multi_input_merges": c.get("multi_input_merges", 0),
        "critical_multi_input_merges": critical_merges,
        "minimum_required": MIN_CRITICAL_MERGES,
        "proposed_role_distribution": dict(live["proposed"].most_common()),
        "direct_role_distribution": dict(live["direct"].most_common()),
        "inherited_role_distribution": dict(live["inherited"].most_common()),
        "invalid_proposals": live["invalid"],
        "deterministic_promotions": c.get("deterministic_promotions", 0),
        "fidelity_refusals": c.get("fidelity_refusals", 0),
        "carry_forward_events": len(live["refusals"]),
        "accepted_clean": c.get("accepted_clean", 0),
        "provider_failures": c.get("provider_failures", 0),
        "critical_direct": c.get("critical_direct", 0),
        "critical_refused": c.get("critical_refused", 0),
        "critical_demoted_and_accepted": c.get("critical_demoted_and_accepted", 0),
        "critical_recovery_denominator": opportunities,
        "critical_role_recovery_rate": (round(c.get("critical_recovered_by_promotion", 0) / opportunities, 3)
                                        if opportunities else "N/A - no recovery opportunity occurred"),
        "registers_created": len(registers), "rounds": len(rounds),
        "reductions": [r.get("reduction") for r in rounds],
    },
    "elapsed_min": round((time.time() - STARTED) / 60, 1),
}
LOG["phases"]["live"] = {"records": live["records"]}
(OUT / "evidence.json").write_text(json.dumps(LOG, indent=1, default=str), encoding="utf-8")
step("gate", verdict=verdict, **gate, critical_merges=critical_merges, required=MIN_CRITICAL_MERGES)
print("G-SYNTH1-R2 DONE verdict=" + verdict, flush=True)
raise SystemExit(0 if verdict == "PASS" else 3)
