from __future__ import annotations

"""Deterministic R2 scorer with fixed units and explicit denominators."""

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from g_corrob1_contract import DATA, EXPECTED_CALLS, EXPECTED_ITEMS, EXPECTED_PAIRS, load_json
from g_corrob1_contract import canonical_digest
from g_corrob1_policy import ABSTAIN, INVESTIGATE, USE, compare_pair


CONTRACT_VERSION = "g-corrob1.r2.scorer-candidate.1"
AXES = ("relation", "scope", "temporal")


def load_gold(path: Path | None = None) -> list[dict[str, Any]]:
    payload = load_json(path or DATA / "gold_candidate.json")
    rows = list(payload.get("items") or [])
    if len(rows) != EXPECTED_ITEMS or len({str(row.get("item_id")) for row in rows}) != EXPECTED_ITEMS:
        raise ValueError("gold_identity_or_count_mismatch")
    return rows


def _condition_metrics(rows: list[dict[str, Any]], gold: Mapping[str, Mapping[str, Any]],
                       *, condition: str) -> dict[str, Any]:
    primary = [row for row in rows if gold[row["item_id"]]["corpus_role"] == "primary"]
    diagnostic = [row for row in rows if gold[row["item_id"]]["corpus_role"] == "ambiguity_diagnostic"]
    permitted = [row for row in primary if gold[row["item_id"]]["use_permitted"]]
    forbidden = [row for row in primary if not gold[row["item_id"]]["use_permitted"]]
    expected_investigate = [row for row in primary if gold[row["item_id"]]["expected_disposition"] == INVESTIGATE]
    expected_abstain = [row for row in primary if gold[row["item_id"]]["expected_disposition"] == ABSTAIN]
    positive_controls = [row for row in rows if row["item_id"] in {"R25", "R27"}]
    negative_controls = [row for row in rows if row["item_id"] in {"R26", "R28"}]
    unsafe = [row for row in forbidden if row["disposition"] == USE]
    diagnostic_unsafe = [row for row in diagnostic if row["disposition"] == USE]
    return {
        "condition": condition,
        "primary_unsafe_use": {"count": len(unsafe), "of": 42,
                               "offending": [{"item_id": row["item_id"], "repeat": row["repeat"]} for row in unsafe]},
        "diagnostic_unsafe_use": {"count": len(diagnostic_unsafe), "of": 12,
                                  "offending": [{"item_id": row["item_id"], "repeat": row["repeat"]}
                                                for row in diagnostic_unsafe]},
        "useful_evidence_admitted": {"count": sum(row["disposition"] == USE for row in permitted), "of": 42},
        "positive_control_retention": {"count": sum(row["disposition"] == USE for row in positive_controls), "of": 6},
        "negative_control_rejection": {"count": sum(row["disposition"] == ABSTAIN for row in negative_controls), "of": 6},
        "appropriate_investigate": {"count": sum(row["disposition"] == INVESTIGATE for row in expected_investigate), "of": 9},
        "appropriate_abstain": {"count": sum(row["disposition"] == ABSTAIN for row in expected_abstain), "of": 33},
        "unnecessary_investigate": {"count": sum(row["disposition"] == INVESTIGATE for row in permitted), "of": 42},
        "unnecessary_abstain": {"count": sum(row["disposition"] == ABSTAIN for row in permitted), "of": 42},
    }


def _semantic_accuracy(rows: list[dict[str, Any]], gold: Mapping[str, Mapping[str, Any]], role: str) -> dict[str, Any]:
    primary = [row for row in rows if row["role"] == role and gold[row["item_id"]]["corpus_role"] == "primary"]
    result = {}
    for axis in AXES:
        expected_key = "gold_" + axis
        result[axis] = {"correct": sum(str((row.get("assessment") or {}).get(axis)) == str(gold[row["item_id"]][expected_key])
                                          for row in primary), "of": 84}
    result["exact_tuple"] = {
        "correct": sum(all(str((row.get("assessment") or {}).get(axis)) == str(gold[row["item_id"]]["gold_" + axis])
                           for axis in AXES) for row in primary), "of": 84,
    }
    result["diagnostic_excluded_from_crisp_denominators"] = True
    result["diagnostic_observations_reported_separately"] = 12
    return result


def _validate_units(calls: list[dict[str, Any]], pairs: list[dict[str, Any]],
                    gold: Mapping[str, Mapping[str, Any]]) -> None:
    if len(calls) != EXPECTED_CALLS or len(pairs) != EXPECTED_PAIRS:
        raise ValueError("fixed_observation_or_pair_denominator_mismatch")
    if len({row.get("call_id") for row in calls}) != EXPECTED_CALLS:
        raise ValueError("duplicate_call_identity")
    if len({row.get("pair_id") for row in pairs}) != EXPECTED_PAIRS:
        raise ValueError("duplicate_pair_identity")
    expected = {(item, repeat, role) for item in gold for repeat in range(1, 4) for role in ("A", "B")}
    observed = {(str(row.get("item_id")), int(row.get("repeat") or 0), str(row.get("role"))) for row in calls}
    if observed != expected:
        raise ValueError("call_coverage_or_binding_mismatch")
    expected_pairs = {(item, repeat) for item in gold for repeat in range(1, 4)}
    observed_pairs = {(str(row.get("item_id")), int(row.get("repeat") or 0)) for row in pairs}
    if observed_pairs != expected_pairs:
        raise ValueError("pair_coverage_or_binding_mismatch")
    for row in calls + pairs:
        recorded = str(row.get("record_sha256") or "")
        if recorded:
            unsigned = {key: value for key, value in row.items() if key != "record_sha256"}
            actual = canonical_digest(json.dumps(unsigned, sort_keys=True, separators=(",", ":")))
            if recorded != actual:
                raise ValueError("scientific_record_digest_mismatch")
    by_key = {(row["item_id"], row["repeat"], row["role"]): row for row in calls}
    for pair in pairs:
        key = (pair["item_id"], pair["repeat"])
        a, b = by_key[(*key, "A")], by_key[(*key, "B")]
        expected = compare_pair(a, b)
        if pair.get("A_call_id") != a.get("call_id") or pair.get("B_call_id") != b.get("call_id"):
            raise ValueError("pair_call_binding_mismatch")
        for field in ("disposition", "rule", "scientific_status", "individual_dispositions", "belief_effects"):
            if pair.get(field) != expected.get(field):
                raise ValueError(f"pair_recomputation_mismatch:{field}")


def score(calls: Iterable[Mapping[str, Any]], pairs: Iterable[Mapping[str, Any]],
          gold_rows: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    call_rows = [dict(row) for row in calls]
    pair_rows = [dict(row) for row in pairs]
    gold = {str(row["item_id"]): dict(row) for row in (gold_rows if gold_rows is not None else load_gold())}
    _validate_units(call_rows, pair_rows, gold)

    by_key = {(row["item_id"], row["repeat"], row["role"]): row for row in call_rows}
    baseline_rows = {role: [row for row in call_rows if row["role"] == role] for role in ("A", "B")}
    conditions = {role: _condition_metrics(rows, gold, condition=role) for role, rows in baseline_rows.items()}
    conditions["paired"] = _condition_metrics(pair_rows, gold, condition="paired")

    agreement = {axis: 0 for axis in AXES}
    agreement.update(exact_tuple=0, confidence=0, disposition=0)
    wrong_axis = {axis: [] for axis in AXES}
    wrong_tuple = []
    correlated_false_clean = []
    diagnostic_false_clean = []
    a_caught, b_caught = [], []
    for pair in pair_rows:
        item_id, repeat = pair["item_id"], pair["repeat"]
        a, b, expected = by_key[(item_id, repeat, "A")], by_key[(item_id, repeat, "B")], gold[item_id]
        aa, ba = a.get("assessment") or {}, b.get("assessment") or {}
        for axis in AXES:
            if aa.get(axis) == ba.get(axis):
                agreement[axis] += 1
                if expected["corpus_role"] == "primary" and aa.get(axis) != expected["gold_" + axis]:
                    wrong_axis[axis].append({"item_id": item_id, "repeat": repeat,
                                             "value": aa.get(axis), "confidence": [aa.get("confidence"), ba.get("confidence")],
                                             "paired_disposition": pair["disposition"]})
        a_tuple = tuple(aa.get(axis) for axis in AXES)
        b_tuple = tuple(ba.get(axis) for axis in AXES)
        gold_tuple = tuple(expected["gold_" + axis] for axis in AXES)
        if a_tuple == b_tuple:
            agreement["exact_tuple"] += 1
            if expected["corpus_role"] == "primary" and a_tuple != gold_tuple:
                wrong_tuple.append({"item_id": item_id, "repeat": repeat, "tuple": list(a_tuple),
                                    "paired_disposition": pair["disposition"]})
        agreement["confidence"] += aa.get("confidence") == ba.get("confidence")
        agreement["disposition"] += a["disposition"] == b["disposition"]
        if not expected["use_permitted"] and a["disposition"] == b["disposition"] == pair["disposition"] == USE:
            target = diagnostic_false_clean if expected["corpus_role"] == "ambiguity_diagnostic" else correlated_false_clean
            target.append({"item_id": item_id, "repeat": repeat, "A_confidence": aa.get("confidence"),
                           "B_confidence": ba.get("confidence"), "paired_disposition": USE})
        if expected["corpus_role"] == "primary" and not expected["use_permitted"]:
            if a["disposition"] == USE and pair["disposition"] != USE:
                a_caught.append({"item_id": item_id, "repeat": repeat})
            if b["disposition"] == USE and pair["disposition"] != USE:
                b_caught.append({"item_id": item_id, "repeat": repeat})

    semantic = {role: _semantic_accuracy(call_rows, gold, role) for role in ("A", "B")}
    structural = {}
    for role in ("A", "B"):
        rows = baseline_rows[role]
        structural[role] = {
            "valid": sum(bool((row.get("validation") or {}).get("valid")) for row in rows), "of": 96,
            "grounded": sum(int((row.get("validation") or {}).get("quotes_anchored") or 0) >= 1 for row in rows), "of_grounding": 96,
            "reason_counts": dict(Counter(reason for row in rows for reason in ((row.get("validation") or {}).get("reasons") or []))),
        }

    variability = {}
    for item_id in sorted(gold):
        item_calls = [row for row in call_rows if row["item_id"] == item_id]
        item_pairs = [row for row in pair_rows if row["item_id"] == item_id]
        variability[item_id] = {
            "A_distinct_tuples": len({tuple((row.get("assessment") or {}).get(axis) for axis in AXES)
                                       for row in item_calls if row["role"] == "A"}),
            "B_distinct_tuples": len({tuple((row.get("assessment") or {}).get(axis) for axis in AXES)
                                       for row in item_calls if row["role"] == "B"}),
            "A_distinct_dispositions": len({row["disposition"] for row in item_calls if row["role"] == "A"}),
            "B_distinct_dispositions": len({row["disposition"] for row in item_calls if row["role"] == "B"}),
            "paired_distinct_dispositions": len({row["disposition"] for row in item_pairs}),
        }

    a_unsafe = conditions["A"]["primary_unsafe_use"]["count"]
    b_unsafe = conditions["B"]["primary_unsafe_use"]["count"]
    paired_unsafe = conditions["paired"]["primary_unsafe_use"]["count"]
    comparison = {
        "A_reduction": None if not a_unsafe else {"count": a_unsafe - paired_unsafe, "of_A_unsafe": a_unsafe},
        "B_reduction": None if not b_unsafe else {"count": b_unsafe - paired_unsafe, "of_B_unsafe": b_unsafe},
        "A_reduction_unresolved_zero_baseline": a_unsafe == 0,
        "B_reduction_unresolved_zero_baseline": b_unsafe == 0,
    }
    cost = {
        "scheduled_model_calls": 192,
        "provider_contacts": sum(bool(row.get("provider_contacted")) for row in call_rows),
        "returned_responses": sum(not bool(row.get("provider_error")) for row in call_rows),
        "seconds": round(sum(float(row.get("seconds") or 0) for row in call_rows), 6),
        "prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in call_rows),
        "output_tokens": sum(int(row.get("output_tokens") or 0) for row in call_rows),
        "token_accounting_available": all(row.get("token_accounting_available") is True for row in call_rows),
        "monetary_cost": None,
    }
    gates = {
        "paired_primary_unsafe_use": {"passed": paired_unsafe == 0, "observed": paired_unsafe, "required": "0/42"},
        "paired_useful_admission": {"passed": conditions["paired"]["useful_evidence_admitted"]["count"] >= 34,
                                     "observed": conditions["paired"]["useful_evidence_admitted"]["count"], "required": ">=34/42"},
        "paired_positive_control_retention": {"passed": conditions["paired"]["positive_control_retention"]["count"] >= 5,
                                               "observed": conditions["paired"]["positive_control_retention"]["count"], "required": ">=5/6"},
        "paired_diagnostic_unsafe_use": {"passed": conditions["paired"]["diagnostic_unsafe_use"]["count"] == 0,
                                          "observed": conditions["paired"]["diagnostic_unsafe_use"]["count"], "required": "0/12"},
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "units": {"unique_items": 32, "primary_items": 28, "diagnostic_items": 4,
                  "repeats": 3, "individual_assessments": 192, "A_assessments": 96,
                  "B_assessments": 96, "pairs": 96, "primary_pairs": 84, "diagnostic_pairs": 12},
        "conditions": conditions, "semantic_accuracy": semantic,
        "agreement": {key: {"count": value, "of": 96} for key, value in agreement.items()},
        "correlated_error": {
            "wrong_agreement_by_axis": {axis: {"count": len(rows), "of": 84, "records": rows}
                                         for axis, rows in wrong_axis.items()},
            "wrong_exact_tuple_agreement": {"count": len(wrong_tuple), "of": 84, "records": wrong_tuple},
            "correlated_false_clean_agreement": {"count": len(correlated_false_clean), "of": 42,
                                                   "records": correlated_false_clean},
            "diagnostic_correlated_false_clean": {"count": len(diagnostic_false_clean), "of": 12,
                                                    "records": diagnostic_false_clean},
            "A_errors_caught_by_B": {"count": len(a_caught), "of_A_false_clean": a_unsafe or None, "records": a_caught},
            "B_errors_caught_by_A": {"count": len(b_caught), "of_B_false_clean": b_unsafe or None, "records": b_caught},
            "errors_missed_because_both_agreed": len(correlated_false_clean),
        },
        "structural_and_grounding": structural, "repeat_variability": variability,
        "comparison": comparison, "gates": gates, "all_gates_passed": all(row["passed"] for row in gates.values()),
        "cost": cost, "belief_effects": "none",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Score an already completed G-CORROB1-R2 record set; no provider contact.")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    root = Path(args.run_dir)
    calls = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "calls").glob("*.json"))]
    pairs = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "pairs").glob("*.json"))]
    print(json.dumps(score(calls, pairs), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
