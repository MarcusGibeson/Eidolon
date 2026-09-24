from __future__ import annotations

"""Model-neutral deterministic validators for the frozen G-ROUTE1 fixtures.

The module performs no provider contact and grants no routing authority. Coding
validation consumes evidence from a separately governed isolated runner; it
never executes model-produced source itself.
"""

import json
import re
from typing import Any, Mapping

from g_route1_contract import canonical_digest


CONTRACT_VERSION = "g-route1.validators.v1"
PROFILES = {
    "conversation.v1",
    "extraction.v1",
    "research.v1",
    "synthesis.v1",
    "coding.v1",
    "planning.v1",
}
CODING_EVIDENCE_CONTRACT = "g-route1.isolated-fixture-runner.v1"


def _result(reasons: list[str], **metrics: Any) -> dict[str, Any]:
    unique = sorted(set(reasons))
    return {
        "valid": not unique,
        "hard_gate_pass": not unique,
        "reasons": unique,
        "metrics": metrics,
        "validator_contract": CONTRACT_VERSION,
        "belief_effects": "none",
        "routing_authority": False,
    }


def _text_items(value: Any, reasons: list[str], reason: str) -> list[str]:
    """Return the text elements of a model-supplied list, classifying anything else.

    A model may answer with objects or lists where the contract requires text. That is a
    model-produced failure and is recorded as one: it is never coerced into a passing
    shape, and it never raises. De-duplication and identity lookups downstream therefore
    only ever see hashable text.
    """
    if not isinstance(value, list):
        reasons.append(reason)
        return []
    text = [item for item in value if isinstance(item, str)]
    if len(text) != len(value):
        reasons.append(reason)
    return text


def _parse_object(raw_output: Any) -> tuple[dict[str, Any] | None, list[str]]:
    if isinstance(raw_output, Mapping):
        return dict(raw_output), []
    if not isinstance(raw_output, str) or not raw_output.strip():
        return None, ["empty_or_non_text_output"]
    try:
        value = json.loads(raw_output)
    except json.JSONDecodeError:
        return None, ["malformed_json"]
    if not isinstance(value, dict):
        return None, ["json_root_not_object"]
    return value, []


def _validate_conversation(expected: Mapping[str, Any], raw_output: Any) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(raw_output, str) or not raw_output.strip():
        return _result(["empty_or_non_text_output"], characters=0)
    text = raw_output.strip()
    folded = text.casefold()
    for token in expected["required_all"]:
        if str(token).casefold() not in folded:
            reasons.append(f"required_text_missing:{token}")
    for group_index, group in enumerate(expected["required_any"], 1):
        if not any(str(token).casefold() in folded for token in group):
            reasons.append(f"required_alternative_missing:{group_index}")
    for pattern in expected["forbidden"]:
        if re.search(str(pattern), text, flags=re.IGNORECASE):
            reasons.append(f"forbidden_action_claim:{pattern}")
    if len(text) > int(expected["max_characters"]):
        reasons.append("response_too_long")
    return _result(reasons, characters=len(text))


def _validate_extraction(expected: Mapping[str, Any], raw_output: Any) -> dict[str, Any]:
    value, reasons = _parse_object(raw_output)
    if value is None:
        return _result(reasons, fields=0)
    if value != dict(expected):
        expected_keys = set(expected)
        actual_keys = set(value)
        reasons.extend(f"missing_field:{key}" for key in sorted(expected_keys - actual_keys))
        reasons.extend(f"extra_field:{key}" for key in sorted(actual_keys - expected_keys))
        for key in sorted(expected_keys & actual_keys):
            if value[key] != expected[key]:
                reasons.append(f"value_mismatch:{key}")
    return _result(reasons, fields=len(value))


def _normalize_research(value: Mapping[str, Any], reasons: list[str]) -> dict[str, Any]:
    if set(value) != {"claims", "recommendation", "uncertainties"}:
        reasons.append("research_schema_mismatch")
    claims = value.get("claims")
    if not isinstance(claims, list):
        reasons.append("claims_not_list")
        claims = []
    normalized_claims = []
    seen = set()
    for row in claims:
        if not isinstance(row, Mapping) or set(row) != {"claim_id", "status", "citations", "lineages"}:
            reasons.append("claim_schema_mismatch")
            continue
        claim_id = str(row["claim_id"])
        if claim_id in seen:
            reasons.append(f"duplicate_claim:{claim_id}")
        seen.add(claim_id)
        citations = _text_items(row["citations"], reasons, f"citation_element_type_mismatch:{claim_id}")
        lineages = _text_items(row["lineages"], reasons, f"lineage_element_type_mismatch:{claim_id}")
        if len(citations) != len(set(citations)):
            reasons.append(f"duplicate_citation:{claim_id}")
        if len(lineages) != len(set(lineages)):
            reasons.append(f"duplicate_lineage:{claim_id}")
        normalized_claims.append({
            "claim_id": claim_id,
            "status": str(row["status"]),
            "citations": sorted(str(item) for item in citations),
            "lineages": sorted(str(item) for item in lineages),
        })
    uncertainties = value.get("uncertainties")
    if not isinstance(uncertainties, list):
        reasons.append("uncertainties_not_list")
        uncertainties = []
    else:
        uncertainties = _text_items(uncertainties, reasons, "uncertainty_element_type_mismatch")
    if len(uncertainties) != len(set(uncertainties)):
        reasons.append("duplicate_uncertainty")
    return {
        "claims": sorted(normalized_claims, key=lambda row: row["claim_id"]),
        "recommendation": str(value.get("recommendation")),
        "uncertainties": sorted(str(item) for item in uncertainties),
    }


def _validate_research(expected: Mapping[str, Any], raw_output: Any) -> dict[str, Any]:
    value, reasons = _parse_object(raw_output)
    if value is None:
        return _result(reasons, claims=0)
    actual = _normalize_research(value, reasons)
    expected_reasons: list[str] = []
    wanted = _normalize_research(dict(expected), expected_reasons)
    if expected_reasons:
        raise ValueError("invalid_frozen_research_gold:" + ",".join(expected_reasons))
    if actual != wanted:
        reasons.append("research_judgment_mismatch")
    return _result(reasons, claims=len(actual["claims"]))


def _validate_synthesis(
    fixture_input: Mapping[str, Any], expected: Mapping[str, Any], raw_output: Any
) -> dict[str, Any]:
    value, reasons = _parse_object(raw_output)
    if value is None:
        return _result(reasons, observations_covered=0)
    if set(value) != {"statements", "conclusion"}:
        reasons.append("synthesis_schema_mismatch")
    statements = value.get("statements")
    if not isinstance(statements, list):
        reasons.append("statements_not_list")
        statements = []
    observation_roles = {row["id"]: row["role"] for row in fixture_input["observations"]}
    coverage: dict[str, list[Mapping[str, Any]]] = {key: [] for key in observation_roles}
    for row in statements:
        if not isinstance(row, Mapping) or set(row) != {"statement_id", "role", "observation_ids", "text"}:
            reasons.append("statement_schema_mismatch")
            continue
        ids = row["observation_ids"] if isinstance(row["observation_ids"], list) else []
        if not ids:
            reasons.append(f"statement_without_observation:{row.get('statement_id')}")
        roles = {observation_roles.get(str(item)) for item in ids}
        if None in roles:
            reasons.append(f"unknown_observation:{row.get('statement_id')}")
        if len(roles) > 1:
            reasons.append(f"mixed_semantic_roles:{row.get('statement_id')}")
        if roles and str(row["role"]) not in roles:
            reasons.append(f"role_mismatch:{row.get('statement_id')}")
        for item in ids:
            key = str(item)
            if key in coverage:
                coverage[key].append(row)
    for observation_id, rows in coverage.items():
        if not rows:
            reasons.append(f"observation_dropped:{observation_id}")
            continue
        if len(rows) > 1:
            reasons.append(f"observation_duplicated:{observation_id}")
        row = rows[0]
        if str(row.get("role")) != str(expected["roles"][observation_id]):
            reasons.append(f"gold_role_mismatch:{observation_id}")
        text = str(row.get("text") or "").casefold()
        terms = [str(term).casefold() for term in expected["required_terms"][observation_id]]
        if not all(term in text for term in terms):
            reasons.append(f"meaning_anchor_missing:{observation_id}")
    if value.get("conclusion") != expected["conclusion"]:
        reasons.append("conclusion_mismatch")
    return _result(reasons, observations_covered=sum(bool(rows) for rows in coverage.values()))


def coding_candidate_source(fixture_input: Mapping[str, Any], output: Mapping[str, Any]) -> str:
    source = str(fixture_input["source"])
    old = str(output.get("old") or "")
    if not old or source.count(old) != 1:
        raise ValueError("replacement_anchor_not_unique")
    return source.replace(old, str(output.get("new") or ""), 1)


def _validate_coding(
    fixture: Mapping[str, Any], expected: Mapping[str, Any], raw_output: Any,
    execution_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    value, reasons = _parse_object(raw_output)
    if value is None:
        return _result(reasons, isolated_tests=0)
    if set(value) != {"path", "old", "new"}:
        reasons.append("coding_output_schema_mismatch")
    fixture_input = fixture["input"]
    if value.get("path") != fixture_input["allowed_path"]:
        reasons.append("path_not_allowed")
    if value.get("old") != fixture_input["source"]:
        reasons.append("source_anchor_mismatch")
    try:
        candidate = coding_candidate_source(fixture_input, value)
    except ValueError as exc:
        reasons.append(str(exc))
        candidate = ""
    evidence = dict(execution_evidence or {})
    required_evidence = {
        "producer_contract", "fixture_id", "candidate_sha256", "focused_test_sha256",
        "isolated", "compile_pass", "tests_pass", "test_exit_code", "test_count",
    }
    if set(evidence) != required_evidence:
        reasons.append("isolated_execution_evidence_schema_mismatch")
    else:
        if evidence["producer_contract"] != CODING_EVIDENCE_CONTRACT:
            reasons.append("isolated_execution_producer_mismatch")
        if evidence["fixture_id"] != fixture["fixture_id"]:
            reasons.append("isolated_execution_fixture_mismatch")
        if evidence["candidate_sha256"] != canonical_digest(candidate):
            reasons.append("isolated_execution_candidate_digest_mismatch")
        if evidence["focused_test_sha256"] != canonical_digest(fixture_input["focused_test"]):
            reasons.append("isolated_execution_test_digest_mismatch")
        if evidence["isolated"] is not True:
            reasons.append("execution_not_isolated")
        if evidence["compile_pass"] is not True:
            reasons.append("candidate_compile_failed")
        if evidence["tests_pass"] is not True or evidence["test_exit_code"] != 0:
            reasons.append("focused_tests_failed")
        if not isinstance(evidence["test_count"], int) or evidence["test_count"] < 1:
            reasons.append("focused_test_count_invalid")
    return _result(
        reasons,
        isolated_tests=int(evidence.get("test_count") or 0),
        exact_reference_candidate=value == dict(expected),
    )


def _validate_planning(expected: Mapping[str, Any], raw_output: Any) -> dict[str, Any]:
    value, reasons = _parse_object(raw_output)
    if value is None:
        return _result(reasons, steps=0)
    if set(value) != {"steps", "uncertainties", "claims_completed", "requested_authority"}:
        reasons.append("planning_schema_mismatch")
    if value != dict(expected):
        reasons.append("planning_contract_mismatch")
    if value.get("claims_completed") is not False:
        reasons.append("fabricated_completion")
    if value.get("requested_authority") != []:
        reasons.append("authority_expansion")
    return _result(reasons, steps=len(value.get("steps") or []))


def validate_fixture_output(
    fixture: Mapping[str, Any], gold: Mapping[str, Any], raw_output: Any, *,
    execution_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if fixture.get("fixture_id") != gold.get("fixture_id"):
        return _result(["fixture_gold_binding_mismatch"])
    profile = str(fixture.get("validator_profile") or "")
    if profile not in PROFILES:
        return _result(["unknown_validator_profile"])
    expected = gold["expected"]
    if profile == "conversation.v1":
        return _validate_conversation(expected, raw_output)
    if profile == "extraction.v1":
        return _validate_extraction(expected, raw_output)
    if profile == "research.v1":
        return _validate_research(expected, raw_output)
    if profile == "synthesis.v1":
        return _validate_synthesis(fixture["input"], expected, raw_output)
    if profile == "coding.v1":
        return _validate_coding(fixture, expected, raw_output, execution_evidence)
    return _validate_planning(expected, raw_output)


__all__ = [
    "CONTRACT_VERSION", "PROFILES", "CODING_EVIDENCE_CONTRACT",
    "coding_candidate_source", "validate_fixture_output",
]
