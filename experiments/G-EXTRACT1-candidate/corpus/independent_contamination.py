"""Independently authored offline contamination logic; no primary helpers.

Accepts the same frozen contract and data, sharing only standard library APIs.
Decisions use integer counts, never floating-point thresholds.
"""
import json
import re
import unicodedata
from datetime import date, time, timedelta
from decimal import Decimal
from fractions import Fraction


def dump(x):
    return json.dumps(x,ensure_ascii=True,separators=(",",":"))


def decimal(x):
    q=Fraction(str(x)); neg=q<0; q=abs(q)
    whole,remainder=divmod(q.numerator,q.denominator)
    digits=[]; seen=set()
    while remainder:
        if remainder in seen: raise ValueError("nonterminating")
        seen.add(remainder)
        digit,remainder=divmod(remainder*10,q.denominator)
        digits.append(str(digit))
    return ("-" if neg else "")+str(whole)+"."+("".join(digits) or "0")


def schema_tag(schema):
    return {"string":"STRING","number":"NUMBER","integer":"INTEGER","boolean":"BOOLEAN","YYYY-MM-DD":"DATE","HH:MM":"TIME"}.get(schema,"ENUM")


def canon(t,x):
    if t=="NUMBER": return decimal(x)
    if t=="INTEGER": return str(int(x))
    if t=="DATE": return x.isoformat() if isinstance(x,date) else x
    if t=="TIME": return f"{x//60:02d}:{x%60:02d}" if isinstance(x,int) else x
    return x


def freshness_type(schema, c):
    specification = c["schema_type_contract"]
    if not isinstance(schema, str):
        raise ValueError("freshness_schema_not_text")
    primitive = specification["primitive_schemas"].get(schema)
    if primitive is not None:
        return primitive, ()
    enumeration = specification["finite_enum_schema"]
    choices = tuple(schema.split("|"))
    if len(choices) < enumeration["minimum_options"] or len(choices) > enumeration["maximum_options"]:
        raise ValueError("freshness_enum_cardinality")
    if len(set(choices)) != len(choices):
        raise ValueError("freshness_enum_duplicates")
    for choice in choices:
        if re.fullmatch(enumeration["option_regex"], choice, flags=re.ASCII) is None:
            raise ValueError("freshness_schema_spelling")
    return enumeration, choices


def freshness_text(schema, x, c):
    definition, choices = freshness_type(schema, c)
    kind = definition["semantic_tag"]
    if kind in ("INTEGER", "NUMBER"):
        if isinstance(x, (bool, float)):
            raise ValueError("freshness_lossy_scalar")
        if isinstance(x, str):
            integer = r"-?(?:0|[1-9][0-9]*)"
            lexical = integer if kind == "INTEGER" else integer + r"(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
            if re.fullmatch(lexical, x, flags=re.ASCII) is None:
                raise ValueError("freshness_bad_numeric_token")
            q = Fraction(Decimal(x))
        elif isinstance(x, (int, Decimal, Fraction)):
            try:
                q = Fraction(x)
            except (ValueError, OverflowError) as error:
                raise ValueError("freshness_bad_exact_number") from error
        else:
            raise ValueError("freshness_unsupported_number")
        if kind == "INTEGER":
            if q.denominator != 1:
                raise ValueError("freshness_integer_domain")
            return str(q.numerator)
        reduced = q.denominator
        for factor in (2, 5):
            while reduced % factor == 0:
                reduced //= factor
        if reduced != 1:
            raise ValueError("freshness_nonterminating_decimal")
        # Independent long division, not the primary power-of-ten scaling path.
        whole, remainder = divmod(abs(q.numerator), q.denominator)
        fraction_digits = ""
        while remainder:
            digit, remainder = divmod(10 * remainder, q.denominator)
            fraction_digits += str(digit)
        magnitude = str(whole)
        if fraction_digits:
            magnitude += "." + fraction_digits
        return ("-" if q < 0 else "") + magnitude
    if kind == "BOOLEAN":
        if x is True: return "true"
        if x is False: return "false"
        raise ValueError("freshness_not_boolean")
    if kind == "DATE" and isinstance(x, date):
        x = x.isoformat()
    if kind == "TIME" and isinstance(x, time):
        if (x.second, x.microsecond, x.tzinfo) != (0, 0, None):
            raise ValueError("freshness_time_not_minutes")
        x = "%02d:%02d" % (x.hour, x.minute)
    if not isinstance(x, str):
        raise ValueError("freshness_not_string")
    if kind == "DATE":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", x, flags=re.ASCII):
            raise ValueError("freshness_bad_date_bytes")
        date.fromisoformat(x)
    if kind == "TIME" and not re.fullmatch(r"[012][0-9]:[0-5][0-9]", x, flags=re.ASCII):
        raise ValueError("freshness_bad_time_bytes")
    if kind == "TIME" and int(x[:2]) > 23:
        raise ValueError("freshness_time_hour")
    if kind == "ENUM" and x not in choices:
        raise ValueError("freshness_option_not_in_schema")
    x.encode("utf-8", errors="strict")
    return x


def freshness_sequence_bytes(rows, c):
    converted = []
    for pair in rows:
        if type(pair) is not list or len(pair) != 2:
            raise ValueError("freshness_bad_pair")
        converted.append([pair[0], freshness_text(pair[0], pair[1], c)])
    return json.dumps(converted, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def freshness_from_source_facts(records, c):
    semantic_rows = []
    for record in records:
        template = record["template_id"]
        if template == "EXPLICIT_ABSENCE": continue
        if template != "VALUE": raise ValueError("freshness_unknown_template")
        specification, _ = freshness_type(record["schema_type"], c)
        literal = record["value"]
        if literal["kind"] not in specification["source_value_kinds"]:
            raise ValueError("freshness_schema_literal_mismatch")
        v = literal["value"]
        if literal["kind"] == "boolean_literal":
            if v == "true": v = True
            elif v == "false": v = False
            else: raise ValueError("freshness_boolean_spelling")
        semantic_rows.append([record["schema_type"], v])
    return freshness_sequence_bytes(semantic_rows, c)


def require_freshness_bytes(candidate, rows, c):
    expected = freshness_sequence_bytes(rows, c)
    if not isinstance(candidate, bytes) or candidate != expected:
        raise ValueError("freshness_encoding_not_canonical")


def ordered_nodes(f):
    done=[]; available=set(); pending=list(f["operation_nodes"])
    while pending:
        eligible=[]
        for n in pending:
            dependencies=[r["value"] for a in n["arguments"].values() for r in (a if isinstance(a,list) else [a]) if r["kind"]=="derived_field_identifier"]
            if all(d in available for d in dependencies): eligible.append(n)
        if len(eligible)!=1: raise ValueError("not_chain")
        n=eligible[0]; pending.remove(n); done.append(n); available.add(n["target"])
    return done


def evaluate(f,c):
    derived={}; ordered=ordered_nodes(f)
    def literal(raw):
        k,x=raw["kind"],raw["value"]
        if k in {"integer_literal","decimal_literal"}: return ("INTEGER" if k=="integer_literal" else "NUMBER"),Fraction(x)
        if k=="date_literal": return "DATE",date.fromisoformat(x)
        if k=="time_literal": return "TIME",int(x[0:2])*60+int(x[3:5])
        if k=="boolean_literal": return "BOOLEAN",x=="true"
        return {"boolean_literal":"BOOLEAN","enum_literal":"ENUM"}.get(k,"STRING"),x
    def source(name,entity):
        matches=[r for r in f["source_fact_records"] if r["template_id"]=="VALUE" and r["field_identifier"]==name and r["entity_selector_value"]==entity]
        if len(matches)!=1: raise ValueError("source_cardinality")
        r=matches[0]; return schema_tag(r["schema_type"]),literal(r["value"])[1]
    def resolve(raw,entity=None):
        if raw["kind"]=="field_identifier": return source(raw["value"],entity)
        if raw["kind"]=="derived_field_identifier": return derived[raw["value"]]
        return literal(raw)
    boundary=temporal="NONE"
    for n in ordered:
        op=n["id"]; a=n["arguments"]
        if op=="ENTITY_FIELD_BIND": t,v=resolve(a["source_field"],a["selector_value"]["value"])
        else:
            catalog=next(r for r in c["operation_definition_contract"]["catalog"] if r["id"]==op)
            vals=[resolve(r) for key in catalog["placeholders"] if key!="target" for r in (a[key] if isinstance(a[key],list) else [a[key]])]
            xs=[r[1] for r in vals]
            t="NUMBER" if any(r[0]=="NUMBER" for r in vals) else "INTEGER"
            if op=="ADD": v=xs[0]+xs[1]
            elif op=="SUBTRACT": v=xs[0]-xs[1]
            elif op=="SUM": v=sum(xs,Fraction(0))
            elif op=="MULTIPLY": v=xs[0]*xs[1]
            elif op=="DIVIDE": t,v="NUMBER",xs[0]/xs[1]
            elif op=="UNIT_CONVERSION": t,v="NUMBER",xs[0]*Fraction(c["operation_semantics_contract"]["unit_conversion_semantics"][n["conversion_id"]]["factor"])
            elif op=="CALENDAR_DAY_OFFSET":
                t,v="DATE",xs[0]+timedelta(days=int(xs[1]))
                days=[xs[0]+timedelta(days=i) for i in range(int(xs[1])+1)]
                temporal="LEAP_DAY_BOUNDARY" if any(d.month==2 and d.day==29 for d in days) else "YEAR_BOUNDARY" if xs[0].year!=v.year else "MONTH_BOUNDARY" if xs[0].month!=v.month else "DATE_WITHIN_MONTH"
            elif op=="CLOCK_MINUTE_OFFSET":
                t,v="TIME",(xs[0]+int(xs[1]))%1440
                temporal="MIDNIGHT_ROLLOVER" if xs[0]+xs[1]>=1440 else "SAME_DAY_FORWARD"
            elif op=="ELAPSED_MINUTES":
                t,v="INTEGER",(xs[1]-xs[0])%1440
                temporal="MIDNIGHT_ROLLOVER" if xs[1]<xs[0] else "SAME_DAY_FORWARD"
            elif op=="EXACT_COPY": t,v=vals[0]
            else:
                boundary="BELOW" if xs[0]<xs[1] else "ABOVE" if xs[0]>xs[1] else "EQUAL"
                t="BOOLEAN"
                v={"GT":xs[0]>xs[1],"GTE":xs[0]>=xs[1],"LT":xs[0]<xs[1],"LTE":xs[0]<=xs[1],"EQ":xs[0]==xs[1]}[op]
        derived[n["target"]]=(t,v)
    return ordered,derived,resolve,boundary,temporal


def fingerprint(f,c):
    nodes,derived,resolve,boundary,temporal=evaluate(f,c)
    bytarget={n["target"]:n for n in nodes}
    def role(field):
        if field["binding_kind"]=="EXPLICIT_ABSENCE": return "absence_sentinel"
        if field["binding_kind"]=="SOURCE_COPY": return "source_copy"
        n=bytarget[field["producer_target"]]
        while n["id"]=="EXACT_COPY":
            r=n["arguments"]["source_field"]
            if r["kind"]=="field_identifier": return "source_copy"
            n=bytarget[r["value"]]
        if n["id"]=="ENTITY_FIELD_BIND": return "entity_bound_value"
        return {"DATE":"derived_date","TIME":"derived_time","BOOLEAN":"derived_boolean"}.get(derived[n["target"]][0],"derived_number")
    graph=[]
    for n in nodes:
        kinds=[]; deps=set()
        cat=next(r for r in c["operation_definition_contract"]["catalog"] if r["id"]==n["id"])
        for key in cat["placeholders"]:
            if key=="target": continue
            raw=n["arguments"][key]
            for r in raw if isinstance(raw,list) else [raw]:
                k=r["kind"]
                kinds.append({"field_identifier":"source_field","derived_field_identifier":"derived_field","entity_selector_literal":"entity_selector"}.get(k,"literal"))
                if k=="derived_field_identifier": deps.add(next(i for i,x in enumerate(nodes) if x["target"]==r["value"]))
        graph.append([n["id"],kinds,sorted(deps)])
    roles=sorted([[r["schema_type"],role(r)] for r in f["output_fields"]],key=lambda x:dump(x).encode())
    sink=nodes[-1] if nodes else None
    targets={r["source_field"] for r in f["output_fields"] if r["binding_kind"]=="SOURCE_COPY"}
    if sink and sink["id"] in {"EXACT_COPY","ENTITY_FIELD_BIND"} and sink["arguments"]["source_field"]["kind"]=="field_identifier": targets.add(sink["arguments"]["source_field"]["value"])
    support={r["value"] for n in nodes for a in n["arguments"].values() for r in (a if isinstance(a,list) else [a]) if r["kind"]=="field_identifier"}
    labels=[e["selector_value"] for e in f["entities"]]
    sequence=[]
    for fact in f["source_fact_records"]:
        r="EXPLICIT_ABSENCE" if fact["template_id"]=="EXPLICIT_ABSENCE" else "TARGET" if fact["field_identifier"] in targets else "SUPPORT" if fact["field_identifier"] in support else "DISTRACTOR"
        sequence.append([r,fact["schema_type"],labels.index(fact["entity_selector_value"]) if fact["entity_selector_value"] is not None else -1])
    layout="EXPLICIT_PARTIAL_ABSENCE" if any(r[0]=="EXPLICIT_ABSENCE" for r in sequence) else "INTERLEAVED_MULTI_ENTITY" if labels else "CONTIGUOUS_SINGLE_ENTITY"
    entity="MULTI_ENTITY_SELECT_BY_"+f["entities"][0]["selector_role"] if labels else "NONE"
    return [graph,roles,entity,boundary,temporal,[layout,sequence]]


def payload(request,historical=False):
    schema=request["input"]["schema"]
    text=request["input"]["text"]+"\n"+"\n".join(k+"="+schema[k] for k in sorted(schema,key=lambda x:x.encode("utf-8")))
    text=" ".join(unicodedata.normalize("NFC",text.replace("\r\n","\n").replace("\r","\n")).casefold().split())
    if not historical:
        ordinal=r"(?:00[1-9]|0[1-9][0-9]|1[0-5][0-9]|16[0-8])"
        text=re.sub(r"\b([fd])"+ordinal+r"_(\d{2})\b",r"\1_\2",text,flags=re.ASCII)
        text=re.sub(r"\bentity "+ordinal+r" ([abc])\b",r"entity \1",text,flags=re.ASCII)
        text=re.sub(r"\b(label|code|id)_"+ordinal+r"_(\d{2})\b",r"\1_\2",text,flags=re.ASCII)
    return text


def grams(request,c,view="ordinary",historical=False):
    tokens=re.findall(c["contamination_contract"]["tokenizer"]["pattern"],payload(request,historical),flags=re.ASCII)
    pat=r"(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}:[0-9]{2}|[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:e[+-]?[0-9]+)?|option_[a-h]|true|false)"
    if view=="content": pat=c["ordinal_neutral_similarity_contract"]["declared_template_content_view"]["content_value_regex"]
    marks=[re.fullmatch(pat,t,re.ASCII) is not None for t in tokens]
    if view=="shape": tokens=["value" if m else t for m,t in zip(marks,tokens)]
    out=set()
    for i in range(len(tokens)-4):
        if view!="content" or any(marks[i:i+5]): out.add(tuple(tokens[i:i+5]))
    return out


def projection(request,c):
    schema=request["input"]["schema"]
    tags=sorted([[schema_tag(s),len(s.split("|")) if "|" in s else 0] for s in schema.values()],key=lambda x:dump(x).encode())
    normal=lambda x:" ".join(unicodedata.normalize("NFC",x.replace("\r\n","\n").replace("\r","\n")).casefold().split())
    tokens=re.findall(c["contamination_contract"]["tokenizer"]["pattern"],normal(request["input"]["text"]),re.ASCII)
    adapter=c["historical_fingerprint_adapter_contract"]
    kinds=[]
    for t in tokens:
        kinds.append(next((k for k in ("DATE","TIME","NUMBER") if re.fullmatch(adapter["source_kind_regex"][k],t,re.ASCII)),"IDENTIFIER"))
    suffix=c["baseline_binding"]["structured_extraction_assembled_template"].replace("{SUBJECT}","")
    if not request["prompt"].endswith(suffix): raise ValueError("suffix")
    subject=normal(request["prompt"][:-len(suffix)])
    regex="|".join(f"(?P<S{i}>{r['regex']})" for i,r in enumerate(adapter["surface_catalog"]))
    surfaces=[adapter["surface_catalog"][int(m.lastgroup[1:])]["id"] for m in re.finditer(regex,subject,re.ASCII)]
    return [tags,kinds,surfaces]


def whole_answer_value(schema, value, c):
    """Independent typed parse: exact semantic object, never a display string."""
    definition, choices = freshness_type(schema, c)
    kind = definition['semantic_tag']
    if kind in ('INTEGER', 'NUMBER'):
        if isinstance(value, (bool, float)): raise ValueError('whole_answer_lossy_scalar')
        if isinstance(value, str):
            lexical = r'-?(?:0|[1-9][0-9]*)'
            if kind == 'NUMBER': lexical += r'(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?'
            if re.fullmatch(lexical, value, flags=re.ASCII) is None:
                raise ValueError('whole_answer_bad_numeric_token')
            exact = Fraction(Decimal(value))
        elif isinstance(value, (int, Decimal, Fraction)):
            try: exact = Fraction(value)
            except (ValueError, OverflowError) as error:
                raise ValueError('whole_answer_bad_exact_number') from error
        else: raise ValueError('whole_answer_unsupported_number')
        if kind == 'INTEGER' and exact.denominator != 1: raise ValueError('whole_answer_integer_domain')
        if kind == 'NUMBER':
            remaining = exact.denominator
            for prime in (2, 5):
                while remaining % prime == 0: remaining //= prime
            if remaining != 1: raise ValueError('whole_answer_nonterminating_decimal')
        return kind, exact
    if kind == 'BOOLEAN':
        if value is not True and value is not False: raise ValueError('whole_answer_not_boolean')
        return kind, value
    if kind == 'DATE' and type(value) is date: value = value.isoformat()
    if kind == 'TIME' and isinstance(value, time):
        if (value.second, value.microsecond, value.tzinfo) != (0, 0, None):
            raise ValueError('whole_answer_time_not_minutes')
        value = '%02d:%02d' % (value.hour, value.minute)
    if not isinstance(value, str): raise ValueError('whole_answer_not_string')
    if kind == 'DATE':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value, flags=re.ASCII):
            raise ValueError('whole_answer_bad_date_bytes')
        date.fromisoformat(value)
    if kind == 'TIME':
        if not re.fullmatch(r'[012][0-9]:[0-5][0-9]', value, flags=re.ASCII) or int(value[:2]) > 23:
            raise ValueError('whole_answer_bad_time_bytes')
    if kind == 'ENUM' and value not in choices: raise ValueError('whole_answer_option_not_in_schema')
    value.encode('utf-8', errors='strict')
    return kind, value


def whole_answer_render(kind, value):
    if kind == 'INTEGER': return str(value.numerator)
    if kind == 'NUMBER':
        integral, remainder = divmod(abs(value.numerator), value.denominator)
        digits = []
        while remainder:
            digit, remainder = divmod(remainder * 10, value.denominator)
            digits.append(str(digit))
        magnitude = str(integral) + ('.' + ''.join(digits) if digits else '')
        return ('-' if value < 0 else '') + magnitude
    if kind == 'BOOLEAN': return 'true' if value else 'false'
    return value


def whole_answer_bytes(rows, c):
    if type(rows) is not list: raise ValueError('whole_answer_bad_rows')
    by_name = {}
    for record in rows:
        if type(record) is not list or len(record) != 3: raise ValueError('whole_answer_bad_record')
        name, schema, value = record
        if not isinstance(name, str): raise ValueError('whole_answer_name_not_text')
        if name in by_name: raise ValueError('whole_answer_duplicate_name')
        name.encode('utf-8', errors='strict')
        kind, parsed = whole_answer_value(schema, value, c)
        by_name[name] = [name, schema, [kind, whole_answer_render(kind, parsed)]]
    encoded_rows = [by_name[name] for name in sorted(by_name, key=lambda name: name.encode('utf-8'))]
    return json.dumps(encoded_rows, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def require_whole_answer_bytes(candidate, rows, c):
    if not isinstance(candidate, bytes) or candidate != whole_answer_bytes(rows, c):
        raise ValueError('whole_answer_encoding_not_canonical')


def evidence(f,request,c):
    nodes,derived,resolve,_,_=evaluate(f,c)
    atoms=[]
    identities=set()
    for e in f["entities"]: identities.add(dump(["ENTITY",e["selector_value"]]))
    for fact in f["source_fact_records"]:
        if fact["template_id"]!="VALUE": continue
        t=schema_tag(fact["schema_type"])
        value=resolve(dict(kind="field_identifier",value=fact["field_identifier"]),fact["entity_selector_value"])[1]
        if t in {"INTEGER","NUMBER","DATE","TIME"}: atoms.append(["SOURCE_FACT",t,canon(t,value)])
        if t=="STRING" and fact["value"]["value"].startswith("id_"): identities.add(dump(["IDENTIFIER",fact["value"]["value"]]))
    for n in nodes:
        cat=next(r for r in c["operation_definition_contract"]["catalog"] if r["id"]==n["id"])
        for key in cat["placeholders"]:
            if key=="target": continue
            raws=n["arguments"][key]
            for r in raws if isinstance(raws,list) else [raws]:
                t,v=resolve(r,n["arguments"]["selector_value"]["value"] if n["id"]=="ENTITY_FIELD_BIND" and r["kind"]=="field_identifier" else None)
                if t in {"INTEGER","NUMBER","DATE","TIME"}: atoms.append(["OPERATION_ARGUMENT",t,canon(t,v)])
    answer=[]
    for field in sorted(f["output_fields"],key=lambda r:r["name"].encode()):
        t=schema_tag(field["schema_type"]);value=f["gold_values"][field["name"]]
        cv=canon(t,value)
        answer.append([field["name"],field["schema_type"],[t,cv]])
        if t in {"INTEGER","NUMBER","DATE","TIME"}: atoms.append(["GOLD",t,cv])
    eligible=any(x[1] in {"DATE","TIME"} for x in atoms) and any(x[1] in {"INTEGER","NUMBER"} for x in atoms)
    return dict(raw_payload=dump(request["input"]),raw_values=freshness_from_source_facts(f["source_fact_records"],c).decode("utf-8"),identities=identities,answer=whole_answer_bytes([[field['name'],field['schema_type'],f['gold_values'][field['name']]] for field in f['output_fields']],c),tuple=dump(atoms) if eligible else None,fp=fingerprint(f,c),projection=projection(request,c),ordinary=grams(request,c),content=grams(request,c,"content"),shape=grams(request,c,"shape"))


def independent_pair(a,b,scaffold):
    if a["base"]==b["base"]: return "SAME_BASE_E5",None
    for key,reason in (("raw_payload","raw_payload_reuse"),("raw_values","raw_value_sequence_reuse"),("answer","whole_answer_reuse")):
        if a[key]==b[key]: return "FAIL",reason
    if a["identities"].intersection(b["identities"]): return "FAIL","identity_reuse"
    if a["tuple"] is not None and a["tuple"]==b["tuple"]: return "FAIL","date_number_reuse"
    row=scaffold.get(frozenset([a["id"],b["id"]]))
    if row:
        forced=set(tuple(g.split(" ")) for g in row["invariant_five_grams"])
        left=a["ordinary"].difference(forced);right=b["ordinary"].difference(forced)
        if len(left)==0 or len(right)==0:return "FAIL","empty_scaffold_residual"
        return ("SCAFFOLD",None) if len(left.intersection(right))*25<len(left.union(right))*3 else ("FAIL","scaffold_residual")
    if a["slot"]==b["slot"]:
        left,right=a["content"],b["content"]
        if len(left)+len(right)==0:return "CONTENT",None
        return ("CONTENT",None) if len(left.intersection(right))*25<len(left.union(right))*3 else ("FAIL","same_subtype_content")
    common=len(a["ordinary"].intersection(b["ordinary"]));union=len(a["ordinary"].union(b["ordinary"]))
    matches=sum(x==y for x,y in zip(a["fp"],b["fp"]))
    fail=common*5>=union or matches==6 or (matches>=5 and common*25>=union*3)
    return ("FAIL","ordinary_similarity_or_replay") if fail else ("ORDINARY",None)
