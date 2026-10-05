"""Narrow offline freshness differential; never author or finalize corpus content."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
from datetime import date, time
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
ROOT = DESIGN.parent.parent
REPORT = HERE / "FRESHNESS_CHECKER_REPAIR_REPORT.json"
BASELINE = json.loads(r'''{"files":{"AUTHORING_ATTEMPTS.json":"b9860b6bd4f662c46935773463bf6caf78035a1c2aa01c0b6a55e5100b9aa8da","AUTHORING_CANDIDATES.json":"f575c8d86ca82f2c5ea7727404d0c8bbb5a72f7b472abfd244471edb3180d068","AUTHORING_FEASIBILITY_REPORT.json":"8767a025c1123541cc858873aff41b60ecc1f8b0186d72ccc738761a24771433","FINALIZATION_FAILURE_REPORT.json":"588b6141e3c25b561dff49d7b004ca508468ed39f4dbef8a8e16c54f69918730","FRESHNESS_CANONICALIZATION_DIAGNOSIS_REPORT.json":"7395408dcf283821d19ed81f6986d64c47b4d31f9dd76d1c72481f7dff48a442","independent_contamination.py":"8bc9d4eee55cbd91aebfb82f9d77bb74592db92e7ba0df9b62f111899d6533b4","validate_corpus.py":"8ff1a923c914e31c42121903b9763fd1e9b97a8b01f6b19b7f35a1de4ce2273d"},"gold":"803e8e4c57b63c7edb22f02194cbefdbf6be3fc964a0d77f65faa658f8904aec","function_ast_sha256":{"validate_corpus.py":{"compact":"afd475b519756597bdc52c20157430e397ec9c3100c1ccdf4b669eb9b9820af7","digest":"0ee938c2ae936d1886ea6f63230755891c80b7d67db85d5bfc57b267058bb0e9","save":"e986d7d9a695a57de9152bf5ec80c29ce47da11edcca8a510950118c7e2c3e04","fixed":"12b046865e6013eb167b63204ddd8122711fa991d73537b38a8462a27b45ee8b","tag":"e61c1adbd0a55ce59a8da16b9f448e5e13cc1dc33e8ee1c909caa8f855ef239e","decode":"b991712c0429ae669ac74e5a3aa57b7baa7ac1d63784dc1568c90b614957b795","canonical":"1cf22959e5fb6a546246904fac8933730807c7095d6c99a917cd835a935f426c","independent_gold":"5ae8ee727f2f97829ceda5d3d73551ba99a461d2ed90abe6e142efe05a780cea","literal":"132c998a4b2857607f433f8007e9a50e4a2c495142c77d8034d976a518b8a822","make_candidate":"58057dbca80a6be0cb58a82de6db596cb9a1d620e44610967b863cdcd7b40f91","check_fixture":"e1006688a07756ec84ba8442ea05a993c07b4e67d46a02c717347551ee23723b","request":"4ee12f3beb5ebaddca1aa18ac3bf3bc616703c457eea97d3c1755e5f0cfbeaf6","cache":"769505b8abd1d3faa4ee4ab2f9b85fdd8c66bef76e2ec733b688ccb7035852f2","ratio":"b8a9af24e2b252b45823e3a0a154316400e69114b1bd139fae6bf8582ad0dc9c","pair_decision":"33569ef1630e9a66d430640554882970e61b90f518d088feec8798dd74f0eaa7","historical_rows":"468105a2fe95328efa550e906dcdb3e96297595c6e63318052d40a25698cce56","historical_decision":"7b8253437073d44489b07c2ab435e1ee1d6559e1770ad9263b468db116de5e4d","author":"fe780d69007f4b773f44e99ce5eba4591cb3fc49ff6dbc7474a9d42c86aed6ef"},"independent_contamination.py":{"dump":"86dc634e2aeff4dfbd2e17ee547a0e1470c8a57bb35bf177d291bed9dc3b113b","decimal":"741112b2f114318f67fb154a788d49f8562c3fb3040b90ec644796e9c256576e","schema_tag":"f1fa310d5ebc85415d3e0741ff9cf79c719de0462800babb7d347e69b964f831","canon":"f67f8c37343369b29deeb7d07bbdd638bc897aae57c53e4d62e89bbc99a4f6d4","ordered_nodes":"6975af9db53c0ccc50a055eb4bbd9caf54e0f3d14a6eda28f840415240e04320","evaluate":"aabeebbb697e693f9eb48b28660152b03a367552f39f3d5c736dce268ac5d6bb","fingerprint":"0d7d95683bcbd5b070864750d0396fb6595267f36fa0d044437cf7a4305037e0","payload":"b3b40edbace6e288b41d103304417aa406c41c188e3cb27bdb5a4b4c06539e9a","grams":"fa2fa7108c51ee4cedccfdccf9cf3328b4ebd4233b6a582576b6319305330e1f","projection":"d3847b4ce0366756ca720aba10435541a314873ba31b3894d14471cd27e408c9","evidence":"d7ecaefccee1a0793892a7f8204c22f935bb1046d55d8a9dae9f993cbfb9c4e9","independent_pair":"8591529444df74d81268eb1463c7bacbeb59f95ada41585e0c8a06582a2b7b98"}}}''')
NORMALIZED_INTEGRATIONS = json.loads(r'''{"primary":"887038132c0833b09c4245c98cc706e82bcc4efd6fe67f5a870f28da2e69f567","independent":"b7cc97bf03eb8acbd09d24e2d7d13f9c9f1a5e118094c9cc2f429cdda65f5b47"}''')
SPECIFICATION_COMMITS = {
    "contamination_repair": "62c783bd8be708a86c82a9e00c80b0fa6fb5b459",
    "freshness_amendment": "e12484224cd11cf9c84026eb7deadf8c4eb9bab8",
    "blueprint": "3bf939ea3160596d89c64f1feef790477991cf8a",
}
CHECKERS = ("validate_corpus.py", "independent_contamination.py")
PRESERVED = tuple(name for name in BASELINE["files"] if name not in CHECKERS)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_bytes(commit, path):
    return subprocess.check_output(
        ["git", "-c", "safe.directory=" + ROOT.as_posix(), "show",
         commit + ":" + path.relative_to(ROOT).as_posix()], cwd=ROOT,
    )


def preservation_snapshot():
    files = {name: digest((HERE / name).read_bytes()) for name in BASELINE["files"]}
    for name in PRESERVED:
        if files[name] != BASELINE["files"][name]:
            raise ValueError("immutable_artifact_changed:" + name)
    candidates = json.loads((HERE / "AUTHORING_CANDIDATES.json").read_bytes())
    projection = [[row["logical_base_id"], row["fixture"]["gold_values"]]
                  for row in candidates["accepted"]]
    gold = digest(json.dumps(projection, sort_keys=True, ensure_ascii=True,
                             separators=(",", ":")).encode("utf-8"))
    if gold != BASELINE["gold"]:
        raise ValueError("immutable_gold_projection_changed")
    bound = {}
    for folder, commit, names in (
        (DESIGN, SPECIFICATION_COMMITS["freshness_amendment"],
         ("DESIGN_CANDIDATE.md", "DESIGN_CANDIDATE.json", "DESIGN_REVISION_CHANGELOG.md",
          "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md", "validate_design.py",
          "DESIGN_VALIDATION_REPORT.json")),
        (DESIGN / "blueprint", SPECIFICATION_COMMITS["blueprint"],
         ("BLUEPRINT.md", "BLUEPRINT.json", "validate_blueprint.py",
          "BLUEPRINT_VALIDATION_REPORT.json", ".gitattributes")),
    ):
        for name in names:
            path = folder / name
            raw = path.read_bytes()
            if raw != git_bytes(commit, path):
                raise ValueError("accepted_artifact_changed:" + name)
            bound[path.relative_to(ROOT).as_posix()] = digest(raw)
    c = json.loads((DESIGN / "DESIGN_CANDIDATE.json").read_bytes())
    historical = {}
    for name, key in (("G_ROUTE4_CLOSURE.json", "closure_sha256"),
                      ("PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json", "diagnostic_sha256")):
        path = ROOT / "experiments/G-ROUTE4-candidate/closure" / name
        historical[name] = digest(path.read_bytes())
        if historical[name] != c["historical_binding"][key].lower():
            raise ValueError("historical_evidence_changed")
    return dict(files=files, gold_projection_sha256=gold,
                accepted_artifacts_sha256=bound, historical_sha256=historical)


def normalized_integration(node, primary):
    node = copy.deepcopy(node)
    if primary:
        statement = next(s for s in node.body if isinstance(s, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "raw_values" for t in s.targets))
        statement.value = ast.Constant("FRESHNESS_ENCODING_ONLY")
    else:
        node.body = [s for s in node.body if not (
            isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "raw" for t in s.targets))]
        loop = next(s for s in node.body if isinstance(s, ast.For)
                    and isinstance(s.target, ast.Name) and s.target.id == "fact")
        loop.body = [s for s in loop.body if not (
            isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
            and isinstance(s.value.func, ast.Attribute)
            and isinstance(s.value.func.value, ast.Name) and s.value.func.value.id == "raw")]
        ret = next(s for s in node.body if isinstance(s, ast.Return))
        next(k for k in ret.value.keywords if k.arg == "raw_values").value = ast.Constant("FRESHNESS_ENCODING_ONLY")
    return digest(ast.dump(node, include_attributes=False).encode())


def scope_audit():
    result = {}
    for name in CHECKERS:
        tree = ast.parse((HERE / name).read_text(encoding="utf-8-sig"))
        functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        old = BASELINE["function_ast_sha256"][name]
        integration = "cache" if name == "validate_corpus.py" else "evidence"
        unchanged = []
        for function, expected in old.items():
            node = functions[function]
            if function == integration:
                key = "primary" if name == "validate_corpus.py" else "independent"
                if normalized_integration(node, key == "primary") != NORMALIZED_INTEGRATIONS[key]:
                    raise ValueError("unrelated_integration_change:" + name)
            elif digest(ast.dump(node, include_attributes=False).encode()) != expected:
                raise ValueError("unrelated_function_change:" + name + ":" + function)
            else:
                unchanged.append(function)
        additions = sorted(set(functions) - set(old))
        if any(not n.startswith(("freshness_", "require_freshness_")) for n in additions):
            raise ValueError("unrelated_new_function:" + name)
        # Freshness logic may use constants, local functions and standard library only.
        for function in additions:
            for node in ast.walk(functions[function]):
                if isinstance(node, ast.Name) and node.id in {"D", "B"}:
                    raise ValueError("shared_design_or_blueprint_freshness_helper")
        if name == "independent_contamination.py":
            imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
            if any(isinstance(n, ast.ImportFrom) and n.module not in
                   {"datetime", "decimal", "fractions"} for n in imports):
                raise ValueError("independent_nonstdlib_import")
            if any(isinstance(n, ast.Import) and any(a.name not in
                   {"json", "re", "unicodedata"} for a in n.names) for n in imports):
                raise ValueError("independent_shared_implementation_import")
        result[name] = dict(unchanged_existing_functions=unchanged,
                            integration_changed_only_in_freshness=True,
                            new_local_freshness_functions=additions)
    return result


def byte_mutations():
    cases = [
        ("integer_numeric_scalar", [["integer", "0"]], [["integer", 0]]),
        ("number_numeric_scalar", [["number", "5"]], [["number", 5]]),
        ("number_exponent_retained", [["number", "5e0"]], [["number", "5e0"]]),
        ("number_trailing_zeroes_retained", [["number", "0.50"]], [["number", "0.50"]]),
        ("number_empty_fraction_point_retained", [["number", "5.0"]], [["number", "5."]]),
        ("negative_zero_retained", [["number", "-0.0"]], [["number", "-0"]]),
        ("integer_leading_plus", [["integer", "1"]], [["integer", "+1"]]),
        ("integer_leading_zeroes", [["integer", "1"]], [["integer", "01"]]),
        ("boolean_capitalized", [["boolean", True]], [["boolean", "True"]]),
        ("date_reformatted", [["YYYY-MM-DD", "2039-10-05"]], [["YYYY-MM-DD", "10/05/2039"]]),
        ("time_reformatted", [["HH:MM", "23:45"]], [["HH:MM", "11:45 PM"]]),
        ("string_trimmed", [["string", " label_001_01 "]], [["string", "label_001_01"]]),
        ("enum_ordinal", [["option_a|option_b", "option_b"]], [["option_a|option_b", 1]]),
        ("atoms_sorted", [["string", "label_001_01"], ["integer", "42"]],
         [["integer", "42"], ["string", "label_001_01"]]),
        ("duplicate_removed", [["integer", "42"], ["integer", "42"]], [["integer", "42"]]),
        ("row_missing_element", [["integer", "0"]], [["integer"]]),
        ("row_extra_element", [["integer", "0"]], [["integer", "0", "extra"]]),
        ("null_value", [["integer", "0"]], [["integer", None]]),
        ("object_value", [["integer", "0"]], [["integer", {}]]),
        ("array_value", [["integer", "0"]], [["integer", []]]),
        ("schema_enum_reordered", [["option_a|option_b", "option_a"]],
         [["option_b|option_a", "option_a"]]),
        ("absence_included", [], [["provided|not_provided", "not_provided"]]),
        ("derived_output_included", [["integer", "1"]], [["integer", "1"], ["integer", "2"]]),
        ("integer_number_schema_collapse", [["number", "5"]], [["integer", "5"]]),
        ("boolean_scalar", [["boolean", True]], [["boolean", True]]),
    ]
    for schema, value, tag in (
        ("integer", "0", "INTEGER"), ("number", "5", "NUMBER"),
        ("YYYY-MM-DD", "2039-10-05", "DATE"), ("HH:MM", "23:45", "TIME"),
        ("string", "label_001_01", "STRING"), ("boolean", True, "BOOLEAN"),
        ("option_a|option_b", "option_a", "ENUM"),
    ):
        cases.append(("semantic_tag_" + tag.lower(), [[schema, value]],
                      [[tag, "true" if value is True else value]]))
    pack = lambda rows: json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    packed = [(name, rows, pack(mutant)) for name, rows, mutant in cases]
    packed.extend([
        ("whitespace_formatted_json", [["integer", "0"]], b'[["integer", "0"]]'),
        ("ensure_ascii_true_non_ascii", [["string", "\u00e9"]], b'[["string","\\u00e9"]]'),
        ("trailing_newline", [["integer", "0"]], b'[["integer","0"]]\n'),
    ])
    return packed


def validate():
    before = preservation_snapshot()
    scope = scope_audit()
    primary = load_module("freshness_primary_checker", HERE / CHECKERS[0])
    independent = load_module("freshness_independent_checker", HERE / CHECKERS[1])
    contract, blueprint = primary.C, primary.B
    accepted = contract["freshness_canonicalization_contract"]
    if blueprint["freshness_serialization_plan"]["materialized_contract"] != accepted:
        raise ValueError("freshness_contract_binding")
    encoders = (primary.freshness_sequence_bytes,
                lambda rows: independent.freshness_sequence_bytes(rows, contract))
    require_bytes = (primary.require_freshness_bytes,
                     lambda raw, rows: independent.require_freshness_bytes(raw, rows, contract))
    checks = []

    def require(ok, label):
        if not ok:
            raise ValueError(label)
        checks.append(label)

    vector_results = []
    for vector in accepted["validation_vectors"]:
        expected = vector["expected_utf8"].encode("utf-8")
        actual = [encode(vector["semantic_rows"]) for encode in encoders]
        require(actual[0] == actual[1] == expected, "schema_vector:" + vector["id"])
        require(all(type(x) is str for row in json.loads(actual[0]) for x in row),
                "two_string_rows:" + vector["id"])
        vector_results.append(dict(id=vector["id"],
                                   schemas=[row[0] for row in vector["semantic_rows"]],
                                   expected_utf8=expected.decode(),
                                   primary_sha256=digest(actual[0]),
                                   independent_sha256=digest(actual[1]), agreement=True))
    supplemental = [
        ("integer_negative_zero", "integer", "-0", "0"),
        ("number_small_exact", "number", "0.000000000000000000000000000001",
         "0.000000000000000000000000000001"),
        ("number_large_exact", "number", "123456789012345678901234567890.125000",
         "123456789012345678901234567890.125"),
        ("number_0.5", "number", "0.5", "0.5"),
        ("number_0.05", "number", "0.05", "0.05"),
        ("number_-12.34", "number", "-12.34", "-12.34"),
    ]
    for name, schema, value, expected_text in supplemental:
        expected = json.dumps([[schema, expected_text]], ensure_ascii=False,
                              separators=(",", ":")).encode()
        actual = [encode([[schema, value]]) for encode in encoders]
        require(actual[0] == actual[1] == expected, "supplemental_vector:" + name)
        vector_results.append(dict(id=name, schemas=[schema], expected_utf8=expected.decode(),
                                   primary_sha256=digest(actual[0]),
                                   independent_sha256=digest(actual[1]), agreement=True))
    covered = sorted({schema for result in vector_results for schema in result["schemas"]})
    require(covered == blueprint["freshness_serialization_plan"]["active_source_schema_types"],
            "all_nine_active_schemas")
    equivalences = []
    for group in accepted["equivalence_groups"]:
        outputs = [encode([[group["schema_type"], value]]) for value in group["values"]
                   for encode in encoders]
        require(set(outputs) == {group["expected_utf8"].encode()}, "equivalence:" + group["id"])
        equivalences.append(dict(group, primary_and_independent_agree=True))
    host_results = []
    for schema in ("integer", "number"):
        for v in (0, 1, -1, 42, 10**70 + 1):
            forms = (v, str(v), Decimal(str(v)), Fraction(v))
            outputs = [encode([[schema, form]]) for form in forms for encode in encoders]
            require(len(set(outputs)) == 1, "host_types:" + schema + ":" + str(v))
            host_results.append(dict(schema=schema, value=str(v),
                                     host_types=["int", "str", "Decimal", "Fraction"], agreement=True))
    for v, text in ((Fraction(1, 8), "0.125"),
                    (Decimal("-0.000"), "0"),
                    (Fraction(-617, 50), "-12.34")):
        require(all(encode([["number", v]]) == ('[["number","' + text + '"]]').encode()
                    for encode in encoders), "exact_rational:" + str(v))
    for schema, value, expected in (
        ("YYYY-MM-DD", date(2039, 10, 5), "2039-10-05"),
        ("HH:MM", time(23, 45), "23:45"),
    ):
        require(all(encode([[schema, value]]) == encode([[schema, expected]]) for encode in encoders),
                "temporal_host_value:" + schema)

    pairs = [
        ([["integer", "5"]], [["number", "5"]]),
        ([["number", "5"]], [["number", "5.0001"]]),
        ([["number", "0.5"]], [["number", "0.05"]]),
        ([["boolean", True]], [["string", "true"]]),
        ([["string", "\u00e9"]], [["string", "e\u0301"]]),
        ([["integer", "1"], ["string", "label_001_01"]],
         [["string", "label_001_01"], ["integer", "1"]]),
        ([["integer", "1"], ["integer", "1"]], [["integer", "1"]]),
    ]
    for index, (left, right) in enumerate(pairs):
        require(all(encode(left) != encode(right) for encode in encoders),
                "distinctness_order_or_duplicate:" + str(index))
    bad_inputs = [
        [["number", 0.5]], [["integer", True]], [["number", Fraction(1, 3)]],
        [["number", "NaN"]], [["number", Decimal("Infinity")]], [["number", Decimal("NaN")]],
        [["integer", "5.0"]], [["integer", "5e0"]], [["integer", "+1"]],
        [["integer", "01"]], [["integer", Fraction(1, 2)]],
        [["boolean", "true"]], [["string", 1]], [["YYYY-MM-DD", "2039-02-29"]],
        [["YYYY-MM-DD", "2039-1-05"]], [["HH:MM", "24:00"]], [["HH:MM", "1:00"]],
        [["option_a|option_b", 1]], [["option_a|option_b", "option_c"]],
        [["INTEGER", "0"]], [["DATE", "2039-10-05"]], [["TIME", "23:45"]],
        [["ENUM", "option_a"]], [["date", "2039-10-05"]],
        [["one|one", "one"]], [["one |two", "one"]], [["string", "\ud800"]],
        [["integer"]], [["integer", "0", "extra"]],
    ]
    class DisplayOnlyNumber:
        def __str__(self):
            return "5"
    bad_inputs.extend([[["number", DisplayOnlyNumber()]], [["integer", DisplayOnlyNumber()]]])
    rejection_results = []
    for index, rows in enumerate(bad_inputs):
        for label, encode in zip(("primary", "independent"), encoders):
            try:
                encode(rows)
            except (ValueError, TypeError, UnicodeError):
                checks.append("invalid_input_rejected:" + label + ":" + str(index))
            else:
                raise ValueError("invalid_semantic_input_accepted:" + label + ":" + str(index))
        rejection_results.append(dict(index=index, primary_rejected=True, independent_rejected=True))
    mutations = []
    for name, rows, altered in byte_mutations():
        for label, checker in zip(("primary", "independent"), require_bytes):
            try:
                checker(altered, rows)
            except ValueError:
                checks.append("byte_mutation_rejected:" + label + ":" + name)
            else:
                raise ValueError("mutated_representation_accepted:" + label + ":" + name)
        mutations.append(dict(id=name, mutated_utf8=altered.decode("utf-8"),
                              primary_rejected=True, independent_rejected=True))
    require(set(accepted["mutation_catalog"]).issubset({r["id"] for r in mutations}),
            "entire_accepted_mutation_catalog")

    candidates = json.loads((HERE / "AUTHORING_CANDIDATES.json").read_bytes())
    bases = {r["logical_base_id"]: r for r in candidates["accepted"]}
    require(len(bases) == 168, "168_existing_bases")
    variant_results = []
    original_failure = None
    gold_results = []
    for p in blueprint["logical_positions"]:
        fixture = bases[p["logical_base_id"]]["fixture"]
        gold, _ = primary.independent_gold(fixture)
        require(gold == fixture["gold_values"], "unchanged_existing_gold:" + p["logical_base_id"])
        gold_results.append(dict(logical_base_id=p["logical_base_id"], existing_gold_matches=True))
        members = primary.D.counterfactual_members(
            fixture, dict(p["subtype"], phase=p["phase"], risk_round=p["risk_round"]), contract,
        ) if p["family"] == "E5" else [fixture]
        for index, member in enumerate(members):
            variant_id = "CF" + str(index + 1) if p["family"] == "E5" else "SINGLE"
            facts = member["source_fact_records"]
            left = primary.freshness_from_source_facts(facts)
            right = independent.freshness_from_source_facts(facts, contract)
            require(left == right, "variant_freshness:" + p["logical_base_id"] + ":" + variant_id)
            # Evidence construction is replayed only to verify wiring, not pairwise acceptance.
            primary_evidence = primary.cache(member, p, variant_id)
            independent_evidence = independent.evidence(member, primary_evidence["request"], contract)
            require(primary_evidence["raw_values"].encode("utf-8") == left
                    and independent_evidence["raw_values"].encode("utf-8") == right,
                    "freshness_integration:" + p["logical_base_id"] + ":" + variant_id)
            variant_results.append(dict(logical_base_id=p["logical_base_id"], variant_id=variant_id,
                                        primary_bytes_sha256=digest(left),
                                        independent_bytes_sha256=digest(right), agreement=True))
            if p["logical_base_id"] == "A:R2:E1-05:PRIMARY":
                expected = accepted["original_failure_semantic_vector"]["expected_utf8"].encode("utf-8")
                require(left == right == expected, "original_failure_replay")
                historical_stop = json.loads((HERE / "FINALIZATION_FAILURE_REPORT.json").read_bytes())["independent_comparison"]
                require(historical_stop["logical_base_id"] == p["logical_base_id"],
                        "original_failure_history_binding")
                original_failure = dict(
                    logical_base_id=p["logical_base_id"], variant_id=variant_id,
                    before_primary_utf8=historical_stop["primary_bytes_utf8"],
                    before_independent_utf8=historical_stop["independent_bytes_utf8"],
                    after_primary_utf8=left.decode(), after_independent_utf8=right.decode(),
                    agreement=True,
                )
    expected_variants = {(v["logical_base_id"], v["variant_id"]) for v in blueprint["rendered_variants"]}
    require({(r["logical_base_id"], r["variant_id"]) for r in variant_results} == expected_variants
            and len(variant_results) == 192, "exact_192_variant_inventory")
    require(original_failure is not None, "original_failure_case_present")

    source_fixture = copy.deepcopy(bases["A:R2:E1-05:PRIMARY"]["fixture"])
    for label, extractor in (
        ("primary", primary.freshness_from_source_facts),
        ("independent", lambda facts: independent.freshness_from_source_facts(facts, contract)),
    ):
        original = extractor(source_fixture["source_fact_records"])
        changed = copy.deepcopy(source_fixture)
        for fact in changed["source_fact_records"]:
            fact["field_identifier"] = "f999_99"
        require(extractor(changed["source_fact_records"]) == original,
                "no_field_names:" + label)
        changed_id = copy.deepcopy(source_fixture)
        changed_id["logical_base_id"] = "TEST_ONLY_ID"
        changed_id["lexical_context"]["fixture_ordinal"] = 999
        require(extractor(changed_id["source_fact_records"]) == original,
                "no_fixture_ids:" + label)
        reversed_records = list(reversed(source_fixture["source_fact_records"]))
        require(extractor(reversed_records) != original, "source_order:" + label)
        doubled = source_fixture["source_fact_records"] * 2
        require(extractor(doubled) != original, "source_duplicates:" + label)
        e7 = next(r["fixture"]["source_fact_records"] for r in candidates["accepted"]
                  if ":E7-" in r["logical_base_id"])
        values = [fact for fact in e7 if fact["template_id"] == "VALUE"]
        require(extractor(e7) == extractor(values), "VALUE_only:" + label)
    after = preservation_snapshot()
    require(before == after, "all_protected_bytes_and_gold_unchanged_during_replay")
    return dict(
        schema_version="g-extract1.freshness-checker-repair-report.v1",
        verdict="PASS", status="READY_TO_RESUME_G_EXTRACT1_CORPUS_FINALIZATION",
        validation_scope="narrow deterministic freshness compatibility only; no final corpus acceptance",
        specification_commits=SPECIFICATION_COMMITS,
        canonicalization_contract_id=accepted["contract_id"],
        normative_path="DESIGN_CANDIDATE.json#/freshness_canonicalization_contract",
        root_cause="Both old raw_values paths used semantic tags. Primary canonical(INTEGER) returned int; independent canon(INTEGER) returned str. Gold/display serializers were incorrectly reused for freshness.",
        primary_implementation="Local schema parser and schema-specific conversion; exact reduced-rational power-of-ten scaling via unchanged local fixed(); freshness removes integral .0.",
        independent_implementation="Local typed schema/parser path; Decimal token to exact Fraction; separate integer long division produces minimal plain decimal.",
        shared_freshness_helper=False, scope_audit=scope,
        checker_sha256={name: after["files"][name] for name in CHECKERS},
        test_artifact_sha256=digest(Path(__file__).read_bytes()),
        before=BASELINE, replay_before=before, after=after,
        original_failure_replay=original_failure,
        rendered_variant_count=len(variant_results), variant_results=variant_results,
        schema_vector_count=len(vector_results), active_schemas=covered,
        schema_vector_results=vector_results, numeric_equivalence_results=equivalences,
        host_type_results=host_results, invalid_semantic_inputs=rejection_results,
        mutation_count=len(mutations), mutation_results=mutations,
        existing_gold_replay=gold_results, disagreement_count=0,
        check_count=len(checks), checks=checks,
        final_contamination_campaign_run=False, corpus_accepted=False, corpus_finalized=False,
        manifest_frozen=False,
        governance=dict(provider_model_calls=0, corpus_regeneration=0, gold_modifications=0,
                        runtime_implementation=False, mechanical_pilot=False,
                        experiment_execution=False, G_ROUTE4="CLOSED FAILED unchanged",
                        belief_effects="none"),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true",
                        help="Write only the narrow repair report after all checks pass.")
    args = parser.parse_args()
    report = validate()
    if args.write_report:
        REPORT.write_bytes((json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2)
                            + "\n").encode("utf-8"))
    elif json.loads(REPORT.read_bytes()) != report:
        raise ValueError("repair_report_stale")
    print(json.dumps({key: report[key] for key in (
        "verdict", "check_count", "rendered_variant_count", "schema_vector_count",
        "mutation_count", "disagreement_count", "corpus_accepted", "corpus_finalized",
    )}, indent=2))


if __name__ == "__main__":
    main()
