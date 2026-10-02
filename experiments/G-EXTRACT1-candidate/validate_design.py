from __future__ import annotations

import argparse
import copy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from fractions import Fraction
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
    if "allowed" in rule and value not in rule["allowed"]:
        raise ValueError(f"operand_allowed:{kind}:{value}")
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


def stable_topological_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            if not dependencies <= targets:
                raise ValueError("missing_derived_target")
            if dependencies <= completed:
                ready.append(node)
        if not ready:
            raise ValueError("operation_cycle_or_missing_dependency")
        node = sorted(ready, key=lambda item: item["target"].encode("utf-8"))[0]
        ordered.append(node)
        completed.add(node["target"])
        remaining.remove(node)
    if len(ordered) == 2:
        second_values = (
            ordered[1]["arguments"]["operands"]
            if "operands" in ordered[1]["arguments"]
            else list(ordered[1]["arguments"].values())
        )
        if ordered[0]["target"] not in {
            item["value"] for item in second_values
            if item["kind"] == "derived_field_identifier"
        }:
            raise ValueError("disconnected_two_node_graph")
    return ordered


def render_subject(vector: dict[str, Any], operation: dict[str, Any]) -> str:
    catalog = {row["id"]: row for row in operation["catalog"]}
    conversions = {row["id"]: row for row in operation["unit_conversion_catalog"]}
    types = operation["placeholder_type_system"]
    nodes = vector["nodes"]
    if not 0 <= len(nodes) <= 2:
        raise ValueError("node_count")
    if not nodes and not vector.get("include_absence_sentence", False):
        raise ValueError("zero_node_non_e7")
    if nodes and vector.get("include_absence_sentence", False):
        raise ValueError("e7_operation_node")
    if re.fullmatch(operation["record_type_regex"], vector["record_type"], re.ASCII) is None:
        raise ValueError("record_type")
    ordered = stable_topological_nodes(nodes)

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
        if re.fullmatch(operation["derived_field_identifier_regex"], node["target"], re.ASCII) is None:
            raise ValueError("target_identifier")
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
    if vector.get("include_absence_sentence", False):
        sentences.append(operation["historical_absence_subject_fragment"])
    subject = operation["subject_fragment_join"].join(sentences)
    if subject.endswith("."):
        raise ValueError("subject_terminal_period")
    return subject


def assemble_prompt(subject: str, baseline: dict[str, Any]) -> str:
    template = baseline["structured_extraction_assembled_template"]
    if template.count("{SUBJECT}") != 1 or subject.endswith("."):
        raise ValueError("prompt_assembly")
    return template.replace("{SUBJECT}", subject)


NUMERIC = {"ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "SUM", "UNIT_CONVERSION"}
COMPARISON = {"GT", "GTE", "LT", "LTE", "EQ"}


def derive_family(vector: dict[str, Any]) -> str:
    if vector["unresolved_required_field_count"] == 1 and vector["unknown_sentinel_available"]:
        if vector["operation_ids"]:
            raise ValueError("e7_operations_prohibited")
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
        features.add("explicit_partial_absence")
    order = [
        "calendar_date", "clock_time", "elapsed_time", "aggregation", "unit_conversion",
        "threshold", "equality_boundary", "entity_binding", "field_binding", "exact_copy",
        "multi_step", "explicit_partial_absence",
    ]
    return [item for item in order if item in features]


def derive_fact_role(vector: dict[str, Any]) -> str:
    if vector["template_id"] == "EXPLICIT_ABSENCE":
        return "EXPLICIT_ABSENCE"
    if vector["field_identifier"] in vector.get("source_copy_fields", []):
        return "TARGET"
    if vector["sink_operation"] in {"ENTITY_FIELD_BIND", "EXACT_COPY"} and vector["field_identifier"] == vector["sink_source_field"]:
        return "TARGET"
    if vector["field_identifier"] in vector["referenced_fields"]:
        return "SUPPORT"
    return "DISTRACTOR"


def lexical_atom_valid(value: str, kind: str, contract: dict[str, Any], phase: str | None = None) -> bool:
    if kind == "record_type":
        return phase in contract["record_type_catalog_by_phase"] and value in contract["record_type_catalog_by_phase"][phase]
    regex_by_kind = {
        "source_field": contract["identifier_generation"]["source_field"]["regex"],
        "derived_target": contract["identifier_generation"]["derived_target"]["regex"],
        "output_field": contract["identifier_generation"]["output_field"]["regex"],
        "entity": contract["entity_label_generation"]["regex"],
        "string": contract["string_value_generation"]["regex"],
    }
    if kind in regex_by_kind:
        return re.fullmatch(regex_by_kind[kind], value, re.ASCII) is not None
    if kind == "enum_schema":
        if value == contract["ordinary_enum_labels"]["special_historical_schema"]:
            return True
        options = value.split("|")
        catalog = contract["ordinary_enum_labels"]["catalog"]
        return 2 <= len(options) <= 8 and options == catalog[:len(options)]
    return False


def content_is_safe(value: str, contract: dict[str, Any], kind: str = "string_literal") -> bool:
    if kind == "entity_selector_literal":
        return re.fullmatch(contract["entity_selector_literal_regex"], value, re.ASCII) is not None
    return re.fullmatch(contract["string_literal_regex"], value, re.ASCII) is not None


def parse_schema_type(schema: str, contract: dict[str, Any]) -> dict[str, Any]:
    if schema in contract["primitive_schemas"]:
        return {"kind": "primitive", "schema": schema, **contract["primitive_schemas"][schema]}
    enum = contract["finite_enum_schema"]
    options = schema.split("|")
    if not enum["minimum_options"] <= len(options) <= enum["maximum_options"]:
        raise ValueError("schema_enum_count")
    if len(set(options)) != len(options):
        raise ValueError("schema_enum_duplicate")
    if any(re.fullmatch(enum["option_regex"], item, re.ASCII) is None for item in options):
        raise ValueError("schema_enum_option")
    return {"kind": "enum", "schema": schema, "options": options, **enum}


OUTPUT_FIELD_KEYS = {
    "name", "schema_type", "required", "binding_kind", "source_field",
    "producer_target", "label_removal", "absence_capable",
}

SOURCE_ID = r"f(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])_(?:0[1-9]|[1-9][0-9])"
DERIVED_ID = r"d(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])_0[12]"


def validate_output_field_shape(field: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if set(field) != OUTPUT_FIELD_KEYS:
        raise ValueError("output_field_keys")
    if re.fullmatch(f"(?:{SOURCE_ID}|{DERIVED_ID})", field["name"], re.ASCII) is None:
        raise ValueError("output_name")
    if not isinstance(field["required"], bool) or not isinstance(field["label_removal"], bool):
        raise ValueError("output_booleans")
    if not isinstance(field["absence_capable"], bool):
        raise ValueError("output_absence_boolean")
    info = parse_schema_type(field["schema_type"], schema)
    if info["kind"] == "enum" and field["schema_type"] != "provided|not_provided":
        if info["options"] != [f"option_{chr(ord('a')+i)}" for i in range(len(info["options"]))]:
            raise ValueError("non_neutral_output_enum")
    binding = field["binding_kind"]
    if binding == "SOURCE_COPY":
        if re.fullmatch(SOURCE_ID, str(field["source_field"]), re.ASCII) is None or field["producer_target"] is not None or field["absence_capable"] or field["name"] != field["source_field"]:
            raise ValueError("source_copy_shape")
    elif binding == "OPERATION_TARGET":
        if field["source_field"] is not None or re.fullmatch(DERIVED_ID, str(field["producer_target"]), re.ASCII) is None or field["absence_capable"] or field["name"] != field["producer_target"]:
            raise ValueError("operation_target_shape")
    elif binding == "EXPLICIT_ABSENCE":
        if (
            re.fullmatch(SOURCE_ID, str(field["source_field"]), re.ASCII) is None or field["producer_target"] is not None or field["name"] != field["source_field"]
            or not field["absence_capable"] or field["schema_type"] != "provided|not_provided"
        ):
            raise ValueError("explicit_absence_shape")
    else:
        raise ValueError("binding_kind")
    return info


def _literal_value(raw: dict[str, Any], semantics: dict[str, Any]) -> tuple[str, Any]:
    kind, token = raw["kind"], raw["value"]
    semantic = semantics["literal_type_map"].get(kind)
    if semantic is None:
        raise ValueError("literal_semantic_type")
    if kind == "integer_literal":
        return semantic, int(token)
    if kind == "decimal_literal":
        return semantic, Decimal(token)
    if kind == "boolean_literal":
        if token not in {"true", "false"}:
            raise ValueError("boolean_literal")
        return semantic, token == "true"
    if kind == "date_literal":
        return semantic, date.fromisoformat(token)
    if kind == "time_literal":
        return semantic, time.fromisoformat(token)
    return semantic, token


def _typed_source_value(
    record: dict[str, Any], schema: dict[str, Any], semantics: dict[str, Any],
) -> tuple[str, Any, str]:
    info = parse_schema_type(record["schema_type"], schema)
    literal_semantic, value = _literal_value(record["value"], semantics)
    if record["value"]["kind"] not in info["source_value_kinds"]:
        raise ValueError("source_literal_schema")
    if info["semantic_tag"] == "NUMBER" and literal_semantic == "INTEGER":
        value = Decimal(value)
    elif info["semantic_tag"] == "ENUM":
        if literal_semantic != "ENUM" or value not in info["options"]:
            raise ValueError("source_enum_value")
    elif literal_semantic != info["semantic_tag"]:
        raise ValueError("source_literal_semantic")
    return info["semantic_tag"], value, info["schema"]


def _schema_for_semantic(semantic: str) -> str:
    return {
        "INTEGER": "integer", "NUMBER": "number", "BOOLEAN": "boolean",
        "DATE": "YYYY-MM-DD", "TIME": "HH:MM", "STRING": "string",
    }.get(semantic, "ENUM")


def _terminating_fraction(value: Fraction) -> bool:
    denominator = value.denominator
    for prime in (2, 5):
        while denominator % prime == 0:
            denominator //= prime
    return denominator == 1


def _fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Decimal):
        return Fraction(value)
    raise ValueError("not_numeric")


def exact_decimal_from_fraction(value: Fraction) -> str:
    if not _terminating_fraction(value):
        raise ValueError("nonterminating_fraction")
    sign = "-" if value < 0 else ""
    numerator, denominator = abs(value.numerator), value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    scale = max(twos, fives)
    integer = numerator * (2 ** (scale - twos)) * (5 ** (scale - fives))
    digits = str(integer).rjust(scale + 1, "0")
    rendered = digits if scale == 0 else f"{digits[:-scale]}.{digits[-scale:]}"
    rendered = canonical_decimal(rendered)
    return "0.0" if rendered == "0.0" else sign + rendered


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _gold_matches(info: dict[str, Any], expected: Any, actual: Any) -> bool:
    tag = info["semantic_tag"]
    if tag == "NUMBER":
        try:
            return Fraction(Decimal(str(expected))) == _fraction(actual)
        except (ArithmeticError, ValueError):
            return False
    if tag == "INTEGER":
        return isinstance(expected, int) and not isinstance(expected, bool) and expected == actual
    if tag == "BOOLEAN":
        return isinstance(expected, bool) and expected is actual
    if tag == "DATE":
        return expected == actual.isoformat()
    if tag == "TIME":
        return expected == actual.strftime("%H:%M")
    return expected == actual


def validate_entity_population(
    fixture: dict[str, Any], selector_field: str, source_field: str, selected: str,
    schema: dict[str, Any], semantics: dict[str, Any], contract: dict[str, Any],
) -> tuple[str, Any, str]:
    entities = fixture.get("entities", [])
    if len(entities) not in contract["entity_count_allowed"]:
        raise ValueError("entity_count")
    if any(set(item) != set(contract["entity_object_exact_keys"]) for item in entities):
        raise ValueError("entity_keys")
    roles = {item["selector_role"] for item in entities}
    if len(roles) != 1 or not roles <= set(contract["selector_roles"]):
        raise ValueError("entity_roles")
    if selector_field == source_field:
        raise ValueError("entity_fields_must_differ")
    labels = [item["selector_value"] for item in entities]
    prefix = labels[0].rsplit(" ", 1)[0]
    if labels != [f"{prefix} {chr(ord('A') + i)}" for i in range(len(labels))]:
        raise ValueError("entity_label_sequence")
    if len(set(labels)) != len(labels) or selected not in labels or labels != sorted(labels):
        raise ValueError("entity_selector_population")
    facts = fixture["source_fact_records"]
    scoped = [item for item in facts if item["entity_selector_value"] is not None]
    if any(item["entity_selector_value"] not in labels for item in scoped):
        raise ValueError("unknown_entity_fact")
    if any(item["field_identifier"] not in {selector_field, source_field} for item in scoped):
        raise ValueError("extra_entity_fact")
    if any(item["field_identifier"] in {selector_field, source_field} for item in facts if item["entity_selector_value"] is None):
        raise ValueError("non_entity_duplicate")
    selector_schemas, source_schemas = set(), set()
    selected_source = None
    for entity in entities:
        label = entity["selector_value"]
        selector_matches = [x for x in scoped if x["entity_selector_value"] == label and x["field_identifier"] == selector_field and x["template_id"] == "VALUE"]
        source_matches = [x for x in scoped if x["entity_selector_value"] == label and x["field_identifier"] == source_field and x["template_id"] == "VALUE"]
        if len(selector_matches) != 1 or len(source_matches) != 1:
            raise ValueError("entity_fact_cardinality")
        selector_type, selector_value, selector_schema = _typed_source_value(selector_matches[0], schema, semantics)
        source_type, source_value, source_schema = _typed_source_value(source_matches[0], schema, semantics)
        if selector_type != "STRING" or selector_schema != "string" or selector_value != label:
            raise ValueError("entity_selector_fact")
        selector_schemas.add(selector_schema)
        source_schemas.add(source_schema)
        if label == selected:
            selected_source = (source_type, source_value, source_schema)
    if len(selector_schemas) != 1 or len(source_schemas) != 1 or selected_source is None:
        raise ValueError("entity_schema_population")
    return selected_source


def validate_fixture_semantics(
    fixture: dict[str, Any], schema: dict[str, Any], operation: dict[str, Any], semantics: dict[str, Any],
    entity_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nodes = stable_topological_nodes(fixture["operation_nodes"])
    if not 1 <= len(nodes) <= 2:
        raise ValueError("semantic_node_count")
    catalog = {row["id"]: row for row in operation["catalog"]}
    conversions = semantics["unit_conversion_semantics"]
    facts = fixture["source_fact_records"]
    for record in facts:
        if set(record) != {"template_id", "field_identifier", "schema_type", "value", "entity_selector_value"}:
            raise ValueError("fact_keys")
        info = parse_schema_type(record["schema_type"], schema)
        if record["template_id"] == "EXPLICIT_ABSENCE":
            if record["value"] is not None or info["schema"] != "provided|not_provided":
                raise ValueError("absence_fact_schema")
        elif record["template_id"] == "VALUE":
            _typed_source_value(record, schema, semantics)
        else:
            raise ValueError("fact_template")
        render_fact(record, operation["placeholder_type_system"], schema)

    def resolve_source(field_name: str) -> tuple[str, Any, str]:
        matches = [
            item for item in facts
            if item["template_id"] == "VALUE" and item["field_identifier"] == field_name
            and item["entity_selector_value"] is None
        ]
        if len(matches) != 1:
            raise ValueError("source_reference_cardinality")
        return _typed_source_value(matches[0], schema, semantics)

    derived: dict[str, tuple[str, Any, str]] = {}

    def operand(raw: dict[str, Any]) -> tuple[str, Any, str]:
        if raw["kind"] == "field_identifier":
            return resolve_source(raw["value"])
        if raw["kind"] == "derived_field_identifier":
            if raw["value"] not in derived:
                raise ValueError("derived_reference")
            return derived[raw["value"]]
        semantic, value = _literal_value(raw, semantics)
        return semantic, value, _schema_for_semantic(semantic)

    for current in nodes:
        op = current["id"]
        if op not in catalog:
            raise ValueError("unknown_operation")
        args = current["arguments"]
        render_subject({"record_type": "record", "nodes": nodes}, operation)
        if op in {"ADD", "SUBTRACT", "MULTIPLY"}:
            names = {"ADD": ("left", "right"), "SUBTRACT": ("minuend", "subtrahend"), "MULTIPLY": ("left", "right")}[op]
            left, right = operand(args[names[0]]), operand(args[names[1]])
            if left[0] not in {"INTEGER", "NUMBER"} or right[0] not in {"INTEGER", "NUMBER"}:
                raise ValueError("numeric_operand_type")
            result_type = "NUMBER" if "NUMBER" in {left[0], right[0]} else "INTEGER"
            left_value, right_value = _fraction(left[1]), _fraction(right[1])
            if op == "ADD": result = left_value + right_value
            elif op == "SUBTRACT": result = left_value - right_value
            else: result = left_value * right_value
            if result_type == "INTEGER":
                result = result.numerator
            result_schema = _schema_for_semantic(result_type)
        elif op == "DIVIDE":
            left, right = operand(args["dividend"]), operand(args["divisor"])
            if left[0] not in {"INTEGER", "NUMBER"} or right[0] not in {"INTEGER", "NUMBER"}:
                raise ValueError("numeric_operand_type")
            if right[1] == 0:
                raise ValueError("divide_zero")
            exact = _fraction(left[1]) / _fraction(right[1])
            if not _terminating_fraction(exact):
                raise ValueError("divide_nonterminating")
            result_type, result, result_schema = "NUMBER", exact, "number"
        elif op == "SUM":
            values = [operand(item) for item in args["operands"]]
            if not 2 <= len(values) <= 4 or any(item[0] not in {"INTEGER", "NUMBER"} for item in values):
                raise ValueError("sum_operand_type")
            result_type = "NUMBER" if any(item[0] == "NUMBER" for item in values) else "INTEGER"
            exact = sum((_fraction(item[1]) for item in values), Fraction(0))
            result = exact if result_type == "NUMBER" else exact.numerator
            result_schema = _schema_for_semantic(result_type)
        elif op == "UNIT_CONVERSION":
            source = operand(args["source"])
            if source[0] not in {"INTEGER", "NUMBER"}:
                raise ValueError("unit_source_type")
            raw_factor = conversions[current["conversion_id"]]["factor"]
            numerator, _, denominator = raw_factor.partition("/")
            factor = Fraction(int(numerator), int(denominator or "1"))
            exact = _fraction(source[1]) * factor
            if not _terminating_fraction(exact):
                raise ValueError("unit_nonterminating")
            result_type, result, result_schema = "NUMBER", exact, "number"
        elif op == "ELAPSED_MINUTES":
            start, end = operand(args["start"]), operand(args["end"])
            if (start[0], end[0]) != ("TIME", "TIME"):
                raise ValueError("elapsed_type")
            result_type, result, result_schema = "INTEGER", (_minutes(end[1]) - _minutes(start[1])) % 1440, "integer"
        elif op == "CALENDAR_DAY_OFFSET":
            source, offset = operand(args["date"]), operand(args["days"])
            if source[0] != "DATE" or offset[0] != "INTEGER" or not 0 <= offset[1] <= 366:
                raise ValueError("calendar_domain")
            result_type, result, result_schema = "DATE", source[1] + timedelta(days=offset[1]), "YYYY-MM-DD"
        elif op == "CLOCK_MINUTE_OFFSET":
            source, offset = operand(args["time"]), operand(args["minutes"])
            if source[0] != "TIME" or offset[0] != "INTEGER" or not 0 <= offset[1] <= 1439:
                raise ValueError("clock_domain")
            total = (_minutes(source[1]) + offset[1]) % 1440
            result_type, result, result_schema = "TIME", time(total // 60, total % 60), "HH:MM"
        elif op in COMPARISON:
            left, right = operand(args["left"]), operand(args["right"])
            pair = [left[0], right[0]]
            allowed = semantics["operations"][op]["compatible_pairs"]
            if pair not in allowed:
                raise ValueError("comparison_types")
            lval, rval = left[1], right[1]
            if set(pair) == {"INTEGER", "NUMBER"}:
                lval, rval = _fraction(lval), _fraction(rval)
            result_type, result_schema = "BOOLEAN", "boolean"
            result = {"GT": lval > rval, "GTE": lval >= rval, "LT": lval < rval, "LTE": lval <= rval, "EQ": lval == rval}[op]
        elif op == "ENTITY_FIELD_BIND":
            selector = args["selector_value"]["value"]
            selector_field = args["selector_field"]["value"]
            source_field = args["source_field"]["value"]
            if entity_contract is None:
                raise ValueError("entity_contract_missing")
            result_type, result, result_schema = validate_entity_population(
                fixture, selector_field, source_field, selector, schema, semantics, entity_contract,
            )
        elif op == "EXACT_COPY":
            result_type, result, result_schema = operand(args["source_field"])
        else:
            raise ValueError("unsupported_operation")
        derived[current["target"]] = (result_type, result, result_schema)

    fields = fixture["output_fields"]
    if [item["name"] for item in fields] != sorted((item["name"] for item in fields), key=lambda item: item.encode("utf-8")):
        raise ValueError("output_field_order")
    if set(fixture["gold_values"]) != {item["name"] for item in fields}:
        raise ValueError("gold_fields")
    for field in fields:
        info = validate_output_field_shape(field, schema)
        if field["binding_kind"] == "SOURCE_COPY":
            semantic, actual, actual_schema = resolve_source(field["source_field"])
            if semantic != info["semantic_tag"] or actual_schema != field["schema_type"]:
                raise ValueError("source_schema_type")
        elif field["binding_kind"] == "EXPLICIT_ABSENCE":
            semantic, actual, actual_schema = "ENUM", "not_provided", "provided|not_provided"
        else:
            if field["producer_target"] not in derived:
                raise ValueError("producer_target")
            semantic, actual, actual_schema = derived[field["producer_target"]]
            if field["schema_type"] != actual_schema:
                raise ValueError("operation_output_schema")
        role = derive_output_role(field, nodes)
        if role not in info["allowed_output_roles"]:
            raise ValueError("schema_role")
        if not _gold_matches(info, fixture["gold_values"][field["name"]], actual):
            raise ValueError("gold_mismatch")
    return {
        target: {"semantic_type": semantic, "schema_type": schema_type, "value": value}
        for target, (semantic, value, schema_type) in derived.items()
    }


def effective_producer(field: dict[str, Any], nodes: list[dict[str, Any]]) -> str:
    if field["binding_kind"] == "SOURCE_COPY":
        return "SOURCE_COPY"
    if field["binding_kind"] == "EXPLICIT_ABSENCE":
        return "EXPLICIT_ABSENCE"
    by_target = {node["target"]: node for node in nodes}
    target = field["producer_target"]
    visited: set[str] = set()
    while True:
        if target in visited or target not in by_target:
            raise ValueError("producer_target")
        visited.add(target)
        node = by_target[target]
        if node["id"] != "EXACT_COPY":
            return node["id"]
        source = node["arguments"]["source_field"]
        if source["kind"] == "field_identifier":
            return "SOURCE_COPY"
        target = source["value"]


def derive_output_role(field: dict[str, Any], nodes: list[dict[str, Any]]) -> str:
    producer = effective_producer(field, nodes)
    if producer == "EXPLICIT_ABSENCE":
        return "absence_sentinel"
    if producer == "SOURCE_COPY":
        return "source_copy"
    if producer == "ENTITY_FIELD_BIND":
        return "entity_bound_value"
    if producer in COMPARISON:
        return "derived_boolean"
    if producer == "CALENDAR_DAY_OFFSET":
        return "derived_date"
    if producer == "CLOCK_MINUTE_OFFSET":
        return "derived_time"
    if producer in NUMERIC | {"ELAPSED_MINUTES"}:
        return "derived_number"
    raise ValueError("unmapped_output_role")


def render_fact(record: dict[str, Any], types: dict[str, Any], schema: dict[str, Any]) -> str:
    if set(record) != {"template_id", "field_identifier", "schema_type", "value", "entity_selector_value"}:
        raise ValueError("fact_keys")
    info = parse_schema_type(record["schema_type"], schema)
    render_operand({"kind": "field_identifier", "value": record["field_identifier"]}, types)
    prefix = ""
    if record["entity_selector_value"] is not None:
        selector = render_operand(
            {"kind": "entity_selector_literal", "value": record["entity_selector_value"]}, types,
        )
        prefix = f"For {selector}, "
    if record["template_id"] == "EXPLICIT_ABSENCE":
        if record["value"] is not None or info["schema"] != "provided|not_provided":
            raise ValueError("absence_value_must_be_null")
        return f"{prefix}{record['field_identifier']} was not provided."
    if record["template_id"] != "VALUE" or record["value"] is None:
        raise ValueError("fact_template_or_value")
    if record["value"]["kind"] not in info["source_value_kinds"]:
        raise ValueError("fact_value_schema")
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


def classify_ambiguity(
    raw: str,
    *,
    provider_truncated: bool = False,
    accepted_override: bool | None = None,
) -> tuple[bool, bool, str, bool]:
    raw_length = len(raw.encode("utf-8"))
    try:
        value = json.loads(raw)
        duplicate = duplicate_keys(raw)
    except json.JSONDecodeError:
        value = None
        duplicate = False
    root_is_object = isinstance(value, dict)
    operational_valid = operational_ambiguity_valid(value) if root_is_object else False
    accepted = operational_valid if accepted_override is None else accepted_override
    if provider_truncated:
        return duplicate, operational_valid, "provider_truncated", bool(accepted)
    if raw_length == 0:
        return False, False, "empty_output", False
    if value is None and raw.strip() != "null":
        return False, False, "json_parse_failure", False
    if not root_is_object:
        return duplicate, False, "non_object_root", False
    if operational_valid and duplicate:
        return duplicate, True, "semantic_schema_invalid", True
    if not operational_valid:
        return duplicate, False, "operational_schema_invalid", False
    if value == {"status": "not_provided", "name": "Aster", "count": 3}:
        return duplicate, True, "exact_valid_not_provided", False
    if value["status"] != "not_provided":
        return duplicate, True, "exact_valid_unsupported_value", True
    return duplicate, True, "exact_valid_supported_field_error", True


def validate_e7_graph(vector: dict[str, Any]) -> str:
    if vector["operation_ids"]:
        return "AUTHORING_ERROR"
    kinds = vector["output_binding_kinds"]
    if kinds.count("EXPLICIT_ABSENCE") != 1 or kinds.count("SOURCE_COPY") < 2:
        return "AUTHORING_ERROR"
    if vector["unresolved_operand"]:
        return "AUTHORING_ERROR"
    return "VALID_E7"


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


def evaluate_fixture(fixture: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    contract = load_json_unique(MACHINE)
    schema = contract["schema_type_contract"]
    semantics = contract["operation_semantics_contract"]
    values: dict[str, Any] = {}
    for fact in fixture["source_fact_records"]:
        if fact["template_id"] != "VALUE" or fact["entity_selector_value"] is not None:
            continue
        _, value, _ = _typed_source_value(fact, schema, semantics)
        values[fact["field_identifier"]] = value
    derived = validate_fixture_semantics(
        fixture, schema, contract["operation_definition_contract"], semantics,
        contract["entity_population_contract"],
    ) if fixture["operation_nodes"] else {}
    temporal_pattern = "NONE"
    boundary = "NONE"

    def operand(raw: dict[str, Any]) -> Any:
        kind, token = raw["kind"], raw["value"]
        if kind in {"field_identifier", "derived_field_identifier"}:
            return values[token]
        return _literal_value(raw, semantics)[1]

    for node in stable_topological_nodes(fixture["operation_nodes"]):
        op = node["id"]
        args = node["arguments"]
        if op == "CALENDAR_DAY_OFFSET":
            start = operand(args["date"])
            result = start + timedelta(days=operand(args["days"]))
            values[node["target"]] = result
            traversed = [start + timedelta(days=i) for i in range(abs(operand(args["days"])) + 1)]
            if any(item.month == 2 and item.day == 29 for item in traversed):
                temporal_pattern = "LEAP_DAY_BOUNDARY"
            elif start.year != result.year:
                temporal_pattern = "YEAR_BOUNDARY"
            elif start.month != result.month:
                temporal_pattern = "MONTH_BOUNDARY"
            else:
                temporal_pattern = "DATE_WITHIN_MONTH"
        elif op == "CLOCK_MINUTE_OFFSET":
            total = _minutes(operand(args["time"])) + operand(args["minutes"])
            temporal_pattern = "MIDNIGHT_ROLLOVER" if total >= 1440 else "SAME_DAY_FORWARD"
        elif op == "ELAPSED_MINUTES":
            temporal_pattern = "MIDNIGHT_ROLLOVER" if _minutes(operand(args["end"])) < _minutes(operand(args["start"])) else "SAME_DAY_FORWARD"
        elif op in COMPARISON:
            left, right = operand(args["left"]), operand(args["right"])
            boundary = "EQUAL" if left == right else ("BELOW" if left < right else "ABOVE")
            values[node["target"]] = {
                "GT": left > right, "GTE": left >= right, "LT": left < right,
                "LTE": left <= right, "EQ": left == right,
            }[op]
        values[node["target"]] = derived[node["target"]]["value"]
    return values, boundary, temporal_pattern


def fingerprint_bytes(vector: dict[str, Any], operation: dict[str, Any]) -> str:
    catalog = {row["id"]: row for row in operation["catalog"]}
    fixture = vector["fixture"]
    nodes = stable_topological_nodes(fixture["operation_nodes"])
    target_index = {node["target"]: index for index, node in enumerate(nodes)}
    kind_map = {
        "field_identifier": "source_field", "derived_field_identifier": "derived_field",
        "integer_literal": "literal", "decimal_literal": "literal", "boolean_literal": "literal", "date_literal": "literal",
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

    roles = [[field["schema_type"], derive_output_role(field, nodes)] for field in fixture["output_fields"]]
    roles.sort(key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    entities = sorted(fixture["entities"], key=lambda item: item["selector_value"].encode("utf-8"))
    count = len(entities)
    entity_nodes = [node for node in nodes if node["id"] == "ENTITY_FIELD_BIND"]
    disambiguation = count >= 2 and bool(entity_nodes)
    if count == 0:
        entity_role = "NONE"
    elif count == 1:
        entity_role = "SINGLE_ENTITY"
    elif not disambiguation:
        entity_role = "MULTI_ENTITY_NO_DISAMBIGUATION"
    else:
        selector = entity_nodes[0]["arguments"]["selector_value"]["value"]
        selected = [item for item in entities if item["selector_value"] == selector]
        if len(selected) != 1:
            raise ValueError("entity_selector_role")
        entity_role = f"MULTI_ENTITY_SELECT_BY_{selected[0]['selector_role']}"

    source_copy_fields = {field["source_field"] for field in fixture["output_fields"] if field["binding_kind"] == "SOURCE_COPY"}
    referenced = {
        item["value"]
        for node in nodes
        for raw in node["arguments"].values()
        for item in (raw if isinstance(raw, list) else [raw])
        if item["kind"] == "field_identifier"
    }
    sink = nodes[-1] if nodes else None
    sink_source = None
    if sink and sink["id"] in {"ENTITY_FIELD_BIND", "EXACT_COPY"}:
        sink_source = sink["arguments"]["source_field"]["value"]
    entity_index = {item["selector_value"]: index for index, item in enumerate(entities)}
    sequence = []
    for index, fact in enumerate(fixture["source_fact_records"]):
        role = derive_fact_role({
            "template_id": fact["template_id"], "field_identifier": fact["field_identifier"],
            "source_copy_fields": list(source_copy_fields), "sink_operation": sink["id"] if sink else "NONE",
            "sink_source_field": sink_source, "referenced_fields": list(referenced),
        })
        sequence.append([index, role, -1 if fact["entity_selector_value"] is None else entity_index[fact["entity_selector_value"]]])
    _, boundary, temporal = evaluate_fixture(fixture)
    fingerprint = [
        graph, roles, entity_role, boundary, temporal,
        [source_fact_layout(sequence), [[row[1], fact["schema_type"], row[2]] for row, fact in zip(sequence, fixture["source_fact_records"])]],
    ]
    return json.dumps(fingerprint, ensure_ascii=False, separators=(",", ":"))


def canonical_answer_bytes(answer: dict[str, dict[str, Any]], schema_contract: dict[str, Any]) -> bytes:
    rows = []
    for name in sorted(answer, key=lambda item: item.encode("utf-8")):
        schema_type, raw = answer[name]["schema_type"], answer[name]["value"]
        info = parse_schema_type(schema_type, schema_contract)
        value_type = info["semantic_tag"]
        if value_type == "NUMBER":
            canonical = canonical_decimal(str(raw))
        elif value_type == "INTEGER":
            canonical = str(int(raw))
        elif value_type == "BOOLEAN":
            canonical = str(raw).lower()
        else:
            canonical = raw
        rows.append([name, schema_type, [value_type, canonical]])
    return json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def identity_reuse(left: list[list[str]], right: list[list[str]]) -> bool:
    encode = lambda atom: json.dumps(atom, ensure_ascii=True, separators=(",", ":"))
    return bool({encode(item) for item in left} & {encode(item) for item in right})


def date_number_tuple_bytes(atoms: list[list[str]]) -> bytes:
    return json.dumps(atoms, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def canonical_atom(tag: str, value: Any) -> str:
    if tag == "NUMBER":
        return exact_decimal_from_fraction(_fraction(value))
    if tag == "INTEGER":
        return str(int(value))
    if tag == "DATE":
        return value.isoformat() if isinstance(value, date) else str(value)
    if tag == "TIME":
        return value.strftime("%H:%M") if isinstance(value, time) else str(value)
    return str(value)


def extract_date_number_atoms(
    fixture: dict[str, Any], operation: dict[str, Any], schema_contract: dict[str, Any],
    semantics: dict[str, Any], entity_contract: dict[str, Any] | None = None,
) -> list[list[str]]:
    literal_tags = {
        "date_literal": "DATE", "time_literal": "TIME",
        "integer_literal": "INTEGER", "decimal_literal": "NUMBER",
    }
    atoms: list[list[str]] = []
    facts = fixture["source_fact_records"]
    derived = validate_fixture_semantics(fixture, schema_contract, operation, semantics, entity_contract) if fixture["operation_nodes"] else {}
    for fact in fixture["source_fact_records"]:
        raw = fact["value"]
        if raw is not None:
            info = parse_schema_type(fact["schema_type"], schema_contract)
            if info["semantic_tag"] in {"DATE", "TIME", "INTEGER", "NUMBER"}:
                _, value, _ = _typed_source_value(fact, schema_contract, semantics)
                atoms.append(["SOURCE_FACT", info["semantic_tag"], canonical_atom(info["semantic_tag"], value)])
    catalog = {row["id"]: row for row in operation["catalog"]}
    for node in stable_topological_nodes(fixture["operation_nodes"]):
        for name in catalog[node["id"]]["placeholders"]:
            if name == "target":
                continue
            raw = node["arguments"][name]
            for item in (raw if isinstance(raw, list) else [raw]):
                tag = None
                value = None
                if item["kind"] in literal_tags:
                    tag = literal_tags[item["kind"]]
                    tag, value = _literal_value(item, semantics)
                elif item["kind"] == "field_identifier":
                    matches = [x for x in facts if x["template_id"] == "VALUE" and x["field_identifier"] == item["value"] and x["entity_selector_value"] is None]
                    if len(matches) != 1:
                        raise ValueError("atom_source_cardinality")
                    tag, value, _ = _typed_source_value(matches[0], schema_contract, semantics)
                elif item["kind"] == "derived_field_identifier":
                    info = derived[item["value"]]
                    tag, value = info["semantic_type"], info["value"]
                if tag in {"DATE", "TIME", "INTEGER", "NUMBER"}:
                    atoms.append(["OPERATION_ARGUMENT", tag, canonical_atom(tag, value)])
    by_name = {field["name"]: field for field in fixture["output_fields"]}
    gold_values = fixture.get("gold_values", fixture.get("gold", {}))
    for name in sorted(gold_values, key=lambda item: item.encode("utf-8")):
        schema = by_name[name]["schema_type"]
        info = parse_schema_type(schema, schema_contract)
        if info["semantic_tag"] in {"DATE", "TIME", "INTEGER", "NUMBER"}:
            raw = gold_values[name]
            tag = info["semantic_tag"]
            value = canonical_decimal(str(raw)) if tag == "NUMBER" else str(raw)
            atoms.append(["GOLD", tag, value])
    return atoms


def reduce_repeats(observations: list[bool]) -> tuple[bool, bool]:
    if len(observations) != 2:
        raise ValueError("repeat_count")
    return all(observations), any(observations)


def reserve_decision(vector: dict[str, Any]) -> str:
    defective = vector["defective_primary_ids"]
    if not defective:
        return "NO_ACTIVATION"
    if len(defective) != 1:
        return "STOP_AUTHORING"
    return "ACTIVATE_SINGLE_RESERVE" if defective == vector["profile_matches"] else "STOP_AUTHORING"


def validate_e7_fixture(fixture: dict[str, Any], contract: dict[str, Any]) -> None:
    schema, semantics = contract["schema_type_contract"], contract["operation_semantics_contract"]
    if fixture["operation_nodes"] or fixture.get("entities", []):
        raise ValueError("e7_graph_or_entities")
    fields, facts = fixture["output_fields"], fixture["source_fact_records"]
    if len({x["name"] for x in fields}) != len(fields):
        raise ValueError("e7_duplicate_output")
    absence = [x for x in fields if x["binding_kind"] == "EXPLICIT_ABSENCE"]
    supported = [x for x in fields if x["binding_kind"] == "SOURCE_COPY"]
    if len(absence) != 1 or len(supported) < 2 or len(absence) + len(supported) != len(fields):
        raise ValueError("e7_output_shape")
    if set(fixture["gold_values"]) != {x["name"] for x in fields}:
        raise ValueError("e7_gold_fields")
    for fact in facts:
        render_fact(fact, contract["operation_definition_contract"]["placeholder_type_system"], schema)
    for field in fields:
        info = validate_output_field_shape(field, schema)
        matching = [x for x in facts if x["field_identifier"] == field["source_field"] and x["entity_selector_value"] is None]
        if len(matching) != 1:
            raise ValueError("e7_source_cardinality")
        fact = matching[0]
        if field in absence:
            if not field["required"] or fact["template_id"] != "EXPLICIT_ABSENCE" or fixture["gold_values"][field["name"]] != "not_provided":
                raise ValueError("e7_absence_binding")
        else:
            if fact["template_id"] != "VALUE" or fact["schema_type"] != field["schema_type"]:
                raise ValueError("e7_supported_binding")
            _, value, _ = _typed_source_value(fact, schema, semantics)
            if not _gold_matches(info, fixture["gold_values"][field["name"]], value):
                raise ValueError("e7_supported_gold")


def validate_lexical_fixture(fixture: dict[str, Any], contract: dict[str, Any], ordinal: int) -> None:
    if not 1 <= ordinal <= 168:
        raise ValueError("lexical_fixture_ordinal")
    unique_sources = list(dict.fromkeys(x["field_identifier"] for x in fixture["source_fact_records"]))
    if unique_sources != [f"f{ordinal:03d}_{i:02d}" for i in range(1,len(unique_sources)+1)]:
        raise ValueError("lexical_source_position")
    nodes = stable_topological_nodes(fixture["operation_nodes"])
    if [x["target"] for x in nodes] != [f"d{ordinal:03d}_{i:02d}" for i in range(1,len(nodes)+1)]:
        raise ValueError("lexical_derived_position")
    labels = [f"Entity {ordinal:03d} {chr(ord('A')+i)}" for i in range(len(fixture.get("entities",[])))]
    if [x["selector_value"] for x in fixture.get("entities",[])] != labels:
        raise ValueError("lexical_entity_generation")
    string_values = []
    for fact in fixture["source_fact_records"]:
        if fact["entity_selector_value"] is not None and fact["entity_selector_value"] not in labels:
            raise ValueError("lexical_unknown_entity")
        if fact["value"] is None:
            continue
        raw = fact["value"]
        if raw["kind"] == "entity_selector_literal" and raw["value"] not in labels:
            raise ValueError("lexical_entity_value")
        if raw["kind"] == "string_literal":
            if raw["value"] not in string_values:
                string_values.append(raw["value"])
            index = string_values.index(raw["value"])+1
            prefix = ("label","code","id")[(index-1)%3]
            if raw["value"] != f"{prefix}_{ordinal:03d}_{index:02d}":
                raise ValueError("lexical_string_generation")
        info=parse_schema_type(fact["schema_type"],contract["schema_type_contract"])
        if info["kind"]=="enum" and not lexical_atom_valid(fact["schema_type"],"enum_schema",contract["lexical_neutrality_contract"]):
            raise ValueError("lexical_enum_schema")


def typed_operands(fixture: dict[str, Any], contract: dict[str, Any], derived: dict[str, Any]) -> Any:
    def resolve(raw: dict[str, Any]) -> tuple[str, Any]:
        if raw["kind"] == "derived_field_identifier":
            item = derived[raw["value"]]
            return item["semantic_type"], item["value"]
        if raw["kind"] == "field_identifier":
            matches = [x for x in fixture["source_fact_records"] if x["template_id"] == "VALUE" and x["field_identifier"] == raw["value"] and x["entity_selector_value"] is None]
            if len(matches) != 1:
                raise ValueError("typed_operand_cardinality")
            tag, value, _ = _typed_source_value(matches[0], contract["schema_type_contract"], contract["operation_semantics_contract"])
            return tag, value
        return _literal_value(raw, contract["operation_semantics_contract"])
    return resolve


def reserve_profile_bytes(fixture: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any]) -> bytes:
    nodes = stable_topological_nodes(fixture["operation_nodes"])
    is_e7 = not nodes
    if is_e7:
        validate_e7_fixture(fixture, contract)
        derived = {}
    else:
        derived = validate_fixture_semantics(fixture, contract["schema_type_contract"], contract["operation_definition_contract"], contract["operation_semantics_contract"], contract["entity_population_contract"])
    resolve = typed_operands(fixture, contract, derived)
    _, boundary, temporal = evaluate_fixture(fixture)
    operations = [x["id"] for x in nodes]
    entities = fixture.get("entities", [])
    metadata = {
        "unresolved_required_field_count": int(is_e7), "unknown_sentinel_available": is_e7,
        "entity_disambiguation_required": bool(entities and "ENTITY_FIELD_BIND" in operations),
        "operation_ids": operations, "terminal_operation": operations[-1] if operations else "NONE",
        "source_operation_types": sorted(set(operations[:-1])), "boundary_relation": boundary,
    }
    comparison = [x for x in nodes if x["id"] in COMPARISON]
    temporal_nodes = [x for x in nodes if x["id"] in {"CALENDAR_DAY_OFFSET","CLOCK_MINUTE_OFFSET","ELAPSED_MINUTES"}]
    promotions = []
    for node in nodes:
        op = node["id"]
        if op == "DIVIDE": promotions.append("DIVIDE_TO_NUMBER")
        elif op == "UNIT_CONVERSION": promotions.append("UNIT_CONVERSION_TO_NUMBER")
        elif op in {"ADD","SUBTRACT","MULTIPLY","SUM"}:
            args = node["arguments"]
            types = [resolve(x)[0] for x in args.get("operands", list(args.values()))]
            promotions.append("INTEGER_ONLY" if set(types) == {"INTEGER"} else "NUMBER_ONLY" if set(types) == {"NUMBER"} else "MIXED_TO_NUMBER")
        else: promotions.append("NOT_APPLICABLE")
    family = derive_family(metadata)
    slot_id = slot["slot_id"]
    if not slot_id.startswith(family + "-"):
        raise ValueError("profile_slot_family")
    allocation = contract["subtype_allocation_contract"]
    allocated = next(x for x in allocation["slot_rows"][family] if x["slot_id"]==slot_id)
    domain_classes = {"slot_domain":allocated["domain"]}
    for name in ("secondary_temporal_domains","field_typing_for_numeric_slots","numeric_result_sign_coverage","comparison_pair_types","entity_selected_index"):
        if slot_id in allocation.get(name,{}):
            domain_classes[name]=allocation[name][slot_id]
    if slot_id=="E1-05":domain_classes["edge_temporal_domain"]=allocation["edge_temporal_domain"][slot["risk_round"]]
    if slot_id=="E3-05":domain_classes["unit_conversion_assignment"]=allocation["unit_conversion_assignment"][f"{slot.get('phase','A')}:{slot['risk_round']}"]
    rows = [row for row, slots in allocation["composed_rows"].items() if slot_id in slots]
    output = sorted(fixture["output_fields"], key=lambda x:json.dumps([x["schema_type"],derive_output_role(x,nodes)],separators=(",",":")).encode())
    operand_type_sequences=[]
    for node in nodes:
        if node["id"]=="ENTITY_FIELD_BIND":
            source_schema=next(x["schema_type"] for x in fixture["source_fact_records"] if x["field_identifier"]==node["arguments"]["source_field"]["value"])
            operand_type_sequences.append([parse_schema_type(source_schema,contract["schema_type_contract"])["semantic_tag"],"STRING","STRING"])
        else:
            catalog=next(x for x in contract["operation_definition_contract"]["catalog"] if x["id"]==node["id"])
            values=[raw for name in catalog["placeholders"] if name!="target" for raw in (node["arguments"][name] if isinstance(node["arguments"][name],list) else [node["arguments"][name]])]
            operand_type_sequences.append([resolve(x)[0] for x in values])
    profile = {
        "primary_family":family, "composed_quota_row":rows[0] if rows else "NONE",
        "secondary_features":derive_features(metadata), "operation_ids":operations,
        "conversion_ids":[x.get("conversion_id","NONE") for x in nodes],
        "source_schema_sequence":sorted((x["schema_type"] for x in fixture["source_fact_records"]),key=lambda x:x.encode()),
        "output_schema_sequence":[x["schema_type"] for x in output],
        "operation_result_semantic_types":[derived[x["target"]]["semantic_type"] for x in nodes],
        "numeric_promotion_classes":promotions,
        "comparison_operator":comparison[0]["id"] if comparison else "NONE",
        "comparison_operand_type_pair":[resolve(comparison[0]["arguments"][name])[0] for name in ("left","right")] if comparison else [],
        "boundary_relation":boundary, "temporal_operation":temporal_nodes[0]["id"] if temporal_nodes else "NONE",
        "temporal_boundary_pattern":temporal, "explicit_absence":is_e7,
        "entity_count":len(entities), "entity_selector_role":entities[0]["selector_role"] if entities else "NONE",
        "output_role_sequence":[derive_output_role(x,nodes) for x in output],
        "consequence_risk":slot["risk_round"], "field_count":len(output), "operation_node_count":len(nodes),
        "subtype_slot":slot_id, "domain_classes":domain_classes,
        "operation_operand_semantic_types":operand_type_sequences,
    }
    keys = contract["reserve_equivalence_contract"]["profile_exact_keys_in_order"]
    if list(profile) != keys:
        raise ValueError("profile_keys_or_order")
    return json.dumps(profile, ensure_ascii=True, separators=(",", ":")).encode()


def validate_v7(contract: dict[str, Any], checks: list[str]) -> None:
    lex = contract["lexical_neutrality_contract"]
    for vector in lex["validation_vectors"]:
        actual = "VALID" if lexical_atom_valid(vector["value"], vector["kind"], lex, vector.get("phase")) else "AUTHORING_ERROR"
        require(actual == vector["expected"], f"lexical:{vector['kind']}:{vector['value']}", checks)
    for phase, catalog in lex["record_type_catalog_by_phase"].items():
        names = [catalog[family] for family in range(7) for _ in range(5)]
        require(len(names) == 35 and all(names.count(x) == 5 for x in catalog), f"record_type_balance:{phase}", checks)
    require(set(lex["record_type_catalog_by_phase"]["A"]).isdisjoint(lex["record_type_catalog_by_phase"]["B"]), "record_type_disjoint_pools", checks)
    ordinals = [1 + phase + risk + slot for phase in (0,84) for risk in (0,35) for slot in range(35)]
    ordinals += [71 + phase + risk + family for phase in (0,84) for risk in (0,7) for family in range(7)]
    require(sorted(ordinals) == list(range(1,169)), "168_unique_primary_reserve_lexical_ordinals", checks)
    schema, operation, semantics = contract["schema_type_contract"], contract["operation_definition_contract"], contract["operation_semantics_contract"]
    entity_contract = contract["entity_population_contract"]

    # These objects are disposable mechanical test vectors, never scored corpus items.
    def field(name: str, kind: str, schema_type: str, source: str | None = None, producer: str | None = None) -> dict[str, Any]:
        return dict(name=name,schema_type=schema_type,required=True,binding_kind=kind,source_field=source,producer_target=producer,label_removal=False,absence_capable=kind=="EXPLICIT_ABSENCE")
    def fact(name: str, schema_type: str, kind: str, value: str, entity: str | None = None) -> dict[str, Any]:
        return dict(template_id="VALUE",field_identifier=name,schema_type=schema_type,value=dict(kind=kind,value=value),entity_selector_value=entity)
    def test_fixture(value: dict[str, Any], expected: str, name: str) -> None:
        try:
            if value["operation_nodes"]:
                validate_fixture_semantics(value,schema,operation,semantics,entity_contract)
            else:
                validate_e7_fixture(value,contract)
        except (ValueError,KeyError,ArithmeticError,TypeError): actual="AUTHORING_ERROR"
        else: actual="VALID"
        require(actual==expected,name,checks)
    base = {
        "operation_nodes":[dict(id="ENTITY_FIELD_BIND",target="d001_01",arguments={"source_field":dict(kind="field_identifier",value="f001_02"),"selector_field":dict(kind="field_identifier",value="f001_01"),"selector_value":dict(kind="entity_selector_literal",value="Entity 001 A")})],
        "output_fields":[field("d001_01","OPERATION_TARGET","integer",producer="d001_01")],
        "entities":[dict(selector_value=f"Entity 001 {x}",selector_role="IDENTIFIER") for x in "AB"],
        "source_fact_records":[item for i,x in enumerate("AB") for item in (fact("f001_01","string","entity_selector_literal",f"Entity 001 {x}",f"Entity 001 {x}"),fact("f001_02","integer","integer_literal",str(i+2),f"Entity 001 {x}"))],
        "gold_values":{"d001_01":2},
    }
    for count,role in [(2,"IDENTIFIER"),(3,"ATTRIBUTE"),(2,"EVENT_ROLE")]:
        value=copy.deepcopy(base)
        for x in value["entities"]:x["selector_role"]=role
        if count==3:
            value["entities"].append(dict(selector_value="Entity 001 C",selector_role=role))
            value["source_fact_records"] += [fact("f001_01","string","entity_selector_literal","Entity 001 C","Entity 001 C"),fact("f001_02","integer","integer_literal","4","Entity 001 C")]
        test_fixture(value,"VALID",f"entity_complete:{count}:{role}")
        validate_lexical_fixture(value,contract,1)
        require(True,f"lexical_entity_population:{count}:{role}",checks)
    variants = {}
    for key,index in [("missing_nonselected_source",3),("missing_nonselected_selector",2),("only_selected_has_source",3),("only_selected_has_selector",2)]:
        v=copy.deepcopy(base);v["source_fact_records"].pop(index);variants[key]=v
    v=copy.deepcopy(base);v["source_fact_records"][3]["schema_type"]="number";variants["mismatched_source_schema"]=v
    v=copy.deepcopy(base);v["source_fact_records"][2]["schema_type"]="option_a|option_b";variants["mismatched_selector_schema"]=v
    v=copy.deepcopy(base);v["entities"][1]["selector_value"]="Entity 001 A";variants["duplicate_selector_values"]=v
    v=copy.deepcopy(base);v["source_fact_records"][2]["value"]["value"]="Entity 001 A";variants["metadata_fact_mismatch"]=v
    v=copy.deepcopy(base);v["source_fact_records"].append(copy.deepcopy(v["source_fact_records"][3]));variants["duplicate_source_fact"]=v
    v=copy.deepcopy(base);v["source_fact_records"].append(fact("f001_02","integer","integer_literal","5"));variants["nonentity_source_duplicate"]=v
    v=copy.deepcopy(base);v["operation_nodes"][0]["arguments"]["selector_value"]["value"]="Entity 001 C";variants["selected_entity_absent"]=v
    v=copy.deepcopy(base);v["source_fact_records"].append(fact("f001_02","integer","integer_literal","5","Entity 001 C"));variants["unknown_entity_fact"]=v
    for name,v in variants.items():test_fixture(v,"AUTHORING_ERROR",f"entity_reject:{name}")
    for vector in semantics["exact_schema_identity_for_preserving_operations"]["test_vectors"]:
        v=copy.deepcopy(base)
        for source in v["source_fact_records"]:
            if source["field_identifier"]=="f001_02":source.update(schema_type=vector["source"],value=dict(kind="enum_literal",value="option_a"))
        v["output_fields"][0]["schema_type"]=vector["output"]
        v["gold_values"]["d001_01"]="option_a"
        test_fixture(v,vector["expected"],f"entity_enum_identity:{vector['source']}:{vector['output']}")
        c={"operation_nodes":[dict(id="EXACT_COPY",target="d001_01",arguments={"source_field":dict(kind="field_identifier",value="f001_01")})],"entities":[],"source_fact_records":[fact("f001_01",vector["source"],"enum_literal","option_a")],"output_fields":[field("d001_01","OPERATION_TARGET",vector["output"],producer="d001_01")],"gold_values":{"d001_01":"option_a"}}
        test_fixture(c,vector["expected"],f"copy_enum_identity:{vector['source']}:{vector['output']}")
    e7={"operation_nodes":[],"entities":[],"source_fact_records":[dict(template_id="EXPLICIT_ABSENCE",field_identifier="f001_01",schema_type="provided|not_provided",value=None,entity_selector_value=None),fact("f001_02","integer","integer_literal","3"),fact("f001_03","string","string_literal","label_001_01")],"output_fields":[field("f001_01","EXPLICIT_ABSENCE","provided|not_provided",source="f001_01"),field("f001_02","SOURCE_COPY","integer",source="f001_02"),field("f001_03","SOURCE_COPY","string",source="f001_03")],"gold_values":{"f001_01":"not_provided","f001_02":3,"f001_03":"label_001_01"}}
    test_fixture(e7,"VALID","e7_integrated_valid")
    validate_lexical_fixture(e7,contract,1)
    require(True,"e7_generated_lexical_shape",checks)
    for name,mutation in [("semantic_source_name","correct_answer"),("wrong_fixture_source_name","f002_01")]:
        v=copy.deepcopy(e7);v["source_fact_records"][0]["field_identifier"]=mutation
        try:validate_lexical_fixture(v,contract,1)
        except ValueError:checks.append(f"lexical_fixture_reject:{name}")
        else:raise AssertionError(f"lexical_fixture_accept:{name}")
    for change in ["schema","gold","two_absence","few_supports","nodes","binding","missing_source"]:
        v=copy.deepcopy(e7)
        if change=="schema":v["output_fields"][0]["schema_type"]="option_a|option_b"
        elif change=="gold":v["gold_values"]["f001_01"]="provided"
        elif change=="two_absence":v["output_fields"][1]=field("f001_02","EXPLICIT_ABSENCE","provided|not_provided",source="f001_02")
        elif change=="few_supports":v["output_fields"].pop()
        elif change=="nodes":v["operation_nodes"]=copy.deepcopy(base["operation_nodes"])
        elif change=="binding":v["output_fields"][1]["source_field"]="f001_04"
        else:v["source_fact_records"].pop()
        test_fixture(v,"AUTHORING_ERROR",f"e7_integrated_reject:{change}")
    domains = [
        ("CALENDAR_DAY_OFFSET","date","date_literal","2028-02-28","days",0,"YYYY-MM-DD","2028-02-28","VALID"),
        ("CALENDAR_DAY_OFFSET","date","date_literal","2028-02-28","days",1,"YYYY-MM-DD","2028-02-29","VALID"),
        ("CALENDAR_DAY_OFFSET","date","date_literal","2028-01-01","days",366,"YYYY-MM-DD","2029-01-01","VALID"),
        ("CALENDAR_DAY_OFFSET","date","date_literal","2028-01-01","days",367,"YYYY-MM-DD","2029-01-02","AUTHORING_ERROR"),
        ("CALENDAR_DAY_OFFSET","date","date_literal","2028-01-01","days",-1,"YYYY-MM-DD","2027-12-31","AUTHORING_ERROR"),
        ("CLOCK_MINUTE_OFFSET","time","time_literal","00:00","minutes",0,"HH:MM","00:00","VALID"),
        ("CLOCK_MINUTE_OFFSET","time","time_literal","00:00","minutes",1439,"HH:MM","23:59","VALID"),
        ("CLOCK_MINUTE_OFFSET","time","time_literal","00:00","minutes",1440,"HH:MM","00:00","AUTHORING_ERROR"),
        ("CLOCK_MINUTE_OFFSET","time","time_literal","00:00","minutes",-1,"HH:MM","23:59","AUTHORING_ERROR"),
        ("CLOCK_MINUTE_OFFSET","time","time_literal","23:45","minutes",30,"HH:MM","00:15","VALID"),
    ]
    for op,source_key,kind,start,offset_key,offset,out_schema,gold,expected in domains:
        v={"operation_nodes":[dict(id=op,target="d001_01",arguments={source_key:dict(kind=kind,value=start),offset_key:dict(kind="integer_literal",value=str(offset))})],"source_fact_records":[],"entities":[],"output_fields":[field("d001_01","OPERATION_TARGET",out_schema,producer="d001_01")],"gold_values":{"d001_01":gold}}
        test_fixture(v,expected,f"domain:{op}:{start}:{offset}")
    for start,end,gold in [("08:00","09:00",60),("23:30","00:15",45),("12:00","12:00",0),("00:01","00:00",1439)]:
        v={"operation_nodes":[dict(id="ELAPSED_MINUTES",target="d001_01",arguments={"start":dict(kind="time_literal",value=start),"end":dict(kind="time_literal",value=end)})],"source_fact_records":[],"entities":[],"output_fields":[field("d001_01","OPERATION_TARGET","integer",producer="d001_01")],"gold_values":{"d001_01":gold}}
        test_fixture(v,"VALID",f"elapsed_domain:{start}:{end}")
    for left,right,gold,expected in [(10,4,"2.5","VALID"),(4,2,"2.0","VALID"),(2,6,"0.3","AUTHORING_ERROR"),(0,5,"0.0","VALID"),(10**80+1,2,str((10**80)//2)+".5","VALID")]:
        v={"operation_nodes":[dict(id="DIVIDE",target="d001_01",arguments={"dividend":dict(kind="integer_literal",value=str(left)),"divisor":dict(kind="integer_literal",value=str(right))})],"source_fact_records":[],"entities":[],"output_fields":[field("d001_01","OPERATION_TARGET","number",producer="d001_01")],"gold_values":{"d001_01":gold}}
        test_fixture(v,expected,f"exact_divide:{left}:{right}")
    require(exact_decimal_from_fraction(Fraction(10**80+1,2)) == str((10**80)//2)+".5","large_divide_no_decimal_context_rounding",checks)
    allocation=contract["subtype_allocation_contract"]
    all_slots=[x["slot_id"] for rows in allocation["slot_rows"].values() for x in rows]
    require(len(all_slots)==35 and len(set(all_slots))==35,"subtype_35_unique_slots",checks)
    for family,rows in allocation["slot_rows"].items():
        require([x["slot_id"] for x in rows]==[f"{family}-{i:02d}" for i in range(1,6)],f"subtype_five:{family}",checks)
    require([x["operation_shape"] for x in allocation["slot_rows"]["E3"]]==["ADD","SUBTRACT","SUM","DIVIDE>EXACT_COPY","UNIT_CONVERSION>EXACT_COPY"],"numeric_subtypes_exact",checks)
    require(set(allocation["numeric_promotion_coverage"])=={"INTEGER_ONLY","NUMBER_ONLY","MIXED_TO_NUMBER","DIVIDE_TO_NUMBER","UNIT_CONVERSION_TO_NUMBER"},"promotion_coverage_exact",checks)
    require(set(allocation["comparison_operator_coverage"])=={"GT","GTE","LT","LTE","EQ"},"comparison_operators_exact",checks)
    require(set(allocation["comparison_boundary_coverage"])=={"BELOW","EQUAL","ABOVE"},"comparison_boundaries_exact",checks)
    composed=[s for slots in allocation["composed_rows"].values() for s in slots]
    require(len(composed)==8 and len(set(composed))==8,"subtype_eight_distinct_composed_slots",checks)
    support_shapes=[x["domain"] for x in allocation["slot_rows"]["E7"]]
    require(len({json.dumps(x) for x in support_shapes})==5 and all(len(x)>=2 for x in support_shapes),"e7_five_support_schema_shapes",checks)
    for shape in support_shapes:
        require(all(parse_schema_type(x,schema) for x in shape),f"e7_support_schema_valid:{shape}",checks)
    # Profile equality is checked as bytes from canonical typed fixtures, not selected fields.
    numeric=copy.deepcopy(semantics["validation_vectors"][0]["fixture"])
    slot={"slot_id":"E3-01","risk_round":"R2","domain":"INTEGER_ONLY"}
    a=reserve_profile_bytes(numeric,slot,contract)
    require(a==reserve_profile_bytes(copy.deepcopy(numeric),slot,contract),"reserve_profile_identical_bytes",checks)
    fabricated=copy.deepcopy(slot);fabricated["domain"]="author-selected arbitrary domain"
    require(a==reserve_profile_bytes(numeric,fabricated,contract),"reserve_domain_derived_from_frozen_matrix",checks)
    n=copy.deepcopy(numeric)
    for x in n["source_fact_records"]:x["schema_type"]="number"
    n["output_fields"][0]["schema_type"]="number"
    b=reserve_profile_bytes(n,slot,contract)
    require(a!=b,"reserve_profile_integer_number_mismatch",checks)
    m=copy.deepcopy(numeric);m["source_fact_records"][1]["schema_type"]="number";m["output_fields"][0]["schema_type"]="number"
    require(a!=reserve_profile_bytes(m,slot,contract),"reserve_profile_promotion_mismatch",checks)
    absent=copy.deepcopy(e7)
    absent["source_fact_records"][2]["schema_type"]="integer"
    absent["source_fact_records"][2]["value"]={"kind":"integer_literal","value":"4"}
    absent["output_fields"][2]["schema_type"]="integer"
    absent["gold_values"]["f001_03"]=4
    absent_slot={"slot_id":"E7-01","risk_round":"R2"}
    moved=copy.deepcopy(absent)
    moved["source_fact_records"]=[moved["source_fact_records"][1],moved["source_fact_records"][0],moved["source_fact_records"][2]]
    mapping={fact["field_identifier"]:f"f001_{index:02d}" for index,fact in enumerate(moved["source_fact_records"],1)}
    for source in moved["source_fact_records"]:source["field_identifier"]=mapping[source["field_identifier"]]
    for output in moved["output_fields"]:
        output["name"]=mapping[output["name"]];output["source_field"]=mapping[output["source_field"]]
    moved["output_fields"].sort(key=lambda x:x["name"])
    moved["gold_values"]={mapping[k]:v for k,v in moved["gold_values"].items()}
    validate_e7_fixture(moved,contract);validate_lexical_fixture(moved,contract,1)
    require(reserve_profile_bytes(absent,absent_slot,contract)==reserve_profile_bytes(moved,absent_slot,contract),"e7_reserve_profile_preserves_types_across_frozen_order",checks)
    require(fingerprint_bytes({"fixture":absent},operation)!=fingerprint_bytes({"fixture":moved},operation),"e7_typed_layout_distinguishes_primary_reserve",checks)
    conversion = {
        "operation_nodes":[dict(id="UNIT_CONVERSION",conversion_id="HOURS_TO_MINUTES",target="d001_01",arguments={"source":dict(kind="field_identifier",value="f001_01")}),dict(id="EXACT_COPY",target="d001_02",arguments={"source_field":dict(kind="derived_field_identifier",value="d001_01")})],
        "source_fact_records":[fact("f001_01","number","decimal_literal","2.0")],"entities":[],
        "output_fields":[field("d001_02","OPERATION_TARGET","number",producer="d001_02")],"gold_values":{"d001_02":"120.0"},
    }
    cs={"slot_id":"E3-05","risk_round":"R2","domain":"UNIT_CONVERSION_TO_NUMBER"}
    c1=reserve_profile_bytes(conversion,cs,contract)
    conversion["operation_nodes"][0]["conversion_id"]="KILOGRAMS_TO_GRAMS";conversion["gold_values"]["d001_02"]="2000.0"
    require(c1!=reserve_profile_bytes(conversion,cs,contract),"reserve_profile_derived_conversion_id_mismatch",checks)
    for vector in contract["reserve_equivalence_contract"]["test_vectors"]:
        require((json.dumps(vector["left"],sort_keys=True,separators=(",",":"))==json.dumps(vector["right"],sort_keys=True,separators=(",",":")))==vector["expected"],f"reserve_profile_differential:{vector['id']}",checks)
    # Field/derived references in atom tuples use their resolved schema/result tags.
    atoms=extract_date_number_atoms(m,operation,schema,semantics,entity_contract)
    require([x[1] for x in atoms if x[0]=="OPERATION_ARGUMENT"]==["INTEGER","NUMBER"],"operation_atom_resolved_source_types",checks)
    chained=copy.deepcopy(numeric)
    chained["operation_nodes"].append(dict(id="EXACT_COPY",target="d001_02",arguments={"source_field":dict(kind="derived_field_identifier",value="d001_01")}))
    chained["output_fields"]=[field("d001_02","OPERATION_TARGET","integer",producer="d001_02")];chained["gold_values"]={"d001_02":5}
    atoms=extract_date_number_atoms(chained,operation,schema,semantics,entity_contract)
    require([x for x in atoms if x[0]=="OPERATION_ARGUMENT"][-1]==["OPERATION_ARGUMENT","INTEGER","5"],"operation_atom_resolved_upstream_type",checks)
    reversed_chain=copy.deepcopy(chained);reversed_chain["operation_nodes"].reverse()
    require(fingerprint_bytes({"fixture":chained},operation)==fingerprint_bytes({"fixture":reversed_chain},operation),"typed_fingerprint_reversed_numeric_chain",checks)
    for atoms_input in ["correct_answer","expected_total","larger_amount"]:
        for kind in ["field_identifier","derived_field_identifier","enum_literal","entity_selector_literal","string_literal"]:
            try:render_operand({"kind":kind,"value":atoms_input},operation["placeholder_type_system"])
            except ValueError:checks.append(f"render_reject_coaching:{kind}:{atoms_input}")
            else:raise AssertionError(f"render_accept_coaching:{kind}:{atoms_input}")


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
    require(contract["schema_version"] == "g-extract1.design-candidate.v7", "schema_v7", checks)
    require(contract["experiment"]["status"] == "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_7", "status_v7", checks)
    for field in ("implemented", "blueprint_authorized", "fixture_authoring_authorized", "execution_authorized"):
        require(contract["experiment"][field] is False, f"authority_false:{field}", checks)
    require(contract["experiment"]["provider_generation_calls"] == 0, "provider_calls_zero", checks)
    require(contract["experiment"]["belief_effects"] == "none", "belief_effects_none", checks)
    validate_v7(contract, checks)

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

    schema_contract = contract["schema_type_contract"]
    require(schema_contract["contract_id"] == "g-extract1.schema-types.v1", "schema_contract_v1", checks)
    require(schema_contract["primitive_schema_tokens"] == ["string", "number", "integer", "boolean", "YYYY-MM-DD", "HH:MM"], "historical_schema_tokens", checks)
    require(schema_contract["aliases_prohibited"] == ["date", "time", "bool", "int", "float"], "schema_aliases_prohibited", checks)
    for vector in schema_contract["test_vectors"]:
        try:
            info = parse_schema_type(vector["schema"], schema_contract)
        except ValueError:
            require(vector.get("expected_error") == "AUTHORING_ERROR", f"schema_reject:{vector['schema']}", checks)
        else:
            require(info["semantic_tag"] == vector["expected_tag"], f"schema_accept:{vector['schema']}", checks)
    require(schema_contract["exact_answer_tag_mapping"] == {
        "string": "STRING", "number": "NUMBER", "integer": "INTEGER", "boolean": "BOOLEAN",
        "YYYY-MM-DD": "DATE", "HH:MM": "TIME", "finite_enum": "ENUM",
    }, "schema_tag_mapping", checks)

    operation = contract["operation_definition_contract"]
    require(operation["contract_id"] == "g-extract1.operation-definitions.v4", "operation_contract_v4", checks)
    require(operation["minimum_operation_nodes_per_fixture"] == 0, "operation_min_nodes", checks)
    require(operation["maximum_operation_nodes_per_fixture"] == 2, "operation_max_nodes", checks)
    require(operation["sum_operands"] == {
        "minimum": 2, "maximum": 4,
        "allowed_kinds": ["field_identifier", "derived_field_identifier", "integer_literal", "decimal_literal"],
        "order": "array order is immutable", "two": "A and B",
        "three_or_four": "comma-space between earlier operands and ', and ' before final operand",
    }, "sum_contract", checks)
    required_kinds = {
        "field_identifier", "derived_field_identifier", "collection_identifier", "integer_literal",
        "decimal_literal", "date_literal", "time_literal", "boolean_literal", "string_literal",
        "entity_selector_literal", "enum_literal",
    }
    require(set(operation["placeholder_type_system"]) == required_kinds, "placeholder_kind_catalog", checks)
    catalog = {row["id"]: row for row in operation["catalog"]}
    require("COUNT" not in catalog, "count_removed", checks)
    require(catalog["UNIT_CONVERSION"]["argument_kinds"]["source"] == ["field_identifier"], "unit_source_kind", checks)
    require(catalog["ENTITY_FIELD_BIND"]["argument_kinds"]["selector_value"] == ["entity_selector_literal"], "selector_kind", checks)
    for row in operation["catalog"]:
        expected_arguments = set(row["placeholders"]) - {"target"}
        require(set(row["argument_kinds"]) == expected_arguments, f"argument_kind_keys:{row['id']}", checks)
    for vector in operation["rendering_test_vectors"]:
        require(render_subject(vector, operation) == vector["expected_subject"], f"render:{vector['id']}", checks)
    require(ids(operation["rendering_test_vectors"]) == [
        "negative_integer", "decimal", "date", "time", "e7_absence", "sum_two", "sum_three",
        "sum_four", "quoted_selector", "escaped_entity_selector", "two_node_dependency",
    ], "render_vector_ids", checks)
    for kind, rejected in (
        ("integer_literal", "-0"), ("integer_literal", "+5"), ("integer_literal", "05"),
        ("decimal_literal", "5.00"), ("decimal_literal", "0.50"),
        ("decimal_literal", "-0.50"), ("decimal_literal", "-0.0"),
    ):
        try:
            render_operand({"kind": kind, "value": rejected}, operation["placeholder_type_system"])
        except ValueError:
            checks.append(f"reject_noncanonical:{kind}:{rejected}")
        else:
            raise AssertionError(f"accepted_noncanonical:{kind}:{rejected}")
    one_operand_sum = {
        "record_type": "invoice",
        "nodes": [{"id": "SUM", "target": "d001_01", "arguments": {"operands": [{"kind": "field_identifier", "value": "f001_01"}]}}],
    }
    try:
        render_subject(one_operand_sum, operation)
    except ValueError:
        checks.append("reject_sum_below_minimum")
    else:
        raise AssertionError("accepted_sum_below_minimum")
    require(operation["historical_absence_sentinel"] == "not_provided", "historical_sentinel", checks)
    require(operation["historical_absence_schema"] == "provided|not_provided", "historical_absence_schema", checks)
    baseline = contract["baseline_binding"]
    rendered_subjects = {vector["id"]: render_subject(vector, operation) for vector in operation["rendering_test_vectors"]}
    for vector in operation["full_prompt_test_vectors"]:
        require(rendered_subjects[vector["render_vector_id"]] == vector["subject"], f"full_prompt_subject:{vector['id']}", checks)
        prompt = assemble_prompt(vector["subject"], baseline)
        require(prompt == vector["expected_prompt"], f"full_prompt:{vector['id']}", checks)
        require(hashlib.sha256(prompt.encode("utf-8")).hexdigest() == vector["sha256"], f"full_prompt_sha:{vector['id']}", checks)
        require(".. Copy names" not in prompt, f"no_double_period:{vector['id']}", checks)
    require(not operation["free_form_operation_instruction_allowed"], "no_free_form_operations", checks)

    semantics = contract["operation_semantics_contract"]
    require(semantics["contract_id"] == "g-extract1.operation-semantics.v2", "operation_semantics_v2", checks)
    require(set(semantics["operations"]) == set(catalog), "operation_semantics_complete", checks)
    require(
        set(semantics["unit_conversion_semantics"]) - {"source_unit_binding"}
        == {row["id"] for row in operation["unit_conversion_catalog"]},
        "unit_semantics_complete", checks,
    )
    require(all("gold" in rule for rule in semantics["operations"].values()), "operation_gold_rules_complete", checks)
    require(semantics["numeric_promotion"]["ADD_SUBTRACT_MULTIPLY_SUM"] == "all INTEGER -> INTEGER; any NUMBER -> NUMBER", "numeric_promotion", checks)
    require(semantics["operations"]["DIVIDE"]["required_output_schema"] == "number", "divide_schema_number", checks)
    require("nonzero" in semantics["operations"]["DIVIDE"]["domain"], "divide_nonzero_rule", checks)
    require(semantics["operations"]["ELAPSED_MINUTES"]["required_output_schema"] == "integer", "elapsed_integer", checks)
    require("equal times equal 0" in semantics["operations"]["ELAPSED_MINUTES"]["domain"], "elapsed_equal_zero", checks)
    require("0..366" in semantics["operations"]["CALENDAR_DAY_OFFSET"]["domain"], "calendar_offset_domain", checks)
    require("0..1439" in semantics["operations"]["CLOCK_MINUTE_OFFSET"]["domain"], "clock_offset_domain", checks)
    for vector in semantics["validation_vectors"]:
        try:
            validate_fixture_semantics(vector["fixture"], schema_contract, operation, semantics, contract["entity_population_contract"])
        except (ValueError, KeyError, ArithmeticError):
            actual = "AUTHORING_ERROR"
        else:
            actual = "VALID"
        require(actual == vector["expected"], f"operation_semantics:{vector['id']}", checks)

    families = contract["family_assignment_contract"]
    require(families["contract_id"] == "g-extract1.family-assignment.v4", "family_contract_v4", checks)
    require(families["metadata_derived_not_author_selected"], "metadata_not_author_selected", checks)
    expected_fields = {
        "unresolved_required_field_count", "unknown_sentinel_available", "entity_record_count",
        "entity_disambiguation_required", "terminal_operation", "source_operation_types",
        "output_role_types", "threshold_operator", "temporal_operation", "aggregation_operation",
        "entity_selector_role", "source_fact_sequence", "direct_copy_only",
    }
    require(set(families["metadata_schema"]) == expected_fields, "family_metadata_fields", checks)
    require(all("derivation" in rule for rule in families["metadata_schema"].values()), "all_family_derivations", checks)
    require(set(families["secondary_feature_derivations"]) == set(families["allowed_secondary_features"]), "all_secondary_derivations", checks)
    require([row["family"] for row in families["priority_first_match"]] == ["E7", "E5", "E4", "E1", "E2", "E3", "E6"], "family_precedence", checks)
    require(
        families["canonical_output_field_contract"]["exact_keys"]
        == ["name", "schema_type", "required", "binding_kind", "source_field", "producer_target", "label_removal", "absence_capable"],
        "canonical_output_field_keys", checks,
    )
    require(
        families["fact_record_contract"]["exact_keys"]
        == ["template_id", "field_identifier", "schema_type", "value", "entity_selector_value"],
        "canonical_source_fact_keys", checks,
    )
    for vector in families["derivation_test_vectors"]:
        expected_terminal = vector["operation_ids"][-1] if vector["operation_ids"] else "NONE"
        require(vector["terminal_operation"] == expected_terminal, f"terminal_derivation:{vector['id']}", checks)
        expected_sources = sorted(set(vector["operation_ids"][:-1]), key=lambda item: item.encode("utf-8")) if vector["operation_ids"] else []
        require(vector["source_operation_types"] == expected_sources, f"source_operation_derivation:{vector['id']}", checks)
        require(derive_family(vector) == vector["expected_family"], f"family_vector:{vector['id']}", checks)
        require(derive_features(vector) == vector["expected_features"], f"feature_vector:{vector['id']}", checks)
    for vector in families["e7_graph_contract"]["test_vectors"]:
        require(validate_e7_graph(vector) == vector["expected"], f"e7_graph:{vector['id']}", checks)
    for vector in families["fact_role_test_vectors"]:
        require(derive_fact_role(vector) == vector["expected"], f"fact_role:{vector['id']}", checks)
    for vector in families["output_role_test_vectors"]:
        validate_output_field_shape(vector["field"], schema_contract)
        role = derive_output_role(vector["field"], vector["nodes"])
        require(role == vector["expected"], f"output_role:{vector['id']}", checks)
        require(role in parse_schema_type(vector["field"]["schema_type"], schema_contract)["allowed_output_roles"], f"output_role_schema:{vector['id']}", checks)
    base_field = dict(families["output_role_test_vectors"][0]["field"])
    invalid_fields: dict[str, dict[str, Any]] = {}
    missing_key = dict(base_field)
    missing_key.pop("required")
    invalid_fields["missing_key"] = missing_key
    extra_key = dict(base_field)
    extra_key["unexpected"] = None
    invalid_fields["extra_key"] = extra_key
    unknown_schema = dict(base_field)
    unknown_schema["schema_type"] = "date"
    invalid_fields["unknown_schema"] = unknown_schema
    bad_source_copy = dict(base_field)
    bad_source_copy["producer_target"] = "d01"
    invalid_fields["source_copy_with_producer"] = bad_source_copy
    bad_operation_target = dict(families["output_role_test_vectors"][2]["field"])
    bad_operation_target["source_field"] = "f01"
    invalid_fields["operation_target_with_source"] = bad_operation_target
    for label, field in invalid_fields.items():
        try:
            validate_output_field_shape(field, schema_contract)
        except ValueError:
            checks.append(f"reject_output_field:{label}")
        else:
            raise AssertionError(f"accepted_output_field:{label}")
    for vector in families["fact_rendering_test_vectors"]:
        require(
            render_fact(vector["record"], operation["placeholder_type_system"], schema_contract) == vector["expected"],
            f"fact_render:{vector['id']}", checks,
        )
    source_fact = dict(families["fact_rendering_test_vectors"][0]["record"])
    bad_fact_schema = dict(source_fact)
    bad_fact_schema["schema_type"] = "YYYY-MM-DD"
    try:
        render_fact(bad_fact_schema, operation["placeholder_type_system"], schema_contract)
    except ValueError:
        checks.append("reject_source_fact_schema_mismatch")
    else:
        raise AssertionError("accepted_source_fact_schema_mismatch")
    safety = families["fact_record_contract"]["content_safety_contract"]
    for vector in safety["test_vectors"]:
        if vector["kind"] in {"string", "entity"}:
            safe_kind = "string_literal" if vector["kind"] == "string" else "entity_selector_literal"
            actual = "VALID" if content_is_safe(vector["value"], safety, safe_kind) else "AUTHORING_ERROR"
            require(actual == vector["expected"], f"content_safety:{vector['value']}", checks)

    composed = contract["composed_feature_requirements"]
    require(ids(composed["requirements"]) == ["C1", "C2", "C3", "C4"], "composed_ids", checks)
    require(sum(row["minimum_distinct_fixtures"] for row in composed["requirements"]) == 8, "composed_total", checks)
    c3 = composed["requirements"][2]
    require(c3["operation_graph_shape"] == ["NUMERIC_OPERATION", "EXACT_COPY"], "c3_graph", checks)
    require(c3["sink_source_must_equal_first_target"], "c3_dependency", checks)

    ambiguity = contract["ambiguity_contract"]
    require(ambiguity["contract_id"] == "g-extract1.explicit-absence-scoring.v4", "explicit_absence_contract_v4", checks)
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
        duplicate, operational_valid, outcome, false_clean = classify_ambiguity(
            vector["raw_output"], provider_truncated=vector.get("provider_truncated", False),
            accepted_override=vector.get("operationally_accepted_override"),
        )
        accepted = vector.get("operationally_accepted_override", operational_valid)
        require(duplicate == vector["expected_duplicate_key_present"], f"duplicate:{vector['id']}", checks)
        require(operational_valid == vector["expected_operational_schema_valid"], f"operational_schema:{vector['id']}", checks)
        require(accepted == vector["expected_operationally_accepted"], f"operational_acceptance:{vector['id']}", checks)
        require(outcome == vector["expected_outcome"], f"ambiguity_outcome:{vector['id']}", checks)
        require(false_clean == vector["expected_false_clean"], f"ambiguity_false_clean:{vector['id']}", checks)
    require(ambiguity["phase_a_gate"]["required_observations"] == 10, "ambiguity_a_10", checks)
    require(ambiguity["phase_b_gate"]["required_observations"] == 5, "ambiguity_b_5", checks)

    exact = contract["exact_value_contract"]
    require(exact["operational_validator_unchanged"], "operational_validator_unchanged", checks)
    require(exact["semantic_parser_requirements"]["duplicate_key_makes_semantic_schema_invalid"], "duplicate_semantic_invalid", checks)
    require(exact["operational_semantic_disagreement_rule"] == "operationally accepted plus semantically invalid is false-clean", "false_clean_bridge", checks)

    contamination = contract["contamination_contract"]
    require(contamination["contract_id"] == "g-extract1.contamination.v4", "contamination_contract_v4", checks)
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
        if len(vector["fixture"]["operation_nodes"]) == 2:
            reversed_vector = json.loads(json.dumps(vector))
            reversed_vector["fixture"]["operation_nodes"].reverse()
            require(
                fingerprint_bytes(reversed_vector, operation) == vector["expected_bytes"],
                f"fingerprint_topological_order:{vector['id']}", checks,
            )
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
    reuse = contamination["exact_reuse_contract"]
    require(reuse["all_rules_apply_to_every_scope"], "reuse_all_scopes", checks)
    require(set(reuse["scope_names"]) == {"historical_new", "phase_a_phase_a", "phase_a_phase_b", "phase_b_phase_b", "scored_reserve", "reserve_reserve"}, "reuse_scope_names", checks)
    for vector in reuse["test_vectors"]:
        if "expected_answer_match" in vector:
            require((canonical_answer_bytes(vector["left"], schema_contract) == canonical_answer_bytes(vector["right"], schema_contract)) == vector["expected_answer_match"], f"reuse_answer:{vector['id']}", checks)
        if "expected_identity_reuse" in vector:
            require(identity_reuse(vector["left_atoms"], vector["right_atoms"]) == vector["expected_identity_reuse"], f"reuse_identity:{vector['id']}", checks)
        if "expected_tuple_match" in vector:
            require((date_number_tuple_bytes(vector["left_atoms"]) == date_number_tuple_bytes(vector["right_atoms"])) == vector["expected_tuple_match"], f"reuse_tuple:{vector['id']}", checks)
    for vector in reuse["fixture_tuple_extraction_vectors"]:
        if "fixture" in vector:
            require(
                extract_date_number_atoms(vector["fixture"], operation, schema_contract, semantics, contract["entity_population_contract"]) == vector["expected_atoms"],
                f"reuse_tuple_extract:{vector['id']}", checks,
            )
        else:
            observed = []
            for fixture in vector["fixtures"]:
                observed.append(extract_date_number_atoms(fixture, operation, schema_contract, semantics, contract["entity_population_contract"])[0][1:])
            require(observed == vector["expected_atoms_by_fixture"], f"reuse_tuple_extract:{vector['id']}", checks)
            require(date_number_tuple_bytes(observed[:1]) != date_number_tuple_bytes(observed[1:]), f"reuse_tuple_type_distinction:{vector['id']}", checks)

    reserve = contract["reserve_activation_contract"]
    require(reserve["contract_id"] == "g-extract1.reserve-activation.v4", "reserve_contract_v4", checks)
    require(reserve["total_reserve_slots"] == 2 * 2 * 7 == 28, "reserve_slot_count", checks)
    require(reserve["slot_id_format"] == "RESERVE:{phase}:{round}:{primary_family}", "reserve_slot_id", checks)
    require(not reserve["selection_pool_allowed"], "no_reserve_pool", checks)
    require(reserve["reserve_consumption_limit"] == 1, "reserve_single_consumption", checks)
    require("output_role_sequence" in reserve["required_match_dimensions"], "reserve_schema_role_match", checks)
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
    reductions = contract["phase_a_fixture_reduction_contract"]
    for vector in reductions["truth_vectors"]:
        all_value, any_value = reduce_repeats(vector["observations"])
        require(all_value == vector["all_repeats"], f"repeat_all:{vector['observations']}", checks)
        require(any_value == vector["any_repeat"], f"repeat_any:{vector['observations']}", checks)
    require(gates_a["family_semantic_floor"]["fixture_reduction"] == "both repeats semantically correct", "family_floor_repeat_reduction", checks)

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

    require(baseline["baseline_behavior_source_commit"] == "0feb1b092bcdb1b934f01a3ce9611c59fcd8fa28", "baseline_source_commit", checks)
    require(baseline["contract_id"] == "g-extract1.baseline-binding.v4", "baseline_contract_v4", checks)
    require(baseline["subject_rendered_only_by"] == "g-extract1.operation-definitions.v4", "catalog_only_subject", checks)
    require(baseline["double_period_before_copy_prohibited"], "double_period_prohibited", checks)
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
        "g-extract1.design-candidate.v7", "g-extract1.operation-definitions.v4",
        "g-extract1.schema-types.v1", "g-extract1.operation-semantics.v2",
        "g-extract1.family-assignment.v4", "g-extract1.contamination.v4",
        "g-extract1.explicit-absence-scoring.v4", "g-extract1.reserve-activation.v4",
        "g-extract1.lexical-neutrality.v1", "g-extract1.entity-population.v1",
        "g-extract1.reserve-equivalence.v1", "g-extract1.subtype-allocation.v1",
        "g-extract1.integrity-events.v2", "g-extract1.result-state-machine.v3",
        "POST_CONTACT_GOLD_DEFECT_DISCOVERED", "UNVERIFIABLE_INTERRUPTION_CHECKPOINT",
        "RESERVE:{phase}:{round}:{primary_family}", "2026-10-01", "5-3",
        "READY_FOR_G_EXTRACT1_DESIGN_REREVIEW_7", "does not prove scientific validity",
        "SOURCE_COPY", "explicit partial absence", "both repeats semantically correct",
    ]
    for literal in human_literals:
        require(literal in human, f"human_literal:{literal}", checks)
    match = re.search(r"<!-- V7_NORMATIVE_BEGIN -->\s*```json\s*(.*?)\s*```\s*<!-- V7_NORMATIVE_END -->", human, re.DOTALL)
    require(match is not None,"human_v7_normative_annex_present",checks)
    annex = json.loads(match.group(1))
    expected_annex = {name:contract[name] for name in ("lexical_neutrality_contract","entity_population_contract","reserve_equivalence_contract","subtype_allocation_contract")}
    expected_annex.update(
        source_contamination_atom_contract=contract["contamination_contract"]["exact_reuse_contract"]["date_number_tuple"],
        identity_atom_contract=contract["contamination_contract"]["exact_reuse_contract"]["identity_atom_derivation"],
        enum_schema_identity_contract=contract["operation_semantics_contract"]["exact_schema_identity_for_preserving_operations"],
        e7_integrated_shape_contract=contract["ambiguity_contract"]["integrated_fixture_shape_validation"],
        fingerprint_layout_contract=next(x for x in contract["contamination_contract"]["fingerprint"]["components"] if x["id"]=="source_fact_layout"),
        reserve_activation_contract=contract["reserve_activation_contract"],
    )
    require(set(annex)==set(expected_annex),"human_machine_v7_annex_exact_sections",checks)
    for name,value in expected_annex.items():
        require(annex[name]==value,f"human_machine_v7_normative_object:{name}",checks)
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
        "schema_version": "g-extract1.design-validation-report.v7",
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
