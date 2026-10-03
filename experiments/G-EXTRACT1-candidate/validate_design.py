from __future__ import annotations

import argparse
import ast
import itertools
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
import unicodedata
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HUMAN = HERE / "DESIGN_CANDIDATE.md"
MACHINE = HERE / "DESIGN_CANDIDATE.json"
REPORT = HERE / "DESIGN_VALIDATION_REPORT.json"
OUTPUT_FIELD_AMENDMENT_SUMMARY: dict[str, Any] = {}
SCAFFOLD_AUDIT: dict[str, Any] = {}
FRESHNESS_AMENDMENT_SUMMARY: dict[str, Any] = {}
WHOLE_ANSWER_AMENDMENT_SUMMARY: dict[str, Any] = {}
PROTECTED_BLUEPRINT_COMMIT = "3bf939ea3160596d89c64f1feef790477991cf8a"
PRESERVED_CORPUS_DIGESTS = {
    "corpus/AUTHORING_ATTEMPTS.json": "b9860b6bd4f662c46935773463bf6caf78035a1c2aa01c0b6a55e5100b9aa8da",
    "corpus/AUTHORING_CANDIDATES.json": "f575c8d86ca82f2c5ea7727404d0c8bbb5a72f7b472abfd244471edb3180d068",
    "corpus/AUTHORING_FEASIBILITY_REPORT.json": "8767a025c1123541cc858873aff41b60ecc1f8b0186d72ccc738761a24771433",
    "corpus/FINALIZATION_FAILURE_REPORT.json": "588b6141e3c25b561dff49d7b004ca508468ed39f4dbef8a8e16c54f69918730",
    "corpus/FRESHNESS_CANONICALIZATION_DIAGNOSIS_REPORT.json": "7395408dcf283821d19ed81f6986d64c47b4d31f9dd76d1c72481f7dff48a442",
    "corpus/FINALIZATION_CONTAMINATION_DISAGREEMENT_REPORT.json": "d9ff96223d36cd2c92d92361be028820d6955b82712f1ed2152178958c8765dc",
    "corpus/FRESHNESS_CHECKER_REPAIR_REPORT.json": "3c57078b5ea88b5fc994252cec52307e5b213969797eaa222bb623ef989e262f",
    "corpus/independent_contamination.py": "c2a8221a37057a3433e2314a7c63fd57aac1cafe3038ba67ec9952eaf9894ef7",
    "corpus/validate_corpus.py": "27cda5efa4856b6fb3b33a46d1daa712cc019213632dfe789686330183f22114",
    "corpus/validate_freshness_repair.py": "9d66678d1fa8b62e820b25cc50305ba91ed112d6add57d63f9f5dc734bea70ae"
}


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
    if field["required"] is not True or field["label_removal"] is not False:
        raise ValueError("g_extract1_output_scoring_constants")
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


def derive_canonical_output_field(
    binding: str, schema_type: str, ordinal: int, binding_ordinal: int,
    schema_contract: dict[str, Any],
) -> dict[str, Any]:
    """Value-free design checking only; no source facts or gold are created."""
    if type(ordinal) is not int or not 1 <= ordinal <= 168:
        raise ValueError("output_fixture_ordinal")
    maximum = 2 if binding == "OPERATION_TARGET" else 99
    if type(binding_ordinal) is not int or not 1 <= binding_ordinal <= maximum:
        raise ValueError("output_binding_ordinal")
    if binding not in {"SOURCE_COPY", "OPERATION_TARGET", "EXPLICIT_ABSENCE"}:
        raise ValueError("output_binding_kind")
    identifier = f"{'d' if binding == 'OPERATION_TARGET' else 'f'}{ordinal:03d}_{binding_ordinal:02d}"
    field = dict(
        name=identifier, schema_type=schema_type, required=True, binding_kind=binding,
        source_field=None if binding == "OPERATION_TARGET" else identifier,
        producer_target=identifier if binding == "OPERATION_TARGET" else None,
        label_removal=False, absence_capable=binding == "EXPLICIT_ABSENCE",
    )
    validate_output_field_shape(field, schema_contract)
    return field


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
    source_values = []
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
        if any(source_value == previous for previous in source_values):
            raise ValueError("entity_source_values_not_distinct")
        source_values.append(source_value)
        if source_type == "BOOLEAN":
            raise ValueError("entity_boolean_source_prohibited")
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
    if any(not isinstance(atom, list) or len(atom) != 2 or atom[0] not in {"IDENTIFIER", "ENTITY"} or not isinstance(atom[1], str) for atom in left + right):
        raise ValueError("identity_comparison_atom_shape")
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
                    selected_entity = node["arguments"]["selector_value"]["value"] if node["id"]=="ENTITY_FIELD_BIND" else None
                    matches = [x for x in facts if x["template_id"] == "VALUE" and x["field_identifier"] == item["value"] and x["entity_selector_value"] == selected_entity]
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
    if re.fullmatch(r"[AB]-R[23]-E[1-7]-01", defective[0], re.ASCII) is None:
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


def fixture_ordinal(phase: str, risk: str, family: str, index: int, reserve: bool) -> int:
    p = {"A": 0, "B": 84}[phase]
    f = int(family[1:]) - 1
    return 71 + p + {"R2": 0, "R3": 7}[risk] + f if reserve else 1 + p + {"R2": 0, "R3": 35}[risk] + f * 5 + index - 1


def validate_subtype_fixture(fixture: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any]) -> None:
    family, index_text = slot["slot_id"].split("-")
    index = int(index_text)
    allocation = contract["subtype_allocation_contract"]
    row = next(x for x in allocation["slot_rows"][family] if x["slot_id"] == slot["slot_id"])
    nodes = stable_topological_nodes(fixture["operation_nodes"])
    schema = contract["schema_type_contract"]
    fields = fixture["output_fields"]
    if family == "E7":
        validate_e7_fixture(fixture, contract)
        derived = {}
    else:
        derived = validate_fixture_semantics(fixture, schema, contract["operation_definition_contract"], contract["operation_semantics_contract"], contract["entity_population_contract"])
    context = fixture["lexical_context"]
    phase, risk = context["phase"], context["risk_round"]
    reserve = context["within_family_slot"] is None
    if risk != slot["risk_round"] or phase != slot.get("phase", phase) or (reserve and index != 1):
        raise ValueError("subtype_context")
    ordinal = fixture_ordinal(phase, risk, family, index, reserve)
    expected = dict(phase=phase, risk_round=risk, fixture_ordinal=ordinal, primary_family_slot=family, within_family_slot=None if reserve else index_text)
    if context != expected:
        raise ValueError("subtype_lexical_context")
    validate_lexical_fixture(fixture, contract, ordinal)
    if len(fields) != allocation["output_field_counts"].get(slot["slot_id"], allocation["output_field_counts"].get(family)):
        raise ValueError("subtype_output_count")
    if family == "E7":
        facts = fixture["source_fact_records"]
        absence = [x for x in facts if x["template_id"] == "EXPLICIT_ABSENCE"]
        support = [x for x in facts if x["template_id"] == "VALUE"]
        if len(absence) != 1 or len(facts) != len(fields) or [x["schema_type"] for x in support] != row["domain"]:
            raise ValueError("e7_slot_support_shape")
        ordered = [support[0], absence[0], *support[1:]] if reserve else [absence[0], *support] if phase == "A" else [*support, absence[0]]
        if facts != ordered:
            raise ValueError("e7_slot_presentation")
        for fact in support:
            if "|" in fact["schema_type"]:
                option_index = allocation["enum_answer_positions"][f"{phase}:{risk}"][slot["slot_id"]]
                if fact["value"]["value"] != fact["schema_type"].split("|")[option_index]:
                    raise ValueError("enum_answer_position")
        return
    shape = ">".join(x["id"] for x in nodes)
    if shape != row["operation_shape"].replace("(source)", ""):
        raise ValueError("subtype_operation_shape")
    if family == "E6" and index <= 3 and nodes[0]["arguments"]["source_field"]["kind"] != "field_identifier":
        raise ValueError("subtype_copy_source")
    resolve = typed_operands(fixture, contract, derived)
    values, boundary, temporal = evaluate_fixture(fixture)
    types = []
    for node in nodes:
        if node["id"] == "ENTITY_FIELD_BIND":
            continue
        op = next(x for x in contract["operation_definition_contract"]["catalog"] if x["id"] == node["id"])
        operands = [raw for key in op["placeholders"] if key != "target" for raw in (node["arguments"][key] if isinstance(node["arguments"][key], list) else [node["arguments"][key]])]
        types.append([resolve(x)[0] for x in operands])
    if slot["slot_id"] in allocation["field_typing_for_numeric_slots"] and types[0] != allocation["field_typing_for_numeric_slots"][slot["slot_id"]]:
        raise ValueError("subtype_operand_types")
    sign = allocation["numeric_result_sign_coverage"].get(slot["slot_id"])
    if sign:
        value = derived[nodes[0]["target"]]["value"]
        if sign.startswith("positive") and value <= 0 or sign == "negative" and value >= 0 or sign == "positive_non_integral" and _fraction(value).denominator == 1:
            raise ValueError("subtype_numeric_sign")
    if family == "E3" and index == 3 and len(nodes[0]["arguments"]["operands"]) != 3:
        raise ValueError("subtype_sum_count")
    if family == "E3" and index == 5 and nodes[0]["conversion_id"] != allocation["unit_conversion_assignment"][f"{phase}:{risk}"]:
        raise ValueError("subtype_conversion")
    if family == "E4":
        expected_comparison = allocation["comparison_slot_matrix"][f"{phase}:{risk}"][slot["slot_id"]]
        comparison = nodes[-1]
        pair = [resolve(comparison["arguments"][key])[0] for key in ("left", "right")]
        if comparison["id"] != expected_comparison["operator"] or boundary != expected_comparison["boundary_relation"] or pair != expected_comparison["operand_type_pair"] or derived[comparison["target"]]["value"] != expected_comparison["gold_boolean"]:
            raise ValueError("subtype_comparison_matrix")
        if index <= 4 and comparison["arguments"]["left"] != {"kind": "derived_field_identifier", "value": nodes[0]["target"]}:
            raise ValueError("subtype_comparison_orientation")
        if index == 5 and any(comparison["arguments"][key]["kind"] != "field_identifier" for key in ("left", "right")):
            raise ValueError("subtype_direct_comparison_sources")
    if family == "E5":
        population = fixture["entities"]
        count, role = row["coverage_class"].split(":")
        selected = nodes[0]["arguments"]["selector_value"]["value"]
        selected_index = contract["entity_selection_allocation_contract"]["selected_index_matrix"][f"{phase}:{risk}"][index-1]
        if len(population) != int(count.split("_")[1]) or any(x["selector_role"] != role for x in population) or selected != population[selected_index]["selector_value"] or fields[0]["schema_type"] != row["domain"]:
            raise ValueError("subtype_entity_population")
        if index == 3:
            source = nodes[0]["arguments"]["source_field"]["value"]
            gold_index = allocation["enum_answer_positions"][f"{phase}:{risk}"][slot["slot_id"]]
            for i, entity in enumerate(population):
                fact = next(x for x in fixture["source_fact_records"] if x["field_identifier"] == source and x["entity_selector_value"] == entity["selector_value"])
                if fact["value"]["value"] != row["domain"].split("|")[(i - selected_index + gold_index) % len(population)]:
                    raise ValueError("enum_entity_permutation")
    if family == "E6" and fields[0]["schema_type"] != row["domain"]:
        raise ValueError("subtype_copy_schema")
    temporal_nodes = [x for x in nodes if x["id"] in {"CALENDAR_DAY_OFFSET", "CLOCK_MINUTE_OFFSET", "ELAPSED_MINUTES"}]
    if temporal_nodes:
        node = temporal_nodes[0]
        args = node["arguments"]
        if node["id"] == "CALENDAR_DAY_OFFSET":
            start, offset = resolve(args["date"])[1], resolve(args["days"])[1]
            end = derived[node["target"]]["value"]
            if family == "E1":
                valid = {1: 1 <= offset <= 27 and temporal == "DATE_WITHIN_MONTH", 2: 1 <= offset <= 31 and temporal == "MONTH_BOUNDARY", 3: 1 <= offset <= 31 and temporal == "YEAR_BOUNDARY", 4: start != end and temporal == "LEAP_DAY_BOUNDARY", 5: offset == (0 if risk == "R2" else 366) and temporal == ("DATE_WITHIN_MONTH" if risk == "R2" else "YEAR_BOUNDARY")}[index]
            else:
                valid = 1 <= offset <= 31 and temporal == ("MONTH_BOUNDARY" if family == "E4" else "YEAR_BOUNDARY")
            if not valid:
                raise ValueError("subtype_calendar_boundary")
        elif node["id"] == "CLOCK_MINUTE_OFFSET":
            offset = resolve(args["minutes"])[1]
            required = "SAME_DAY_FORWARD" if family == "E2" and index == 1 else "MIDNIGHT_ROLLOVER"
            if offset <= 0 or temporal != required:
                raise ValueError("subtype_clock_boundary")
        else:
            start, end = (_minutes(resolve(args[key])[1]) for key in ("start", "end"))
            if not {3: end > start, 4: end < start, 5: end == start}[index]:
                raise ValueError("subtype_elapsed_boundary")


def historical_projection(fixture: dict[str, Any], contract: dict[str, Any]) -> bytes:
    adapter = contract["historical_fingerprint_adapter_contract"]
    if not isinstance(fixture, dict) or not isinstance(fixture.get("input"), dict):
        raise ValueError("legacy_input_object")
    payload = fixture["input"]
    schema = payload.get("schema")
    if not isinstance(schema, dict) or not schema or any(not isinstance(k, str) or not isinstance(v, str) for k, v in schema.items()):
        raise ValueError("legacy_schema_object")
    if not isinstance(payload.get("text"), str) or not isinstance(fixture.get("prompt"), str):
        raise ValueError("legacy_text_or_prompt_type")
    tags = []
    for value in schema.values():
        info = parse_schema_type(value, contract["schema_type_contract"])
        tags.append([info["semantic_tag"], len(info.get("options", []))])
    tags.sort(key=lambda x: json.dumps(x, separators=(",", ":")).encode())
    normalize = lambda x: " ".join(unicodedata.normalize("NFC", x.replace("\r\n", "\n").replace("\r", "\n")).casefold().split())
    token_pattern = re.compile(contract["contamination_contract"]["tokenizer"]["pattern"], re.ASCII)
    tokens = token_pattern.findall(normalize(fixture["input"]["text"]))
    shapes = [next((kind for kind in ("DATE", "TIME", "NUMBER") if re.fullmatch(adapter["source_kind_regex"][kind], token, re.ASCII)), "IDENTIFIER") for token in tokens]
    suffix = contract["baseline_binding"]["structured_extraction_assembled_template"].replace("{SUBJECT}", "")
    prompt = fixture["prompt"]
    if not prompt.endswith(suffix) or not tokens:
        raise ValueError("legacy_projection_shape_or_suffix")
    subject = normalize(prompt[:-len(suffix)])
    pattern = "|".join("(?P<S%d>%s)" % (i, row["regex"]) for i, row in enumerate(adapter["surface_catalog"]))
    surface = [adapter["surface_catalog"][int(x.lastgroup[1:])]["id"] for x in re.finditer(pattern, subject, re.ASCII)]
    return json.dumps([tags, shapes, surface], ensure_ascii=True, separators=(",", ":")).encode()


def historical_adaptation_summary(contract: dict[str, Any]) -> dict[str, Any]:
    examined, adapted, rejected, evidence, artifacts = 0, 0, [], [], []
    for item in contract["historical_fingerprint_adapter_contract"]["artifact_bindings"]:
        path = ROOT / item["path"]
        if sha256(path) != item["sha256"]:
            raise ValueError("historical_input_digest")
        artifact_examined, artifact_adapted = 0, 0
        for fixture in load_json_unique(path)["fixtures"]:
            if fixture["task_class"] != "structured_extraction":
                continue
            examined += 1
            artifact_examined += 1
            try:
                first = historical_projection(fixture, contract)
                if first != historical_projection(fixture, contract):
                    raise ValueError("unstable_projection")
            except (KeyError, ValueError, TypeError) as error:
                rejected.append(dict(path=item["path"], fixture_id=fixture.get("fixture_id"), reason=str(error)))
            else:
                adapted += 1
                artifact_adapted += 1
                evidence.append([item["path"], fixture["fixture_id"], json.loads(first)])
        artifacts.append(dict(path=item["path"], examined=artifact_examined, adapted=artifact_adapted, rejected=artifact_examined-artifact_adapted))
    digest = hashlib.sha256(json.dumps(evidence, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    return dict(examined=examined, adapted=adapted, rejected=len(rejected), rejection_reasons=rejected, artifacts=artifacts, projection_evidence_sha256=digest)


def historical_structural_replay(left: bytes, right: bytes, jaccard: float) -> bool:
    lhs, rhs = json.loads(left), json.loads(right)
    if len(lhs) != 3 or len(rhs) != 3 or not 0 <= jaccard <= 1:
        raise ValueError("legacy_comparison_shape")
    equal = sum(a == b for a, b in zip(lhs, rhs))
    return equal == 3 or (equal >= 2 and jaccard >= 0.12)


def similarity_vector_payload(request: dict[str, Any]) -> str:
    schema = request["input"]["schema"]
    rendered = "\n".join(f"{key}={schema[key]}" for key in sorted(schema, key=lambda key: key.encode("utf-8")))
    payload = request["input"]["text"] + "\n" + rendered
    return " ".join(unicodedata.normalize("NFC", payload.replace("\r\n", "\n").replace("\r", "\n")).casefold().split())


def ordinal_neutral_payload(request: dict[str, Any], historical: bool = False) -> str:
    payload = similarity_vector_payload(request)
    if historical:
        return payload
    ordinal = r"(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])"
    payload = re.sub(r"\b([fd])" + ordinal + r"_(\d{2})\b", r"\1_\2", payload, flags=re.ASCII)
    payload = re.sub(r"\bentity " + ordinal + r" ([abc])\b", r"entity \1", payload, flags=re.ASCII)
    return re.sub(r"\b(label|code|id)_" + ordinal + r"_(\d{2})\b", r"\1_\2", payload, flags=re.ASCII)


def comparison_grams(payload: str, contract: dict[str, Any], view: str = "ordinary") -> set[tuple[str, ...]]:
    tokens = re.findall(contract["contamination_contract"]["tokenizer"]["pattern"], payload, re.ASCII)
    value_pattern = r"(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}:[0-9]{2}|[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:e[+-]?[0-9]+)?|option_[a-h]|true|false)"
    is_value = [bool(re.fullmatch(value_pattern, x, re.ASCII)) for x in tokens]
    if view == "shape":
        tokens = ["value" if value else token for token, value in zip(tokens, is_value)]
    elif view not in {"ordinary", "content"}:
        raise ValueError("similarity_view")
    if view=="content":
        content_pattern=contract["ordinal_neutral_similarity_contract"]["declared_template_content_view"]["content_value_regex"]
        is_value=[bool(re.fullmatch(content_pattern,x,re.ASCII)) for x in tokens]
    return {tuple(tokens[i:i+5]) for i in range(max(0, len(tokens)-4)) if view != "content" or any(is_value[i:i+5])}


def gram_jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    return len(left & right) / len(left | right) if left | right else 1.0


def planned_fingerprint(contract: dict[str, Any], context: str, slot_id: str, reserve: bool) -> list[Any]:
    """Derive a value-free design position, not an authored corpus fixture."""
    phase, risk = context.split(":")
    family, index_text = slot_id.split("-"); index = int(index_text)
    row = next(x for x in contract["subtype_allocation_contract"]["slot_rows"][family] if x["slot_id"] == slot_id)
    graph, roles, sequence = [], [], []
    boundary, temporal, entity_role, layout = "NONE", "NONE", "NONE", "CONTIGUOUS_SINGLE_ENTITY"
    if family == "E7":
        support = [["TARGET", st, -1] for st in row["domain"]]
        absence = ["EXPLICIT_ABSENCE", "provided|not_provided", -1]
        sequence = [support[0], absence, *support[1:]] if reserve else [absence, *support] if phase == "A" else [*support, absence]
        roles = [[st, "source_copy"] for st in row["domain"]] + [["provided|not_provided", "absence_sentinel"]]
        layout = "EXPLICIT_PARTIAL_ABSENCE"
    elif family == "E5":
        count, selector = row["coverage_class"].split(":"); count = int(count.split("_")[1])
        graph = [["ENTITY_FIELD_BIND", ["source_field", "source_field", "entity_selector"], []]]
        roles = [[row["domain"], "entity_bound_value"]]
        sequence = [["SUPPORT", "string", i] for i in range(count)] + [["TARGET", row["domain"], i] for i in range(count)]
        entity_role, layout = "MULTI_ENTITY_SELECT_BY_" + selector, "INTERLEAVED_MULTI_ENTITY"
    else:
        operations = row["operation_shape"].replace("(source)", "").split(">")
        first = operations[0]
        if family == "E1" or first == "CALENDAR_DAY_OFFSET":
            source_types = ["YYYY-MM-DD", "integer"] if family == "E1" and index == 5 else ["YYYY-MM-DD"]
            kinds = ["source_field", "source_field" if len(source_types) == 2 else "literal"]
            temporal = {1:"DATE_WITHIN_MONTH", 2:"MONTH_BOUNDARY", 3:"YEAR_BOUNDARY", 4:"LEAP_DAY_BOUNDARY", 5:"DATE_WITHIN_MONTH" if risk=="R2" else "YEAR_BOUNDARY"}[index] if family=="E1" else "MONTH_BOUNDARY" if family=="E4" else "YEAR_BOUNDARY"
            result_schema, role = "YYYY-MM-DD", "derived_date"
        elif first == "CLOCK_MINUTE_OFFSET":
            source_types, kinds = ["HH:MM"], ["source_field", "literal"]
            temporal = "SAME_DAY_FORWARD" if family=="E2" and index==1 else "MIDNIGHT_ROLLOVER"
            result_schema, role = "HH:MM", "derived_time"
        elif first == "ELAPSED_MINUTES":
            source_types = ["HH:MM"] if index==5 else ["HH:MM","HH:MM"]
            kinds = ["source_field", "literal" if index==5 else "source_field"]
            temporal = "MIDNIGHT_ROLLOVER" if index==4 else "SAME_DAY_FORWARD"
            result_schema, role = "integer", "derived_number"
        elif first == "EXACT_COPY":
            source_types, kinds = [row["domain"]], ["source_field"]
            result_schema, role = row["domain"], "source_copy"
        elif family=="E4" and index==5:
            source_types, kinds = ["number","number"], ["source_field","source_field"]
            result_schema, role = "boolean", "derived_boolean"
        else:
            types = contract["subtype_allocation_contract"]["field_typing_for_numeric_slots"][slot_id]
            source_types = [{"INTEGER":"integer", "NUMBER":"number"}[t] for t in types]
            kinds = ["source_field"] * len(types)
            result_schema, role = ("integer" if set(types)=={"INTEGER"} and first!="DIVIDE" else "number"), "derived_number"
        graph = [[first, kinds, []]]
        if len(operations)==2:
            graph.append([operations[1], ["derived_field", "literal"] if operations[1] in COMPARISON else ["derived_field"], [0]])
            if operations[1] in COMPARISON: result_schema,role="boolean","derived_boolean"
        if family=="E4": boundary=contract["subtype_allocation_contract"]["comparison_slot_matrix"][context][slot_id]["boundary_relation"]
        roles = [[result_schema, role]]
        sequence = [["TARGET" if first=="EXACT_COPY" else "SUPPORT", st, -1] for st in source_types]
    roles.sort(key=lambda x:json.dumps(x,separators=(",",":")).encode())
    return [graph,roles,entity_role,boundary,temporal,[layout,sequence]]


def template_ledger(contract: dict[str, Any]) -> dict[str, Any]:
    positions, classes = [], {}
    for context in ("A:R2","A:R3","B:R2","B:R3"):
        for family in ("E1","E2","E3","E4","E5","E6","E7"):
            for index in range(1,7):
                reserve=index==6; slot=f"{family}-{1 if reserve else index:02d}"
                position=f"{context}:{slot}:{'RESERVE' if reserve else 'PRIMARY'}"
                fp=planned_fingerprint(contract,context,slot,reserve)
                encoded=json.dumps(fp,ensure_ascii=True,separators=(",",":")).encode()
                key=hashlib.sha256(encoded).hexdigest()
                classes.setdefault(key,dict(slot=slot,fingerprint=fp,members=[]))["members"].append(position)
                positions.append(dict(position=position,subtype_slot=slot,fingerprint_class=key))
    for key, group in classes.items():
        if any(x.split(":")[2]!=group["slot"] for x in group["members"]):
            raise ValueError("unrelated_subtype_fingerprint_collision")
        group["maximum_recurrence_count"]=len(group["members"])
    return dict(positions=positions,classes=classes)


def selector_blind_summary(matrix: dict[str, list[int]]) -> dict[str, Any]:
    contexts=list(matrix)
    scores={str(i):[sum(x==i for x in matrix[c]) for c in contexts] for i in range(3)}
    result=dict(context_order=contexts,always_index_scores=scores,mapping_families={})
    for name,groups in (("schema",[0,1,2,3,4]),("subtype",[0,1,2,3,4]),("selector_role",[0,1,2,0,1])):
        unique=sorted(set(groups)); rows=[]
        for assignment in itertools.product(range(3),repeat=len(unique)):
            mapping=dict(zip(unique,assignment))
            row=[sum(mapping[g]==selected for g,selected in zip(groups,matrix[c])) for c in contexts]
            rows.append(row)
            if any(row[contexts.index('A:'+risk)]>=4 and row[contexts.index('B:'+risk)]>=4 for risk in ('R2','R3')):
                raise ValueError("selector_blind_passes_both_phases")
        result["mapping_families"][name]=dict(exhaustive_mapping_count=len(rows),maximum_by_context=[max(x[i] for x in rows) for i in range(4)],maps_passing_all_contexts=sum(all(x>=4 for x in row) for row in rows),maps_passing_both_phases_same_round=0)
    return result


def value_shape_profile(contract: dict[str, Any], context: str, slot_id: str) -> dict[str, Any]:
    rules = contract["value_allocation_contract"]
    row = copy.deepcopy(rules["slot_profiles"][slot_id])
    phase, risk = context.split(":")
    parameters = rules["context_parameters"][str(rules["context_pattern"][context])]
    substitutions = {
        "CONTEXT_PRECISION": parameters["precision_places"],
        "CONTEXT_ADD_CARRY": {"operation":"ADD", "carry":parameters["add_carry"]},
        "CONTEXT_SUBTRACT_BORROW": {"operation":"SUBTRACT", "borrow":parameters["subtract_borrow"]},
        "TERMINATING_NONINTEGRAL_QUOTIENT_CONTEXT_DECIMAL_LENGTH": {
            "operation":"DIVIDE", "places":parameters["divide_quotient_places"],
            "denominator_class":parameters["divide_reduced_denominator"], "divisor_digits":2},
        "FROZEN_CONVERSION_ID": contract["subtype_allocation_contract"]["unit_conversion_assignment"][context],
        "CONTEXT_NUMERIC_GAP": parameters["numeric_gap"],
        "CONTEXT_DATE_GAP": parameters["date_gap_days"],
        "CONTEXT_TIME_GAP": parameters["time_gap_minutes"],
        "CONTEXT_NUMERIC_ENTITY_GAP": parameters["numeric_entity_gap"],
        "CONTEXT_DATE_ENTITY_GAP": parameters["date_entity_gap_days"],
        "CONTEXT_TIME_ENTITY_GAP": parameters["time_entity_gap_minutes"],
        "CONTEXT_TWO_ENTITY_RANK": parameters["two_entity_selected_rank"],
        "CONTEXT_THREE_ENTITY_RANK": rules["three_entity_rank_override"][context],
        "R2_SMALL_R3_LARGE": ["SMALL" if risk=="R2" else "LARGE"],
        "R2_0_R3_366": [0,0] if risk=="R2" else [366,366],
    }
    for key, value in row.items():
        if isinstance(value,str) and value in substitutions: row[key]=substitutions[value]
    if slot_id.startswith("E4") and contract["subtype_allocation_contract"]["comparison_slot_matrix"][context][slot_id]["boundary_relation"]=="EQUAL":
        row["comparison_distance"]=0
    return row


def fractional_places(value: Any) -> int:
    fixed = exact_decimal_from_fraction(Fraction(str(value)))
    return len(fixed.split(".")[1].rstrip("0"))


def digit_event(values: list[Any], operation: str) -> bool:
    precision=max(fractional_places(x) for x in values)
    integers=[int(abs(Fraction(str(x)))*10**precision) for x in values]
    if operation in {"ADD","SUM"}:
        carry=0; event=False
        while any(integers) or carry:
            total=sum(x%10 for x in integers)+carry
            carry=total//10;event |= carry>0
            integers=[x//10 for x in integers]
        return event
    if operation!="SUBTRACT" or len(integers)!=2: raise ValueError("digit_event_operation")
    large,small=sorted(integers,reverse=True);borrow=0;event=False
    while large or small:
        borrow=int(large%10-borrow<small%10);event |= bool(borrow)
        large//=10;small//=10
    return event


def validate_value_shape(fixture: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    context=f"{fixture['lexical_context']['phase']}:{fixture['lexical_context']['risk_round']}"
    profile=value_shape_profile(contract,context,slot["slot_id"])
    nodes=stable_topological_nodes(fixture["operation_nodes"])
    typed=[_typed_source_value(x,contract["schema_type_contract"],contract["operation_semantics_contract"]) for x in fixture["source_fact_records"] if x["template_id"]=="VALUE"]
    # Use the same exact gold evaluator as the existing design checks, not floats.
    derived={} if not nodes else validate_fixture_semantics(fixture,contract["schema_type_contract"],contract["operation_definition_contract"],contract["operation_semantics_contract"],contract["entity_population_contract"])
    resolve=typed_operands(fixture,contract,derived)
    for result in derived.values():
        if result["semantic_type"]=="DATE" and not profile["date_years"][0]<=result["value"].year<=profile["date_years"][1]:raise ValueError("value_result_year")
    for node in nodes:
        for raw in node["arguments"].values():
            for item in raw if isinstance(raw,list) else [raw]:
                if item["kind"] in {"integer_literal","decimal_literal"}:
                    value=Fraction(item["value"])
                    if value<=0 and not (slot["slot_id"]=="E1-05" and value==0):raise ValueError("value_literal_sign")
                if item["kind"]=="date_literal" and not profile["date_years"][0]<=date.fromisoformat(item["value"]).year<=profile["date_years"][1]:raise ValueError("value_literal_year")
    numeric=[x[1] for x in typed if x[0] in {"INTEGER","NUMBER"}]
    bands=profile["magnitude_bands"]
    if bands and len(bands)!=len(numeric):raise ValueError("value_magnitude_count")
    for value,band in zip(numeric,bands):
        lower,upper=contract["value_allocation_contract"]["magnitude_bands"][band]
        if not lower<=abs(Fraction(str(value)))//1<=upper:raise ValueError("value_magnitude_band")
    if any(Fraction(str(x))<=0 for x in numeric) and not slot["slot_id"].startswith("E1"):
        raise ValueError("value_numeric_sign")
    for tag,value,_schema in typed:
        if tag=="NUMBER" and fractional_places(value)!=profile["number_precision"]:raise ValueError("value_number_precision")
        if tag=="DATE" and not profile["date_years"][0]<=value.year<=profile["date_years"][1]:raise ValueError("value_date_year")
        if tag=="TIME" and profile["source_time_class"]=="IRREGULAR_MINUTE" and _minutes(value)%30==0:raise ValueError("value_time_precision")
        if tag=="BOOLEAN" and value!=contract["value_allocation_contract"]["e7_boolean_source_allocation"][context]:raise ValueError("value_boolean_allocation")
    complexity=profile["arithmetic_complexity"]
    if isinstance(complexity,dict) and complexity["operation"] in {"ADD","SUBTRACT"}:
        if digit_event(numeric,complexity["operation"])!=complexity.get("carry",complexity.get("borrow")):raise ValueError("value_digit_complexity")
    if complexity=="THREE_OPERANDS_AT_LEAST_ONE_CARRY" and (len(numeric)!=3 or not digit_event(numeric,"SUM")):raise ValueError("value_sum_complexity")
    if isinstance(complexity,dict) and complexity["operation"]=="DIVIDE":
        quotient=Fraction(str(numeric[0]))/Fraction(str(numeric[1])); denominator=quotient.denominator
        twos=fives=0
        while denominator%2==0:denominator//=2;twos+=1
        while denominator%5==0:denominator//=5;fives+=1
        kind="POWER_OF_2_ONLY" if twos and not fives else "BOTH_2_AND_5" if twos and fives else "OTHER"
        if denominator!=1 or kind!=complexity["denominator_class"] or fractional_places(exact_decimal_from_fraction(quotient))!=complexity["places"]:raise ValueError("value_divide_complexity")
    for node in nodes:
        args=node["arguments"];op=node["id"]
        if op in COMPARISON:
            operands=[resolve(args[k]) for k in ("left","right")]
            tag=operands[0][0];a,b=(x[1] for x in operands)
            gap=abs((a-b).days) if tag=="DATE" else abs(_minutes(a)-_minutes(b)) if tag=="TIME" else abs(Fraction(str(a))-Fraction(str(b)))
            if gap!=Fraction(str(profile["comparison_distance"])):raise ValueError("value_comparison_distance")
        if op=="CALENDAR_DAY_OFFSET":distance=resolve(args["days"])[1]
        elif op=="CLOCK_MINUTE_OFFSET":distance=resolve(args["minutes"])[1]
        elif op=="ELAPSED_MINUTES":distance=derived[node["target"]]["value"]
        else:continue
        if not profile["temporal_distance"][0]<=distance<=profile["temporal_distance"][1]:raise ValueError("value_temporal_distance")
    if slot["slot_id"] in {"E5-01","E5-04","E5-05"}:
        node=nodes[0]; source=node["arguments"]["source_field"]["value"]
        sources=[x for x in fixture["source_fact_records"] if x["field_identifier"]==source]
        vals=[_typed_source_value(x,contract["schema_type_contract"],contract["operation_semantics_contract"])[1] for x in sources]
        scalar=lambda v:v.toordinal() if slot["slot_id"]=="E5-04" else _minutes(v) if slot["slot_id"]=="E5-05" else Fraction(str(v))
        ordered=sorted(scalar(x) for x in vals)
        if any(b-a!=Fraction(str(profile["entity_separation"])) for a,b in zip(ordered,ordered[1:])):raise ValueError("value_entity_separation")
        selected=node["arguments"]["selector_value"]["value"]
        chosen=next(x for x in sources if x["entity_selector_value"]==selected)
        if ordered.index(scalar(_typed_source_value(chosen,contract["schema_type_contract"],contract["operation_semantics_contract"])[1]))!=profile["entity_selected_rank"]:raise ValueError("value_entity_rank")
    return profile


def validate_v9_fixture(fixture: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    validate_subtype_fixture(fixture,slot,contract)
    profile=validate_value_shape(fixture,slot,contract)
    ctx=fixture["lexical_context"];context=f"{ctx['phase']}:{ctx['risk_round']}"
    actual=json.loads(fingerprint_bytes(dict(fixture=fixture),contract["operation_definition_contract"]))
    if actual!=planned_fingerprint(contract,context,slot["slot_id"],ctx["within_family_slot"] is None):raise ValueError("unallocated_structural_layout")
    return profile


def declared_template_pair(left: str, right: str, contract: dict[str, Any]) -> bool:
    rows={x["position"]:x for x in contract["template_recurrence_contract"]["positions"]}
    if left==right or left not in rows or right not in rows:raise ValueError("template_position_pair")
    return rows[left]["subtype_slot"]==rows[right]["subtype_slot"]


def checking_pair_decision(left: str, right: str, actual_left: list[Any], actual_right: list[Any], facts: dict[str, Any], contract: dict[str, Any]) -> str:
    """Exercise the frozen decision table with checked design facts, not model outputs."""
    rules=contract["template_recurrence_contract"]
    positions={x["position"]:x for x in rules["positions"]}
    if left not in positions or right not in positions or left==right:raise ValueError("comparison_positions")
    expected=lambda pos:rules["fingerprint_classes"][positions[pos]["fingerprint_class"]]["fingerprint"]
    if not facts["slot_value_semantics_valid"] or actual_left!=expected(left) or actual_right!=expected(right):return "AUTHORING_ERROR_STRUCTURE"
    if not facts["exact_reuse_pass"] or not facts["raw_value_sequence_fresh"] or facts["raw_payload_equal"]:return "REJECT_CONTAMINATION"
    amendment = contract.get("declared_scaffold_overlap_contract")
    if amendment:
        pair = frozenset((left, right))
        group = next((g for g in amendment["eligible_groups"]
                      if any(frozenset(p) == pair for p in g["position_pairs"])), None)
        if group is not None:
            # Flags are derived checks in a future audit, never author assertions.
            if not facts.get("all_freshness_checks_pass", False):
                return "REJECT_CONTAMINATION"
            if "ordinary_grams_left" not in facts or "ordinary_grams_right" not in facts:
                return "AUTHORING_ERROR_MISSING_SCAFFOLD_EVIDENCE"
            removed = {tuple(g.split(" ")) for g in group["forced_overlapping_five_grams"]}
            a = facts["ordinary_grams_left"] - removed
            b = facts["ordinary_grams_right"] - removed
            if not a or not b:
                return "AUTHORING_ERROR_EMPTY_RESIDUAL"
            return "PERMITTED_DECLARED_SCAFFOLD" if Fraction(len(a & b),len(a | b)) < Fraction(3,25) else "REJECT_CONTAMINATION"
    if declared_template_pair(left,right,contract):
        content=facts["content_jaccard"]
        if content is None:
            numeric={"integer","number","YYYY-MM-DD","HH:MM"}
            if any(row[1] in numeric for fp in (actual_left,actual_right) for row in fp[5][1]):return "AUTHORING_ERROR_EMPTY_CONTENT"
            return "PERMITTED_DECLARED_RECURRENCE"
        return "PERMITTED_DECLARED_RECURRENCE" if content<0.12 else "REJECT_CONTAMINATION"
    matched=sum(a==b for a,b in zip(actual_left,actual_right))
    return "REJECT_CONTAMINATION" if facts["ordinary_jaccard"]>=0.20 or matched==6 or matched>=5 and facts["ordinary_jaccard"]>=0.12 else "PERMITTED_DISTINCT_SUBTYPE"


def symbolic_position_tokens(position: dict[str, Any], contract: dict[str, Any]) -> list[Any]:
    """Value-free token algebra; no source text, numeric literals or gold authored."""
    base = position["logical_base_id"]
    slot = position["subtype_slot"]
    context = position["phase"] + ":" + position["risk_round"]
    sequence = position["schema_plan"]["source_fact_role_schema_entity_sequence"]
    tokens, string_index = [], 0
    for i, (role, schema, entity) in enumerate(sequence):
        field_index = (1 if i < len(sequence)//2 else 2) if entity >= 0 else i + 1
        if entity >= 0:
            tokens.extend(["for", "entity", chr(97 + entity)])
        tokens.append(f"f_{field_index:02d}")
        if role == "EXPLICIT_ABSENCE":
            tokens.extend(["was", "not", "provided"])
            continue
        tokens.append("is")
        if slot.startswith("E5") and role == "SUPPORT":
            tokens.extend(["entity", chr(97 + entity)])
        elif schema == "string":
            string_index += 1
            tokens.append(f"{('label','code','id')[(string_index-1)%3]}_{string_index:02d}")
        elif schema == "boolean":
            tokens.append(str(contract["value_allocation_contract"]["e7_boolean_source_allocation"][context]).lower())
        elif "|" in schema:
            options = schema.split("|")
            gold_index = contract["subtype_allocation_contract"]["enum_answer_positions"][context][slot]
            if slot == "E5-03":
                selected = contract["entity_selection_allocation_contract"]["selected_index_matrix"][context][2]
                value = options[(gold_index + entity - selected) % len(options)]
            else:
                value = options[gold_index]
            tokens.append(value)
        elif slot == "E1-05" and schema == "integer":
            tokens.append("0" if position["risk_round"] == "R2" else "366")
        else:
            # One token for every legal numeric/date/time value. Disjoint atoms
            # attain the pairwise lower bound; fixed catalog atoms stay above.
            tokens.append(("FRESH", base, i, schema))
    pattern = contract["contamination_contract"]["tokenizer"]["pattern"]
    for output in position["schema_plan"]["output_fields"]:
        name = re.sub(r"([fd])\d{3}_", r"\1_", output["name"], flags=re.ASCII)
        tokens.extend(re.findall(pattern, name + "=" + output["schema_type"].casefold(), re.ASCII))
    return tokens


def symbolic_grams(tokens: list[Any], contract: dict[str, Any], view: str) -> set[tuple[Any, ...]]:
    pattern = contract["ordinal_neutral_similarity_contract"]["declared_template_content_view"]["content_value_regex"]
    def content(token: Any) -> bool:
        return isinstance(token, tuple) or bool(re.fullmatch(pattern, token, re.ASCII))
    if view == "shape":
        value_pattern = contract["ordinal_neutral_similarity_contract"]["shape_view"]["value_token_regex"]
        tokens = ["value" if isinstance(t, tuple) or re.fullmatch(value_pattern, t, re.ASCII) else t for t in tokens]
    return {tuple(tokens[i:i+5]) for i in range(max(0, len(tokens)-4))
            if view != "content" or any(content(t) for t in tokens[i:i+5])}


def scaffold_feasibility_audit(contract: dict[str, Any]) -> dict[str, Any]:
    blueprint = load_json_unique(HERE / "blueprint" / "BLUEPRINT.json")
    positions = blueprint["logical_positions"]
    classes, all_pairs = {}, []
    for left, right in itertools.combinations(positions, 2):
        lp, rp = left["logical_base_id"], right["logical_base_id"]
        lt, rt = symbolic_position_tokens(left, contract), symbolic_position_tokens(right, contract)
        a, b = symbolic_grams(lt, contract, "ordinary"), symbolic_grams(rt, contract, "ordinary")
        sa, sb = symbolic_grams(lt, contract, "shape"), symbolic_grams(rt, contract, "shape")
        ca, cb = symbolic_grams(lt, contract, "content"), symbolic_grams(rt, contract, "content")
        fp, fq = left["recurrence"]["planned_six_components"], right["recurrence"]["planned_six_components"]
        matches = sum(x == y for x, y in zip(fp, fq))
        same = left["subtype_slot"] == right["subtype_slot"]
        ordinary = Fraction(len(a & b), len(a | b)) if a | b else Fraction(1)
        content = Fraction(len(ca & cb), len(ca | cb)) if ca | cb else None
        limit = Fraction(3, 25) if same or matches >= 5 else Fraction(1, 5)
        infeasible = (content is not None and content >= limit) if same else ordinary >= limit or matches == 6
        weight = (2 if left["family"] == "E5" else 1) * (2 if right["family"] == "E5" else 1)
        record = dict(left=lp, right=rp, same_subtype=same, fingerprint_matches=matches,
                      ordinary_minimum=str(ordinary), ordinary_minimum_decimal=float(ordinary),
                      shape_jaccard=str(Fraction(len(sa & sb), len(sa | sb))),
                      content_minimum=None if content is None else str(content),
                      threshold_exclusive=str(limit), rendered_pair_count=weight,
                      classification="STRUCTURALLY_INFEASIBLE_WITH_EXISTING_RULES" if infeasible else "FEASIBLE_WITH_EXISTING_RULES")
        all_pairs.append(record)
        if infeasible:
            forced = sorted(" ".join(g) for g in a & b)
            key_data = [sorted([left["subtype_slot"],right["subtype_slot"]]), matches,
                        sorted([left["recurrence"]["fingerprint_class"],right["recurrence"]["fingerprint_class"]]),
                        str(ordinary), record["shape_jaccard"], record["content_minimum"], str(limit), forced]
            key = hashlib.sha256(json.dumps(key_data,separators=(",",":")).encode()).hexdigest()
            group = classes.setdefault(key, dict(group_id=key, subtype_pair=key_data[0],
                fingerprint_classes=key_data[2], fingerprint_matches=matches,
                ordinary_minimum=str(ordinary), ordinary_minimum_decimal=float(ordinary),
                shape_jaccard=record["shape_jaccard"], content_minimum=record["content_minimum"],
                threshold_exclusive=str(limit), forced_overlapping_five_grams=forced, position_pairs=[],
                rendered_pair_count=0, root_cause="mandatory source/schema/finite-catalog scaffold; no variable-value gram in forced intersection"))
            group["position_pairs"].append([lp,rp]); group["rendered_pair_count"] += weight
    return dict(logical_positions=len(positions), rendered_variants=len(blueprint["rendered_variants"]),
        logical_cross_base_pairs=len(all_pairs), rendered_cross_base_pairs=sum(x["rendered_pair_count"] for x in all_pairs),
        same_base_counterfactual_pairs=24, infeasible_classes=list(classes.values()),
        infeasible_logical_pairs=sum(len(x["position_pairs"]) for x in classes.values()),
        infeasible_rendered_pairs=sum(x["rendered_pair_count"] for x in classes.values()), all_pair_classifications=all_pairs)


def scaffold_contract_proposal(contract: dict[str, Any]) -> dict[str, Any]:
    """Construct the prospective value-free amendment, never corpus content."""
    audit = scaffold_feasibility_audit(contract)
    return dict(
        contract_id="g-extract1.declared-scaffold-overlap.v1",
        parent_commit="28fb6bbd3fb668265e4cc50cda0da0f9afdf3ce5",
        precedence="Only exact listed cross-base position pairs override the old ordinary/content veto. All other rules and pair-local E5 exception remain unchanged.",
        blueprint_status="Unchanged accepted 28fb6bbd blueprint; contamination rebinding requires independent amendment rereview and separate future authorization. No corpus authority granted.",
        scope=dict(logical_positions=168,rendered_variants=192,logical_pairs=14028,
                   rendered_cross_base_pairs=18312,same_base_e5_pairs_separate=24),
        old_rule=dict(ordinary_exclusive="1/5",near_replay_inclusive="3/25",unchanged_globally=True),
        eligibility=[
            "Both are different logical base IDs in exactly one listed position_pair; rendered variant multiplicity never broadens base membership.",
            "Each actual fixture independently passes lexical, typed schema/operation/gold, subtype, value-shape, output amendment and exact planned six-component fingerprint validation; E5 full pair/request audit also required.",
            "Actual position and complete fingerprint equal the bound unchanged blueprint and frozen recurrence ledger; no author-selected group or output-derived eligibility.",
            "Cross-subtype pairs retain different subtype IDs AND different full fingerprints; schema/operation/entity-role/fact-sequence differences are validated, not inferred from IDs.",
            "The two E1-05 same-subtype pairs are separately named fixed-boundary recurrence corrections, not distinct-subtype independence claims.",
        ],
        view=dict(
            input="same ordinal-neutral input.text plus canonical schema payload as existing ordinary view",
            normalization="existing NFC/CRLF/casefold/whitespace and NEW-only ordinal masking, unchanged",
            tokenizer="existing contamination.v5 tokenizer, unchanged",
            ngram_size=5,construction="ordinary set minus exactly group.forced_overlapping_five_grams on EACH side; no token deletion, no new adjacency or re-tokenization",
            removed="Only the exact listed invariant five-grams proven from frozen source/schema syntax, generated ordinal-neutral catalog atoms, or required fixed E1-05 boundary offset. No arbitrary shared gram or mutable literal may be removed.",
            retained="Every other ordinary five-gram, including all grams bearing freely chosen numeric/date/time values. Exact raw typed values including generated labels, finite enums/Booleans and fixed offsets remain in all existing freshness/semantic checks.",
            metric="set Jaccard with exact integer cross-multiplication: 25*intersection < 3*union",
            limit_exclusive="3/25",one_or_both_empty="AUTHORING_ERROR_EMPTY_RESIDUAL; never automatic independence credit",
            reporting="ordinary, shape, existing content (or NOT_APPLICABLE), residual, removed grams, exact membership, actual validations and all freshness results; shape alone never permits a pair",
            finite_catalog="generated labels/enum/Boolean and fixed boundary offsets are not scalable freshness evidence; nonempty residual alone is not independence evidence; all structural and raw freshness requirements mandatory",
        ),
        freshness_required=["raw typed VALUE sequence inequality","whole-answer exact-reuse pass","identity atom disjointness","eligible date-number tuple exact-reuse pass","raw payload inequality","generated identities bound to distinct base ordinals","independent A/B authorship/review and no A content reuse in B"],
        empty_content="Old content sets may be empty for finite/generated catalogs. Eligibility and nonempty residual plus all freshness/structural requirements still mandatory; report NOT_APPLICABLE, not proof of independence.",
        historical="106/106 adapter unchanged; reject ordinary>=0.20, projection3/3, or projection>=2/3 and ordinary>=0.12; amendment never applies to historical/new",
        audit_algorithm=dict(
            source="unchanged blueprint schema_plan source role/schema/entity sequence and canonical outputs; frozen value/enum/Boolean/lexical allocations; no concrete source text/gold",
            token_algebra="symbolic_position_tokens: one unique FRESH(base,record,schema) per freely variable single-token value; fixed 0/366, generated label/code/id order, E5 selector entity letters, opaque enum allocation and Boolean context atoms remain exact; source renderer/schema tokenizer unchanged",
            minimum_proof="Legal fresh numeric/date/time literals each occupy one token. All value-bearing window intersections can be avoided pairwise by disjoint legal literals; fixed grammar windows remain. Denominators use maximum distinct five-gram sets. Additional literal equality cannot reduce intersection or increase union. Thus recorded rational ordinary/content minima are attained pairwise, not mere sample estimates.",
            domain_support="Each variable occurrence has at least two alternatives under its accepted magnitude/precision/arithmetic/date/time/gap profile; entity values preserve frozen gaps/permutation. Select disjoint anchors across a pair; fixed equality/offset/enum/Boolean cases explicitly retained. No concrete value is selected or corpus authored by this algebra.",
            shape="all scalable symbolic values and existing numeric/date/time/enum/Boolean tokens replaced by value exactly as old shape algorithm",
            content="old content filter retains five-grams with scalable symbolic values or fixed numeric/date/time tokens; no other catalog atom",
            classification="old decision table per pair: same-subtype content<0.12 or allowed empty; different subtype ordinary<0.20, or <0.12 for >=5/6; exact6 different-subtype forbidden",
            quantifier="No planned pair has a forced contamination violation. Pairwise lower-bound feasibility does NOT prove a simultaneous concrete assignment, future corpus acceptance, independence or scientific validity; all concrete audits still mandatory.",
            inventory="Validation report includes all14028 logical pair classifications/minima and all14 impossible classes, exact234 position pairs, weighted906 rendered pairs; 24 same-base E5 scopes separate.",
        ),
        eligible_groups=audit["infeasible_classes"],
        pre_repair_summary={k:audit[k] for k in ("infeasible_logical_pairs","infeasible_rendered_pairs")},
        preservation="All prior machine sections byte-equivalent as JSON objects except experiment.status/final_verdict; schedules/seeds/gates/call budget/authority, profiles/positions/recurrence classes, E4/E7/E5 science, exact reuse and history unchanged.",
        authority=dict(blueprint_update=False,corpus_gold_authoring=False,implementation=False,execution=False,provider_calls=0,belief_effects="none"),
        review_required=True,
    )


def validate_scaffold_amendment(contract: dict[str, Any], human: str, checks: list[str]) -> dict[str, Any]:
    amendment = contract["declared_scaffold_overlap_contract"]
    require(amendment == scaffold_contract_proposal(contract), "scaffold_exact_preregistered_contract_and_groups",checks)
    match = re.search(r"<!-- SCAFFOLD_AMENDMENT_NORMATIVE_BEGIN -->\s*```json\s*(.*?)\s*```\s*<!-- SCAFFOLD_AMENDMENT_NORMATIVE_END -->",human,re.DOTALL)
    require(match is not None and json.loads(match.group(1)) == amendment,"scaffold_human_machine_complete_equivalence",checks)
    parent = json.loads(subprocess.check_output(["git","-c","safe.directory="+ROOT.as_posix(),"show",amendment["parent_commit"]+":experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json"],cwd=ROOT))
    projected=copy.deepcopy(contract); projected.pop("declared_scaffold_overlap_contract")
    projected.pop("freshness_canonicalization_contract", None)
    projected.pop("whole_answer_canonicalization_contract", None)
    for key in ("experiment","final_verdict"):
        if key == "experiment": projected[key]["status"] = parent[key]["status"]
        else: projected[key] = parent[key]
    require(projected==parent,"scaffold_only_authorized_machine_paths_changed",checks)
    audit=scaffold_feasibility_audit(contract)
    require((audit["logical_cross_base_pairs"],audit["rendered_cross_base_pairs"],audit["infeasible_logical_pairs"],audit["infeasible_rendered_pairs"],len(audit["infeasible_classes"]))==(14028,18312,234,906,14),"scaffold_full_pre_repair_inventory",checks)
    positions={p["logical_base_id"]:p for p in load_json_unique(HERE/"blueprint"/"BLUEPRINT.json")["logical_positions"]}
    covered={frozenset(pair):g for g in amendment["eligible_groups"] for pair in g["position_pairs"]}
    post=[]
    for row in audit["all_pair_classifications"]:
        pair=frozenset((row["left"],row["right"]))
        if pair in covered:
            left,right=(positions[row[k]] for k in ("left","right"))
            a=symbolic_grams(symbolic_position_tokens(left,contract),contract,"ordinary")
            b=symbolic_grams(symbolic_position_tokens(right,contract),contract,"ordinary")
            fixed={tuple(g.split(" ")) for g in covered[pair]["forced_overlapping_five_grams"]}
            require(fixed==a&b and bool(a-fixed) and bool(b-fixed),"scaffold_fixed_intersection_proof:"+row["left"]+":"+row["right"],checks)
            facts=dict(slot_value_semantics_valid=True,exact_reuse_pass=True,raw_value_sequence_fresh=True,
                       raw_payload_equal=False,all_freshness_checks_pass=True,ordinary_grams_left=a,
                       ordinary_grams_right=b,ordinary_jaccard=float(Fraction(row["ordinary_minimum"])),content_jaccard=0)
            result=checking_pair_decision(row["left"],row["right"],left["recurrence"]["planned_six_components"],right["recurrence"]["planned_six_components"],facts,contract)
            require(result=="PERMITTED_DECLARED_SCAFFOLD","scaffold_pair_lower_bound_pass:"+row["left"]+":"+row["right"],checks)
            post.append(dict(left=row["left"],right=row["right"],residual_minimum="0",classification="NO_FORCED_VIOLATION"))
        else:
            require(row["classification"]=="FEASIBLE_WITH_EXISTING_RULES","scaffold_unrelated_pair_unchanged_feasible:"+row["left"]+":"+row["right"],checks)
    # Isolated gram-algebra mutations, not concrete fixtures or corpus authoring.
    group=next(g for g in amendment["eligible_groups"] if g["subtype_pair"]==["E5-01","E5-02"])
    lp,rp=group["position_pairs"][0];left,right=positions[lp],positions[rp]
    a=symbolic_grams(symbolic_position_tokens(left,contract),contract,"ordinary")
    b=symbolic_grams(symbolic_position_tokens(right,contract),contract,"ordinary")
    fpl,fpr=left["recurrence"]["planned_six_components"],right["recurrence"]["planned_six_components"]
    facts=dict(slot_value_semantics_valid=True,exact_reuse_pass=True,raw_value_sequence_fresh=True,
               raw_payload_equal=False,all_freshness_checks_pass=True,ordinary_grams_left=a,
               ordinary_grams_right=b,ordinary_jaccard=0.5,content_jaccard=0)
    for label,changes in (
        ("copied_non_scaffold_content",dict(ordinary_grams_right=a)),
        ("raw_value_replay",dict(raw_value_sequence_fresh=False)),
        ("raw_payload_replay",dict(raw_payload_equal=True)),
        ("identity_replay",dict(all_freshness_checks_pass=False)),
        ("whole_answer_replay",dict(exact_reuse_pass=False)),
        ("undeclared_structure",dict(slot_value_semantics_valid=False)),
    ):
        changed=dict(facts,**changes)
        require(checking_pair_decision(lp,rp,fpl,fpr,changed,contract) in {"REJECT_CONTAMINATION","AUTHORING_ERROR_STRUCTURE"},"scaffold_adversarial_reject:"+label,checks)
    u="A:R2:E3-01:PRIMARY";w="A:R2:E3-02:PRIMARY"
    require(checking_pair_decision(u,w,positions[u]["recurrence"]["planned_six_components"],positions[w]["recurrence"]["planned_six_components"],dict(facts,ordinary_jaccard=0.5),contract)=="REJECT_CONTAMINATION","scaffold_unrelated_high_overlap_rejected",checks)
    require(all(x[0]!=x[1] for g in amendment["eligible_groups"] for x in g["position_pairs"]),"scaffold_no_same_base_cf_scope",checks)
    require(within_counterfactual_exception(dict(base_position=lp,variant_id="CF1"),dict(base_position=lp,variant_id="CF2"),{lp}),"scaffold_old_same_base_exception_retained",checks)
    require(not within_counterfactual_exception(dict(base_position=lp,variant_id="CF1"),dict(base_position=rp,variant_id="CF2"),{lp,rp}),"scaffold_cross_base_not_pair_local_exception",checks)
    changed_fp=copy.deepcopy(fpr);changed_fp[2]="UNDECLARED"
    require(checking_pair_decision(lp,rp,fpl,changed_fp,facts,contract)=="AUTHORING_ERROR_STRUCTURE","scaffold_wrong_fingerprint_denied",checks)
    fixed={tuple(g.split(" ")) for g in group["forced_overlapping_five_grams"]}
    require(checking_pair_decision(lp,rp,fpl,fpr,dict(facts,ordinary_grams_right=fixed),contract)=="AUTHORING_ERROR_EMPTY_RESIDUAL","scaffold_empty_residual_not_independence",checks)
    # Exactly three shared residual windows out of 25 union windows is a reject.
    pool=[("ISOLATED_WINDOW",i) for i in range(25)]
    exact_limit=dict(facts,ordinary_grams_left=set(pool[:14]),ordinary_grams_right=set(pool[:3]+pool[14:]))
    require(checking_pair_decision(lp,rp,fpl,fpr,exact_limit,contract)=="REJECT_CONTAMINATION","scaffold_residual_strict_three_of_25_reject",checks)
    for score,expected in ((0.119,False),(0.12,True)):
        require(historical_structural_replay(b'[1,2,3]',b'[1,2,4]',score)==expected,"scaffold_historical_near_boundary:"+str(score),checks)
    require(historical_structural_replay(b'[1,2,3]',b'[1,2,3]',0),"scaffold_historical_exact_collision_reject",checks)
    require(historical_adaptation_summary(contract)["rejected"]==0,"scaffold_historical_adapter_unchanged",checks)
    audit["post_repair"]=dict(planned_pairs_without_forced_violation=14028,rendered_pairs_without_forced_violation=18312,
        remaining_forced_violations=0,bounded_pairs=post,concrete_corpus_acceptance_proven=False,
        scope="symbolic pairwise feasibility only; future actual values/freshness/independent audits remain required")
    return audit


def similarity_diagnostics(contract: dict[str, Any]) -> dict[str, Any]:
    def request(text: str, field: str, st: str="integer") -> dict[str, Any]:
        return dict(input=dict(text=text,schema={field:st}))
    a=request("f011_01 is 2. f011_02 is 3.","d011_01")
    cases={
        "A_ordinal_only":request("f095_01 is 2. f095_02 is 3.","d095_01"),
        "B_same_subtype_fresh":request("f095_01 is 4. f095_02 is 5.","d095_01"),
        "C_demonstrated_near_replay":request("f095_01 is 4. f095_02 is 5. f095_03 is 6.","d095_01"),
        "D_distinct_subtype_valid_values":request("f095_01 is 12. f095_02 is 27.","d095_01"),
    }
    output={}
    for name,b in cases.items():
        raw=gram_jaccard(comparison_grams(similarity_vector_payload(a),contract),comparison_grams(similarity_vector_payload(b),contract))
        left,right=ordinal_neutral_payload(a),ordinal_neutral_payload(b)
        normal=gram_jaccard(comparison_grams(left,contract),comparison_grams(right,contract))
        shape=gram_jaccard(comparison_grams(left,contract,"shape"),comparison_grams(right,contract,"shape"))
        content_left,content_right=comparison_grams(left,contract,"content"),comparison_grams(right,contract,"content")
        content=gram_jaccard(content_left,content_right) if content_left or content_right else None
        output[name]=dict(before=raw,ordinal_neutral=normal,shape=shape,content=content)
    # Mechanical fixed-template probes, not scored/reserve content authoring.
    a=request("f071_01 is 5. f071_02 has not been provided. f071_03 is 7.","f071_01")
    a["input"]["schema"].update(f071_02="provided|not_provided",f071_03="integer")
    b=request("f078_01 is 8. f078_02 has not been provided. f078_03 is 9.","f078_01")
    b["input"]["schema"].update(f078_02="provided|not_provided",f078_03="integer")
    left,right=ordinal_neutral_payload(a),ordinal_neutral_payload(b)
    output["E7_required_template_contradiction"]=dict(ordinal_neutral=gram_jaccard(comparison_grams(left,contract),comparison_grams(right,contract)),content=gram_jaccard(comparison_grams(left,contract,"content"),comparison_grams(right,contract,"content")))
    return output


def validate_v9(contract: dict[str, Any], checks: list[str]) -> None:
    preserved=preserved_v8_sections(contract)
    for name,identical in preserved["sections"].items():
        require(identical,"v9_preserved_parent_section:"+name,checks)
    frozen=contract["template_recurrence_contract"]; ledger=template_ledger(contract)
    require(ledger["positions"]==frozen["positions"],"v9_168_position_ledger_rederived",checks)
    require(ledger["classes"]==frozen["fingerprint_classes"],"v9_all_exact_classes_rederived",checks)
    require(len(ledger["positions"])==168,"v9_168_no_authored_content",checks)
    positions=ledger["positions"]; exact_count=0
    for left,right in itertools.combinations(positions,2):
        if left["fingerprint_class"]==right["fingerprint_class"]:
            exact_count+=1
            if not declared_template_pair(left["position"],right["position"],contract):raise AssertionError("undeclared_exact_collision")
    require(exact_count>0,"v9_all_14028_pairs_no_prohibited_exact_collision",checks)
    expected_groups={slot:dict(members=[x["position"] for x in positions if x["subtype_slot"]==slot],fingerprint_classes=sorted({x["fingerprint_class"] for x in positions if x["subtype_slot"]==slot}),maximum_members=sum(x["subtype_slot"]==slot for x in positions)) for slot in sorted({x["subtype_slot"] for x in positions})}
    require(expected_groups==frozen["subtype_template_groups"],"v9_35_template_groups_exact_members_maxima",checks)
    for key,group in ledger["classes"].items():
        require(group["maximum_recurrence_count"]==len(group["members"]) and len({x.split(':')[2] for x in group["members"]})==1,f"v9_class_maximum:{key}",checks)
    reserves=[x for x in positions if x["subtype_slot"]=="E7-01" and x["position"].endswith(":RESERVE")]
    require(len(reserves)==4 and len({x["fingerprint_class"] for x in reserves})==1,"v9_four_E7_reserves_one_exact_class",checks)
    for left,right,expected in (
        ("A:R2:E7-01:RESERVE","B:R3:E7-01:RESERVE",True),
        ("A:R2:E7-01:RESERVE","A:R3:E7-01:PRIMARY",True),
        ("A:R2:E3-01:PRIMARY","A:R2:E3-01:RESERVE",True),
        ("A:R2:E7-01:RESERVE","A:R3:E7-02:PRIMARY",False),
        ("A:R2:E1-01:PRIMARY","B:R2:E1-02:PRIMARY",False),
    ):require(declared_template_pair(left,right,contract)==expected,f"v9_scope:{left}:{right}",checks)
    pair=("A:R2:E7-01:RESERVE","B:R3:E7-01:RESERVE")
    fp=[planned_fingerprint(contract,x.rsplit(":",2)[0],x.split(':')[2],True) for x in pair]
    facts=dict(slot_value_semantics_valid=True,exact_reuse_pass=True,raw_value_sequence_fresh=True,raw_payload_equal=False,content_jaccard=0.0,ordinary_jaccard=0.272727272727)
    require(checking_pair_decision(*pair,*fp,facts,contract)=="PERMITTED_DECLARED_RECURRENCE","v9_E7_four_way_pair_content_pass",checks)
    for name,key,value,expected in (
        ("no_value_freshness","raw_value_sequence_fresh",False,"REJECT_CONTAMINATION"),
        ("identity_or_answer_reuse","exact_reuse_pass",False,"REJECT_CONTAMINATION"),
        ("raw_payload_replay","raw_payload_equal",True,"REJECT_CONTAMINATION"),
        ("content_at_threshold","content_jaccard",0.12,"REJECT_CONTAMINATION"),
        ("profile_not_validated","slot_value_semantics_valid",False,"AUTHORING_ERROR_STRUCTURE"),
        ("numeric_empty_content","content_jaccard",None,"AUTHORING_ERROR_EMPTY_CONTENT"),
    ):
        changed=dict(facts);changed[key]=value
        require(checking_pair_decision(*pair,*fp,changed,contract)==expected,"v9_pair_rule:"+name,checks)
    forged=copy.deepcopy(fp);forged[1][5][1].append(["DISTRACTOR","integer",-1])
    require(checking_pair_decision(*pair,*forged,facts,contract)=="AUTHORING_ERROR_STRUCTURE","v9_near_replay_forged_layout_not_ledger",checks)
    strings=("A:R2:E6-03:PRIMARY","B:R3:E6-03:PRIMARY")
    string_fp=[planned_fingerprint(contract,x.rsplit(':',2)[0],"E6-03",False) for x in strings]
    empty=dict(facts);empty.update(content_jaccard=None,ordinary_jaccard=1.0)
    require(checking_pair_decision(*strings,*string_fp,empty,contract)=="PERMITTED_DECLARED_RECURRENCE","v9_generated_label_NA_not_dissimilarity_claim",checks)
    different=("A:R2:E1-01:PRIMARY","B:R3:E1-02:PRIMARY")
    different_fp=[planned_fingerprint(contract,x.rsplit(':',2)[0],x.split(':')[2],False) for x in different]
    fresh=dict(facts);fresh['ordinary_jaccard']=0.0
    require(checking_pair_decision(*different,*different_fp,fresh,contract)=="PERMITTED_DISTINCT_SUBTYPE","v9_planned_boundary_variant_retains_ordinary_rule",checks)
    fresh['ordinary_jaccard']=0.12
    require(checking_pair_decision(*different,*different_fp,fresh,contract)=="REJECT_CONTAMINATION","v9_different_subtype_near_threshold_not_exempt",checks)
    for token,expected in (
        ("f001_01","f_01"),("f087_02","f_02"),("d168_02","d_02"),
        ("Entity 001 A","entity a"),("label_001_01","label_01"),("code_087_02","code_02"),("id_168_03","id_03"),
    ):
        request=dict(input=dict(text=token,schema={}))
        require(ordinal_neutral_payload(request)==expected,f"v9_mask:{token}",checks)
        require(ordinal_neutral_payload(request,True)==token.casefold(),f"v9_historical_not_masked:{token}",checks)
    x=dict(input=dict(text="f011_01 is 2.",schema={"f011_01":"integer"}))
    require("f011" not in ordinal_neutral_payload(x) and "f_01=integer" in ordinal_neutral_payload(x),"v9_schema_and_text_both_neutral",checks)
    diagnostics=similarity_diagnostics(contract)
    require(diagnostics["A_ordinal_only"]["ordinal_neutral"]==1.0,"v9_only_ordinal_cannot_hide_replay",checks)
    near=diagnostics["C_demonstrated_near_replay"]
    require(near["before"]==0 and near["ordinal_neutral"]==0 and near["shape"]>=0.12,"v9_zero_after_ordinal_requires_additional_shape_guard",checks)
    require(diagnostics["D_distinct_subtype_valid_values"]["content"]<0.12,"v9_fresh_declared_template_content_can_pass",checks)
    require(diagnostics["E7_required_template_contradiction"]["ordinal_neutral"]>=0.20 and diagnostics["E7_required_template_contradiction"]["content"]<0.12,"v9_bounded_template_correction_needed_and_sufficient_for_probe",checks)
    selected=contract["entity_selection_allocation_contract"]
    require(selector_blind_summary(selected["selected_index_matrix"])==selected["baseline_expected"],"v9_exhaustive_selector_blind_baselines",checks)
    for i in range(5):
        choices={x[i] for x in selected["selected_index_matrix"].values()}
        require(choices==set(range(3 if i in (2,4) else 2)),f"v9_E5_slot_index_coverage:{i+1}",checks)
    values=contract["value_allocation_contract"]
    require(values["context_pattern"]=={"A:R2":0,"A:R3":1,"B:R2":1,"B:R3":0},"v9_value_pattern_counterbalance",checks)
    for context in selected["selected_index_matrix"]:
        for family,rows in contract["subtype_allocation_contract"]["slot_rows"].items():
            for row in rows:
                profile=value_shape_profile(contract,context,row["slot_id"])
                require(profile["distractor_count"]==0,f"v9_exact_zero_distractors:{context}:{row['slot_id']}",checks)
                require(not any(isinstance(x,str) and x.startswith("CONTEXT_") for x in profile.values()),f"v9_profile_fully_expanded:{context}:{row['slot_id']}",checks)
                require(set(profile)==set(values["slot_profiles"][row["slot_id"]]),f"v9_profile_exact_keys:{context}:{row['slot_id']}",checks)
    for op,args,expected in (("ADD",[12,27],False),("ADD",[18,27],True),("SUM",["12.8","23.7","34.6"],True),("SUBTRACT",[98,12],False),("SUBTRACT",[92,18],True)):
        require(digit_event(args,op)==expected,f"v9_digit_event:{op}:{args}",checks)
    for token,places in (("5.0",0),("5.1",1),("5.12",2),("100.01",2)):
        require(fractional_places(token)==places,f"v9_exact_precision:{token}",checks)
    for fraction,places in ((Fraction(100,40),1),(Fraction(101,20),2)):
        require(fractional_places(exact_decimal_from_fraction(fraction))==places,f"v9_divide_exact_shape:{fraction}",checks)
    # Perturb an existing isolated numerical checking vector, not scored content.
    base=copy.deepcopy(contract["operation_semantics_contract"]["validation_vectors"][0]["fixture"])
    for fact,value in zip(base["source_fact_records"],[18,27]):fact["value"]["value"]=str(value)
    base["gold_values"][base["output_fields"][0]["name"]]=45
    slot=dict(phase="A",risk_round="R2",slot_id="E3-01")
    vector=slot_vector(base,slot)
    require(validate_v9_fixture(vector,slot,contract)==value_shape_profile(contract,"A:R2","E3-01"),"v9_actual_fixture_profile_and_ledger",checks)
    require(json.loads(reserve_profile_bytes(vector,slot,contract,True))["value_shape_profile"]==value_shape_profile(contract,"A:R2","E3-01"),"v9_profile_after_actual_value_validation",checks)
    for name,mutation in (
        ("magnitude",lambda x:x["source_fact_records"][0]["value"].update(value="8")),
        ("negative",lambda x:x["source_fact_records"][0]["value"].update(value="-18")),
        ("carry",lambda x:x["source_fact_records"][0]["value"].update(value="12")),
    ):
        broken=copy.deepcopy(vector);mutation(broken)
        a,b=[int(x["value"]["value"]) for x in broken["source_fact_records"]]
        broken["gold_values"][broken["output_fields"][0]["name"]]=a+b
        try:validate_v9_fixture(broken,slot,contract)
        except ValueError:checks.append("v9_actual_profile_reject:"+name)
        else:raise AssertionError("v9_profile_mutation_accepted:"+name)
    extra=copy.deepcopy(vector)
    fact=copy.deepcopy(extra["source_fact_records"][0]);fact.update(field_identifier=f"f{vector['lexical_context']['fixture_ordinal']:03d}_03");extra["source_fact_records"].append(fact)
    try:validate_v9_fixture(extra,slot,contract)
    except ValueError:checks.append("v9_unallocated_distractor_rejects_demonstrated_escape")
    else:raise AssertionError("v9_unallocated_distractor_accepted")
    for context,numerator,denominator in (("A:R2",100,40),("B:R2",101,20)):
        divide=copy.deepcopy(base)
        divide["operation_nodes"][0].update(id="DIVIDE",arguments={"dividend":{"kind":"field_identifier","value":"f001_01"},"divisor":{"kind":"field_identifier","value":"f001_02"}})
        divide["operation_nodes"].append(dict(id="EXACT_COPY",target="d001_02",arguments={"source_field":{"kind":"derived_field_identifier","value":"d001_01"}}))
        for fact,value in zip(divide["source_fact_records"],[numerator,denominator]):fact["value"]["value"]=str(value)
        field=divide["output_fields"][0];field.update(name="d001_02",schema_type="number",producer_target="d001_02")
        divide["gold_values"]={"d001_02":exact_decimal_from_fraction(Fraction(numerator,denominator))}
        phase,risk=context.split(":");slot=dict(phase=phase,risk_round=risk,slot_id="E3-04")
        divide=slot_vector(divide,slot)
        require(validate_v9_fixture(divide,slot,contract)==value_shape_profile(contract,context,"E3-04"),f"v9_divide_actual_profile:{context}",checks)
        broken=copy.deepcopy(divide);broken["source_fact_records"][1]["value"]["value"]="25"
        broken["gold_values"][broken["output_fields"][0]["name"]]=exact_decimal_from_fraction(Fraction(numerator,25))
        try:validate_v9_fixture(broken,slot,contract)
        except ValueError:checks.append(f"v9_divide_wrong_profile_denominator:{context}")
        else:raise AssertionError("v9_divide_wrong_complexity_accepted")
    require("prospectively shifted presentation order" in contract["ambiguity_contract"]["phase_b_interpretation"],"v9_E7_presentation_shift_not_freshness_only",checks)


def preserved_v8_sections(contract: dict[str, Any]) -> dict[str, Any]:
    parent="500f29dbfc157cd4a024976694da47e8f3e2e5b7"
    old=json.loads(subprocess.check_output(["git","show",parent+":experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json"],cwd=ROOT,text=True,encoding="utf-8"))
    names=("baseline_binding","operation_definition_contract","schema_type_contract","operation_semantics_contract","confidence_contract","integrity_event_contract","result_state_machine","model_provider","governance","historical_binding","value_allocation_contract","subtype_allocation_contract","entity_population_contract","template_recurrence_contract","ordinal_neutral_similarity_contract","historical_fingerprint_adapter_contract")
    return dict(reviewed_parent=parent,sections={name:contract[name]==old[name] for name in names})


def slot_vector(fixture: dict[str, Any], slot: dict[str, Any], reserve: bool = False) -> dict[str, Any]:
    """Reindex isolated design test vectors; never write corpus records."""
    phase, risk = slot.get("phase", "A"), slot["risk_round"]
    family, index = slot["slot_id"].split("-")
    ordinal = fixture_ordinal(phase, risk, family, int(index), reserve)
    names = list(dict.fromkeys(x["field_identifier"] for x in fixture["source_fact_records"]))
    mapping = {name: f"f{ordinal:03d}_{i:02d}" for i, name in enumerate(names, 1)}
    mapping.update({x["target"]: f"d{ordinal:03d}_{i:02d}" for i, x in enumerate(stable_topological_nodes(fixture["operation_nodes"]), 1)})
    mapping.update({x["selector_value"]: f"Entity {ordinal:03d} {chr(ord('A') + i)}" for i, x in enumerate(fixture.get("entities", []))})
    strings = list(dict.fromkeys(x["value"]["value"] for x in fixture["source_fact_records"] if x["value"] and x["value"]["kind"] == "string_literal"))
    mapping.update({value: f"{('label','code','id')[(i-1)%3]}_{ordinal:03d}_{i:02d}" for i, value in enumerate(strings, 1)})
    def renamed(value: Any) -> Any:
        if isinstance(value, dict): return {mapping.get(k, k): renamed(v) for k, v in value.items()}
        if isinstance(value, list): return [renamed(x) for x in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    result = renamed(fixture)
    result["output_fields"].sort(key=lambda x: x["name"].encode())
    result["lexical_context"] = dict(phase=phase, risk_round=risk, fixture_ordinal=ordinal, primary_family_slot=family, within_family_slot=None if reserve else index)
    return result


def new_fixture_projection(fixture: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any]) -> bytes:
    validate_subtype_fixture(fixture, slot, contract)
    context = fixture["lexical_context"]
    family_index = int(context["primary_family_slot"][1:]) - 1
    operation = contract["operation_definition_contract"]
    subject = render_subject(dict(record_type=contract["lexical_neutrality_contract"]["record_type_catalog_by_phase"][context["phase"]][family_index], nodes=fixture["operation_nodes"], include_absence_sentence=not fixture["operation_nodes"]), operation)
    request = dict(input=dict(schema={x["name"]: x["schema_type"] for x in fixture["output_fields"]}, text=" ".join(render_fact(x, operation["placeholder_type_system"], contract["schema_type_contract"]) for x in fixture["source_fact_records"])), prompt=assemble_prompt(subject, contract["baseline_binding"]))
    return historical_projection(request, contract)


def reserve_profile_bytes(fixture: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any], enforce_v9: bool = False) -> bytes:
    if enforce_v9:
        validate_v9_fixture(fixture, slot, contract)
    validate_subtype_fixture(fixture, slot, contract)
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
    context_key = f"{fixture['lexical_context']['phase']}:{fixture['lexical_context']['risk_round']}"
    if family == "E4": domain_classes["comparison_slot"] = allocation["comparison_slot_matrix"][context_key][slot_id]
    if slot_id in allocation["enum_answer_positions"][context_key]: domain_classes["enum_answer_position"] = allocation["enum_answer_positions"][context_key][slot_id]
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
        "value_shape_profile":value_shape_profile(contract, context_key, slot_id),
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
            if source["field_identifier"]=="f001_02":source.update(schema_type=vector["source"],value=dict(kind="enum_literal",value="option_a" if source["entity_selector_value"]=="Entity 001 A" else "option_b"))
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
    require(all(set(x)=={"BELOW","EQUAL","ABOVE"} for x in allocation["comparison_boundary_coverage"].values()),"comparison_boundaries_exact",checks)
    composed=[s for slots in allocation["composed_rows"].values() for s in slots]
    require(len(composed)==8 and len(set(composed))==8,"subtype_eight_distinct_composed_slots",checks)
    support_shapes=[x["domain"] for x in allocation["slot_rows"]["E7"]]
    require(len({json.dumps(x) for x in support_shapes})==5 and all(len(x)>=2 for x in support_shapes),"e7_five_support_schema_shapes",checks)
    for shape in support_shapes:
        require(all(parse_schema_type(x,schema) for x in shape),f"e7_support_schema_valid:{shape}",checks)
    # Profile equality is checked as bytes from canonical typed fixtures, not selected fields.
    numeric=copy.deepcopy(semantics["validation_vectors"][0]["fixture"])
    slot={"slot_id":"E3-01","risk_round":"R2","domain":"INTEGER_ONLY"}
    profile = lambda fixture, position, reserve=False: reserve_profile_bytes(slot_vector(fixture, position, reserve), position, contract)
    a=profile(numeric,slot)
    require(a==profile(copy.deepcopy(numeric),slot),"reserve_profile_identical_bytes",checks)
    fabricated=copy.deepcopy(slot);fabricated["domain"]="author-selected arbitrary domain"
    require(a==profile(numeric,fabricated),"reserve_domain_derived_from_frozen_matrix",checks)
    n=copy.deepcopy(numeric)
    for x in n["source_fact_records"]:x["schema_type"]="number"
    n["output_fields"][0]["schema_type"]="number"
    try: profile(n,slot)
    except ValueError: checks.append("reserve_wrong_integer_number_slot_rejected")
    else: raise AssertionError("reserve_wrong_integer_number_slot_accepted")
    m=copy.deepcopy(numeric);m["source_fact_records"][1]["schema_type"]="number";m["output_fields"][0]["schema_type"]="number"
    try: profile(m,slot)
    except ValueError: checks.append("reserve_wrong_promotion_slot_rejected")
    else: raise AssertionError("reserve_wrong_promotion_slot_accepted")
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
    require(profile(absent,absent_slot)==profile(moved,absent_slot,True),"e7_reserve_profile_preserves_types_across_frozen_order",checks)
    require(fingerprint_bytes({"fixture":absent},operation)!=fingerprint_bytes({"fixture":moved},operation),"e7_typed_layout_distinguishes_primary_reserve",checks)
    conversion = {
        "operation_nodes":[dict(id="UNIT_CONVERSION",conversion_id="HOURS_TO_MINUTES",target="d001_01",arguments={"source":dict(kind="field_identifier",value="f001_01")}),dict(id="EXACT_COPY",target="d001_02",arguments={"source_field":dict(kind="derived_field_identifier",value="d001_01")})],
        "source_fact_records":[fact("f001_01","number","decimal_literal","2.0")],"entities":[],
        "output_fields":[field("d001_02","OPERATION_TARGET","number",producer="d001_02")],"gold_values":{"d001_02":"120.0"},
    }
    cs={"slot_id":"E3-05","risk_round":"R2","domain":"UNIT_CONVERSION_TO_NUMBER"}
    c1=profile(conversion,cs)
    conversion["operation_nodes"][0]["conversion_id"]="KILOGRAMS_TO_GRAMS";conversion["gold_values"]["d001_02"]="2000.0"
    try: profile(conversion,cs)
    except ValueError: checks.append("reserve_wrong_conversion_slot_rejected")
    else: raise AssertionError("reserve_wrong_conversion_slot_accepted")
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


def validate_v8(contract: dict[str, Any], checks: list[str]) -> None:
    schema, operation, semantics = (contract[x] for x in ("schema_type_contract", "operation_definition_contract", "operation_semantics_contract"))
    allocation = contract["subtype_allocation_contract"]
    summary = historical_adaptation_summary(contract)
    require(summary["examined"] == summary["adapted"] == 106 and summary["rejected"] == 0, "historical_106_adapted_zero_rejections", checks)
    require(summary == historical_adaptation_summary(contract), "historical_projection_repeat_identical", checks)
    for binding in contract["historical_fingerprint_adapter_contract"]["artifact_bindings"]:
        rows = [x for x in load_json_unique(ROOT / binding["path"])["fixtures"] if x["task_class"] == "structured_extraction"]
        for historical in rows:
            encoded = historical_projection(historical, contract)
            require(encoded == historical_projection(historical, contract) and len(json.loads(encoded)) == 3, f"historical_projection:{binding['path']}:{historical['fixture_id']}", checks)
    historical = copy.deepcopy(rows[0])
    for name, mutation in (
        ("missing_input", lambda x: x.pop("input")),
        ("schema_not_object", lambda x: x["input"].update(schema=[])),
        ("unsupported_schema", lambda x: x["input"].update(schema={"field": "date"})),
        ("text_not_string", lambda x: x["input"].update(text=None)),
        ("empty_tokens", lambda x: x["input"].update(text="")),
        ("prompt_not_string", lambda x: x.update(prompt=None)),
        ("suffix_mismatch", lambda x: x.update(prompt="different prompt")),
    ):
        broken = copy.deepcopy(historical); mutation(broken)
        try: historical_projection(broken, contract)
        except ValueError: checks.append(f"historical_unsupported_blocks:{name}")
        else: raise AssertionError(f"historical_unsupported_accepted:{name}")
    encoded = historical_projection(historical, contract)
    changed = json.loads(encoded); changed[2] = ["unmatched_surface"]
    changed_bytes = json.dumps(changed, separators=(",", ":")).encode()
    require(historical_structural_replay(encoded, encoded, 0.0), "historical_exact_collision_even_zero_jaccard", checks)
    require(historical_structural_replay(encoded, changed_bytes, 0.12), "historical_two_of_three_at_threshold", checks)
    require(not historical_structural_replay(encoded, changed_bytes, 0.119999), "historical_two_of_three_below_threshold", checks)
    changed[1] = ["different_kind_sequence"]
    require(not historical_structural_replay(encoded, json.dumps(changed).encode(), 0.19), "historical_one_component_not_structural_replay", checks)
    require(contract["contamination_contract"]["maximum_payload_token_5gram_jaccard_exclusive"] == 0.20, "historical_shared_jaccard_unchanged", checks)
    probe = dict(input=dict(text="f001_01 for Entity 001 A is label_001_01.", schema={"f001_02": "option_a|option_b", "f001_01": "string"}), prompt="record plus hints", system="system text", input_marker="INPUT\n")
    payload = similarity_vector_payload(probe)
    require(payload == "f001_01 for entity 001 a is label_001_01. f001_01=string f001_02=option_a|option_b", "similarity_exact_input_schema_lexical_inclusion", checks)
    altered = copy.deepcopy(probe); altered.update(prompt="different SUBJECT, record type and suffix", system="different system", input_marker="different INPUT")
    require(payload == similarity_vector_payload(altered), "similarity_excludes_request_boilerplate", checks)
    altered["input"]["schema"]["f001_02"] = "option_a|option_b|option_c"
    require(payload != similarity_vector_payload(altered), "similarity_includes_schema_option_bytes", checks)

    def rejected(fixture: dict[str, Any], slot: dict[str, Any], name: str) -> None:
        try: reserve_profile_bytes(fixture, slot, contract)
        except (ValueError, KeyError): checks.append(name)
        else: raise AssertionError(name)

    def field(name: str, st: str, binding: str = "OPERATION_TARGET") -> dict[str, Any]:
        return dict(name=name, schema_type=st, required=True, binding_kind=binding, source_field=name if binding != "OPERATION_TARGET" else None, producer_target=name if binding == "OPERATION_TARGET" else None, label_removal=False, absence_capable=binding == "EXPLICIT_ABSENCE")

    def fact(name: str, st: str, kind: str, value: str, entity: str | None = None) -> dict[str, Any]:
        return dict(template_id="VALUE", field_identifier=name, schema_type=st, value=dict(kind=kind, value=value), entity_selector_value=entity)

    def raw(kind: str, value: str) -> dict[str, str]: return dict(kind=kind, value=value)

    # Mechanical type/operation vectors have no scored identity or corpus file.
    for context, rows in allocation["comparison_slot_matrix"].items():
        phase, risk = context.split(":")
        truths = []
        for slot_id, expected in rows.items():
            index = int(slot_id[-2:])
            difficulty=value_shape_profile(contract,context,slot_id)
            if index == 1:
                base = copy.deepcopy(semantics["validation_vectors"][0]["fixture"])
                operands=[18,27] if difficulty["arithmetic_complexity"]["carry"] else [12,27]
                for fact_row,operand in zip(base["source_fact_records"],operands):fact_row["value"]["value"]=str(operand)
                value, kind = str(sum(operands)), "integer_literal"
            elif index == 2:
                base = copy.deepcopy(semantics["validation_vectors"][0]["fixture"])
                base["operation_nodes"][0].update(id="SUBTRACT", arguments=dict(minuend=raw("field_identifier", "f001_01"), subtrahend=raw("field_identifier", "f001_02")))
                base["source_fact_records"][0]["value"]["value"] = "31"
                fractional="12.1" if difficulty["number_precision"]==1 else "12.12"
                base["source_fact_records"][1].update(schema_type="number", value=raw("decimal_literal", fractional))
                value, kind = exact_decimal_from_fraction(Fraction(31)-Fraction(fractional)), "decimal_literal"
            elif index == 3:
                base = copy.deepcopy(next(x["fixture"] for x in contract["contamination_contract"]["fingerprint"]["generation_test_vectors"] if x["id"] == "calendar_threshold"))
                base["operation_nodes"] = base["operation_nodes"][:1]
                base["source_fact_records"][0]["value"]["value"]="2031-02-28"
                base["operation_nodes"][0]["arguments"]["days"]["value"]="7"
                value, kind = "2031-03-07", "date_literal"
            elif index == 4:
                base = dict(operation_nodes=[dict(id="CLOCK_MINUTE_OFFSET", target="d001_01", arguments=dict(time=raw("field_identifier", "f001_01"), minutes=raw("integer_literal", "35")))], source_fact_records=[fact("f001_01", "HH:MM", "time_literal", "23:41")], entities=[])
                value, kind = "00:16", "time_literal"
            else:
                lo="20.1" if difficulty["number_precision"]==1 else "20.12"
                hi=exact_decimal_from_fraction(Fraction(lo)+1)
                base = dict(operation_nodes=[], entities=[], source_fact_records=[fact("f001_01", "number", "decimal_literal", lo), fact("f001_02", "number", "decimal_literal", lo)])
                bd = expected["boundary_relation"]
                base["source_fact_records"][0]["value"]["value"] = hi if bd == "ABOVE" else lo
                base["source_fact_records"][1]["value"]["value"] = hi if bd == "BELOW" else lo
            if index <= 4:
                bd = expected["boundary_relation"]
                if kind == "date_literal": threshold = {"ABOVE": "2031-03-06", "EQUAL": value, "BELOW": "2031-03-08"}[bd]
                elif kind == "time_literal": threshold = {"ABOVE": "00:11", "EQUAL": value, "BELOW": "00:21"}[bd]
                else: threshold = exact_decimal_from_fraction(Fraction(value) + {"ABOVE": -1, "EQUAL": 0, "BELOW": 1}[bd]) if kind == "decimal_literal" else str(int(value) + {"ABOVE": -1, "EQUAL": 0, "BELOW": 1}[bd])
                target = "d001_02"
                args = dict(left=raw("derived_field_identifier", "d001_01"), right=raw(kind, threshold))
            else:
                target = "d001_01"
                args = dict(left=raw("field_identifier", "f001_01"), right=raw("field_identifier", "f001_02"))
            base["operation_nodes"].append(dict(id=expected["operator"], target=target, arguments=args))
            base["output_fields"] = [field(target, "boolean")]
            base["gold_values"] = {target: expected["gold_boolean"]}
            slot = dict(slot_id=slot_id, phase=phase, risk_round=risk)
            vector = slot_vector(base, slot)
            validate_subtype_fixture(vector, slot, contract)
            require(validate_v9_fixture(vector,slot,contract)==difficulty,f"v9_comparison_gap_actual:{context}:{slot_id}",checks)
            require(new_fixture_projection(vector, slot, contract) == new_fixture_projection(vector, slot, contract), f"new_shared_projection:{context}:{slot_id}", checks)
            truths.append(expected["gold_boolean"])
            changed = copy.deepcopy(vector); changed["operation_nodes"][-1]["id"] = "LTE" if expected["operator"] != "LTE" else "GT"
            bd = expected["boundary_relation"]
            changed["gold_values"][changed["output_fields"][0]["name"]] = (bd != "ABOVE") if changed["operation_nodes"][-1]["id"] == "LTE" else (bd == "ABOVE")
            rejected(changed, slot, f"wrong_slot_operator:{context}:{slot_id}")
        require(sum(truths) == 3 and truths.count(False) == 2 and max(sum(truths), truths.count(False)) < 4, f"both_constants_fail_family_floor:{context}", checks)
        require({x["boundary_relation"] for x in rows.values()} == {"BELOW", "EQUAL", "ABOVE"}, f"boundary_coverage:{context}", checks)
    for slot_id in allocation["comparison_slot_matrix"]["A:R2"]:
        require({x[slot_id]["gold_boolean"] for x in allocation["comparison_slot_matrix"].values()} == {True, False}, f"operator_truth_rotates:{slot_id}", checks)

    for context in allocation["enum_answer_positions"]:
        phase, risk = context.split(":")
        for row in allocation["slot_rows"]["E5"]:
            slot_id, st = row["slot_id"], row["domain"]
            count = int(row["coverage_class"].split(":")[0].split("_")[1]); role = row["coverage_class"].split(":")[1]
            selected = contract["entity_selection_allocation_contract"]["selected_index_matrix"][context][int(slot_id[-2:])-1]
            labels = [f"Entity 001 {chr(65+i)}" for i in range(count)]
            entities = [dict(selector_value=x, selector_role=role) for x in labels]
            selectors = [fact("f001_01", "string", "entity_selector_literal", x, x) for x in labels]
            profile=value_shape_profile(contract,context,slot_id)
            if st == "number":
                kind="decimal_literal"
                suffix=".1" if profile["number_precision"]==1 else ".12"
                sorted_vals=[str(20+2*i)+suffix for i in range(count)]
                vals=[sorted_vals[(i-selected+profile["entity_selected_rank"])%count] for i in range(count)]
            elif st == "string": kind, vals = "string_literal", [f"{('label','code','id')[i]}_001_{i+1:02d}" for i in range(count)]
            elif st == "YYYY-MM-DD":
                kind="date_literal"; sorted_vals=[f"2031-01-{1+2*i:02d}" for i in range(count)]
                vals=[sorted_vals[(i-selected+profile["entity_selected_rank"])%count] for i in range(count)]
            elif st == "HH:MM":
                kind="time_literal"; sorted_vals=[f"08:{1+13*i:02d}" for i in range(count)]
                vals=[sorted_vals[(i-selected+profile["entity_selected_rank"])%count] for i in range(count)]
            else:
                kind = "enum_literal"; gi = allocation["enum_answer_positions"][context][slot_id]
                vals = [st.split("|")[(i-selected+gi)%count] for i in range(count)]
            sources = [fact("f001_02", st, kind, val, entity) for val, entity in zip(vals, labels)]
            base = dict(entities=entities, source_fact_records=selectors+sources, operation_nodes=[dict(id="ENTITY_FIELD_BIND", target="d001_01", arguments=dict(source_field=raw("field_identifier", "f001_02"), selector_field=raw("field_identifier", "f001_01"), selector_value=raw("entity_selector_literal", labels[selected])))], output_fields=[field("d001_01", st)], gold_values={"d001_01":vals[selected]})
            slot = dict(slot_id=slot_id, phase=phase, risk_round=risk); vector = slot_vector(base, slot)
            validate_subtype_fixture(vector, slot, contract)
            require(validate_v9_fixture(vector,slot,contract)==profile,f"v9_entity_separation_rank_actual:{context}:{slot_id}",checks)
            validate_counterfactual_vector(vector, slot, contract, checks)
            if slot_id == "E5-01":
                reserve_vector = slot_vector(base, slot, reserve=True)
                validate_counterfactual_vector(reserve_vector, slot, contract, checks)
                require(counterfactual_reserve_profile(vector, slot, contract) == counterfactual_reserve_profile(reserve_vector, slot, contract), f"v10_whole_pair_reserve_equivalence:{context}", checks)
            atoms=extract_date_number_atoms(vector,operation,schema,semantics,contract["entity_population_contract"])
            expected_atom_count=count+2 if st in {"number","YYYY-MM-DD","HH:MM"} else 0
            require(len(atoms)==expected_atom_count,f"v9_entity_contamination_operand_resolution:{context}:{slot_id}",checks)
            require("AUTHORING_ERROR" not in fingerprint_bytes(dict(fixture=vector), operation), f"entity_slot_typed_fingerprint:{context}:{slot_id}", checks)
            for i in range(count):
                if i == selected: continue
                wrong = copy.deepcopy(vector)
                source = [x for x in wrong["source_fact_records"] if x["field_identifier"] == wrong["operation_nodes"][0]["arguments"]["source_field"]["value"]][i]
                wrong["gold_values"][wrong["output_fields"][0]["name"]] = source["value"]["value"]
                rejected(wrong, slot, f"wrong_entity_value_fails_gold:{context}:{slot_id}:{i}")
            duplicate = copy.deepcopy(vector)
            sf = [x for x in duplicate["source_fact_records"] if x["field_identifier"] == duplicate["operation_nodes"][0]["arguments"]["source_field"]["value"]]
            sf[-1]["value"] = copy.deepcopy(sf[0]["value"])
            rejected(duplicate, slot, f"equal_entity_values_rejected:{context}:{slot_id}")
            if slot_id == "E5-01":
                boolean_source = copy.deepcopy(vector)
                source_name = boolean_source["operation_nodes"][0]["arguments"]["source_field"]["value"]
                source_fields = [x for x in boolean_source["source_fact_records"] if x["field_identifier"] == source_name]
                for i, source in enumerate(source_fields): source.update(schema_type="boolean", value=raw("boolean_literal", "true" if i == 0 else "false"))
                boolean_source["output_fields"][0]["schema_type"] = "boolean"
                boolean_source["gold_values"][boolean_source["output_fields"][0]["name"]] = selected == 0
                try: validate_fixture_semantics(boolean_source, schema, operation, semantics, contract["entity_population_contract"])
                except ValueError as error: require(str(error) == "entity_boolean_source_prohibited", f"boolean_entity_source_prohibited:{context}", checks)
                else: raise AssertionError("boolean_entity_source_accepted")
            if slot_id == "E5-03":
                wrong = copy.deepcopy(vector)
                source_fields = [x for x in wrong["source_fact_records"] if x["field_identifier"] == wrong["operation_nodes"][0]["arguments"]["source_field"]["value"]]
                for source in source_fields:
                    options = source["schema_type"].split("|")
                    source["value"]["value"] = options[(options.index(source["value"]["value"])+1)%3]
                wrong["gold_values"][wrong["output_fields"][0]["name"]] = source_fields[selected]["value"]["value"]
                rejected(wrong, slot, f"wrong_enum_gold_position:{context}:{slot_id}")

        for row in allocation["slot_rows"]["E7"]:
            profile=value_shape_profile(contract,context,row["slot_id"])
            facts = [dict(template_id="EXPLICIT_ABSENCE", field_identifier="f001_01", schema_type="provided|not_provided", value=None, entity_selector_value=None)]
            gold = {"f001_01":"not_provided"}
            for i, st in enumerate(row["domain"], 2):
                if st == "integer": kind,val="integer_literal",str(i+2)
                elif st == "number": kind,val="decimal_literal","20.1" if profile["number_precision"]==1 else "20.12"
                elif st == "string": kind,val="string_literal","label_001_01"
                elif st == "boolean": kind,val="boolean_literal","true" if contract["value_allocation_contract"]["e7_boolean_source_allocation"][context] else "false"
                elif st == "YYYY-MM-DD": kind,val="date_literal","2031-01-01"
                elif st == "HH:MM": kind,val="time_literal","08:11"
                else: kind,val="enum_literal",st.split("|")[allocation["enum_answer_positions"][context][row["slot_id"]]]
                facts.append(fact(f"f001_{i:02d}",st,kind,val))
                gold[f"f001_{i:02d}"]=int(val) if st == "integer" else val == "true" if st == "boolean" else val
            if phase == "B": facts = facts[1:]+facts[:1]
            base = dict(operation_nodes=[], entities=[], source_fact_records=facts, output_fields=[field(name, next(x["schema_type"] for x in facts if x["field_identifier"]==name), "EXPLICIT_ABSENCE" if name=="f001_01" else "SOURCE_COPY") for name in sorted(gold)], gold_values=gold)
            slot = dict(slot_id=row["slot_id"],phase=phase,risk_round=risk); vector=slot_vector(base,slot)
            validate_subtype_fixture(vector,slot,contract)
            require(validate_v9_fixture(vector,slot,contract)==profile,f"v9_e7_actual_support_value_profile:{context}:{row['slot_id']}",checks)
            require(len(json.loads(new_fixture_projection(vector,slot,contract)))==3,f"e7_integrated_slot:{context}:{row['slot_id']}",checks)
            wrong=copy.deepcopy(vector);wrong["source_fact_records"].reverse();wrong=slot_vector(wrong,slot)
            rejected(wrong,slot,f"e7_wrong_presentation:{context}:{row['slot_id']}")
            wrong=copy.deepcopy(vector);wrong["lexical_context"]["fixture_ordinal"]+=1
            rejected(wrong,slot,f"e7_wrong_lexical_context:{context}:{row['slot_id']}")
            wrong=copy.deepcopy(vector);support=next(x for x in wrong["source_fact_records"] if x["template_id"]=="VALUE")
            support["schema_type"]="string";support["value"]=raw("string_literal","label_001_99")
            rejected(wrong,slot,f"e7_wrong_support_shape:{context}:{row['slot_id']}")
            if row["slot_id"] == "E7-04":
                wrong = copy.deepcopy(vector)
                enum_fact = next(x for x in wrong["source_fact_records"] if x["schema_type"] == "option_a|option_b")
                enum_fact["value"]["value"] = "option_b" if enum_fact["value"]["value"] == "option_a" else "option_a"
                wrong["gold_values"][enum_fact["field_identifier"]] = enum_fact["value"]["value"]
                rejected(wrong, slot, f"wrong_enum_gold_position:{context}:{row['slot_id']}")
            if row["slot_id"]=="E7-01":
                reserve_base=copy.deepcopy(base)
                absent=next(x for x in reserve_base["source_fact_records"] if x["template_id"]=="EXPLICIT_ABSENCE")
                support=[x for x in reserve_base["source_fact_records"] if x["template_id"]=="VALUE"]
                reserve_base["source_fact_records"]=[support[0],absent,*support[1:]]
                reserved=slot_vector(reserve_base,slot,True)
                require(reserve_profile_bytes(vector,slot,contract,True)==reserve_profile_bytes(reserved,slot,contract,True),f"e7_matched_reserve_profile:{context}",checks)

    numeric=copy.deepcopy(semantics["validation_vectors"][0]["fixture"])
    slot=dict(slot_id="E3-01",phase="A",risk_round="R2")
    wrong=copy.deepcopy(numeric)
    for x in wrong["source_fact_records"]:x["schema_type"]="number"
    wrong["output_fields"][0]["schema_type"]="number"
    rejected(slot_vector(wrong,slot),slot,"subtype_INTEGER_ONLY_rejects_NUMBER_ONLY")
    calendar=copy.deepcopy(semantics["validation_vectors"][5]["fixture"])
    calendar_slot=dict(slot_id="E1-03",phase="A",risk_round="R2")
    rejected(slot_vector(calendar,calendar_slot),calendar_slot,"subtype_year_boundary_rejects_other_actual_boundary")
    for vector in contract["reserve_activation_contract"]["test_vectors"]:
        require(reserve_decision(vector)==vector["expected"],f"v8_reserve:{vector['id']}",checks)
    for phase in "AB":
        for risk in ("R2","R3"):
            for family in range(1,8):
                for index in range(2,6):
                    claim=f"{phase}-{risk}-E{family}-{index:02d}"
                    require(reserve_decision(dict(defective_primary_ids=[claim],profile_matches=[claim]))=="STOP_AUTHORING",f"uncovered_reserve_forced_stop:{claim}",checks)
    for vector in contract["contamination_contract"]["exact_reuse_contract"]["test_vectors"]:
        for key in ("left_atoms","right_atoms"):
            for atom in vector.get(key,[]):
                if atom[0] in {"IDENTIFIER","ENTITY"}:require(len(atom)==2,"canonical_identity_two_strings",checks)
    for atom in (["IDENTIFIER", "old_field", "value"], ["ENTITY"], ["ENTITY", 1]):
        try: identity_reuse([atom], [])
        except ValueError: checks.append(f"noncanonical_identity_rejected:{atom}")
        else: raise AssertionError("noncanonical_identity_accepted")


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


COUNTERFACTUAL_AUDITS: list[dict[str, Any]] = []


def counterfactual_members(anchor: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Transform existing isolated design vectors in memory, never author corpus files."""
    validate_v9_fixture(anchor, slot, contract)
    context = slot['phase'] + ':' + slot['risk_round']
    indices = contract['e5_counterfactual_selector_contract']['selector_pair_matrix'][context][int(slot['slot_id'][-2:])-1]
    first, second = copy.deepcopy(anchor), copy.deepcopy(anchor)
    node = second['operation_nodes'][0]
    node['arguments']['selector_value']['value'] = second['entities'][indices[1]]['selector_value']
    selected = next(x for x in second['source_fact_records'] if x['field_identifier'] == node['arguments']['source_field']['value'] and x['entity_selector_value'] == node['arguments']['selector_value']['value'])
    second['gold_values'][second['output_fields'][0]['name']] = selected['value']['value']
    return [first, second]


def counterfactual_request(fixture: dict[str, Any], model: str, seed: int, contract: dict[str, Any]) -> tuple[bytes, int, int, bytes]:
    operation = contract['operation_definition_contract']
    record_type = contract['lexical_neutrality_contract']['record_type_catalog_by_phase'][fixture['lexical_context']['phase']][4]
    subject = render_subject(dict(record_type=record_type, nodes=fixture['operation_nodes']), operation)
    prompt = assemble_prompt(subject, contract['baseline_binding'])
    source = ' '.join(render_fact(x, operation['placeholder_type_system'], contract['schema_type_contract']) for x in fixture['source_fact_records'])
    input_object = dict(schema={x['name']:x['schema_type'] for x in fixture['output_fields']}, text=source)
    user = prompt + '\n\nINPUT:\n' + json.dumps(input_object, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    options = dict(load_json_unique(ROOT / 'experiments/G-ROUTE4-candidate/model_bindings.json')['generation_configuration']['options'])
    options['seed'] = seed
    body = dict(model=model, system=contract['baseline_binding']['system_text'], prompt=user, stream=False, think=False, options=options)
    # Execute only the two read-only bound builder definitions, not a runtime module.
    source_ast = ast.parse((ROOT / 'tools/g_route4_contract.py').read_text(encoding='utf-8'))
    definitions = [x for x in source_ast.body if isinstance(x, ast.FunctionDef) and x.name in {'render_prompt','request_body'}]
    namespace = dict(json=json, Mapping=dict, Any=Any, load_json=load_json_unique,
                     PROMPT_PROFILES_PATH=ROOT / 'experiments/G-ROUTE1-candidate/prompt_profiles.json',
                     load_model_bindings=lambda:load_json_unique(ROOT / 'experiments/G-ROUTE4-candidate/model_bindings.json'))
    exec(compile(ast.Module(body=definitions,type_ignores=[]), '<bound read-only request builders>', 'exec'), namespace)
    historical_body = namespace['request_body'](dict(prompt=prompt,input=input_object,validator_profile='extraction.v1'),dict(model=model,seed=seed))
    if body != historical_body:
        raise ValueError('counterfactual_historical_request_builder_mismatch')
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    node = fixture['operation_nodes'][0]
    # E5 is a single bind node with selector placeholder at the end of SUBJECT.
    selector = render_operand(node['arguments']['selector_value'], operation['placeholder_type_system'])
    if not subject.endswith(selector):
        raise ValueError('selector_span_not_terminal_subject')
    prefix = subject[:-len(selector)]
    wire_prefix = json.dumps(prefix, ensure_ascii=False, separators=(',', ':'))[1:-1].encode('utf-8')
    wire_selector = json.dumps(selector, ensure_ascii=False, separators=(',', ':'))[1:-1].encode('utf-8')
    start = encoded.index(b'"prompt":') + len(b'"prompt":') + 1 + len(wire_prefix)
    end = start + len(wire_selector)
    if encoded[start:end] != wire_selector:
        raise ValueError('selector_span_serialization')
    return encoded, start, end, wire_selector


def audit_counterfactual(first: dict[str, Any], second: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any], model: str, repeat: int) -> dict[str, Any]:
    validate_v9_fixture(first, slot, contract)
    expected = counterfactual_members(first, slot, contract)[1]
    if second != expected:
        raise ValueError('counterfactual_unpermitted_fixture_difference')
    validate_fixture_semantics(second, contract['schema_type_contract'], contract['operation_definition_contract'], contract['operation_semantics_contract'], contract['entity_population_contract'])
    gold = [canonical_answer_bytes({x['name']:dict(schema_type=x['schema_type'], value=f['gold_values'][x['name']]) for x in f['output_fields']}, contract['schema_type_contract']) for f in (first, second)]
    if gold[0] == gold[1]:
        raise ValueError('counterfactual_identical_gold')
    context = first['lexical_context']
    seed = contract['sampling']['candidate_phase_' + slot['phase'].lower() + '_seed_base'] + (context['fixture_ordinal']-1)*10 + repeat
    left = counterfactual_request(first, model, seed, contract)
    right = counterfactual_request(second, model, seed, contract)
    lb, ls, le, lv = left; rb, rs, re_, rv = right
    mask = b'<SELECTOR_REQUEST>'
    lm, rm = lb[:ls]+mask+lb[le:], rb[:rs]+mask+rb[re_:]
    if lv == rv or lm != rm or lb[:ls] != rb[:rs] or lb[le:] != rb[re_:]:
        raise ValueError('counterfactual_request_difference')
    base_id = f"{slot['phase']}:{slot['risk_round']}:{slot['slot_id']}:{'RESERVE' if context['within_family_slot'] is None else 'PRIMARY'}"
    return dict(base_position=base_id, base_fixture_id=base_id, variant_ids=['CF1','CF2'], model=model, repeat=repeat, seed=seed,
                selector_spans=[[ls,le],[rs,re_]], selector_bytes=[lv.decode(),rv.decode()],
                differing_byte_offsets=[i for i,(a,b) in enumerate(zip(lb,rb)) if a!=b],
                request_sha256=[hashlib.sha256(x).hexdigest() for x in (lb,rb)], masked_sha256=hashlib.sha256(lm).hexdigest(),
                masked_bytes_equal=True, gold_distinct=True, exact_diff_only_selector=True)


def counterfactual_reserve_profile(anchor: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any]) -> bytes:
    members = counterfactual_members(anchor, slot, contract)
    audit_counterfactual(*members, slot, contract, contract['model_provider']['models'][0]['model'], 1)
    context = slot['phase'] + ':' + slot['risk_round']
    indices = contract['e5_counterfactual_selector_contract']['selector_pair_matrix'][context][int(slot['slot_id'][-2:])-1]
    base = json.loads(reserve_profile_bytes(anchor, slot, contract, True))
    return json.dumps(dict(base_profile=base, selector_transition=indices, variants=['CF1','CF2'], invariant_request_required=True, distinct_gold_required=True), ensure_ascii=True, separators=(',', ':')).encode('utf-8')


def reduce_counterfactual(values: list[bool], phase: str, adverse: bool = False) -> bool:
    if phase not in {'A','B'} or len(values) != (4 if phase == 'A' else 2) or any(type(x) is not bool for x in values):
        raise ValueError('counterfactual_denominator')
    return any(values) if adverse else all(values)


def within_counterfactual_exception(left: dict[str, str], right: dict[str, str], validated_pairs: set[str]) -> bool:
    return (left['base_position'] in validated_pairs and left['base_position'] == right['base_position']
            and {left['variant_id'], right['variant_id']} == {'CF1','CF2'} and ':E5-' in left['base_position'])


def validate_counterfactual_vector(anchor: dict[str, Any], slot: dict[str, Any], contract: dict[str, Any], checks: list[str]) -> None:
    members = counterfactual_members(anchor, slot, contract)
    context = slot['phase'] + ':' + slot['risk_round']
    reserve = anchor['lexical_context']['within_family_slot'] is None
    tag = context + ':' + slot['slot_id'] + (':RESERVE' if reserve else ':PRIMARY')
    for repeat in range(1, 3 if slot['phase']=='A' else 2):
        for binding in contract['model_provider']['models']:
            result = audit_counterfactual(*members, slot, contract, binding['model'], repeat)
            require(result['masked_bytes_equal'] and result['gold_distinct'], 'v10_bytes_and_gold:' + tag + ':' + binding['tier'] + ':' + str(repeat), checks)
            require(all(result['selector_spans'][0][0] <= i < result['selector_spans'][0][1] for i in result['differing_byte_offsets']), 'v10_exact_diff_offsets:' + tag + ':' + binding['tier'] + ':' + str(repeat), checks)
            if binding['tier']=='small' and repeat==1:
                COUNTERFACTUAL_AUDITS.append(result)
    require(members[0]['lexical_context']==members[1]['lexical_context'] and members[0]['source_fact_records']==members[1]['source_fact_records'] and members[0]['output_fields']==members[1]['output_fields'], 'v10_identifiers_source_schema_identical:' + tag, checks)
    require(fingerprint_bytes(dict(fixture=members[0]),contract['operation_definition_contract'])==fingerprint_bytes(dict(fixture=members[1]),contract['operation_definition_contract']), 'v10_fingerprint_ignores_selector_choice:' + tag, checks)
    first_request = counterfactual_request(members[0], contract['model_provider']['models'][0]['model'], 1, contract)
    second_request = counterfactual_request(members[1], contract['model_provider']['models'][0]['model'], 1, contract)
    lbytes,ls,le,_ = first_request; rbytes,rs,re_,_ = second_request
    masked = lbytes[:ls]+b'<SELECTOR_REQUEST>'+lbytes[le:]
    for name, change in (
        ('seed', lambda body:body['options'].update(seed=2)),
        ('model', lambda body:body.update(model='unbound')),
        ('system', lambda body:body.update(system=body['system']+' ')),
        ('source_selector', lambda body:body.update(prompt=body['prompt'].replace('INPUT:', 'INPUT: '))),
        ('metadata_header', lambda body:body.update(variant_id='CF2')),
    ):
        changed=json.loads(rbytes);change(changed)
        changed_bytes=json.dumps(changed,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        require(changed_bytes[:rs]+b'<SELECTOR_REQUEST>'+changed_bytes[re_:]!=masked, 'v10_nonselector_byte_mutation_denied:'+tag+':'+name, checks)
    for name, mutate in (
        ('schema', lambda x:x['output_fields'][0].update(schema_type='integer')),
        ('source', lambda x:x['source_fact_records'][0]['value'].update(value='Entity 001 C')),
        ('order', lambda x:x['source_fact_records'].reverse()),
        ('ordinal', lambda x:x['lexical_context'].update(fixture_ordinal=169)),
        ('gold', lambda x:x.update(gold_values=copy.deepcopy(members[0]['gold_values']))),
    ):
        broken=copy.deepcopy(members[1]);mutate(broken)
        try:audit_counterfactual(members[0],broken,slot,contract,contract['model_provider']['models'][0]['model'],1)
        except ValueError:checks.append('v10_pair_mutation_rejected:'+tag+':'+name)
        else:raise AssertionError('counterfactual_mutation_accepted:'+name)
    if reserve:
        require(slot['slot_id']=='E5-01','v10_reserve_slot01_pair:'+context,checks)


def expanded_variant_ledger(contract: dict[str, Any]) -> list[dict[str, str]]:
    return [dict(base_position=x['position'], variant_id=v, fingerprint_class=x['fingerprint_class'])
            for x in template_ledger(contract)['positions'] for v in (['CF1','CF2'] if x['subtype_slot'].startswith('E5-') else ['SINGLE'])]


def validate_v10(contract: dict[str, Any], checks: list[str]) -> None:
    pair=contract['e5_counterfactual_selector_contract']
    require(pair['contract_id']=='g-extract1.e5-counterfactual-selector.v1','v10_counterfactual_contract',checks)
    expected={c:[[i,(i+1)%(3 if j in (2,4) else 2)] for j,i in enumerate(row)] for c,row in contract['entity_selection_allocation_contract']['selected_index_matrix'].items()}
    require(pair['selector_pair_matrix']==expected,'v10_frozen_ordered_selector_matrix',checks)
    require(pair['qualification_unit']==['model','risk_round','phase'],'v10_actual_cell_unit_no_round_pooling',checks)
    for phase in ('A','B'):
        for truth in itertools.product((False,True),repeat=4 if phase=='A' else 2):
            require(reduce_counterfactual(list(truth),phase)==all(truth),'v10_positive_truth:'+phase+str(truth),checks)
            require(reduce_counterfactual(list(truth),phase,True)==any(truth),'v10_adverse_truth:'+phase+str(truth),checks)
        gate=contract['cell_gates']['phase_'+phase.lower()]['e5_counterfactual_pairs']
        require(gate['minimum_correct_pairs']==gate['denominator_logical_pairs']==5 and gate['required_observations_per_pair']==(4 if phase=='A' else 2),'v10_strict_pair_gate:'+phase,checks)
        required = 4 if phase=='A' else 2
        for missing in range(required):
            obs=[True]*required;obs[missing]=False
            require(not reduce_counterfactual(obs,phase),'v10_no_best_of_or_partial_credit:'+phase+str(missing),checks)
    require(len(COUNTERFACTUAL_AUDITS)==24 and len({x['base_position'] for x in COUNTERFACTUAL_AUDITS})==24,'v10_20_scored_4_reserve_design_vectors_only',checks)
    # An arbitrary deterministic answer for a shared masked key cannot equal both distinct golds.
    for row in COUNTERFACTUAL_AUDITS:
        require(row['masked_bytes_equal'] and row['gold_distinct'],'v10_lookup_incompatibility:'+row['base_position'],checks)
    variants=expanded_variant_ledger(contract);validated={x['base_position'] for x in COUNTERFACTUAL_AUDITS}
    exceptions=0; cross_pairs=0
    for left,right in itertools.combinations(variants,2):
        if within_counterfactual_exception(left,right,validated):exceptions+=1
        else:
            cross_pairs+=1
            if left['fingerprint_class']==right['fingerprint_class']:
                require(declared_template_pair(left['base_position'],right['base_position'],contract),'v10_cross_base_recurrence:'+left['base_position']+':'+right['base_position'],checks)
    require((len(variants),exceptions,cross_pairs)==(192,24,18312),'v10_expanded_scope_accounting',checks)
    require(contract['counterfactual_accounting']['structural_pairs']==18336 and contract['counterfactual_accounting']['cross_base_variant_pairs']==cross_pairs,'v10_machine_pair_counts',checks)
    for name,left,right in (
        ('same_variant',dict(base_position='A:R2:E5-01:PRIMARY',variant_id='CF1'),dict(base_position='A:R2:E5-01:PRIMARY',variant_id='CF1')),
        ('other_base',dict(base_position='A:R2:E5-01:PRIMARY',variant_id='CF1'),dict(base_position='B:R2:E5-01:PRIMARY',variant_id='CF2')),
        ('other_family',dict(base_position='A:R2:E4-01:PRIMARY',variant_id='CF1'),dict(base_position='A:R2:E4-01:PRIMARY',variant_id='CF2')),
        ('primary_reserve',dict(base_position='A:R2:E5-01:PRIMARY',variant_id='CF1'),dict(base_position='A:R2:E5-01:RESERVE',variant_id='CF2')),
    ):require(not within_counterfactual_exception(left,right,validated),'v10_no_exception_leak:'+name,checks)
    require(contract['corpus']['rendered_scored_variants']==160 and contract['corpus']['rendered_reserve_variants']==32,'v10_logical_vs_rendered_counts',checks)
    require(contract['efficiency']['phase_a_calls']==480 and contract['efficiency']['phase_b_maximum_calls']==240,'v10_efficiency_calls',checks)
    for phase in ('A','B'):
        scored=[x for x in variants if x['base_position'].startswith(phase+':') and x['base_position'].endswith(':PRIMARY')]
        require(len(scored)==80,'v10_rendered_phase_scored:'+phase,checks)
        for risk in ('R2','R3'):
            cell=[x for x in scored if x['base_position'].startswith(phase+':'+risk+':')]
            require(len(cell)==40 and len({x['base_position'] for x in cell})==35,'v10_actual_cell_denominators:'+phase+':'+risk,checks)
        # Per model, only the two variants of one base/repeat may intentionally collide.
        seeds={}
        for row in scored:
            _,risk,slot,kind=row['base_position'].split(':')
            family,index=slot.split('-');ordinal=fixture_ordinal(phase,risk,family,int(index),False)
            for repeat in range(1,3 if phase=='A' else 2):
                seed=contract['sampling']['candidate_phase_'+phase.lower()+'_seed_base']+(ordinal-1)*10+repeat
                seeds.setdefault(seed,[]).append((row['base_position'],row['variant_id'],repeat))
        for seed,rows in seeds.items():
            require(len(rows)==1 or len(rows)==2 and rows[0][0]==rows[1][0] and {x[1] for x in rows}=={'CF1','CF2'} and rows[0][2]==rows[1][2], 'v10_exact_seed_collision_scope:'+phase+str(seed),checks)


def validate_output_field_amendment(
    contract: dict[str, Any], human: str, checks: list[str],
) -> dict[str, Any]:
    amendment = contract["output_field_amendment_contract"]
    require(amendment["contract_id"] == "g-extract1.output-field-amendment.v1", "output_amendment_id", checks)
    require(amendment["accepted_v10_commit"] == "394d24121309ec9dce80e725b50dbe5eb60f6d2a", "output_amendment_parent", checks)
    require(amendment["reviewed_blueprint_commit"] == "99707b4f13abd6533f1d09313bdb066793996be9", "output_amendment_blueprint_untouched", checks)
    require(amendment["scope"] == dict(
        scored_logical_bases=140, reserve_logical_bases=28, rendered_variants=192,
        all_output_fields=True, all_schema_types_and_output_roles=True,
        e5_members=["CF1", "CF2"], all_e7_outputs=True,
    ), "output_amendment_universal_scope", checks)
    require(amendment["global_constants"] == dict(required=True, label_removal=False), "output_amendment_constants", checks)
    expected_keys = ["name", "schema_type", "required", "binding_kind", "source_field", "producer_target", "label_removal", "absence_capable"]
    require(amendment["exact_output_field_keys"] == expected_keys, "output_amendment_eight_keys", checks)
    identifiers = {
        "SOURCE_COPY": "$generated_source_field_identifier",
        "OPERATION_TARGET": "$generated_operation_target",
        "EXPLICIT_ABSENCE": "$generated_explicit_absence_field_identifier",
    }
    expected_templates = {}
    for binding, identifier in identifiers.items():
        expected_templates[binding] = dict(
            name=identifier,
            schema_type="provided|not_provided" if binding == "EXPLICIT_ABSENCE" else "$exact_producer_result_schema" if binding == "OPERATION_TARGET" else "$exact_bound_source_schema",
            required=True, binding_kind=binding,
            source_field=None if binding == "OPERATION_TARGET" else identifier,
            producer_target=identifier if binding == "OPERATION_TARGET" else None,
            label_removal=False, absence_capable=binding == "EXPLICIT_ABSENCE",
        )
    require(amendment["binding_construction"] == expected_templates, "output_amendment_exact_templates", checks)
    require(amendment["author_selectable_output_fields"] == [], "output_amendment_no_author_choice", checks)
    require(amendment["output_role_separate_metadata"] and amendment["output_role_derivation_unchanged"], "output_amendment_roles_separate", checks)
    require(amendment["scoring"] == dict(
        leading_label_normalization_permitted=False,
        string_entity_equality="exact case, whitespace, punctuation and Unicode scalar sequence",
        labels_not_stripped=["the", "Order", "Vendor"],
        general_historical_comparator_capability_removed=False,
        historical_operational_validator_changed=False,
    ), "output_amendment_exact_strings_no_historical_change", checks)
    for key in ("blueprint_update_authorized_by_this_amendment", "corpus_gold_authoring_authorized", "implementation_authorized", "execution_authorized"):
        require(amendment[key] is False, "output_amendment_no_authority:" + key, checks)

    # Check preservation against the accepted artifact, not a copy of today's contract.
    accepted = json.loads(subprocess.check_output([
        "git", "-c", "safe.directory=" + ROOT.as_posix(), "show",
        amendment["accepted_v10_commit"] + ":experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json",
    ], cwd=ROOT, encoding="utf-8"))
    before_keys = set(accepted)
    expected = copy.deepcopy(accepted)
    expected["output_field_amendment_contract"] = amendment
    expected["experiment"]["status"] = "READY_FOR_G_EXTRACT1_OUTPUT_FIELD_AMENDMENT_REREVIEW"
    expected["final_verdict"] = "READY_FOR_G_EXTRACT1_OUTPUT_FIELD_AMENDMENT_REREVIEW"
    field_contract = expected["family_assignment_contract"]["canonical_output_field_contract"]
    field_contract.update(required=True, label_removal=False, construction_contract_ref="output_field_amendment_contract")
    rules = expected["exact_value_contract"]["semantic_rules"]
    rules.update(g_extract1_output_field_contract_ref="output_field_amendment_contract", g_extract1_leading_label_normalization_permitted=False)
    projection = copy.deepcopy(contract)
    projection.pop("freshness_canonicalization_contract", None)
    projection.pop("whole_answer_canonicalization_contract", None)
    if "declared_scaffold_overlap_contract" in projection:
        projection.pop("declared_scaffold_overlap_contract")
        projection["experiment"]["status"] = expected["experiment"]["status"]
        projection["final_verdict"] = expected["final_verdict"]
    require(projection == expected, "output_amendment_only_authorized_machine_paths_changed", checks)
    unchanged = sorted(key for key in before_keys if accepted[key] == contract[key])
    for key in unchanged:
        require(accepted[key] == contract[key], "output_amendment_preserved_section:" + key, checks)

    match = re.search(r"<!-- OUTPUT_FIELD_AMENDMENT_NORMATIVE_BEGIN -->\s*```json\s*(.*?)\s*```\s*<!-- OUTPUT_FIELD_AMENDMENT_NORMATIVE_END -->", human, re.DOTALL)
    require(match is not None, "output_amendment_human_annex_present", checks)
    require(json.loads(match.group(1)) == dict(
        output_field_amendment_contract=amendment,
        canonical_output_field_contract=contract["family_assignment_contract"]["canonical_output_field_contract"],
        exact_value_semantic_rules=contract["exact_value_contract"]["semantic_rules"],
    ), "output_amendment_exact_human_machine_objects", checks)

    schema = contract["schema_type_contract"]
    bases, variants, output_count, scored, reserves = 0, 0, 0, 0, 0
    coverage: set[tuple[str, str, str]] = set()
    for row in contract["template_recurrence_contract"]["positions"]:
        phase, risk, slot, kind = row["position"].split(":")
        family, index = slot.split("-")
        reserve = kind == "RESERVE"
        ordinal = fixture_ordinal(phase, risk, family, int(index), reserve)
        fingerprint = planned_fingerprint(contract, phase + ":" + risk, slot, reserve)
        graph, roles, _, _, _, layout = fingerprint
        planned = []
        if family == "E7":
            for field_index, (role, st, _) in enumerate(layout[1], 1):
                binding = "EXPLICIT_ABSENCE" if role == "EXPLICIT_ABSENCE" else "SOURCE_COPY"
                planned.append(derive_canonical_output_field(binding, st, ordinal, field_index, schema))
        else:
            planned.append(derive_canonical_output_field("OPERATION_TARGET", roles[0][0], ordinal, len(graph), schema))
        planned.sort(key=lambda field: field["name"].encode("utf-8"))
        bases += 1
        scored += not reserve
        reserves += reserve
        for member in (["CF1", "CF2"] if family == "E5" else ["SINGLE"]):
            variants += 1
            coverage.add((family, kind, member))
            for field in planned:
                output_count += 1
                label = row["position"] + ":" + member + ":" + field["name"]
                validate_output_field_shape(field, schema)
                require(list(field) == expected_keys, "planned_output_eight_keys:" + label, checks)
                require(field["required"] is True and field["label_removal"] is False, "planned_output_fixed_flags:" + label, checks)
                binding = field["binding_kind"]
                identifier = field["name"]
                require(
                    field["source_field"] == (None if binding == "OPERATION_TARGET" else identifier)
                    and field["producer_target"] == (identifier if binding == "OPERATION_TARGET" else None)
                    and field["absence_capable"] is (binding == "EXPLICIT_ABSENCE"),
                    "planned_output_exact_binding:" + label, checks,
                )
                for flag, bad_value in (("label_removal", True), ("required", False)):
                    bad = dict(field, **{flag: bad_value})
                    try:
                        validate_output_field_shape(bad, schema)
                    except ValueError as error:
                        require(str(error) == "g_extract1_output_scoring_constants", "planned_output_reject:" + flag + ":" + label, checks)
                    else:
                        raise AssertionError("accepted_scoring_flag_mutation:" + label)
    require((bases, scored, reserves, variants) == (168, 140, 28, 192), "output_amendment_all_positions_variants", checks)
    for family in ("E1", "E3", "E4", "E5", "E6", "E7"):
        for kind in ("PRIMARY", "RESERVE"):
            for member in (["CF1", "CF2"] if family == "E5" else ["SINGLE"]):
                require((family, kind, member) in coverage, "output_amendment_representative:" + family + ":" + kind + ":" + member, checks)
    for binding, st, identifier in (("SOURCE_COPY", "string", "f001_01"), ("OPERATION_TARGET", "integer", "d001_01"), ("EXPLICIT_ABSENCE", "provided|not_provided", "f001_01")):
        field = derive_canonical_output_field(binding, st, 1, 1, schema)
        for label, mutation in (
            ("missing_key", {key: value for key, value in field.items() if key != "required"}),
            ("extra_key", dict(field, output_role="source_copy")),
            ("binding_corruption", dict(field, source_field=identifier) if binding == "OPERATION_TARGET" else dict(field, producer_target="d001_01")),
        ):
            try:
                validate_output_field_shape(mutation, schema)
            except ValueError:
                checks.append("output_amendment_reject_shape:" + binding + ":" + label)
            else:
                raise AssertionError("output_amendment_accepted_shape_mutation:" + binding + ":" + label)
    return dict(
        contract_id=amendment["contract_id"], accepted_v10_commit=amendment["accepted_v10_commit"],
        all_other_machine_rules_unchanged=True, unchanged_top_level_sections=unchanged,
        logical_bases_checked=bases, scored_bases_checked=scored, reserve_bases_checked=reserves,
        rendered_variants_checked=variants, planned_output_instances_checked=output_count,
        scoring_flag_mutations_rejected=2 * output_count,
        required=True, label_removal=False, output_roles_remain_separate=True,
        scope="value-free design metadata and isolated mutations only; no corpus or gold authored",
    )


def freshness_semantic_text(schema_type: str, value: Any, contract: dict[str, Any]) -> str:
    """Isolated design-test canonicalization, not a corpus-checker repair."""
    info = parse_schema_type(schema_type, contract["schema_type_contract"])
    semantic = info["semantic_tag"]
    if semantic in {"INTEGER", "NUMBER"}:
        if isinstance(value, (bool, float)):
            raise ValueError("freshness_not_exact_numeric")
        if isinstance(value, str):
            pattern = r"-?(?:0|[1-9][0-9]*)" if semantic == "INTEGER" else r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
            if re.fullmatch(pattern, value, re.ASCII) is None:
                raise ValueError("freshness_numeric_lexeme")
        elif not isinstance(value, (int, Fraction, Decimal)):
            raise ValueError("freshness_numeric_type")
        number = Fraction(value)
        if semantic == "INTEGER":
            if number.denominator != 1:
                raise ValueError("freshness_nonintegral_integer")
            return str(number.numerator)
        # Integer-only long division avoids binary floats and Decimal context.
        denominator = number.denominator
        for prime in (2, 5):
            while denominator % prime == 0:
                denominator //= prime
        if denominator != 1:
            raise ValueError("freshness_nonterminating_number")
        whole, remainder = divmod(abs(number.numerator), number.denominator)
        digits = []
        while remainder:
            digit, remainder = divmod(remainder * 10, number.denominator)
            digits.append(str(digit))
        text = str(whole) + ("." + "".join(digits) if digits else "")
        return ("-" if number < 0 else "") + text
    if semantic == "BOOLEAN":
        if not isinstance(value, bool):
            raise ValueError("freshness_boolean_type")
        return "true" if value else "false"
    if semantic == "DATE" and isinstance(value, date) and not isinstance(value, datetime):
        value = value.isoformat()
    if semantic == "TIME" and isinstance(value, time):
        if value.second or value.microsecond or value.tzinfo is not None:
            raise ValueError("freshness_time_resolution")
        value = value.strftime("%H:%M")
    if not isinstance(value, str):
        raise ValueError("freshness_string_type")
    if semantic == "DATE":
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value, re.ASCII) is None:
            raise ValueError("freshness_date_format")
        date.fromisoformat(value)
    elif semantic == "TIME":
        if re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value, re.ASCII) is None:
            raise ValueError("freshness_time_format")
    elif semantic == "ENUM" and value not in info["options"]:
        raise ValueError("freshness_enum_value")
    value.encode("utf-8", errors="strict")
    return value


def freshness_sequence_bytes(semantic_rows: list[list[Any]], contract: dict[str, Any]) -> bytes:
    rows = []
    for row in semantic_rows:
        if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str):
            raise ValueError("freshness_row_shape")
        schema_type, value = row
        rows.append([schema_type, freshness_semantic_text(schema_type, value, contract)])
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def freshness_from_source_facts(facts: list[dict[str, Any]], contract: dict[str, Any]) -> bytes:
    rows = []
    for fact in facts:
        if fact["template_id"] == "EXPLICIT_ABSENCE":
            continue
        if fact["template_id"] != "VALUE":
            raise ValueError("freshness_fact_template")
        _, value, schema_type = _typed_source_value(
            fact, contract["schema_type_contract"], contract["operation_semantics_contract"],
        )
        rows.append([schema_type, value])
    return freshness_sequence_bytes(rows, contract)


def require_freshness_bytes(raw: bytes, semantic_rows: list[list[Any]], contract: dict[str, Any]) -> None:
    if not isinstance(raw, bytes) or raw != freshness_sequence_bytes(semantic_rows, contract):
        raise ValueError("freshness_noncanonical_bytes")


def validate_freshness_amendment(contract: dict[str, Any], human: str, checks: list[str]) -> dict[str, Any]:
    amendment = contract["freshness_canonicalization_contract"]
    parent_id = "01aafde7410a44085999aa4aa39f883618e78799"
    require(amendment["contract_id"] == "g-extract1.freshness-canonicalization.v1", "freshness_contract_id", checks)
    require(amendment["accepted_parent_commit"] == parent_id, "freshness_parent_identity", checks)
    parent = json.loads(subprocess.check_output([
        "git", "-c", "safe.directory=" + ROOT.as_posix(), "show",
        parent_id + ":experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json",
    ], cwd=ROOT))
    projected = copy.deepcopy(contract)
    projected.pop("freshness_canonicalization_contract")
    projected.pop("whole_answer_canonicalization_contract", None)
    projected["experiment"]["status"] = parent["experiment"]["status"]
    projected["final_verdict"] = parent["final_verdict"]
    require(projected == parent, "freshness_only_new_contract_and_review_status_paths", checks)
    for name in sorted(parent):
        if name not in {"experiment", "final_verdict"}:
            require(contract[name] == parent[name], "freshness_preserved_section:" + name, checks)
    match = re.search(r"<!-- FRESHNESS_AMENDMENT_NORMATIVE_BEGIN -->\s*```json\s*(.*?)\s*```\s*<!-- FRESHNESS_AMENDMENT_NORMATIVE_END -->", human, re.DOTALL)
    require(match is not None and json.loads(match.group(1)) == amendment, "freshness_exact_human_machine_annex", checks)
    require(amendment["sequence"]["row_elements"] == "JSON strings only" and amendment["sequence"]["row_exact_length"] == 2, "freshness_two_strings", checks)
    require(amendment["sequence"]["included_template_ids"] == ["VALUE"] and amendment["sequence"]["sorting"] is False, "freshness_value_only_source_order", checks)
    require(amendment["schema_binding"]["primitive_spellings"] == contract["schema_type_contract"]["primitive_schema_tokens"], "freshness_exact_schema_binding", checks)
    require(amendment["byte_serialization"]["ensure_ascii"] is False and amendment["byte_serialization"]["separators"] == [",", ":"] and amendment["byte_serialization"]["trailing_newline"] is False, "freshness_utf8_compact_no_newline", checks)
    for name, value in amendment["authority"].items():
        if name in {"independent_rereview_required", "separate_blueprint_rebind_required"}:
            require(value is True, "freshness_later_review_required:" + name, checks)
        elif name == "belief_effects":
            require(value == "none", "freshness_belief_none", checks)
        elif name == "provider_calls":
            require(value == 0, "freshness_provider_zero", checks)
        else:
            require(value is False, "freshness_no_authority:" + name, checks)

    vectors = amendment["validation_vectors"]
    require(len({r["id"] for r in vectors}) == len(vectors), "freshness_unique_vector_ids", checks)
    covered_schemas = set()
    for vector in vectors:
        actual = freshness_sequence_bytes(vector["semantic_rows"], contract)
        require(actual == vector["expected_utf8"].encode("utf-8"), "freshness_vector_bytes:" + vector["id"], checks)
        require(json.loads(actual) == vector["expected_sequence"], "freshness_vector_rows:" + vector["id"], checks)
        require(all(len(r) == 2 and all(isinstance(x, str) for x in r) for r in json.loads(actual)), "freshness_vector_no_host_scalars:" + vector["id"], checks)
        covered_schemas.update(row[0] for row in vector["semantic_rows"])
    blueprint = load_json_unique(HERE / "blueprint/BLUEPRINT.json")
    schema_surface = {row[1] for p in blueprint["logical_positions"] for row in p["schema_plan"]["source_fact_role_schema_entity_sequence"]}
    require(covered_schemas == schema_surface, "freshness_full_blueprint_schema_surface", checks)
    for group in amendment["equivalence_groups"]:
        outputs = [freshness_sequence_bytes([[group["schema_type"], value]], contract) for value in group["values"]]
        require(all(raw == group["expected_utf8"].encode() for raw in outputs), "freshness_equivalence:" + group["id"], checks)
    for schema_type in ("integer", "number"):
        values = [-1, 0, 1, 42, 10**70+1]
        outputs = [freshness_sequence_bytes([[schema_type, value]], contract) for value in values]
        require(len(set(outputs)) == len(values), "freshness_distinct_numeric_values:" + schema_type, checks)
        for value, raw in zip(values, outputs):
            for equivalent in (Fraction(value), Decimal(str(value)), str(value)):
                require(freshness_sequence_bytes([[schema_type, equivalent]], contract) == raw, "freshness_host_exact_equivalence:" + schema_type + ":" + str(value) + ":" + type(equivalent).__name__, checks)
    require(freshness_sequence_bytes([["number", Fraction(1, 8)]], contract) == b'[["number","0.125"]]', "freshness_exact_fraction", checks)
    require(freshness_sequence_bytes([["number", Decimal("123456789012345678901234567890.125000")]], contract) == b'[["number","123456789012345678901234567890.125"]]', "freshness_no_decimal_context_rounding", checks)
    require(freshness_sequence_bytes([["integer", "5"]], contract) != freshness_sequence_bytes([["number", "5"]], contract), "freshness_schema_types_remain_distinct", checks)
    require(freshness_sequence_bytes([["string", "e\u0301"]], contract) != freshness_sequence_bytes([["string", "\u00e9"]], contract), "freshness_no_unicode_normalization", checks)

    facts = [
        dict(template_id="VALUE", field_identifier="f001_01", schema_type="integer", value=dict(kind="integer_literal", value="42"), entity_selector_value=None),
        dict(template_id="EXPLICIT_ABSENCE", field_identifier="f001_02", schema_type="provided|not_provided", value=None, entity_selector_value=None),
        dict(template_id="VALUE", field_identifier="f001_03", schema_type="integer", value=dict(kind="integer_literal", value="42"), entity_selector_value=None),
        dict(template_id="VALUE", field_identifier="f001_04", schema_type="number", value=dict(kind="integer_literal", value="5"), entity_selector_value=None),
    ]
    require(freshness_from_source_facts(facts, contract) == b'[["integer","42"],["integer","42"],["number","5"]]', "freshness_source_record_scope_order_duplicates", checks)
    renamed = copy.deepcopy(facts)
    for i, fact in enumerate(renamed):
        fact["field_identifier"] = f"f168_{i+1:02d}"
    require(freshness_from_source_facts(renamed, contract) == freshness_from_source_facts(facts, contract), "freshness_no_field_names_or_fixture_ids", checks)

    def packed(rows: list[list[Any]]) -> bytes:
        return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    mutation_rows = {
        "integer_numeric_scalar": ([["integer", "0"]], [["integer", 0]]),
        "number_numeric_scalar": ([["number", "5"]], [["number", 5]]),
        "number_exponent_retained": ([["number", "5e0"]], [["number", "5e0"]]),
        "number_trailing_zeroes_retained": ([["number", "0.50"]], [["number", "0.50"]]),
        "number_empty_fraction_point_retained": ([["number", "5.0"]], [["number", "5."]]),
        "negative_zero_retained": ([["number", "-0.0"]], [["number", "-0"]]),
        "integer_leading_plus": ([["integer", "1"]], [["integer", "+1"]]),
        "integer_leading_zeroes": ([["integer", "1"]], [["integer", "01"]]),
        "boolean_capitalized": ([["boolean", True]], [["boolean", "True"]]),
        "date_reformatted": ([["YYYY-MM-DD", "2039-10-05"]], [["YYYY-MM-DD", "10/05/2039"]]),
        "time_reformatted": ([["HH:MM", "23:45"]], [["HH:MM", "11:45 PM"]]),
        "string_trimmed": ([["string", " label_001_01 "]], [["string", "label_001_01"]]),
        "enum_ordinal": ([["option_a|option_b", "option_b"]], [["option_a|option_b", 1]]),
        "atoms_sorted": ([["string", "label_001_01"], ["integer", "42"]], [["integer", "42"], ["string", "label_001_01"]]),
        "duplicate_removed": ([["integer", "42"], ["integer", "42"]], [["integer", "42"]]),
        "row_missing_element": ([["integer", "0"]], [["integer"]]),
        "row_extra_element": ([["integer", "0"]], [["integer", "0", "extra"]]),
        "null_value": ([["integer", "0"]], [["integer", None]]),
        "object_value": ([["integer", "0"]], [["integer", {}]]),
        "array_value": ([["integer", "0"]], [["integer", []]]),
        "schema_enum_reordered": ([["option_a|option_b", "option_b"]], [["option_b|option_a", "option_b"]]),
        "absence_included": ([["integer", "42"]], [["integer", "42"], ["provided|not_provided", "not_provided"]]),
        "derived_output_included": ([["integer", "42"]], [["integer", "42"], ["integer", "84"]]),
    }
    for schema_type, value, generic in (
        ("integer", "0", "INTEGER"), ("number", "5", "NUMBER"),
        ("YYYY-MM-DD", "2039-10-05", "DATE"), ("HH:MM", "23:45", "TIME"),
        ("string", "label_001_01", "STRING"), ("boolean", "true", "BOOLEAN"),
        ("option_a|option_b", "option_a", "ENUM"),
    ):
        semantic = True if schema_type == "boolean" else value
        mutation_rows["semantic_tag_" + generic.lower()] = ([[schema_type, semantic]], [[generic, value]])
    mutations = [(label, rows, packed(changed)) for label, (rows, changed) in mutation_rows.items()]
    mutations.extend([
        ("whitespace_formatted_json", [["integer", "0"]], b'[["integer", "0"]]'),
        ("ensure_ascii_true_non_ascii", [["string", "\u00e9"]], json.dumps([["string", "\u00e9"]], ensure_ascii=True, separators=(",", ":")).encode()),
        ("trailing_newline", [["integer", "0"]], b'[["integer","0"]]\n'),
    ])
    require({label for label, _, _ in mutations} == set(amendment["mutation_catalog"]), "freshness_mutation_catalog_exact_coverage", checks)
    for label, rows, mutated in mutations:
        try:
            require_freshness_bytes(mutated, rows, contract)
        except ValueError:
            rejected = True
        else:
            rejected = False
        require(rejected, "freshness_mutation_rejected:" + label, checks)
    invalid_inputs = [
        ("integer", True), ("integer", 5.0), ("integer", "5e0"),
        ("integer", "05"), ("integer", "+5"), ("integer", Fraction(1, 2)),
        ("number", 0.5), ("number", True), ("number", "NaN"), ("number", Fraction(1, 3)),
        ("boolean", "True"), ("boolean", 1), ("YYYY-MM-DD", "2039-02-29"),
        ("YYYY-MM-DD", "2039-1-05"), ("HH:MM", "24:00"), ("HH:MM", "3:45"),
        ("option_a|option_b", 0), ("option_a|option_b", "option_c"),
        ("DATE", "2039-10-05"), ("string", None), ("string", "\ud800"),
    ]
    for i, (schema_type, value) in enumerate(invalid_inputs):
        try:
            freshness_sequence_bytes([[schema_type, value]], contract)
        except (ValueError, TypeError, UnicodeEncodeError):
            rejected = True
        else:
            rejected = False
        require(rejected, f"freshness_invalid_semantic_input:{i}", checks)

    # These are preservation digests only; do not read/score candidate content.
    preserved = {}
    directory = HERE / "corpus"
    require({p.name for p in directory.iterdir()} == {Path(p).name for p in PRESERVED_CORPUS_DIGESTS}, "freshness_preserved_corpus_inventory", checks)
    for name, expected in PRESERVED_CORPUS_DIGESTS.items():
        actual = sha256(HERE / name)
        require(actual == expected, "freshness_preserved_corpus_bytes:" + name, checks)
        preserved[name] = dict(before_sha256=expected, after_sha256=actual, byte_identical=True)
    # Hash the existing gold projection only; do not derive or adjudicate gold.
    candidates = load_json_unique(directory / "AUTHORING_CANDIDATES.json")
    gold_projection = [[row["logical_base_id"], row["fixture"]["gold_values"]] for row in candidates["accepted"]]
    gold_hash = hashlib.sha256(json.dumps(gold_projection, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    gold_before = "803e8e4c57b63c7edb22f02194cbefdbf6be3fc964a0d77f65faa658f8904aec"
    require(gold_hash == gold_before, "freshness_preserved_gold_projection", checks)
    blueprint_digests = {}
    for path in sorted((HERE / "blueprint").iterdir()):
        old = subprocess.check_output([
            "git", "-c", "safe.directory=" + ROOT.as_posix(), "show",
            PROTECTED_BLUEPRINT_COMMIT + ":experiments/G-EXTRACT1-candidate/blueprint/" + path.name,
        ], cwd=ROOT)
        before = hashlib.sha256(old).hexdigest()
        after = sha256(path)
        require(before == after, "freshness_preserved_blueprint_digest:" + path.name, checks)
        blueprint_digests[path.name] = dict(before_sha256=before, after_sha256=after, byte_identical=True)
    groups = blueprint["comparison_scope"]["scaffold_overlap"]["classes"]
    scaffold_pairs = {frozenset(pair) for row in groups for pair in row["rendered_position_pairs"]}
    positions = {p["logical_base_id"]: p for p in blueprint["logical_positions"]}
    counts = dict(same_base_e5=0, scaffold=0, same_subtype=0, ordinary=0)
    for a, b in itertools.combinations(blueprint["rendered_variants"], 2):
        if a["logical_base_id"] == b["logical_base_id"]:
            counts["same_base_e5"] += 1
        elif frozenset((a["rendered_variant_id"], b["rendered_variant_id"])) in scaffold_pairs:
            counts["scaffold"] += 1
        elif positions[a["logical_base_id"]]["subtype_slot"] == positions[b["logical_base_id"]]["subtype_slot"]:
            counts["same_subtype"] += 1
        else:
            counts["ordinary"] += 1
    require(counts == dict(same_base_e5=24, scaffold=906, same_subtype=518, ordinary=16888), "freshness_blueprint_comparison_partition_preserved", checks)
    require(len(groups) == 14 and sum(len(r["logical_position_pairs"]) for r in groups) == 234, "freshness_scaffold_membership_preserved", checks)
    require((len(positions), len(blueprint["rendered_variants"]), len(blueprint["reserve_map"])) == (168, 192, 28), "freshness_architecture_preserved", checks)
    return dict(
        contract_id=amendment["contract_id"], parent_commit=parent_id,
        semantic_vector_count=len(vectors), numeric_equivalence_groups=len(amendment["equivalence_groups"]),
        mutation_count=len(mutations), mutations_rejected=len(mutations),
        invalid_semantic_inputs_rejected=len(invalid_inputs), canonical_case=amendment["original_failure_semantic_vector"]["expected_utf8"],
        preserved_corpus_files=preserved, blueprint_unchanged_commit=PROTECTED_BLUEPRINT_COMMIT,
        preserved_gold_projection=dict(before_sha256=gold_before, after_sha256=gold_hash, byte_identical=True),
        preserved_blueprint_files=blueprint_digests,
        comparison_partition=counts, corpus_content_used_for_rule_choice=False,
        existing_corpus_checker_repaired=False, corpus_finalized=False,
        gold_byte_identity_evidence="entire AUTHORING_CANDIDATES.json SHA-256 unchanged; embedded gold therefore unchanged; no gold rescoring",
        scope="isolated design vectors and byte preservation only; no concrete corpus contamination campaign",
    )


def whole_answer_semantic_text(schema_type: str, value: Any, contract: dict[str, Any]) -> str:
    """Isolated amended-encoding test path; not used by corpus tooling."""
    tag = parse_schema_type(schema_type, contract["schema_type_contract"])["semantic_tag"]
    if tag in {"INTEGER", "NUMBER"}:
        if isinstance(value, (bool, float)):
            raise ValueError("whole_answer_not_exact_numeric")
        if isinstance(value, str):
            pattern = r"-?(?:0|[1-9][0-9]*)"
            if tag == "NUMBER":
                pattern += r"(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
            if re.fullmatch(pattern, value, re.ASCII) is None:
                raise ValueError("whole_answer_numeric_lexeme")
        elif not isinstance(value, (int, Decimal, Fraction)):
            raise ValueError("whole_answer_numeric_type")
        exact = Fraction(value)
        if tag == "INTEGER":
            if exact.denominator != 1:
                raise ValueError("whole_answer_nonintegral_integer")
            return str(exact.numerator)
        denominator = exact.denominator
        powers = []
        for prime in (2, 5):
            count = 0
            while denominator % prime == 0:
                denominator //= prime
                count += 1
            powers.append(count)
        if denominator != 1:
            raise ValueError("whole_answer_nonterminating_number")
        # Scale by powers of ten using integers, never a Decimal context.
        scale = max(powers)
        digits = str(abs(exact.numerator) * 2 ** (scale - powers[0]) * 5 ** (scale - powers[1]))
        if scale:
            digits = digits.zfill(scale + 1)
            text = (digits[:-scale] + "." + digits[-scale:]).rstrip("0").rstrip(".")
        else:
            text = digits
        return ("-" if exact < 0 else "") + text
    if tag == "BOOLEAN":
        if type(value) is not bool:
            raise ValueError("whole_answer_boolean_type")
        return "true" if value else "false"
    if tag == "DATE" and isinstance(value, date) and not isinstance(value, datetime):
        value = value.isoformat()
    if tag == "TIME" and isinstance(value, time):
        if value.second or value.microsecond or value.tzinfo is not None:
            raise ValueError("whole_answer_time_resolution")
        value = f"{value.hour:02d}:{value.minute:02d}"
    if not isinstance(value, str):
        raise ValueError("whole_answer_string_type")
    if tag == "DATE":
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value, re.ASCII) is None:
            raise ValueError("whole_answer_date_format")
        date.fromisoformat(value)
    elif tag == "TIME":
        if re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value, re.ASCII) is None:
            raise ValueError("whole_answer_time_format")
    elif tag == "ENUM":
        if value not in parse_schema_type(schema_type, contract["schema_type_contract"])["options"]:
            raise ValueError("whole_answer_enum_value")
    value.encode("utf-8", errors="strict")
    return value


def whole_answer_canonical_bytes(semantic_rows: list[list[Any]], contract: dict[str, Any]) -> bytes:
    """Complete whole-answer bytes for design vectors only."""
    if not isinstance(semantic_rows, list):
        raise ValueError("whole_answer_rows_type")
    rows, seen = [], set()
    for row in semantic_rows:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("whole_answer_row_shape")
        field, schema, value = row
        if not isinstance(field, str) or not isinstance(schema, str) or field in seen:
            raise ValueError("whole_answer_field_schema_or_duplicate")
        field.encode("utf-8", errors="strict")
        seen.add(field)
        tag = parse_schema_type(schema, contract["schema_type_contract"])["semantic_tag"]
        rows.append([field, schema, [tag, whole_answer_semantic_text(schema, value, contract)]])
    rows.sort(key=lambda row: row[0].encode("utf-8"))
    return json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def require_whole_answer_bytes(raw: bytes, semantic_rows: list[list[Any]], contract: dict[str, Any]) -> None:
    if not isinstance(raw, bytes) or raw != whole_answer_canonical_bytes(semantic_rows, contract):
        raise ValueError("whole_answer_noncanonical_bytes")



def validate_whole_answer_amendment(contract: dict[str, Any], human: str, checks: list[str]) -> dict[str, Any]:
    amendment = contract["whole_answer_canonicalization_contract"]
    parent_id = "6fb3f2af5806760c034006a8561ce08e938c210a"
    require(amendment["contract_id"] == "g-extract1.whole-answer-canonicalization.v1", "whole_answer_contract_id", checks)
    require(amendment["accepted_parent_commit"] == parent_id, "whole_answer_parent_identity", checks)
    require(amendment["accepted_blueprint"] == PROTECTED_BLUEPRINT_COMMIT, "whole_answer_blueprint_identity", checks)
    parent = json.loads(subprocess.check_output([
        "git", "-c", "safe.directory=" + ROOT.as_posix(), "show",
        parent_id + ":experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json",
    ], cwd=ROOT))
    projected = copy.deepcopy(contract)
    projected.pop("whole_answer_canonicalization_contract")
    projected["experiment"]["status"] = parent["experiment"]["status"]
    projected["final_verdict"] = parent["final_verdict"]
    require(projected == parent, "whole_answer_only_encoding_contract_and_review_status_paths", checks)
    for name in sorted(parent):
        if name not in {"experiment", "final_verdict"}:
            require(contract[name] == parent[name], "whole_answer_preserved_section:" + name, checks)
    match = re.search(r"<!-- WHOLE_ANSWER_AMENDMENT_NORMATIVE_BEGIN -->\s*\x60{3}json\s*(.*?)\s*\x60{3}\s*<!-- WHOLE_ANSWER_AMENDMENT_NORMATIVE_END -->", human, re.DOTALL)
    require(match is not None and json.loads(match.group(1)) == amendment, "whole_answer_exact_human_machine_annex", checks)
    require(amendment["binds"] == "contamination_contract.exact_reuse_contract.whole_answer.canonical_values", "whole_answer_binding_path", checks)
    require(amendment["semantic_tags"] == ["STRING", "NUMBER", "INTEGER", "BOOLEAN", "DATE", "TIME", "ENUM"], "whole_answer_seven_exact_tags", checks)
    shape = amendment["row_contract"]
    require(shape["outer_length"] == 3 and shape["inner_length"] == 2 and shape["all_leaf_elements"] == "JSON strings only", "whole_answer_row_contract", checks)
    byte = amendment["outer_serialization"]
    require(byte["ensure_ascii"] is True and byte["separators"] == [",", ":"] and byte["terminal_newline"] is False and byte["encoding"] == "UTF-8", "whole_answer_outer_byte_constants", checks)
    reuse = contract["contamination_contract"]["exact_reuse_contract"]
    require(amendment["comparison"]["scope_ref"] == "contamination_contract.exact_reuse_contract.scope_names" and reuse["all_rules_apply_to_every_scope"] is True, "whole_answer_scope_path_and_preservation", checks)
    require(amendment["comparison"]["match_rule"] == reuse["whole_answer"]["match_rule"] and amendment["comparison"]["per_field_or_subset_matching"] is False, "whole_answer_unchanged_match_unit", checks)
    require(amendment["separation"]["freshness_ensure_ascii"] is False and amendment["separation"]["whole_answer_ensure_ascii"] is True, "whole_answer_freshness_serialization_separate", checks)
    for key, value in amendment["authority"].items():
        if key.endswith("_required"):
            require(value is True, "whole_answer_separate_review_required:" + key, checks)
        elif key == "belief_effects":
            require(value == "none", "whole_answer_belief_none", checks)
        elif key == "provider_calls":
            require(value == 0, "whole_answer_provider_zero", checks)
        else:
            require(value is False, "whole_answer_no_authority:" + key, checks)

    vectors = amendment["validation_vectors"]
    require(len({v["id"] for v in vectors}) == len(vectors), "whole_answer_unique_vector_ids", checks)
    tags, schemas = set(), set()
    for vector in vectors:
        raw = whole_answer_canonical_bytes(vector["semantic_rows"], contract)
        require(raw == vector["expected_utf8"].encode("utf-8"), "whole_answer_golden_bytes:" + vector["id"], checks)
        rows = json.loads(raw)
        require(rows == vector["expected_rows"], "whole_answer_golden_rows:" + vector["id"], checks)
        require(all(len(r) == 3 and isinstance(r[0], str) and isinstance(r[1], str) and len(r[2]) == 2 and all(isinstance(x, str) for x in r[2]) for r in rows), "whole_answer_only_string_leaves:" + vector["id"], checks)
        require(whole_answer_canonical_bytes(list(reversed(vector["semantic_rows"])), contract) == raw, "whole_answer_input_order_not_field_binding:" + vector["id"], checks)
        tags.update(row[2][0] for row in rows)
        schemas.update(row[1] for row in rows)
    require(tags == set(amendment["semantic_tags"]), "whole_answer_full_tag_surface", checks)
    require(schemas == {"string", "number", "integer", "boolean", "YYYY-MM-DD", "HH:MM", "option_a|option_b", "option_a|option_b|option_c", "provided|not_provided"}, "whole_answer_full_active_schema_surface", checks)
    for group in amendment["equivalence_groups"]:
        require(all(whole_answer_canonical_bytes([["field", group["schema_type"], value]], contract) == group["expected_utf8"].encode() for value in group["values"]), "whole_answer_numeric_equivalence:" + group["id"], checks)
    for schema in ("integer", "number"):
        outputs = []
        for value in (-1, 0, 1, 42, 10**70 + 1):
            raw = whole_answer_canonical_bytes([["field", schema, value]], contract)
            outputs.append(raw)
            for equivalent in (str(value), Decimal(str(value)), Fraction(value)):
                require(whole_answer_canonical_bytes([["field", schema, equivalent]], contract) == raw, "whole_answer_host_equivalence:" + schema + ":" + str(value) + ":" + type(equivalent).__name__, checks)
        require(len(set(outputs)) == len(outputs), "whole_answer_distinct_numbers:" + schema, checks)
    require(whole_answer_canonical_bytes([["field", "number", Fraction(1, 8)]], contract) == b'[["field","number",["NUMBER","0.125"]]]', "whole_answer_exact_rational", checks)
    require(whole_answer_canonical_bytes([["field", "number", Decimal("123456789012345678901234567890.125000")]], contract) == b'[["field","number",["NUMBER","123456789012345678901234567890.125"]]]', "whole_answer_no_decimal_context_rounding", checks)
    require(whole_answer_canonical_bytes([["field", "integer", 5]], contract) != whole_answer_canonical_bytes([["field", "number", 5]], contract), "whole_answer_typed_numeric_distinction", checks)
    require(whole_answer_canonical_bytes([["field", "string", "\u00e9"]], contract) != whole_answer_canonical_bytes([["field", "string", "e\u0301"]], contract), "whole_answer_no_unicode_normalization", checks)
    require(b"\\u00e9" in whole_answer_canonical_bytes([["field", "string", "\u00e9"]], contract), "whole_answer_ensure_ascii_true_non_ascii", checks)
    require("\u00e9".encode() in freshness_sequence_bytes([["string", "\u00e9"]], contract), "whole_answer_does_not_change_freshness_ascii", checks)
    require(whole_answer_semantic_text("YYYY-MM-DD", date(2039, 10, 5), contract) == "2039-10-05", "whole_answer_date_host_representation", checks)
    require(whole_answer_semantic_text("HH:MM", time(0, 5), contract) == "00:05", "whole_answer_time_host_representation", checks)

    def packed(rows: list[list[Any]], ascii_only: bool = True) -> bytes:
        return json.dumps(rows, ensure_ascii=ascii_only, separators=(",", ":")).encode("utf-8")

    mutations = []
    cases = [
        ("boolean_scalar_true", "boolean", True, True),
        ("boolean_scalar_false", "boolean", False, False),
        ("integer_numeric_scalar", "integer", "0", 0),
        ("number_numeric_scalar", "number", "5", 5),
        ("number_exponent", "number", "5e0", "5e0"),
        ("number_trailing_zeroes", "number", "5.00", "5.00"),
        ("number_negative_zero", "number", "-0.0", "-0"),
        ("integer_negative_zero", "integer", "-0", "-0"),
        ("date_reformatted", "YYYY-MM-DD", "2039-10-05", "10/05/2039"),
        ("time_reformatted", "HH:MM", "23:45", "11:45 PM"),
        ("string_trimmed", "string", " label_001_01 ", "label_001_01"),
        ("enum_ordinal", "option_a|option_b", "option_b", 1),
        ("not_provided_null", "provided|not_provided", "not_provided", None),
        ("null_value", "integer", "0", None),
        ("array_value", "integer", "0", []),
        ("object_value", "integer", "0", {}),
    ]
    for label, schema, semantic, replacement in cases:
        rows = [["field", schema, semantic]]
        changed = json.loads(whole_answer_canonical_bytes(rows, contract))
        changed[0][2][1] = replacement
        mutations.append((label, rows, packed(changed)))
    base = [["field", "integer", "0"]]
    golden = json.loads(whole_answer_canonical_bytes(base, contract))
    for label, location, replacement in [
        ("tag_lowercase", "tag", "integer"),
        ("tag_replaced_by_schema", "tag", "integer"),
        ("schema_replaced_by_tag", "schema", "INTEGER"),
        ("typed_numeric_collapse", "tag", "NUMBER"),
    ]:
        changed = copy.deepcopy(golden)
        if location == "tag":
            changed[0][2][0] = replacement
        else:
            changed[0][1] = replacement
        mutations.append((label, base, packed(changed)))
    for label, changed in [
        ("inner_missing_element", [["field", "integer", ["INTEGER"]]]),
        ("inner_extra_element", [["field", "integer", ["INTEGER", "0", "extra"]]]),
        ("outer_missing_element", [["field", ["INTEGER", "0"]]]),
        ("outer_extra_element", [["field", "integer", ["INTEGER", "0"], "extra"]]),
    ]:
        mutations.append((label, base, packed(changed)))
    unicode_rows = [["field", "string", "\u00e9"]]
    sort_rows = [["z", "integer", "0"], ["a", "integer", "1"]]
    mutations.extend([
        ("ensure_ascii_false", unicode_rows, packed(json.loads(whole_answer_canonical_bytes(unicode_rows, contract)), False)),
        ("pretty_JSON", base, json.dumps(golden, ensure_ascii=True, indent=2).encode()),
        ("terminal_newline", base, packed(golden) + b"\n"),
        ("wrong_field_sorting", sort_rows, packed(list(reversed(json.loads(whole_answer_canonical_bytes(sort_rows, contract)))))),
    ])
    require({name for name, _, _ in mutations} == set(amendment["mutation_catalog"]), "whole_answer_mutation_catalog_exact_coverage", checks)
    for name, rows, raw in mutations:
        try:
            require_whole_answer_bytes(raw, rows, contract)
        except ValueError:
            rejected = True
        else:
            rejected = False
        require(rejected, "whole_answer_mutation_rejected:" + name, checks)

    invalid = [
        [["field", "integer", True]], [["field", "integer", 5.0]],
        [["field", "integer", "5e0"]], [["field", "integer", "05"]],
        [["field", "integer", "+5"]], [["field", "integer", Fraction(1, 2)]],
        [["field", "number", 0.5]], [["field", "number", True]],
        [["field", "number", "NaN"]], [["field", "number", Fraction(1, 3)]],
        [["field", "number", object()]], [["field", "boolean", "true"]],
        [["field", "boolean", 1]], [["field", "YYYY-MM-DD", "2039-02-29"]],
        [["field", "YYYY-MM-DD", "2039-1-05"]], [["field", "HH:MM", "24:00"]],
        [["field", "HH:MM", "3:45"]], [["field", "option_a|option_b", 0]],
        [["field", "option_a|option_b", "option_c"]], [["field", "DATE", "2039-10-05"]],
        [["field", "date", "2039-10-05"]], [["field", "TIME", "23:45"]],
        [["field", "time", "23:45"]], [["field", "ENUM", "not_provided"]],
        [["field", "string", None]], [["field", "string", "\ud800"]],
        [["\ud800", "string", "value"]], [["field", "integer", "0"], ["field", "integer", "1"]],
        [["field", "integer"]], [["field", "integer", "0", "extra"]],
        [[1, "integer", "0"]], [["field", "integer", {"display": "0"}]],
    ]
    for i, rows in enumerate(invalid):
        try:
            whole_answer_canonical_bytes(rows, contract)
        except (ValueError, TypeError, UnicodeEncodeError):
            rejected = True
        else:
            rejected = False
        require(rejected, "whole_answer_invalid_semantic_input:" + str(i), checks)

    # Existing corpus imports must still see the unrepaired legacy helper.
    previous_source = subprocess.check_output([
        "git", "-c", "safe.directory=" + ROOT.as_posix(), "show",
        parent_id + ":experiments/G-EXTRACT1-candidate/validate_design.py",
    ], cwd=ROOT).decode("utf-8")
    current_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    previous_tree = ast.parse(previous_source)
    isolated = {"whole_answer_semantic_text", "whole_answer_canonical_bytes", "require_whole_answer_bytes", "validate_whole_answer_amendment"}
    protected = {"canonical_answer_bytes", "canonical_atom", "freshness_semantic_text", "freshness_sequence_bytes", "freshness_from_source_facts", "require_freshness_bytes"}
    for name in sorted(protected):
        current = next(node for node in current_tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        old = next(node for node in previous_tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        require(ast.dump(current, include_attributes=False) == ast.dump(old, include_attributes=False), "whole_answer_legacy_helper_unchanged:" + name, checks)
    for node in current_tree.body:
        if isinstance(node, ast.FunctionDef) and node.name not in isolated | {"validate"}:
            called = {child.func.id for child in ast.walk(node) if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)}
            require(not called.intersection(isolated), "whole_answer_no_silent_old_helper_rewire:" + node.name, checks)
    preserved = FRESHNESS_AMENDMENT_SUMMARY["preserved_corpus_files"]
    require(len(preserved) == 10 and all(row["byte_identical"] for row in preserved.values()), "whole_answer_ten_corpus_tooling_files_unchanged", checks)
    historical = historical_adaptation_summary(contract)
    require((historical["examined"], historical["adapted"], historical["rejected"]) == (106, 106, 0), "whole_answer_historical_adapter_106", checks)
    require(historical["projection_evidence_sha256"] == "a14935bf93e8932854b545cacd638daf869d67d8742826887f187956b75e0810", "whole_answer_historical_projection_digest_unchanged", checks)
    historical_preserved = {}
    for name, expected in (
        ("G_ROUTE4_CLOSURE.json", "d992a169a2be293909f0fe0f1b39720656f40a09dc4f6b4e9c53449110cef8be"),
        ("PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json", "461a85368a6cbbd39429bebbae883c0b17be614db52e343150b23051041b4868"),
    ):
        actual = sha256(ROOT / "experiments/G-ROUTE4-candidate/closure" / name)
        require(actual == expected, "whole_answer_historical_closure_preserved:" + name, checks)
        historical_preserved[name] = dict(before_sha256=expected, after_sha256=actual, byte_identical=True)
    counts = dict(
        logical_bases=168, rendered_variants=192, scaffold_classes=14,
        logical_scaffold_memberships=234, rendered_scaffold_memberships=906,
        same_subtype_branch=518, ordinary_branch=16888, same_base_e5_scopes=24,
        fingerprint_classes=len(contract["template_recurrence_contract"]["fingerprint_classes"]),
        subtype_groups=len(contract["template_recurrence_contract"]["subtype_template_groups"]),
        reserves=28, phase_a_calls=480, max_phase_b_calls=240, max_total_calls=720,
    )
    require(counts["fingerprint_classes"] == 51 and counts["subtype_groups"] == 35, "whole_answer_recurrence_counts_preserved", checks)
    return dict(
        contract_id=amendment["contract_id"], parent_commit=parent_id,
        semantic_vector_count=len(vectors), numeric_equivalence_groups=len(amendment["equivalence_groups"]),
        mutation_count=len(mutations), mutations_rejected=len(mutations),
        invalid_semantic_inputs_rejected=len(invalid), original_failure_completed_bytes=vectors[-1]["expected_utf8"],
        preserved_corpus_files=preserved,
        preserved_gold_projection=FRESHNESS_AMENDMENT_SUMMARY["preserved_gold_projection"],
        preserved_blueprint_files=FRESHNESS_AMENDMENT_SUMMARY["preserved_blueprint_files"],
        protected_blueprint_commit=PROTECTED_BLUEPRINT_COMMIT,
        preserved_historical_files=historical_preserved,
        preservation_counts=counts, historical_adapter=historical,
        corpus_content_used_to_choose_encoding=False, corpus_rescored=False,
        existing_checker_helpers_unchanged=True, blueprint_modified=False,
        checker_repair=False, corpus_finalized=False,
        scope="isolated design vectors, read-only historical adaptation and preservation hashes only",
    )



def validate_existing_blueprint_inventory(checks: list[str]) -> None:
    directory = HERE / "blueprint"
    if not directory.exists():
        return
    names = {".gitattributes", "BLUEPRINT.json", "BLUEPRINT.md", "BLUEPRINT_VALIDATION_REPORT.json", "validate_blueprint.py"}
    require(directory.is_dir() and {path.name for path in directory.iterdir()} == names, "existing_blueprint_exact_inventory", checks)
    for name in sorted(names):
        path = directory / name
        old = subprocess.check_output([
            "git", "-c", "safe.directory=" + ROOT.as_posix(), "show",
            PROTECTED_BLUEPRINT_COMMIT + ":experiments/G-EXTRACT1-candidate/blueprint/" + name,
        ], cwd=ROOT)
        require(path.is_file() and path.read_bytes() == old, "existing_blueprint_unchanged:" + name, checks)


def validate(contract: dict[str, Any], human: str) -> list[str]:
    COUNTERFACTUAL_AUDITS.clear()
    OUTPUT_FIELD_AMENDMENT_SUMMARY.clear()
    checks: list[str] = []
    require(contract["schema_version"] == "g-extract1.design-candidate.v10", "schema_v10", checks)
    require(contract["experiment"]["status"] == "READY_FOR_G_EXTRACT1_WHOLE_ANSWER_CANONICALIZATION_REREVIEW", "status_whole_answer_amendment", checks)
    require(contract["final_verdict"] == contract["experiment"]["status"], "whole_answer_final_status", checks)
    require(contract["experiment"]["design_revision"] == 10, "design_revision_v10", checks)
    for field in ("implemented", "blueprint_authorized", "fixture_authoring_authorized", "execution_authorized"):
        require(contract["experiment"][field] is False, f"authority_false:{field}", checks)
    require(contract["experiment"]["provider_generation_calls"] == 0, "provider_calls_zero", checks)
    require(contract["experiment"]["belief_effects"] == "none", "belief_effects_none", checks)
    OUTPUT_FIELD_AMENDMENT_SUMMARY.update(validate_output_field_amendment(contract, human, checks))
    validate_v7(contract, checks)
    validate_v8(contract, checks)
    validate_v9(contract, checks)
    validate_v10(contract, checks)
    SCAFFOLD_AUDIT.clear()
    SCAFFOLD_AUDIT.update(validate_scaffold_amendment(contract,human,checks))
    FRESHNESS_AMENDMENT_SUMMARY.clear()
    FRESHNESS_AMENDMENT_SUMMARY.update(validate_freshness_amendment(contract, human, checks))
    WHOLE_ANSWER_AMENDMENT_SUMMARY.clear()
    WHOLE_ANSWER_AMENDMENT_SUMMARY.update(validate_whole_answer_amendment(contract, human, checks))

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
    require(phases["A"]["scheduled_calls"] == 480, "phase_a_calls", checks)
    require(phases["B"]["maximum_scheduled_calls"] == 240, "phase_b_calls", checks)
    require(contract["efficiency"]["maximum_total_calls"] == 720, "maximum_calls", checks)
    require(abs(contract["efficiency"]["maximum_call_reduction_fraction"] - (1 - 720 / 1395)) < 1e-6, "call_reduction", checks)

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
    require(contamination["contract_id"] == "g-extract1.contamination.v5", "contamination_contract_v5", checks)
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
        "every historical extraction versus every new scored/reserve using shared three-component projection",
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
    require(reserve["contract_id"] == "g-extract1.reserve-activation.v5", "reserve_contract_v5", checks)
    require(reserve["total_reserve_slots"] == 2 * 2 * 7 == 28, "reserve_slot_count", checks)
    require(reserve["slot_id_format"] == "RESERVE:{phase}:{round}:{primary_family}", "reserve_slot_id", checks)
    require(not reserve["selection_pool_allowed"], "no_reserve_pool", checks)
    require(reserve["reserve_consumption_limit"] == 1, "reserve_single_consumption", checks)
    require("output_role_sequence" in reserve["required_match_dimensions"], "reserve_schema_role_match", checks)
    for vector in reserve["test_vectors"]:
        require(reserve_decision(vector) == vector["expected"], f"reserve:{vector['id']}", checks)

    gates_a, gates_b = contract["cell_gates"]["phase_a"], contract["cell_gates"]["phase_b"]
    require(gates_a["denominator_integrity"]["required_observations"] == 80, "gate_a_observations", checks)
    require(gates_a["denominator_integrity"]["required_repeat_pairs"] == 40, "gate_a_pairs", checks)
    require(gates_b["denominator_integrity"]["required_observations"] == 40, "gate_b_observations", checks)
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
    require(contract["sampling"]["seed_formula"] == "phase_base + (logical_fixture_ordinal - 1)*10 + one_based_repeat", "seed_formula", checks)

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
        "g-extract1.design-candidate.v10", "g-extract1.operation-definitions.v4",
        "g-extract1.schema-types.v1", "g-extract1.operation-semantics.v2",
        "g-extract1.family-assignment.v4", "g-extract1.contamination.v5",
        "g-extract1.explicit-absence-scoring.v4", "g-extract1.reserve-activation.v5",
        "g-extract1.lexical-neutrality.v1", "g-extract1.entity-population.v2",
        "g-extract1.reserve-equivalence.v1", "g-extract1.subtype-allocation.v2",
        "g-extract1.historical-fingerprint-adapter.v1", "g-extract1.subtype-content-validation.v1",
        "g-extract1.integrity-events.v2", "g-extract1.result-state-machine.v3",
        "POST_CONTACT_GOLD_DEFECT_DISCOVERED", "UNVERIFIABLE_INTERRUPTION_CHECKPOINT",
        "RESERVE:{phase}:{round}:{primary_family}", "2026-10-01", "5-3",
        "READY_FOR_G_EXTRACT1_OUTPUT_FIELD_AMENDMENT_REREVIEW", "does not prove scientific validity",
        "SOURCE_COPY", "explicit partial absence", "both repeats semantically correct",
    ]
    for literal in human_literals:
        require(literal in human, f"human_literal:{literal}", checks)
    match = re.search(r"<!-- V10_NORMATIVE_BEGIN -->\s*```json\s*(.*?)\s*```\s*<!-- V10_NORMATIVE_END -->", human, re.DOTALL)
    require(match is not None,"human_v9_normative_annex_present",checks)
    annex = json.loads(match.group(1))
    expected_annex = {name:contract[name] for name in ("lexical_neutrality_contract","entity_population_contract","reserve_equivalence_contract","subtype_allocation_contract","historical_fingerprint_adapter_contract","subtype_content_validation_contract")}
    expected_annex.update(
        source_contamination_atom_contract=contract["contamination_contract"]["exact_reuse_contract"]["date_number_tuple"],
        identity_atom_contract=contract["contamination_contract"]["exact_reuse_contract"]["identity_atom_derivation"],
        enum_schema_identity_contract=contract["operation_semantics_contract"]["exact_schema_identity_for_preserving_operations"],
        e7_integrated_shape_contract=contract["ambiguity_contract"]["integrated_fixture_shape_validation"],
        fingerprint_layout_contract=next(x for x in contract["contamination_contract"]["fingerprint"]["components"] if x["id"]=="source_fact_layout"),
        reserve_activation_contract=contract["reserve_activation_contract"],
        comparison_modes=contract["contamination_contract"]["comparison_modes"],
        lexical_similarity_categories=contract["contamination_contract"]["lexical_atoms"],
        whole_answer_reuse_limit=contract["contamination_contract"]["exact_reuse_contract"]["whole_answer"]["limit"],
        canonical_identity_atom_shape=contract["contamination_contract"]["exact_reuse_contract"]["entity_identifier_atoms"]["canonical_atom_shape"],
    )
    expected_annex.update({name:contract[name] for name in ("template_recurrence_contract","ordinal_neutral_similarity_contract","entity_selection_allocation_contract","value_allocation_contract")})
    expected_annex.update({name:contract[name] for name in ("e5_counterfactual_selector_contract","counterfactual_accounting","corpus","phases","cell_gates","sampling","efficiency","phase_a_fixture_reduction_contract","analysis_units")})
    require(set(annex)==set(expected_annex),"human_machine_v9_annex_exact_sections",checks)
    for name,value in expected_annex.items():
        require(annex[name]==value,f"human_machine_v9_normative_object:{name}",checks)
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
        "validate_design.py", "blueprint", "corpus",
    }
    require(not [path.name for path in HERE.iterdir() if path.name not in allowed], "design_inventory_with_preserved_untracked_corpus", checks)
    validate_existing_blueprint_inventory(checks)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--summary", action="store_true", help="Print compact deterministic report summary")
    args = parser.parse_args()
    contract = load_json_unique(MACHINE)
    human = HUMAN.read_text(encoding="utf-8")
    checks = validate(contract, human)
    report = {
        "schema_version": "g-extract1.design-validation-report.v10",
        "verdict": "PASS",
        "validation_scope": "deterministic structural and cross-representation consistency only",
        "scientific_validity_assessed": False,
        "adversarial_review_replaced": False,
        "check_count": len(checks),
        "output_field_amendment": OUTPUT_FIELD_AMENDMENT_SUMMARY,
        "declared_scaffold_feasibility_audit": SCAFFOLD_AUDIT,
        "freshness_canonicalization_amendment": FRESHNESS_AMENDMENT_SUMMARY,
        "whole_answer_canonicalization_amendment": WHOLE_ANSWER_AMENDMENT_SUMMARY,
        "historical_adapter": historical_adaptation_summary(contract),
        "preserved_v8_sections":preserved_v8_sections(contract),
        "template_ledger_summary": {
            "positions":len(contract["template_recurrence_contract"]["positions"]),
            "classes":len(contract["template_recurrence_contract"]["fingerprint_classes"]),
            "recurring_exact_classes":sum(len(x["members"])>1 for x in contract["template_recurrence_contract"]["fingerprint_classes"].values()),
            "subtype_groups":len(contract["template_recurrence_contract"]["subtype_template_groups"]),
            "pairwise_structural_checks":168*167//2,
            "scope":"symbolic structural feasibility only; future content/gold/contamination audit still mandatory",
        },
        "similarity_diagnostics":similarity_diagnostics(contract),
        "selector_blind_baselines":selector_blind_summary(contract["entity_selection_allocation_contract"]["selected_index_matrix"]),
        "selector_blind_baselines_scope":"secondary bounded CF1 anchor diagnostics only; not universal protection",
        "counterfactual_accounting":contract["counterfactual_accounting"],
        "counterfactual_request_audits":COUNTERFACTUAL_AUDITS,
        "counterfactual_audit_scope":"in-memory isolated design checking vectors only; rendered bytes are not provider calls or authored scored/reserve corpus items",
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
    if args.summary:
        print(json.dumps(dict(verdict=report["verdict"],check_count=report["check_count"],
            audit_scope=report["validation_scope"],historical_adapter=report["historical_adapter"],
            pre_repair=SCAFFOLD_AUDIT["infeasible_logical_pairs"],
            remaining_forced_violations=SCAFFOLD_AUDIT["post_repair"]["remaining_forced_violations"]),sort_keys=True))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
