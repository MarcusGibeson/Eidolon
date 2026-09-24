from __future__ import annotations

"""Counterfactual / prospective normalization diagnostic over frozen G-ROUTE1 raw records.

This is NOT a rescoring of G-ROUTE1 and produces no scientific result. It exists
only to demonstrate, before any G-ROUTE2 provider contact, that the prospective
transport canonicalization is semantics-free. The canonical G-ROUTE1 result is
read-only here and is never amended.
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from g_route1_contract import indexed_fixture_gold
from g_route1_operational import validate_operational
from g_route1_validators import validate_fixture_output
from g_route2_normalization import (ACCEPTED_OUTCOMES, CONTRACT_VERSION, FENCE_REMOVED,
                                    JSON_PROFILES, normalize, outcome_counts,
                                    semantic_values_preserved)

LABEL = "counterfactual / prospective normalization diagnostic"
G_ROUTE1_RESULT = ROOT / "experiments" / "G-ROUTE1-RESULT-R3"
TRANSPORT_PARSE_REASONS = frozenset({"malformed_json", "empty_or_non_text_output", "json_root_not_object"})


def canonical_records(package: Path = G_ROUTE1_RESULT) -> list[dict[str, Any]]:
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((package / "calls").glob("*.json"))]
    return sorted(rows, key=lambda row: int(row["schedule_position"]))


def replay(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = records if records is not None else canonical_records()
    index = indexed_fixture_gold()
    findings: list[str] = []
    per_record = []
    for row in rows:
        fixture, gold = index[row["fixture_id"]]
        profile = str(fixture["validator_profile"])
        record = normalize(row["raw_output"], validator_profile=profile)
        evidence = row.get("coding_execution_evidence")
        raw_operational = row["operational_validation"]
        raw_semantic = row["semantic_evaluation"]
        normalized_operational = validate_operational(fixture, record["payload"], execution_evidence=evidence)
        normalized_semantic = validate_fixture_output(fixture, gold, record["payload"], execution_evidence=evidence)
        raw_transport_only = bool(set(raw_semantic["reasons"]) <= TRANSPORT_PARSE_REASONS and raw_semantic["reasons"])
        per_record.append({
            "call_id": row["call_id"], "model_tier": row["model_tier"], "model": row["model"],
            "task_class": row["task_class"], "risk_class": row["risk_class"], "profile": profile,
            "outcome": record["outcome"], "normalized": record["normalized"],
            "raw_preserved": record["raw_output"] == row["raw_output"],
            "semantic_values_preserved": semantic_values_preserved(record),
            "raw_operational_accepted": raw_operational["accepted"],
            "normalized_operational_accepted": normalized_operational["accepted"],
            "raw_semantic_pass": raw_semantic["hard_gate_pass"],
            "normalized_semantic_pass": normalized_semantic["hard_gate_pass"],
            "raw_semantic_reasons": raw_semantic["reasons"],
            "normalized_semantic_reasons": normalized_semantic["reasons"],
            "raw_failure_was_transport_only": raw_transport_only,
        })

    def flag(name: str, ok: bool) -> None:
        if not ok:
            findings.append(name)

    normalized_rows = [row for row in per_record if row["normalized"]]
    json_rows = [row for row in per_record if row["profile"] in JSON_PROFILES]
    large_fenced = [row for row in normalized_rows if row["model_tier"] == "large"]

    flag("raw_outputs_preserved", all(row["raw_preserved"] for row in per_record))
    flag("semantic_values_preserved", all(row["semantic_values_preserved"] for row in per_record))
    flag("every_normalized_payload_parses",
         all(row["normalized_operational_accepted"] or "malformed_json" not in row["normalized_semantic_reasons"]
             for row in normalized_rows))

    # A judged semantic failure must never become a pass. Only failures that were
    # purely transport-parse failures may change, and only into a judged outcome.
    flipped = [row for row in per_record
               if row["normalized_semantic_pass"] and not row["raw_semantic_pass"]
               and not row["raw_failure_was_transport_only"]]
    flag("no_judged_semantic_failure_became_a_pass", not flipped)

    unchanged = [row for row in per_record if not row["normalized"]]
    flag("non_normalized_records_are_bit_identical",
         all(row["raw_semantic_reasons"] == row["normalized_semantic_reasons"]
             and row["raw_operational_accepted"] == row["normalized_operational_accepted"]
             for row in unchanged))

    still_invalid = [row for row in per_record
                     if not row["normalized"] and "malformed_json" in row["raw_semantic_reasons"]]
    flag("non_wrapper_invalid_outputs_remain_invalid",
         all("malformed_json" in row["normalized_semantic_reasons"] for row in still_invalid))

    gold_before = json.loads((ROOT / "experiments/G-ROUTE1-candidate/gold.json").read_text(encoding="utf-8"))
    flag("evaluator_gold_unchanged", gold_before["gold_id"] == "G-ROUTE1-GOLD-R1")

    report = {
        "label": LABEL,
        "is_canonical_result": False,
        "amends_g_route1": False,
        "normalization_contract": CONTRACT_VERSION,
        "records_replayed": len(per_record),
        "json_profile_records": len(json_rows),
        "outcome_counts": outcome_counts(
            [{"outcome": row["outcome"]} for row in per_record]),
        "normalized_records": len(normalized_rows),
        "normalized_by_tier": dict(Counter(row["model_tier"] for row in normalized_rows)),
        "large_tier_fenced_records": len(large_fenced),
        "large_tier_fenced_now_structurally_parseable": sum(
            1 for row in large_fenced if "malformed_json" not in row["normalized_semantic_reasons"]),
        "judged_failures_flipped_to_pass": len(flipped),
        "records_whose_raw_failure_was_transport_only": sum(
            1 for row in per_record if row["raw_failure_was_transport_only"]),
        "operational_acceptance_raw": sum(row["raw_operational_accepted"] for row in per_record),
        "operational_acceptance_normalized": sum(row["normalized_operational_accepted"] for row in per_record),
        "semantic_pass_raw": sum(row["raw_semantic_pass"] for row in per_record),
        "semantic_pass_normalized": sum(row["normalized_semantic_pass"] for row in per_record),
        "findings": findings,
        "valid": not findings,
        "per_record": per_record,
    }
    return report


def main() -> int:
    report = replay()
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if target:
        target.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")
    summary = {key: value for key, value in report.items() if key != "per_record"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["LABEL", "TRANSPORT_PARSE_REASONS", "canonical_records", "replay"]
