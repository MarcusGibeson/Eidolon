from __future__ import annotations

import argparse
from datetime import date, time
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HUMAN = HERE / "DESIGN_CANDIDATE.md"
MACHINE = HERE / "DESIGN_CANDIDATE.json"
REPORT = HERE / "DESIGN_VALIDATION_REPORT.json"


class DuplicateKeyError(ValueError):
    pass


def load_json_unique(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DuplicateKeyError(f"duplicate_key:{path}:{key}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)], cwd=ROOT, check=True,
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def require(condition: bool, name: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def cp_zero_upper(trials: int, alpha: float = 0.05) -> float:
    return 1.0 - alpha ** (1.0 / trials)


def cp_success_lower(successes: int, trials: int, alpha: float = 0.05) -> float:
    def upper_tail(p: float) -> float:
        return sum(
            math.comb(trials, value) * p**value * (1.0 - p) ** (trials - value)
            for value in range(successes, trials + 1)
        )

    low, high = 0.0, 1.0
    for _ in range(120):
        mid = (low + high) / 2.0
        if upper_tail(mid) < alpha:
            low = mid
        else:
            high = mid
    return high


def ids(rows: list[dict[str, Any]], key: str = "id") -> list[str]:
    return [str(row[key]) for row in rows]


def canonical_decimal(value: str) -> str:
    number = Decimal(value)
    if number == 0:
        return "0.0"
    rendered = format(number, "f")
    if "." not in rendered:
        rendered += ".0"
    else:
        rendered = rendered.rstrip("0").rstrip(".")
        if "." not in rendered:
            rendered += ".0"
    return rendered


def render_operand(operand: dict[str, Any], types: dict[str, Any]) -> str:
    require_keys = {"kind", "value"}
    if set(operand) != require_keys:
        raise ValueError("operand_keys")
    kind, value = operand["kind"], operand["value"]
    if kind not in types or not isinstance(value, str):
        raise ValueError("operand_kind_or_value")
    rule = types[kind]
    if "regex" in rule and re.fullmatch(rule["regex"], value, re.ASCII) is None:
        raise ValueError(f"operand_regex:{kind}:{value}")
    if kind == "decimal_literal" and canonical_decimal(value) != value:
        raise ValueError("noncanonical_decimal")
    if kind == "date_literal":
        date.fromisoformat(value)
    if kind == "time_literal":
        time.fromisoformat(value)
    if kind in {"string_literal", "entity_selector_literal"}:
        if any(ord(char) < 0x20 or ord(char) > 0x7E for char in value):
            raise ValueError("non_ascii_literal")
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return value


def render_subject(vector: dict[str, Any], operation: dict[str, Any]) -> str:
    catalog = {row["id"]: row for row in operation["catalog"]}
    conversions = {row["id"]: row for row in operation["unit_conversion_catalog"]}
    types = operation["placeholder_type_system"]
    nodes = vector["nodes"]
    if not 1 <= len(nodes) <= 2:
        raise ValueError("node_count")
    targets = {node["target"] for node in nodes}
    if len(targets) != len(nodes):
        raise ValueError("duplicate_target")
    ordered: list[dict[str, Any]] = []
    remaining = list(nodes)
    completed: set[str] = set()
    while remaining:
        ready = []
        for node in remaining:
            values = (
                node["arguments"]["operands"]
                if "operands" in node["arguments"]
                else list(node["arguments"].values())
            )
            dependencies = {
                item["value"] for item in values
                if item["kind"] == "derived_field_identifier"
            }
            if dependencies <= completed:
                ready.append(node)
        if not ready:
            raise ValueError("operation_cycle_or_missing_dependency")
        node = sorted(ready, key=lambda item: item["target"].encode("utf-8"))[0]
        ordered.append(node)
        completed.add(node["target"])
        remaining.remove(node)
    if len(ordered) == 2:
        second_operands = (
            ordered[1]["arguments"]["operands"]
            if "operands" in ordered[1]["arguments"]
            else list(ordered[1]["arguments"].values())
        )
        if ordered[0]["target"] not in {
            item["value"] for item in second_operands
            if item["kind"] == "derived_field_identifier"
        }:
            raise ValueError("disconnected_two_node_graph")

    sentences = [operation["opening_template"].format(record_type=vector["record_type"])]
    for node in ordered:
        op = catalog[node["id"]]
        if node["id"] == "UNIT_CONVERSION":
            if set(node) != {"id", "conversion_id", "target", "arguments"}:
                raise ValueError("unit_node_keys")
            template = conversions[node["conversion_id"]]["template"]
        else:
            if set(node) != {"id", "target", "arguments"}:
                raise ValueError("ordinary_node_keys")
            template = op["template"]
        rendered: dict[str, str] = {"target": node["target"]}
        expected_arguments = set(op["placeholders"]) - {"target"}
        if set(node["arguments"]) != expected_arguments:
            raise ValueError("argument_keys")
        for name, raw in node["arguments"].items():
            if name == "operands":
                if not operation["sum_operands"]["minimum"] <= len(raw) <= operation["sum_operands"]["maximum"]:
                    raise ValueError("sum_operand_count")
                parts = [render_operand(item, types) for item in raw]
                rendered[name] = (
                    f"{parts[0]} and {parts[1]}" if len(parts) == 2
                    else ", ".join(parts[:-1]) + ", and " + parts[-1]
                )
            else:
                allowed = op["argument_kinds"][name]
                if raw["kind"] not in allowed:
                    raise ValueError("argument_kind")
                rendered[name] = render_operand(raw, types)
        sentences.append(template.format(**rendered))
    return " ".join(sentences)


NUMERIC = {"ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "SUM", "COUNT", "UNIT_CONVERSION"}
COMPARISON = {"GT", "GTE", "LT", "LTE", "EQ"}


def derive_family(vector: dict[str, Any]) -> str:
    if vector["unresolved_required_field_count"] == 1 and vector["unknown_sentinel_available"]:
        return "E7"
    if vector["entity_disambiguation_required"]:
        return "E5"
    terminal = vector["terminal_operation"]
    if terminal in COMPARISON:
        return "E4"
    if terminal == "CALENDAR_DAY_OFFSET":
        return "E1"
    if terminal in {"CLOCK_MINUTE_OFFSET", "ELAPSED_MINUTES"}:
        return "E2"
    if terminal in NUMERIC or (terminal == "EXACT_COPY" and set(vector["source_operation_types"]) & NUMERIC):
        return "E3"
    if terminal in {"ENTITY_FIELD_BIND", "EXACT_COPY"}:
        return "E6"
    raise ValueError("family_no_match")


def derive_features(vector: dict[str, Any]) -> list[str]:
    operation_ids = set(vector["operation_ids"])
    features: set[str] = set()
    mapping = {
        "calendar_date": {"CALENDAR_DAY_OFFSET"},
        "clock_time": {"CLOCK_MINUTE_OFFSET"},
        "elapsed_time": {"ELAPSED_MINUTES"},
        "aggregation": NUMERIC,
        "unit_conversion": {"UNIT_CONVERSION"},
        "threshold": COMPARISON,
        "entity_binding": {"ENTITY_FIELD_BIND"},
        "exact_copy": {"EXACT_COPY"},
    }
    for feature, candidates in mapping.items():
        if operation_ids & candidates:
            features.add(feature)
    if "EQ" in operation_ids or vector["boundary_relation"] == "EQUAL":
        features.add("equality_boundary")
    if vector["terminal_operation"] in {"ENTITY_FIELD_BIND", "EXACT_COPY"}:
        features.add("field_binding")
    if len(vector["operation_ids"]) == 2:
        features.add("multi_step")
    if vector["unresolved_required_field_count"] == 1 and vector["unknown_sentinel_available"]:
        features.add("ambiguity")
    order = [
        "calendar_date", "clock_time", "elapsed_time", "aggregation", "unit_conversion",
        "threshold", "equality_boundary", "entity_binding", "field_binding", "exact_copy",
        "multi_step", "ambiguity",
    ]
    return [item for item in order if item in features]


def derive_fact_role(vector: dict[str, Any]) -> str:
    if vector["template_id"] == "EXPLICIT_ABSENCE":
        return "EXPLICIT_ABSENCE"
    if vector["sink_operation"] in {"ENTITY_FIELD_BIND", "EXACT_COPY"} and vector["field_identifier"] == vector["sink_source_field"]:
        return "TARGET"
    if vector["field_identifier"] in vector["referenced_fields"]:
        return "SUPPORT"
    return "DISTRACTOR"


def render_fact(record: dict[str, Any], types: dict[str, Any]) -> str:
    prefix = ""
    if record["entity_selector_value"] is not None:
        selector = render_operand(
            {"kind": "entity_selector_literal", "value": record["entity_selector_value"]}, types,
        )
        prefix = f"For {selector}, "
    if record["template_id"] == "EXPLICIT_ABSENCE":
        if record["value"] is not None:
            raise ValueError("absence_value_must_be_null")
        return f"{prefix}{record['field_identifier']} was not provided."
    if record["template_id"] != "VALUE" or record["value"] is None:
        raise ValueError("fact_template_or_value")
    return f"{prefix}{record['field_identifier']} is {render_operand(record['value'], types)}."


def duplicate_keys(raw: str) -> bool:
    found = False

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        nonlocal found
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                found = True
            result[key] = value
        return result

    json.loads(raw, object_pairs_hook=pairs_hook)
    return found


def operational_ambiguity_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"status", "name", "count"}
        and value["status"] in {"provided", "not_provided"}
        and isinstance(value["name"], str)
        and isinstance(value["count"], int)
        and not isinstance(value["count"], bool)
    )


def classify_ambiguity(raw: str) -> tuple[bool, bool, str, bool]:
    value = json.loads(raw)
    operational_valid = operational_ambiguity_valid(value)
    duplicate = duplicate_keys(raw)
    if operational_valid and duplicate:
        return duplicate, True, "semantic_schema_invalid", True
    if not operational_valid:
        return duplicate, False, "operational_schema_invalid", False
    if value == {"status": "not_provided", "name": "Aster", "count": 3}:
        return duplicate, True, "exact_valid_not_provided", False
    if value["status"] != "not_provided":
        return duplicate, True, "exact_valid_unsupported_value", True
    return duplicate, True, "exact_valid_supported_field_error", True


def source_fact_layout(sequence: list[list[Any]]) -> str:
    roles = [row[1] for row in sequence]
    if "EXPLICIT_ABSENCE" in roles:
        return "EXPLICIT_PARTIAL_ABSENCE"
    projected = [row[2] for row in sequence if row[1] in {"TARGET", "SUPPORT"} and row[2] >= 0]
    if (
        len(projected) >= 4 and len(set(projected)) >= 2
        and all(left != right for left, right in zip(projected, projected[1:]))
        and all(projected.count(item) >= 2 for item in set(projected))
    ):
        return "INTERLEAVED_MULTI_ENTITY"
    distractors = [row[0] for row in sequence if row[1] == "DISTRACTOR"]
    targets_supports = [row[0] for row in sequence if row[1] in {"TARGET", "SUPPORT"}]
    if distractors and targets_supports and max(distractors) < min(targets_supports):
        return "DISTRACTOR_BEFORE_TARGET"
    if distractors and targets_supports and min(distractors) > max(targets_supports):
        return "DISTRACTOR_AFTER_TARGET"
    targets = [row[0] for row in sequence if row[1] == "TARGET"]
    supports = [row[0] for row in sequence if row[1] == "SUPPORT"]
    if targets and supports and min(targets) < min(supports):
        return "TARGET_BEFORE_SUPPORTING_FACTS"
    entities = {row[2] for row in sequence if row[1] in {"TARGET", "SUPPORT"} and row[2] >= 0}
    if targets_supports and len(entities) <= 1:
        interval = set(range(min(targets_supports), max(targets_supports) + 1))
        if set(targets_supports) == interval:
            return "CONTIGUOUS_SINGLE_ENTITY"
    return "AUTHORING_ERROR"


def fingerprint_bytes(vector: dict[str, Any], operation: dict[str, Any]) -> str:
    catalog = {row["id"]: row for row in operation["catalog"]}
    nodes = vector["operation_nodes"]
    target_index = {node["target"]: index for index, node in enumerate(nodes)}
    kind_map = {
        "field_identifier": "source_field", "derived_field_identifier": "derived_field",
        "integer_literal": "literal", "decimal_literal": "literal", "date_literal": "literal",
        "time_literal": "literal", "string_literal": "literal", "enum_literal": "literal",
        "collection_identifier": "collection", "entity_selector_literal": "entity_selector",
    }
    graph = []
    for node in nodes:
        op = catalog[node["id"]]
        operands: list[dict[str, Any]] = []
        for name in op["placeholders"]:
            if name == "target":
                continue
            raw = node["arguments"][name]
            operands.extend(raw if isinstance(raw, list) else [raw])
        dependencies = sorted({target_index[item["value"]] for item in operands if item["kind"] == "derived_field_identifier"})
        graph.append([node["id"], [kind_map[item["kind"]] for item in operands], dependencies])

    roles = []
    numeric = NUMERIC | {"ELAPSED_MINUTES"}
    for field in vector["output_fields"]:
        producer = field["producer"]
        effective = field["upstream_producer"] or producer
        if field["absence"]:
            role = "absence_sentinel"
        elif producer == "ENTITY_FIELD_BIND":
            role = "entity_bound_value"
        elif effective in COMPARISON:
            role = "derived_boolean"
        elif effective == "CALENDAR_DAY_OFFSET":
            role = "derived_date"
        elif effective == "CLOCK_MINUTE_OFFSET":
            role = "derived_time"
        elif effective in numeric:
            role = "derived_number"
        else:
            role = "source_copy"
        roles.append([field["schema_type"], role])
    roles.sort(key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    count = vector["entity_record_count"]
    if count == 0:
        entity_role = "NONE"
    elif count == 1:
        entity_role = "SINGLE_ENTITY"
    elif not vector["entity_disambiguation_required"]:
        entity_role = "MULTI_ENTITY_NO_DISAMBIGUATION"
    else:
        entity_role = f"MULTI_ENTITY_SELECT_BY_{vector['entity_selector_role']}"
    fingerprint = [
        graph, roles, entity_role, vector["boundary_relation"], vector["temporal_pattern"],
        source_fact_layout(vector["source_fact_sequence"]),
    ]
    return json.dumps(fingerprint, ensure_ascii=False, separators=(",", ":"))


def reserve_decision(vector: dict[str, Any]) -> str:
    defective = vector["defective_primary_ids"]
    if not defective:
        return "NO_ACTIVATION"
    if len(defective) != 1:
        return "STOP_AUTHORING"
    return "ACTIVATE_SINGLE_RESERVE" if defective == vector["profile_matches"] else "STOP_AUTHORING"


def event_category(event: str, events: dict[str, Any]) -> str:
    if event in events["invalid_events"]:
        return "INVALID"
    if event in events["precontact_blocking_events"]:
        return "PRE_CONTACT_BLOCKED"
    if event == events["abort_event"]:
        return "ABORTED"
    if event in events["incomplete_events"]:
        return "INCOMPLETE"
    raise ValueError(f"uncataloged_event:{event}")


def result_verdict(facts: dict[str, Any], events: dict[str, Any]) -> str:
    emitted = facts.get("events", [])
    if any(item in events["invalid_events"] for item in emitted):
        return "INVALID"
    if facts.get("provider_generation_calls", 1) == 0 and any(item in events["precontact_blocking_events"] for item in emitted):
        return "PRE_CONTACT_BLOCKED"
    if events["abort_event"] in emitted:
        return "ABORTED"
    if any(item in events["incomplete_events"] for item in emitted) or set(facts.get("cell_states", [])) & {"A_INCOMPLETE", "B_INCOMPLETE"}:
        return "INCOMPLETE"
    if facts.get("phase_a_terminal") and facts.get("phase_b_entrant_count") == 0:
        return "NO_PHASE_A_CELL_QUALIFIED"
    if facts.get("phase_b_entrant_count", 0) >= 1 and facts.get("finally_qualified_count") == 0 and facts.get("phase_b_terminal"):
        return "QUALIFICATION_METHOD_FAILED_VALIDATION"
    if facts.get("finally_qualified_count", 0) >= 1 and facts.get("b_failed_validation_count", 0) >= 1 and facts.get("phase_b_terminal"):
        return "MIXED_TARGETED_REQUALIFICATION_SUPPORTED"
    if (
        facts.get("finally_qualified_count", 0) >= 1
        and facts.get("finally_qualified_count") == facts.get("phase_b_entrant_count")
        and facts.get("phase_b_terminal")
    ):
        return "TARGETED_REQUALIFICATION_SUPPORTED"
    raise ValueError("no_terminal_verdict")


def validate(contract: dict[str, Any], human: str) -> list[str]:
    checks: list[str] = []
    require(contract["schema_version"] == "g-extract1.design-candidate.v4", "schema_v4", checks)
    require(contract["experiment"]["status"] == "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_4", "status_v4", checks)
    for field in ("implemented", "blueprint_authorized", "fixture_authoring_authorized", "execution_authorized"):
        require(contract["experiment"][field] is False, f"authority_false:{field}", checks)
    require(contract["experiment"]["provider_generation_calls"] == 0, "provider_calls_zero", checks)
    require(contract["experiment"]["belief_effects"] == "none", "belief_effects_none", checks)

    corpus, phases = contract["corpus"], contract["phases"]
    expected_counts = {
        "families_per_phase_round": 7, "fixtures_per_family_phase_round": 5,
        "fixtures_per_phase_round": 35, "determinate_fixtures_per_phase_round": 30,
        "ambiguity_fixtures_per_phase_round": 5, "phase_a_scored_fixtures": 70,
        "phase_b_scored_fixtures": 70, "phase_a_reserves": 14, "phase_b_reserves": 14,
        "total_to_author_before_model_contact": 168,
    }
    for field, expected in expected_counts.items():
        require(corpus[field] == expected, f"corpus_count:{field}", checks)
    require(corpus["scored_fixtures_authored_at_this_checkpoint"] == 0, "zero_scored_fixtures", checks)
    require(corpus["reserve_fixtures_authored_at_this_checkpoint"] == 0, "zero_reserve_fixtures", checks)
    require(phases["A"]["scheduled_calls"] == 420, "phase_a_calls", checks)
    require(phases["B"]["maximum_scheduled_calls"] == 210, "phase_b_calls", checks)
    require(contract["efficiency"]["maximum_total_calls"] == 630, "maximum_calls", checks)
    require(abs(contract["efficiency"]["maximum_call_reduction_fraction"] - (1 - 630 / 1395)) < 1e-6, "call_reduction", checks)

    operation = contract["operation_definition_contract"]
    require(operation["contract_id"] == "g-extract1.operation-definitions.v2", "operation_contract_v2", checks)
    require(operation["minimum_operation_nodes_per_fixture"] == 1, "operation_min_nodes", checks)
    require(operation["maximum_operation_nodes_per_fixture"] == 2, "operation_max_nodes", checks)
    require(operation["sum_operands"] == {
        "minimum": 2, "maximum": 4,
        "allowed_kinds": ["field_identifier", "derived_field_identifier", "integer_literal", "decimal_literal"],
        "order": "array order is immutable", "two": "A and B",
        "three_or_four": "comma-space between earlier operands and ', and ' before final operand",
    }, "sum_contract", checks)
    required_kinds = {
        "field_identifier", "derived_field_identifier", "collection_identifier", "integer_literal",
        "decimal_literal", "date_literal", "time_literal", "string_literal",
        "entity_selector_literal", "enum_literal",
    }
    require(set(operation["placeholder_type_system"]) == required_kinds, "placeholder_kind_catalog", checks)
    require(operation["catalog"][14]["id"] == "UNIT_CONVERSION", "unit_operation_position", checks)
    require(operation["catalog"][14]["argument_kinds"]["source"] == ["field_identifier"], "unit_source_kind", checks)
    require(operation["catalog"][15]["argument_kinds"]["selector_value"] == ["entity_selector_literal"], "selector_kind", checks)
    for row in operation["catalog"]:
        expected_arguments = set(row["placeholders"]) - {"target"}
        require(set(row["argument_kinds"]) == expected_arguments, f"argument_kind_keys:{row['id']}", checks)
    for vector in operation["rendering_test_vectors"]:
        require(render_subject(vector, operation) == vector["expected_subject"], f"render:{vector['id']}", checks)
    require(ids(operation["rendering_test_vectors"]) == [
        "negative_integer", "decimal", "date", "time", "sum_two", "sum_three",
        "quoted_selector", "escaped_entity_selector", "two_node_dependency",
    ], "render_vector_ids", checks)
    for kind, rejected in (("integer_literal", "-0"), ("integer_literal", "+5"), ("decimal_literal", "5.00")):
        try:
            render_operand({"kind": kind, "value": rejected}, operation["placeholder_type_system"])
        except ValueError:
            checks.append(f"reject_noncanonical:{kind}:{rejected}")
        else:
            raise AssertionError(f"accepted_noncanonical:{kind}:{rejected}")
    one_operand_sum = {
        "record_type": "invoice",
        "nodes": [{"id": "SUM", "target": "total", "arguments": {"operands": [{"kind": "field_identifier", "value": "subtotal"}]}}],
    }
    try:
        render_subject(one_operand_sum, operation)
    except ValueError:
        checks.append("reject_sum_below_minimum")
    else:
        raise AssertionError("accepted_sum_below_minimum")
    require(operation["historical_absence_sentinel"] == "not_provided", "historical_sentinel", checks)
    require(operation["historical_absence_schema"] == "provided|not_provided", "historical_absence_schema", checks)
    require(not operation["free_form_operation_instruction_allowed"], "no_free_form_operations", checks)

    families = contract["family_assignment_contract"]
    require(families["contract_id"] == "g-extract1.family-assignment.v2", "family_contract_v2", checks)
    require(families["metadata_derived_not_author_selected"], "metadata_not_author_selected", checks)
    expected_fields = {
        "unresolved_required_field_count", "unknown_sentinel_available", "entity_record_count",
        "entity_disambiguation_required", "terminal_operation", "source_operation_types",
        "output_role_type", "threshold_operator", "temporal_operation", "aggregation_operation",
        "entity_selector_role", "source_fact_sequence", "direct_copy_only",
    }
    require(set(families["metadata_schema"]) == expected_fields, "family_metadata_fields", checks)
    require(all("derivation" in rule for rule in families["metadata_schema"].values()), "all_family_derivations", checks)
    require(set(families["secondary_feature_derivations"]) == set(families["allowed_secondary_features"]), "all_secondary_derivations", checks)
    require([row["family"] for row in families["priority_first_match"]] == ["E7", "E5", "E4", "E1", "E2", "E3", "E6"], "family_precedence", checks)
    for vector in families["derivation_test_vectors"]:
        require(vector["terminal_operation"] == vector["operation_ids"][-1], f"terminal_derivation:{vector['id']}", checks)
        require(vector["source_operation_types"] == sorted(set(vector["operation_ids"][:-1]), key=lambda item: item.encode("utf-8")), f"source_operation_derivation:{vector['id']}", checks)
        require(derive_family(vector) == vector["expected_family"], f"family_vector:{vector['id']}", checks)
        require(derive_features(vector) == vector["expected_features"], f"feature_vector:{vector['id']}", checks)
    for vector in families["fact_role_test_vectors"]:
        require(derive_fact_role(vector) == vector["expected"], f"fact_role:{vector['id']}", checks)
    for vector in families["fact_rendering_test_vectors"]:
        require(render_fact(vector["record"], operation["placeholder_type_system"]) == vector["expected"], f"fact_render:{vector['id']}", checks)

    composed = contract["composed_feature_requirements"]
    require(ids(composed["requirements"]) == ["C1", "C2", "C3", "C4"], "composed_ids", checks)
    require(sum(row["minimum_distinct_fixtures"] for row in composed["requirements"]) == 8, "composed_total", checks)
    c3 = composed["requirements"][2]
    require(c3["operation_graph_shape"] == ["NUMERIC_OPERATION", "EXACT_COPY"], "c3_graph", checks)
    require(c3["sink_source_must_equal_first_target"], "c3_dependency", checks)

    ambiguity = contract["ambiguity_contract"]
    require(ambiguity["contract_id"] == "g-extract1.ambiguity-scoring.v3", "ambiguity_contract_v3", checks)
    require("duplicate_key_present" in ambiguity["observable_classifier_inputs"], "ambiguity_duplicate_input", checks)
    require("semantic_schema_valid" in ambiguity["observable_classifier_inputs"], "ambiguity_semantic_schema_input", checks)
    expected_outcomes = [
        "infrastructure_missing", "provider_truncated", "empty_output", "json_parse_failure",
        "non_object_root", "operational_schema_invalid", "semantic_schema_invalid",
        "exact_valid_not_provided", "exact_valid_unsupported_value",
        "exact_valid_supported_field_error",
    ]
    require(ids(ambiguity["primary_outcome_precedence"], "outcome") == expected_outcomes, "ambiguity_outcomes", checks)
    require([row["priority"] for row in ambiguity["primary_outcome_precedence"]] == list(range(1, 11)), "ambiguity_precedence", checks)
    for vector in ambiguity["classifier_test_vectors"]:
        duplicate, operational_valid, outcome, false_clean = classify_ambiguity(vector["raw_output"])
        require(duplicate == vector["expected_duplicate_key_present"], f"duplicate:{vector['id']}", checks)
        require(operational_valid == vector["expected_operational_schema_valid"], f"operational_schema:{vector['id']}", checks)
        require(outcome == vector["expected_outcome"], f"ambiguity_outcome:{vector['id']}", checks)
        require(false_clean == vector["expected_false_clean"], f"ambiguity_false_clean:{vector['id']}", checks)
    require(ambiguity["phase_a_gate"]["required_observations"] == 10, "ambiguity_a_10", checks)
    require(ambiguity["phase_b_gate"]["required_observations"] == 5, "ambiguity_b_5", checks)

    exact = contract["exact_value_contract"]
    require(exact["operational_validator_unchanged"], "operational_validator_unchanged", checks)
    require(exact["semantic_parser_requirements"]["duplicate_key_makes_semantic_schema_invalid"], "duplicate_semantic_invalid", checks)
    require(exact["operational_semantic_disagreement_rule"] == "operationally accepted plus semantically invalid is false-clean", "false_clean_bridge", checks)

    contamination = contract["contamination_contract"]
    require(contamination["contract_id"] == "g-extract1.contamination.v2", "contamination_contract_v2", checks)
    tokenizer = contamination["tokenizer"]
    require(tokenizer["alternative_precedence"] == ["date", "time", "number", "identifier"], "token_precedence", checks)
    compiled = re.compile(tokenizer["pattern"], re.ASCII)
    for vector in tokenizer["test_vectors"]:
        require(compiled.findall(vector["input"].casefold()) == vector["expected"], f"tokenizer:{vector['input']}", checks)
    require(contamination["ngram"]["size"] == 5, "ngram_size", checks)
    require(contamination["maximum_payload_token_5gram_jaccard_exclusive"] == 0.2, "jaccard_limit", checks)
    require(ids(contamination["fingerprint"]["components"]) == [
        "operation_graph", "output_schema_roles", "entity_role_graph", "boundary_relation",
        "temporal_pattern", "source_fact_layout",
    ], "fingerprint_components", checks)
    for vector in contamination["fingerprint"]["generation_test_vectors"]:
        require(fingerprint_bytes(vector, operation) == vector["expected_bytes"], f"fingerprint:{vector['id']}", checks)
    for vector in contamination["source_fact_layout_algorithm"]["test_vectors"]:
        require(source_fact_layout(vector["sequence"]) == vector["expected"], f"layout:{vector['id']}", checks)
    independent = contamination["independent_implementation_contract"]
    require(independent["separately_authored_source_modules"], "independent_modules", checks)
    require(not independent["shared_normative_implementation_code_allowed"], "no_shared_normative_code", checks)
    require(not independent["shared_derivation_helpers_allowed"], "no_shared_derivation_helpers", checks)
    require(independent["any_disagreement"] == "block_freeze", "differential_blocks_freeze", checks)
    required_scopes = {
        "every G-ROUTE4 extraction fixture versus every G-EXTRACT1 scored or reserve fixture",
        "Phase A versus Phase A", "Phase A versus Phase B", "Phase B versus Phase B",
        "every scored fixture versus every reserve", "reserve versus reserve",
    }
    require(set(contamination["pairwise_scope"]) == required_scopes, "pairwise_scope", checks)

    reserve = contract["reserve_activation_contract"]
    require(reserve["contract_id"] == "g-extract1.reserve-activation.v3", "reserve_contract_v3", checks)
    require(reserve["total_reserve_slots"] == 2 * 2 * 7 == 28, "reserve_slot_count", checks)
    require(reserve["slot_id_format"] == "RESERVE:{phase}:{round}:{primary_family}", "reserve_slot_id", checks)
    require(not reserve["selection_pool_allowed"], "no_reserve_pool", checks)
    require(reserve["reserve_consumption_limit"] == 1, "reserve_single_consumption", checks)
    require("output_schema_roles" in reserve["required_match_dimensions"], "reserve_schema_role_match", checks)
    for vector in reserve["test_vectors"]:
        require(reserve_decision(vector) == vector["expected"], f"reserve:{vector['id']}", checks)

    gates_a, gates_b = contract["cell_gates"]["phase_a"], contract["cell_gates"]["phase_b"]
    require(gates_a["denominator_integrity"]["required_observations"] == 70, "gate_a_observations", checks)
    require(gates_a["denominator_integrity"]["required_repeat_pairs"] == 35, "gate_a_pairs", checks)
    require(gates_b["denominator_integrity"]["required_observations"] == 35, "gate_b_observations", checks)
    for label, gates in (("a", gates_a), ("b", gates_b)):
        semantic = gates["determinate_semantic_correctness"]
        structural = gates["determinate_structural_validity"]
        useful = gates["useful_correct_acceptance"]
        require(semantic.get("minimum_fixtures_with_both_repeats_correct", semantic.get("minimum_correct_fixtures")) == 29, f"gate_{label}_semantic", checks)
        require(structural.get("minimum_fixtures_with_both_repeats_valid", structural.get("minimum_valid_fixtures")) == 29, f"gate_{label}_structural", checks)
        require(useful.get("minimum_fixtures_with_both_repeats_accepted_and_correct", useful.get("minimum_accepted_and_correct_fixtures")) == 27, f"gate_{label}_useful", checks)
        require(gates["false_clean"]["maximum_affected_fixtures"] == 0, f"gate_{label}_false_clean", checks)
        require(gates["malformed_determinate"]["maximum_affected_fixtures"] == 1, f"gate_{label}_malformed", checks)
    require(gates_a["correlated_false_clean"]["maximum_repeat_pairs"] == 0, "gate_a_correlated", checks)
    require(gates_b["correlated_false_clean"]["classification"] == "not_applicable_single_observation_phase", "gate_b_no_repeat_guardrail", checks)

    confidence = contract["confidence_contract"]
    require(abs(confidence["zero_failures_of_35_upper_95"] - cp_zero_upper(35)) < 5e-10, "cp_0_35", checks)
    require(abs(confidence["zero_failures_of_30_upper_95"] - cp_zero_upper(30)) < 5e-10, "cp_0_30", checks)
    require(abs(confidence["29_successes_of_30_lower_95"] - cp_success_lower(29, 30)) < 5e-10, "cp_29_30", checks)
    require(abs(confidence["27_successes_of_30_lower_95"] - cp_success_lower(27, 30)) < 5e-10, "cp_27_30", checks)
    require(not confidence["iid_population_claim_allowed"], "no_iid_claim", checks)

    cell = contract["cell_state_machine"]
    require(cell["phase_b_selector"] == "sorted exact set of A_QUALIFIED_FOR_B cell IDs", "phase_b_selector", checks)
    require(not cell["operator_selection_allowed"], "no_operator_selection", checks)
    require(not cell["phase_a_phase_b_pooling_allowed"], "no_pooling", checks)
    require(not cell["failed_cell_reentry_allowed"], "no_reentry", checks)

    events = contract["integrity_event_contract"]
    require(events["contract_id"] == "g-extract1.integrity-events.v2", "integrity_contract_v2", checks)
    require(events["event_catalog_complete_for_frozen_lifecycle"], "event_catalog_complete", checks)
    required_new_invalid = {
        "POST_CONTACT_GOLD_DEFECT_DISCOVERED", "UNVERIFIABLE_INTERRUPTION_CHECKPOINT",
        "CORRUPTED_CHECKPOINT", "MISSING_CHECKPOINT_AFTER_INTERRUPTION",
        "UNVERIFIABLE_JOURNAL_PREFIX", "PROVIDER_FAILURE_WITHOUT_RECEIPT",
    }
    require(required_new_invalid <= set(events["invalid_events"]), "new_invalid_events", checks)
    require(set(events["precontact_blocking_events"]).isdisjoint(events["invalid_events"]), "event_catalog_disjoint", checks)
    for vector in events["classification_test_vectors"]:
        require(event_category(vector["event"], events) == vector["expected_category"], f"event:{vector['id']}", checks)

    result = contract["result_state_machine"]
    require(result["contract_id"] == "g-extract1.result-state-machine.v3", "result_contract_v3", checks)
    require([row["verdict"] for row in result["first_match_precedence"]] == [
        "INVALID", "PRE_CONTACT_BLOCKED", "ABORTED", "INCOMPLETE",
        "NO_PHASE_A_CELL_QUALIFIED", "QUALIFICATION_METHOD_FAILED_VALIDATION",
        "MIXED_TARGETED_REQUALIFICATION_SUPPORTED", "TARGETED_REQUALIFICATION_SUPPORTED",
    ], "result_precedence", checks)
    for vector in result["deterministic_test_vectors"]:
        require(result_verdict(vector["facts"], events) == vector["expected"], f"verdict:{vector['id']}", checks)

    baseline = contract["baseline_binding"]
    require(baseline["baseline_behavior_source_commit"] == "0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28", "baseline_source_commit", checks)
    require(baseline["subject_rendered_only_by"] == "g-extract1.operation-definitions.v2", "catalog_only_subject", checks)
    for artifact in baseline["existing_behavior_artifacts"]:
        path = ROOT / artifact["path"]
        require(path.is_file(), f"baseline_exists:{artifact['role']}", checks)
        require(sha256(path) == artifact["sha256"], f"baseline_sha256:{artifact['role']}", checks)
        require(git_blob(path) == artifact["git_blob"], f"baseline_git_blob:{artifact['role']}", checks)
    profile = load_json_unique(ROOT / "experiments/G-ROUTE1-candidate/prompt_profiles.json")
    blueprint = load_json_unique(ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json")
    extraction_template = blueprint["templates"]["structured_extraction"]
    require(profile["profiles"]["extraction.v1"] == baseline["system_text"], "system_text_matches_source", checks)
    require(extraction_template["assembled_template"] == baseline["structured_extraction_assembled_template"], "template_matches_source", checks)
    require(extraction_template["absence_sentence"] == operation["historical_absence_sentence"], "absence_sentence_matches_source", checks)

    models = contract["model_provider"]
    require(models["provider"] == "ollama" and models["provider_version"] == "0.34.3", "provider_binding", checks)
    require([row["model"] for row in models["models"]] == ["qwen2.5:7b", "qwen3:14b", "qwen3.8:27b"], "model_names", checks)
    require(all(re.fullmatch(r"[0-9a-f]{64}", row["blob_sha256"]) for row in models["models"]), "model_hashes", checks)
    require(contract["sampling"]["seed_formula"] == "base + zero_based_fixture_index * 10 + one_based_repeat", "seed_formula", checks)

    gold = contract["gold_adjudication_contract"]
    require(gold["post_contact_gold_defect_invalidates_affected_run"], "gold_defect_invalidates", checks)
    require(not gold["post_contact_gold_repair_allowed"], "no_gold_repair", checks)
    governance = contract["governance"]
    for field in (
        "separate_blueprint_authorization", "separate_fixture_authoring_authorization",
        "separate_implementation_authorization", "separate_pilot_authorization",
        "separate_execution_freeze_authorization", "separate_phase_a_authorization",
        "separate_conditional_phase_b_authorization",
    ):
        require(governance[field], f"governance:{field}", checks)
    require(governance["g_route4_remains_failed"], "g_route4_failed", checks)
    require(not governance["source_runtime_behavior_changed"], "runtime_unchanged", checks)
    require(not governance["provider_contacted"], "provider_not_contacted", checks)
    require(not governance["new_experiment_started"], "experiment_not_started", checks)
    require(governance["belief_effects"] == "none", "belief_none", checks)
    history = contract["historical_binding"]
    require(sha256(ROOT / "experiments/G-ROUTE4-candidate/closure/G_ROUTE4_CLOSURE.json") == history["closure_sha256"], "closure_unchanged", checks)
    require(sha256(ROOT / "experiments/G-ROUTE4-candidate/closure/PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json") == history["diagnostic_sha256"], "diagnostic_unchanged", checks)

    human_literals = [
        "g-extract1.design-candidate.v4", "g-extract1.operation-definitions.v2",
        "g-extract1.family-assignment.v2", "g-extract1.contamination.v2",
        "g-extract1.ambiguity-scoring.v3", "g-extract1.reserve-activation.v3",
        "g-extract1.integrity-events.v2", "g-extract1.result-state-machine.v3",
        "POST_CONTACT_GOLD_DEFECT_DISCOVERED", "UNVERIFIABLE_INTERRUPTION_CHECKPOINT",
        "RESERVE:{phase}:{round}:{primary_family}", "2026-10-01", "5-3",
        "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_4", "does not prove scientific validity",
    ]
    for literal in human_literals:
        require(literal in human, f"human_literal:{literal}", checks)
    for row in operation["catalog"]:
        if "template" in row:
            require(f"`{row['template']}`" in human, f"human_template:{row['id']}", checks)
    for event in events["invalid_events"]:
        require(f"`{event}`" in human, f"human_invalid_event:{event}", checks)

    validation_scope = contract["validation_claim_scope"]
    require(validation_scope["validator_claim"] == "deterministic structural and cross-representation consistency only", "validator_scope", checks)
    require(not validation_scope["scientific_validity_proven"], "no_scientific_validity_claim", checks)
    require(not validation_scope["adversarial_review_replaced"], "review_not_replaced", checks)
    allowed = {
        "DESIGN_CANDIDATE.md", "DESIGN_CANDIDATE.json", "DESIGN_REVISION_CHANGELOG.md",
        "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md", "DESIGN_VALIDATION_REPORT.json",
        "validate_design.py",
    }
    require(not [path.name for path in HERE.iterdir() if path.name not in allowed], "no_fixture_or_runtime_artifacts", checks)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    contract = load_json_unique(MACHINE)
    human = HUMAN.read_text(encoding="utf-8")
    checks = validate(contract, human)
    report = {
        "schema_version": "g-extract1.design-validation-report.v3",
        "verdict": "PASS",
        "validation_scope": "deterministic structural and cross-representation consistency only",
        "scientific_validity_assessed": False,
        "adversarial_review_replaced": False,
        "check_count": len(checks),
        "checks": checks,
        "artifacts": {
            "DESIGN_CANDIDATE.md": sha256(HUMAN),
            "DESIGN_CANDIDATE.json": sha256(MACHINE),
            "DESIGN_REVISION_CHANGELOG.md": sha256(HERE / "DESIGN_REVISION_CHANGELOG.md"),
            "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md": sha256(HERE / "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md"),
            "validate_design.py": sha256(Path(__file__)),
        },
        "provider_generation_calls": 0,
        "scored_fixtures_authored": 0,
        "reserve_fixtures_authored": 0,
        "belief_effects": "none",
    }
    rendered = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if args.write_report:
        REPORT.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
