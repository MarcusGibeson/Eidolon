"""Offline source-corpus authoring/checking only. Never sends provider requests.

The accepted design checker is a second gold path, not the evaluator below.
This file grants no pilot, freeze, implementation, or execution authority.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
import random
import re
from collections import Counter
from decimal import Decimal
from datetime import date, time, timedelta
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
SEED = "G-EXTRACT1-01aafde-corpus-authoring-1"
MAX_ATTEMPTS = 20000
spec = importlib.util.spec_from_file_location("bound_design", BASE / "validate_design.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
C = D.load_json_unique(BASE / "DESIGN_CANDIDATE.json")
B = D.load_json_unique(BASE / "blueprint/BLUEPRINT.json")
POSITIONS = {p["logical_base_id"]: p for p in B["logical_positions"]}
CATALOG = {r["id"]: r for r in C["operation_definition_contract"]["catalog"]}
SCAFFOLD = {frozenset(pair): row for row in B["comparison_scope"]["scaffold_overlap"]["classes"] for pair in row["rendered_position_pairs"]}


def compact(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def fixed(value):
    """Exact terminating rational serialization without Decimal context."""
    value = Fraction(value)
    den = value.denominator
    a = b = 0
    while den % 2 == 0:
        den //= 2
        a += 1
    while den % 5 == 0:
        den //= 5
        b += 1
    if den != 1:
        raise ValueError("nonterminating")
    scale = max(a, b)
    digits = str(abs(value.numerator) * 2 ** (scale-a) * 5 ** (scale-b)).zfill(scale+1)
    text = digits if not scale else digits[:-scale] + "." + digits[-scale:]
    if "." not in text:
        text += ".0"
    else:
        text = text.rstrip("0").rstrip(".")
        if "." not in text:
            text += ".0"
    return ("-" if value < 0 else "") + text


def tag(schema):
    return {"integer":"INTEGER", "number":"NUMBER", "boolean":"BOOLEAN", "string":"STRING", "YYYY-MM-DD":"DATE", "HH:MM":"TIME"}.get(schema, "ENUM")


def decode(raw, schema=None):
    kind, value = raw["kind"], raw["value"]
    if kind in {"integer_literal", "decimal_literal"}:
        return Fraction(value)
    if kind == "date_literal":
        return date.fromisoformat(value)
    if kind == "time_literal":
        return int(value[:2])*60 + int(value[3:])
    if kind == "boolean_literal": return value == "true"
    return value


def canonical(value, schema):
    t = tag(schema)
    if t == "NUMBER": return fixed(value)
    if t == "INTEGER":
        if Fraction(value).denominator != 1: raise ValueError("noninteger")
        return int(value)
    if t == "DATE": return value.isoformat()
    if t == "TIME": return f"{value//60:02d}:{value%60:02d}"
    return value


def freshness_schema(schema):
    """Parse exact schema bytes locally; semantic tags never enter freshness rows."""
    if not isinstance(schema, str):
        raise ValueError("freshness_schema_type")
    types = C["schema_type_contract"]
    if schema in types["primitive_schema_tokens"]:
        return types["primitive_schemas"][schema], None
    rule = types["finite_enum_schema"]
    options = schema.split("|")
    if not (rule["minimum_options"] <= len(options) <= rule["maximum_options"]
            and len(set(options)) == len(options)
            and all(re.fullmatch(rule["option_regex"], option, re.ASCII) for option in options)):
        raise ValueError("freshness_unknown_schema")
    return rule, options


def freshness_semantic_text(schema, value):
    info, options = freshness_schema(schema)
    semantic = info["semantic_tag"]
    if semantic in {"INTEGER", "NUMBER"}:
        if isinstance(value, (bool, float)) or not isinstance(value, (int, Decimal, Fraction, str)):
            raise ValueError("freshness_inexact_numeric")
        if isinstance(value, str):
            pattern = r"-?(?:0|[1-9][0-9]*)"
            if semantic == "NUMBER":
                pattern += r"(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
            if re.fullmatch(pattern, value, re.ASCII) is None:
                raise ValueError("freshness_numeric_lexeme")
        try:
            exact = Fraction(value)
        except (ValueError, OverflowError) as error:
            raise ValueError("freshness_nonfinite_numeric") from error
        if semantic == "INTEGER":
            if exact.denominator != 1:
                raise ValueError("freshness_nonintegral_integer")
            return str(exact.numerator)
        # The existing primary rational scaler is exact; only freshness drops .0.
        return fixed(exact).removesuffix(".0")
    if semantic == "BOOLEAN":
        if type(value) is not bool:
            raise ValueError("freshness_boolean_type")
        return "true" if value else "false"
    if semantic == "DATE" and isinstance(value, date):
        value = value.isoformat()
    elif semantic == "TIME" and isinstance(value, time):
        if value.second or value.microsecond or value.tzinfo is not None:
            raise ValueError("freshness_time_resolution")
        value = f"{value.hour:02d}:{value.minute:02d}"
    if not isinstance(value, str):
        raise ValueError("freshness_text_type")
    if semantic == "DATE":
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value, re.ASCII) is None:
            raise ValueError("freshness_date_format")
        date.fromisoformat(value)
    elif semantic == "TIME":
        if re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value, re.ASCII) is None:
            raise ValueError("freshness_time_format")
    elif semantic == "ENUM" and value not in options:
        raise ValueError("freshness_enum_membership")
    value.encode("utf-8", errors="strict")
    return value


def freshness_sequence_bytes(rows):
    canonical_rows = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError("freshness_row_shape")
        schema, value = row
        canonical_rows.append([schema, freshness_semantic_text(schema, value)])
    return json.dumps(canonical_rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def freshness_from_source_facts(facts):
    rows = []
    for fact in facts:
        if fact["template_id"] == "EXPLICIT_ABSENCE":
            continue
        if fact["template_id"] != "VALUE":
            raise ValueError("freshness_fact_template")
        info, _ = freshness_schema(fact["schema_type"])
        raw = fact["value"]
        if raw["kind"] not in info["source_value_kinds"]:
            raise ValueError("freshness_source_kind")
        value = raw["value"]
        if info["semantic_tag"] == "BOOLEAN":
            if value not in ("true", "false"):
                raise ValueError("freshness_boolean_literal")
            value = value == "true"
        rows.append([fact["schema_type"], value])
    return freshness_sequence_bytes(rows)


def require_freshness_bytes(raw, rows):
    if type(raw) is not bytes or raw != freshness_sequence_bytes(rows):
        raise ValueError("freshness_noncanonical_bytes")


def independent_gold(fixture):
    """Evaluator A: own dependency walk, exact rational and minute arithmetic."""
    facts = fixture["source_fact_records"]
    derived, traces = {}, []
    pending = list(fixture["operation_nodes"])
    def resolve(raw, entity=None):
        if raw["kind"] == "derived_field_identifier": return derived[raw["value"]]
        if raw["kind"] == "field_identifier":
            matches = [f for f in facts if f["template_id"] == "VALUE" and f["field_identifier"] == raw["value"] and f["entity_selector_value"] == entity]
            if len(matches) != 1: raise ValueError("independent_source_cardinality")
            f = matches[0]
            return f["schema_type"], decode(f["value"])
        schemas = {"integer_literal":"integer", "decimal_literal":"number", "date_literal":"YYYY-MM-DD", "time_literal":"HH:MM", "boolean_literal":"boolean", "entity_selector_literal":"string", "string_literal":"string"}
        return schemas.get(raw["kind"], "ENUM"), decode(raw)
    while pending:
        ready = [n for n in pending if all(x["kind"] != "derived_field_identifier" or x["value"] in derived for raw in n["arguments"].values() for x in (raw if isinstance(raw,list) else [raw]))]
        if len(ready) != 1: raise ValueError("independent_graph_chain")
        n = ready[0]; pending.remove(n)
        op, args = n["id"], n["arguments"]
        if op == "ENTITY_FIELD_BIND":
            schema, value = resolve(args["source_field"], args["selector_value"]["value"])
        else:
            vals = [resolve(x) for key in CATALOG[op]["placeholders"] if key != "target" for x in (args[key] if isinstance(args[key],list) else [args[key]])]
            v = [x[1] for x in vals]
            promoted = "number" if any(x[0] == "number" for x in vals) else "integer"
            if op == "ADD": schema,value = promoted,v[0]+v[1]
            elif op == "SUBTRACT": schema,value = promoted,v[0]-v[1]
            elif op == "MULTIPLY": schema,value = promoted,v[0]*v[1]
            elif op == "SUM": schema,value = promoted,sum(v,Fraction(0))
            elif op == "DIVIDE": schema,value = "number",v[0]/v[1]
            elif op == "UNIT_CONVERSION":
                factor = Fraction(C["operation_semantics_contract"]["unit_conversion_semantics"][n["conversion_id"]]["factor"])
                schema,value = "number",v[0]*factor
            elif op == "CALENDAR_DAY_OFFSET": schema,value = "YYYY-MM-DD",v[0]+timedelta(days=int(v[1]))
            elif op == "CLOCK_MINUTE_OFFSET": schema,value = "HH:MM",(v[0]+int(v[1]))%1440
            elif op == "ELAPSED_MINUTES": schema,value = "integer",(v[1]-v[0])%1440
            elif op == "EXACT_COPY": schema,value = vals[0]
            elif op in {"GT","GTE","LT","LTE","EQ"}:
                schema = "boolean"
                value = {"GT":v[0]>v[1],"GTE":v[0]>=v[1],"LT":v[0]<v[1],"LTE":v[0]<=v[1],"EQ":v[0]==v[1]}[op]
            else: raise ValueError("independent_unknown_operation")
        derived[n["target"]] = (schema,value)
        traces.append(dict(target=n["target"],operation=op,semantic_type=tag(schema),canonical_value=canonical(value,schema),arguments=copy.deepcopy(args),unique=True))
    gold, outputs = {}, []
    for field in fixture["output_fields"]:
        if field["binding_kind"] == "EXPLICIT_ABSENCE": schema,value = "provided|not_provided","not_provided"
        elif field["binding_kind"] == "SOURCE_COPY": schema,value = resolve(dict(kind="field_identifier",value=field["source_field"]))
        else: schema,value = derived[field["producer_target"]]
        if schema != field["schema_type"]: raise ValueError("independent_output_schema")
        gold[field["name"]] = canonical(value,schema)
        outputs.append(dict(name=field["name"],semantic_type=tag(schema),canonical_value=gold[field["name"]],binding_path=field["source_field"],producer_path=field["producer_target"],determinacy="exactly one binding and exact evaluation"))
    return gold, dict(nodes=traces,outputs=outputs)


def literal(schema, value):
    kinds = {"integer":"integer_literal", "number":"decimal_literal", "YYYY-MM-DD":"date_literal", "HH:MM":"time_literal", "boolean":"boolean_literal", "string":"string_literal"}
    if schema == "number": value = fixed(value)
    elif schema == "integer": value = str(value)
    elif schema == "YYYY-MM-DD" and isinstance(value,date): value = value.isoformat()
    elif schema == "HH:MM" and isinstance(value,int): value = f"{value//60:02d}:{value%60:02d}"
    elif schema == "boolean": value = "true" if value else "false"
    return dict(kind=kinds.get(schema,"enum_literal"),value=value)


def make_candidate(p, attempt):
    rng = random.Random(int(digest(SEED+":"+p["logical_base_id"]+":"+str(attempt)),16))
    ordinal = p["fixture_ordinal"]; family = p["family"]; index = p["within_family_slot"] or 1
    profile = p["value_shape_profile"]
    precision = profile["number_precision"]
    def number(band):
        low,high = C["value_allocation_contract"]["magnitude_bands"][band]
        return Fraction(rng.randint(low,high)) + Fraction(rng.choice([x for x in range(1,10**precision) if x%10]),10**precision)
    def random_date(): return date(2028,1,1)+timedelta(days=rng.randrange((date(2043,12,31)-date(2028,1,1)).days+1))
    def random_time(): return rng.choice([m for m in range(1440) if m%30])
    def raw_value(schema, i):
        if schema == "integer":
            bounds = C["value_allocation_contract"]["magnitude_bands"][profile["magnitude_bands"][i]] if profile["magnitude_bands"] else profile["temporal_distance"]
            return literal(schema,rng.randint(*bounds))
        if schema == "number": return literal(schema,number(profile["magnitude_bands"][i]))
        if schema == "YYYY-MM-DD": return literal(schema,random_date())
        if schema == "HH:MM": return literal(schema,random_time())
        if schema == "boolean": return literal(schema,C["value_allocation_contract"]["e7_boolean_source_allocation"][p["phase"]+":"+p["risk_round"]])
        if schema == "string": return literal(schema,f"label_{ordinal:03d}_01")
        option = C["subtype_allocation_contract"]["enum_answer_positions"][p["phase"]+":"+p["risk_round"]][p["subtype_slot"]]
        return literal(schema,schema.split("|")[option])
    fixture = dict(operation_nodes=[],output_fields=copy.deepcopy(p["schema_plan"]["output_fields"]),gold_values={},entities=[],source_fact_records=[],required_output_fields=[x["name"] for x in p["schema_plan"]["output_fields"]],lexical_context=dict(phase=p["phase"],risk_round=p["risk_round"],fixture_ordinal=ordinal,primary_family_slot=family,within_family_slot=None if p["primary_or_reserve"]=="RESERVE" else f"{index:02d}"))
    sequences = p["schema_plan"]["source_fact_role_schema_entity_sequence"]
    numeric_index = 0
    for i,(role,schema,entity) in enumerate(sequences):
        if family == "E5": field = f"f{ordinal:03d}_{1 if role=='SUPPORT' else 2:02d}"
        else: field = f"f{ordinal:03d}_{i+1:02d}"
        value = None if role == "EXPLICIT_ABSENCE" else raw_value(schema,numeric_index)
        if schema in {"integer","number"} and role != "EXPLICIT_ABSENCE": numeric_index += 1
        label = f"Entity {ordinal:03d} {chr(65+entity)}" if entity >= 0 else None
        if family == "E5" and role == "SUPPORT": value=dict(kind="entity_selector_literal",value=label)
        fixture["source_fact_records"].append(dict(template_id="EXPLICIT_ABSENCE" if role=="EXPLICIT_ABSENCE" else "VALUE",field_identifier=field,schema_type=schema,value=value,entity_selector_value=label))
    if family == "E5":
        ep = p["entity_plan"]; count = ep["entity_count"]
        fixture["entities"] = [dict(selector_value=f"Entity {ordinal:03d} {chr(65+i)}",selector_role=ep["selector_role"]) for i in range(count)]
        source = fixture["source_fact_records"][count:]
        schema = ep["source_schema"]
        selected = ep["selector_transition"][0]
        if schema in {"number","YYYY-MM-DD","HH:MM"}:
            low = number("MEDIUM") if schema=="number" else random_date() if schema=="YYYY-MM-DD" else rng.choice([m for m in range(1400) if m%30 and (m+13)%30 and (m+26)%30])
            gap = Fraction(str(profile["entity_separation"])) if schema=="number" else int(profile["entity_separation"])
            values = [low+timedelta(days=gap*i) if schema=="YYYY-MM-DD" else low+gap*i for i in range(count)]
            order = list(range(count)); order.remove(profile["entity_selected_rank"])
            rng.shuffle(order); order.insert(selected,profile["entity_selected_rank"])
            for i,f in enumerate(source): f["value"] = literal(schema,values[order[i]])
        elif schema == "string":
            for i,f in enumerate(source): f["value"] = literal(schema,f"{['label','code','id'][i%3]}_{ordinal:03d}_{i+1:02d}")
        else:
            options = schema.split("|")
            for i,f in enumerate(source): f["value"] = literal(schema,options[(i-selected+ep["enum_anchor_option_index"])%count])
    facts = fixture["source_fact_records"]
    plans = p["operation_plan"]["nodes"]
    if plans:
        first = plans[0]; op = first["operation_id"]
        if op == "CALENDAR_DAY_OFFSET":
            offset = rng.randint(*profile["temporal_distance"])
            want = p["recurrence"]["planned_six_components"][4]
            year = rng.randint(2028,2042)
            if want == "YEAR_BOUNDARY": start = date(year,12,rng.randint(20,31)) if offset<32 else date(year,3,rng.randint(1,20))
            elif want == "MONTH_BOUNDARY": start = date(year,rng.choice([1,3,4,5,6,7,8,9,10,11]),rng.randint(24,28))
            elif want == "LEAP_DAY_BOUNDARY": start = date(rng.choice([2028,2032,2036,2040]),2,rng.randint(23,29))
            else: start = date(year,rng.randint(1,12),rng.randint(1,13))
            facts[0]["value"] = literal("YYYY-MM-DD",start)
            if len(facts)>1: facts[1]["value"] = literal("integer",offset)
        elif op == "CLOCK_MINUTE_OFFSET":
            offset = rng.randint(*profile["temporal_distance"])
            lo,hi = (1440-offset,1439) if p["recurrence"]["planned_six_components"][4]=="MIDNIGHT_ROLLOVER" else (1,1439-offset)
            facts[0]["value"] = literal("HH:MM",rng.choice([m for m in range(lo,hi+1) if m%30]))
        elif op == "ELAPSED_MINUTES":
            offset = rng.randint(*profile["temporal_distance"])
            lo,hi = (1440-offset,1439) if index==4 else (1,1439-offset)
            start = rng.choice([m for m in range(lo,hi+1) if m%30 and (m+offset)%30])
            facts[0]["value"] = literal("HH:MM",start)
            if len(facts)>1: facts[1]["value"] = literal("HH:MM",(start+offset)%1440)
        source_cursor = 0
        for ni,plan in enumerate(plans):
            op = plan["operation_id"]; args = {}
            for path,kind,semantic in zip(plan["operand_argument_paths"],plan["operand_reference_kinds"],plan["operand_semantic_types"]):
                if kind == "source_field":
                    if op == "ENTITY_FIELD_BIND": name=f"f{ordinal:03d}_{2 if path=='source_field' else 1:02d}"
                    else:
                        name=facts[source_cursor]["field_identifier"]; source_cursor+=1
                    raw=dict(kind="field_identifier",value=name)
                elif kind == "derived_field": raw=dict(kind="derived_field_identifier",value=plans[0]["target_identifier"])
                elif kind == "entity_selector": raw=dict(kind="entity_selector_literal",value=fixture["entities"][p["entity_plan"]["selector_transition"][0]]["selector_value"])
                else:
                    if path in {"days","minutes"}: raw=literal("integer",offset)
                    elif op=="ELAPSED_MINUTES": raw=copy.deepcopy(facts[0]["value"])
                    else:
                        # Derive the upstream result before creating comparison operand.
                        temp=copy.deepcopy(fixture)
                        temp["output_fields"]=[dict(name=plans[0]["target_identifier"],schema_type=plans[0]["result_schema_type"],required=True,binding_kind="OPERATION_TARGET",source_field=None,producer_target=plans[0]["target_identifier"],label_removal=False,absence_capable=False)]
                        result=independent_gold(temp)[0][plans[0]["target_identifier"]]
                        schema=plans[0]["result_schema_type"]
                        value=decode(literal(schema,result))
                        gap=Fraction(str(profile["comparison_distance"])); relation=p["comparison_allocation"]["boundary_relation"]
                        delta=gap if relation=="BELOW" else -gap if relation=="ABOVE" else 0
                        value=value+timedelta(days=int(delta)) if schema=="YYYY-MM-DD" else int(value+delta) if schema=="HH:MM" else value+delta
                        raw=literal(schema,value)
                if "/" in path:
                    key=path.split("/")[0]; args.setdefault(key,[]).append(raw)
                else: args[path]=raw
            node=dict(id=op,target=plan["target_identifier"],arguments=args)
            if op=="UNIT_CONVERSION": node["conversion_id"]=p["operation_plan"]["conversion_id"]
            fixture["operation_nodes"].append(node)
        if family=="E4" and index==5:
            value=Fraction(facts[0]["value"]["value"])
            relation=p["comparison_allocation"]["boundary_relation"]
            gap=Fraction(str(profile["comparison_distance"]))
            facts[1]["value"]=literal("number",value+(gap if relation=="BELOW" else -gap if relation=="ABOVE" else 0))
    fixture["gold_values"],trace=independent_gold(fixture)
    return fixture,trace


def check_fixture(fixture,p):
    if fixture["output_fields"] != p["schema_plan"]["output_fields"]: raise ValueError("blueprint_output_construction")
    slot=dict(p["subtype"],phase=p["phase"],risk_round=p["risk_round"])
    actual_gold,_=independent_gold(fixture)
    if actual_gold!=fixture["gold_values"]: raise ValueError("independent_gold_disagreement")
    D.validate_v9_fixture(fixture,slot,C)
    fp=json.loads(D.fingerprint_bytes(dict(fixture=fixture),C["operation_definition_contract"]))
    if fp!=p["recurrence"]["planned_six_components"]: raise ValueError("blueprint_fingerprint")
    return fp


def request(fixture,p):
    op=C["operation_definition_contract"]
    subject=D.render_subject(dict(record_type=p["record_type"],nodes=fixture["operation_nodes"],include_absence_sentence=p["family"]=="E7"),op)
    return dict(prompt=D.assemble_prompt(subject,C["baseline_binding"]),input=dict(text=" ".join(D.render_fact(f,op["placeholder_type_system"],C["schema_type_contract"]) for f in fixture["source_fact_records"]),schema={f["name"]:f["schema_type"] for f in fixture["output_fields"]}))


def cache(fixture,p,variant):
    r=request(fixture,p)
    payload=D.ordinal_neutral_payload(r)
    answer=D.canonical_answer_bytes({f["name"]:dict(schema_type=f["schema_type"],value=fixture["gold_values"][f["name"]]) for f in fixture["output_fields"]},C["schema_type_contract"])
    atoms=D.extract_date_number_atoms(fixture,C["operation_definition_contract"],C["schema_type_contract"],C["operation_semantics_contract"],C["entity_population_contract"])
    identities={compact(["ENTITY",e["selector_value"]]) for e in fixture["entities"]}
    identities|={compact(["IDENTIFIER",f["value"]["value"]]) for f in fixture["source_fact_records"] if f["value"] and f["value"]["kind"]=="string_literal" and f["value"]["value"].startswith("id_")}
    raw_values=freshness_from_source_facts(fixture["source_fact_records"]).decode("utf-8")
    eligible=any(a[1] in {"DATE","TIME"} for a in atoms) and any(a[1] in {"INTEGER","NUMBER"} for a in atoms)
    return dict(id=p["logical_base_id"]+":"+variant,base=p["logical_base_id"],slot=p["subtype_slot"],request=r,raw_payload=compact(r["input"]),raw_values=raw_values,answer=answer,identities=identities,tuple=compact(atoms) if eligible else None,fp=json.loads(D.fingerprint_bytes(dict(fixture=fixture),C["operation_definition_contract"])),projection=json.loads(D.historical_projection(r,C)),ordinary=D.comparison_grams(payload,C),content=D.comparison_grams(payload,C,"content"),shape=D.comparison_grams(payload,C,"shape"))


def ratio(a,b):
    return [len(a&b),len(a|b)]


def pair_decision(a,b):
    if a["base"]==b["base"]: return "SAME_BASE_E5",None
    if a["raw_payload"]==b["raw_payload"]: return "FAIL","raw_payload_reuse"
    if a["raw_values"]==b["raw_values"]: return "FAIL","raw_value_sequence_reuse"
    if a["answer"]==b["answer"]: return "FAIL","whole_answer_reuse"
    if a["identities"]&b["identities"]: return "FAIL","identity_reuse"
    if a["tuple"] and a["tuple"]==b["tuple"]: return "FAIL","date_number_reuse"
    scaffold=SCAFFOLD.get(frozenset((a["id"],b["id"])))
    if scaffold:
        invariant={tuple(x.split(" ")) for x in scaffold["invariant_five_grams"]}
        ra,rb=a["ordinary"]-invariant,b["ordinary"]-invariant
        if not ra or not rb: return "FAIL","empty_scaffold_residual"
        i,u=ratio(ra,rb)
        return ("SCAFFOLD",None) if 25*i<3*u else ("FAIL","scaffold_residual")
    if a["slot"]==b["slot"]:
        if not a["content"] and not b["content"]: return "CONTENT",None
        i,u=ratio(a["content"],b["content"])
        return ("CONTENT",None) if u and 25*i<3*u else ("FAIL","same_subtype_content")
    i,u=ratio(a["ordinary"],b["ordinary"])
    matched=sum(x==y for x,y in zip(a["fp"],b["fp"]))
    return ("ORDINARY",None) if u and 5*i<u and matched!=6 and not(matched>=5 and 25*i>=3*u) else ("FAIL","ordinary_similarity_or_replay")


def historical_rows():
    result=[]
    for binding in C["historical_fingerprint_adapter_contract"]["artifact_bindings"]:
        if digest((ROOT/binding["path"]).read_bytes())!=binding["sha256"].lower(): raise ValueError("historical_digest")
        for f in D.load_json_unique(ROOT/binding["path"])["fixtures"]:
            if f["task_class"]=="structured_extraction":
                result.append(dict(id=f["fixture_id"],fixture=f,projection=json.loads(D.historical_projection(f,C)),grams=D.comparison_grams(D.ordinal_neutral_payload(f,True),C)))
    if len(result)!=106: raise ValueError("historical_count")
    return result


def historical_decision(h,a):
    i,u=ratio(h["grams"],a["ordinary"])
    equal=sum(x==y for x,y in zip(h["projection"],a["projection"]))
    return u and 5*i<u and equal!=3 and not(equal>=2 and 25*i>=3*u)


def author():
    accepted,accepted_cache,attempts=[],[],[]
    previous = HERE / "AUTHORING_FEASIBILITY_REPORT.json"
    history = HERE / "AUTHORING_ATTEMPTS.json"
    runs = D.load_json_unique(history)["runs"] if history.exists() else [dict(status="FAILED_TOOL_MAPPING",blocked_position="A:R2:E1-05:PRIMARY",attempt_count=20000,reason="list index out of range",candidate=None,source="first offline pass terminal evidence; no candidate constructed for blocked position")]
    if previous.exists():
        prior=D.load_json_unique(previous)
        if prior.get("status")=="INCOMPLETE_SEARCH_LIMIT_NOT_IMPOSSIBILITY_PROOF":
            runs.append(prior)
            save("AUTHORING_ATTEMPTS.json",dict(runs=runs))
    hist=historical_rows()
    for p in sorted(B["logical_positions"],key=lambda x:x["fixture_ordinal"]):
        for attempt in range(1,MAX_ATTEMPTS+1):
            fixture=None
            try:
                fixture,trace=make_candidate(p,attempt)
                check_fixture(fixture,p)
                members=D.counterfactual_members(fixture,dict(p["subtype"],phase=p["phase"],risk_round=p["risk_round"]),C) if p["family"]=="E5" else [fixture]
                caches=[cache(f,p,"CF"+str(i+1) if p["family"]=="E5" else "SINGLE") for i,f in enumerate(members)]
                for a in caches:
                    for h in hist:
                        if not historical_decision(h,a): raise ValueError("historical_contamination:"+h["id"])
                    for b in accepted_cache:
                        branch,reason=pair_decision(a,b)
                        if reason: raise ValueError(reason+":"+b["id"])
            except (ValueError,KeyError,TypeError,ZeroDivisionError,IndexError) as error:
                attempts.append(dict(base=p["logical_base_id"],attempt=attempt,reason=str(error),candidate=fixture))
            else:
                accepted.append(dict(logical_base_id=p["logical_base_id"],fixture=fixture,trace=trace,attempt=attempt))
                accepted_cache.extend(caches)
                print(p["logical_base_id"],"accepted",attempt,flush=True)
                break
        else:
            save("AUTHORING_FEASIBILITY_REPORT.json",dict(status="INCOMPLETE_SEARCH_LIMIT_NOT_IMPOSSIBILITY_PROOF",seed=SEED,max_attempts=MAX_ATTEMPTS,blocked_position=p["logical_base_id"],accepted=accepted,failed_attempts=attempts,provider_calls=0))
            raise RuntimeError("search_exhausted:"+p["logical_base_id"])
    save("AUTHORING_CANDIDATES.json",dict(seed=SEED,accepted=accepted,failed_attempts=attempts))
    print("Complete simultaneous candidate set; final independent validation required.",flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--author",action="store_true")
    args=parser.parse_args()
    if args.author: author()
    else: raise SystemExit("Final corpus validation has not been implemented; no readiness claim.")
