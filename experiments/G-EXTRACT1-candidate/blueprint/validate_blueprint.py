"""Value-free blueprint construction/checking. No corpus, scorer or provider code."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import itertools
import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
ROOT = DESIGN.parent.parent
SCIENTIFIC_BASIS = "394d24121309ec9dce80e725b50dbe5eb60f6d2a"
ORIGINAL_BLUEPRINT = "99707b4f13abd6533f1d09313bdb066793996be9"
OUTPUT_AMENDMENT = "aef3e0900cba41481904c8a451c4ca28b9d46c53"
OUTPUT_BLUEPRINT = "28fb6bbd3fb668265e4cc50cda0da0f9afdf3ce5"
PRIOR_BLUEPRINT = "01aafde7410a44085999aa4aa39f883618e78799"
CONTAMINATION_REPAIR = "62c783bd8be708a86c82a9e00c80b0fa6fb5b459"
FRESHNESS_AMENDMENT = "e12484224cd11cf9c84026eb7deadf8c4eb9bab8"
WHOLE_PRIOR_BLUEPRINT = "3bf939ea3160596d89c64f1feef790477991cf8a"
ACCEPTED = "d1b9e2aa5dbe0aeebb74f8226ca8033182f7b3c1"
SOURCE_NAMES = (
    "DESIGN_CANDIDATE.md", "DESIGN_CANDIDATE.json",
    "DESIGN_REVISION_CHANGELOG.md", "HUMAN_MACHINE_EQUIVALENCE_CHECKLIST.md",
    "DESIGN_VALIDATION_REPORT.json", "validate_design.py",
)
FILES = ("BLUEPRINT.json", "BLUEPRINT.md", "validate_blueprint.py",
         "BLUEPRINT_VALIDATION_REPORT.json", ".gitattributes")


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.run(
        ["git", "-c", "safe.directory=" + ROOT.as_posix(), *args], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout


def load_authority():
    hashes = {}
    for name in SOURCE_NAMES:
        path = DESIGN / name
        committed = git("show", ACCEPTED + ":" + path.relative_to(ROOT).as_posix())
        if path.read_bytes() != committed:
            raise ValueError("BLUEPRINT_BLOCKED_BY_DESIGN_AMBIGUITY: accepted artifact mismatch: " + name)
        hashes[name] = digest(committed)
    contract = json.loads((DESIGN / "DESIGN_CANDIDATE.json").read_text(encoding='utf-8'))
    spec = importlib.util.spec_from_file_location("accepted_design_checks", DESIGN / "validate_design.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return contract, module, hashes


def ref(pointer):
    return "DESIGN_CANDIDATE.json#" + pointer


def traceability():
    return {
        "identity": [ref("/lexical_neutrality_contract/fixture_ordinal_assignment"), ref("/e5_counterfactual_selector_contract/base_fixture_id_format")],
        "lexical_context": [ref("/lexical_neutrality_contract")],
        "subtype": [ref("/subtype_allocation_contract/slot_rows")],
        "operation_plan": [ref("/template_recurrence_contract/structural_wiring"), ref("/operation_semantics_contract"), ref("/operation_definition_contract")],
        "secondary_features": [ref("/family_assignment_contract/secondary_feature_derivations")],
        "schema_plan": [ref("/schema_type_contract"), ref("/family_assignment_contract/canonical_output_field_contract"), ref("/template_recurrence_contract/fingerprint_classes"), ref("/output_field_amendment_contract")],
        "value_shape_profile": [ref("/value_allocation_contract")],
        "comparison_allocation": [ref("/subtype_allocation_contract/comparison_slot_matrix")],
        "entity_plan": [ref("/entity_population_contract"), ref("/subtype_allocation_contract/enum_answer_positions"), ref("/e5_counterfactual_selector_contract")],
        "e7_presentation": [ref("/subtype_allocation_contract/e7_source_order"), ref("/ambiguity_contract/integrated_fixture_shape_validation")],
        "recurrence": [ref("/template_recurrence_contract"), ref("/e5_counterfactual_selector_contract/contamination")],
        "reserve_map": [ref("/reserve_activation_contract"), ref("/reserve_equivalence_contract"), ref("/e5_counterfactual_selector_contract/reserves")],
        "gate_membership": [ref("/cell_gates"), ref("/phase_a_fixture_reduction_contract"), ref("/e5_counterfactual_selector_contract/scoring")],
        "authoring_constraints": [ref("/subtype_content_validation_contract"), ref("/operation_semantics_contract/gold_derivation"), ref("/contamination_contract")],
        "rendered_variants": [ref("/e5_counterfactual_selector_contract"), ref("/counterfactual_accounting")],
        "schedule": [ref("/sampling"), ref("/e5_counterfactual_selector_contract/seeds")],
        "request_template": [ref("/baseline_binding"), ref("/e5_counterfactual_selector_contract/request_contract"), ref("/model_provider")],
        "comparison_scope": [ref("/contamination_contract"), ref("/ordinal_neutral_similarity_contract"), ref("/historical_fingerprint_adapter_contract"), ref("/e5_counterfactual_selector_contract/contamination")],
        "scaffold_overlap": [ref("/declared_scaffold_overlap_contract")],
        "freshness_serialization": [ref("/freshness_canonicalization_contract"), ref("/template_recurrence_contract/freshness_sequence"), ref("/schema_type_contract")],
        "whole_answer_serialization": [ref("/whole_answer_canonicalization_contract"), ref("/contamination_contract/exact_reuse_contract/whole_answer"), ref("/schema_type_contract")],
        "governance": [ref("/governance"), ref("/implementation_authorization_prerequisites")],
    }


def features(ids, boundary, family, order):
    present = {
        "calendar_date": "CALENDAR_DAY_OFFSET" in ids,
        "clock_time": "CLOCK_MINUTE_OFFSET" in ids,
        "elapsed_time": "ELAPSED_MINUTES" in ids,
        "aggregation": bool(set(ids) & {"ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "SUM", "UNIT_CONVERSION"}),
        "unit_conversion": "UNIT_CONVERSION" in ids,
        "threshold": bool(set(ids) & {"GT", "GTE", "LT", "LTE", "EQ"}),
        "equality_boundary": "EQ" in ids or boundary == "EQUAL",
        "entity_binding": "ENTITY_FIELD_BIND" in ids,
        "field_binding": bool(ids) and ids[-1] in {"ENTITY_FIELD_BIND", "EXACT_COPY"},
        "exact_copy": "EXACT_COPY" in ids,
        "multi_step": len(ids) == 2,
        "explicit_partial_absence": family == "E7",
    }
    return [tag for tag in order if present[tag]]


def typed_node_plan(graph, source_sequence, output_roles, row, ordinal, c):
    tags = {schema: info["semantic_tag"] for schema, info in c["schema_type_contract"]["primitive_schemas"].items()}
    tag = lambda schema: tags.get(schema, "ENUM")
    source_types = [tag(item[1]) for item in source_sequence]
    nodes = []
    prior_type = None
    prior_schema = None
    for index, (op, kinds, dependencies) in enumerate(graph):
        semantics = c["operation_semantics_contract"]["operations"][op]
        catalog = next(x for x in c["operation_definition_contract"]["catalog"] if x["id"]==op)
        if index:
            operand_types = [prior_type] * len(kinds)
        elif op == "ENTITY_FIELD_BIND":
            operand_types = [tag(row["domain"]), "STRING", "STRING"]
        elif op == "CALENDAR_DAY_OFFSET":
            operand_types = ["DATE", "INTEGER"]
        elif op == "CLOCK_MINUTE_OFFSET":
            operand_types = ["TIME", "INTEGER"]
        elif op == "ELAPSED_MINUTES":
            operand_types = ["TIME", "TIME"]
        else:
            operand_types = source_types
        if op in {"ADD","SUBTRACT","MULTIPLY","SUM"}:
            result_type = "INTEGER" if all(t=="INTEGER" for t in operand_types) else "NUMBER"
            promotion = "INTEGER_ONLY" if result_type=="INTEGER" else "NUMBER_ONLY" if all(t=="NUMBER" for t in operand_types) else "MIXED_TO_NUMBER"
        else:
            result_type = semantics.get("result_type")
            if op == "EXACT_COPY":result_type = prior_type if index else source_types[0]
            if op == "ENTITY_FIELD_BIND":result_type = tag(row["domain"])
            promotion = {"DIVIDE":"DIVIDE_TO_NUMBER","UNIT_CONVERSION":"UNIT_CONVERSION_TO_NUMBER"}.get(op,"NOT_APPLICABLE")
        if result_type is None:raise ValueError("BLUEPRINT_BLOCKED_BY_DESIGN_AMBIGUITY: unknown result typing")
        schema = {"INTEGER":"integer","NUMBER":"number","BOOLEAN":"boolean","DATE":"YYYY-MM-DD","TIME":"HH:MM","STRING":"string"}.get(result_type)
        if op == "EXACT_COPY":schema = prior_schema if index else source_sequence[0][1]
        if op == "ENTITY_FIELD_BIND":schema = row["domain"]
        argument_names=[name for name in catalog["placeholders"] if name!='target']
        if op=='SUM':argument_names=[f"operands/{i}" for i in range(len(kinds))]
        nodes.append(dict(node_index=index,operation_id=op,operand_reference_kinds=kinds,
                          operand_argument_paths=argument_names, operand_semantic_types=operand_types,
                          upstream_node_indices=dependencies,target_identifier=f"d{ordinal:03d}_{index+1:02d}",
                          result_semantic_type=result_type,result_schema_type=schema,numeric_promotion_class=promotion,
                          typing_and_domain_ref=ref("/operation_semantics_contract/operations/"+op),
                          rendering_ref=ref("/operation_definition_contract/catalog")))
        prior_type,prior_schema=result_type,schema
    if nodes and nodes[-1]['result_schema_type']!=output_roles[0][0]:
        raise ValueError("BLUEPRINT_BLOCKED_BY_DESIGN_AMBIGUITY: planned output schema mismatch")
    return nodes


def canonical_output(binding, schema, ordinal, binding_ordinal, c):
    amendment = c["output_field_amendment_contract"]
    if binding not in amendment["binding_construction"]:
        raise ValueError("BLUEPRINT_UPDATE_BLOCKED_BY_DESIGN_AMBIGUITY: output binding")
    lex = c["lexical_neutrality_contract"]["identifier_generation"]
    generator = lex["derived_target" if binding == "OPERATION_TARGET" else "source_field"]["format"]
    identifier = generator.format(fixture_ordinal=ordinal, source_field_ordinal=binding_ordinal,
                                  topological_node_ordinal=binding_ordinal)
    substitutions = dict.fromkeys(("$generated_source_field_identifier", "$generated_operation_target",
                                   "$generated_explicit_absence_field_identifier"), identifier)
    substitutions.update({"$exact_bound_source_schema":schema, "$exact_producer_result_schema":schema})
    field = {key:substitutions.get(value,value) if isinstance(value,str) else value
             for key,value in amendment["binding_construction"][binding].items()}
    if set(field) != set(amendment["exact_output_field_keys"]) or field["schema_type"] != schema:
        raise ValueError("BLUEPRINT_UPDATE_BLOCKED_BY_DESIGN_AMBIGUITY: output construction")
    return field


def output_metadata(field, role, source_index, producer_index):
    pointer = "/output_field_amendment_contract/binding_construction/" + field["binding_kind"] + "/"
    return dict(name=field["name"], output_role=role, binding_source_field_ordinal=source_index,
                producer_node=producer_index,
                canonical_field_traceability={key:ref(pointer+key) for key in field},
                output_role_ref=ref("/family_assignment_contract/output_role_derivation"))


def position(row, c, helper):
    phase, risk, slot, kind = row["position"].split(":")
    family, index = slot.split("-")
    reserve = kind == "RESERVE"
    context = phase + ":" + risk
    allocation = c["subtype_allocation_contract"]
    subtype = next(x for x in allocation["slot_rows"][family] if x["slot_id"] == slot)
    ordinal = helper.fixture_ordinal(phase, risk, family, int(index), reserve)
    fp = helper.planned_fingerprint(c, context, slot, reserve)
    graph, output_roles, entity_role, boundary, temporal, layout = fp
    ids = [node[0] for node in graph]
    composed = next((key for key, slots in allocation["composed_rows"].items() if slot in slots), "NONE")
    source_sequence = layout[1]
    nodes = typed_node_plan(graph,source_sequence,output_roles,subtype,ordinal,c)
    output_fields = []
    output_field_metadata = []
    if family == "E7":
        for i, (role, schema, _) in enumerate(source_sequence, 1):
            field = canonical_output("EXPLICIT_ABSENCE" if role == "EXPLICIT_ABSENCE" else "SOURCE_COPY",schema,ordinal,i,c)
            output_fields.append(field)
            output_field_metadata.append(output_metadata(field,"absence_sentinel" if role == "EXPLICIT_ABSENCE" else "source_copy",i,None))
    else:
        field = canonical_output("OPERATION_TARGET",nodes[-1]["result_schema_type"],ordinal,len(nodes),c)
        output_fields.append(field)
        output_field_metadata.append(output_metadata(field,output_roles[0][1],None,len(nodes)-1))
    entity = None
    if family == "E5":
        count, role = subtype["coverage_class"].split(":")
        entity = dict(entity_count=int(count.split("_")[1]), selector_role=role,
                      selector_schema="string", source_schema=subtype["domain"],
                      selector_transition=c["e5_counterfactual_selector_contract"]["selector_pair_matrix"][context][int(index)-1],
                      pair_member_order=["CF1", "CF2"], population_contract_ref=ref("/entity_population_contract"),
                      population_shared=True, source_values_pairwise_semantically_distinct=True,
                      request_invariant_ref=ref("/e5_counterfactual_selector_contract/request_contract"),
                      cf1_value_shape_is_anchor=True, cf2_rank_and_enum_position="derive from unchanged population, not anchor rank",
                      enum_anchor_option_index=allocation["enum_answer_positions"][context].get(slot))
    e7 = None
    if family == "E7":
        e7 = dict(supported_schema_order=subtype["domain"], absence_schema="provided|not_provided",
                  absence_source_index=next(i for i, item in enumerate(source_sequence) if item[0]=="EXPLICIT_ABSENCE"),
                  source_presentation="reserve" if reserve else phase,
                  presentation_rule=allocation["e7_source_order"]["reserve" if reserve else phase],
                  support_enum_option_index=allocation["enum_answer_positions"][context].get(slot),
                  supported_boolean_expectation_class=c["value_allocation_contract"]["e7_boolean_source_allocation"][context] if slot=="E7-05" else None)
    comparison = copy.deepcopy(allocation["comparison_slot_matrix"][context][slot]) if family=="E4" else None
    gate = dict(determinate_semantic=family!="E7", determinate_structural=family!="E7",
                useful=family!="E7", family_floor=family!="E7", e7=family=="E7", e5_pair=family=="E5",
                binding_error=family in {"E5","E6"}, malformed_determinate=family!="E7",
                false_clean=True, scored=not reserve)
    return dict(
        logical_base_id=row["position"], phase=phase, risk_round=risk, family=family,
        subtype_slot=slot, primary_or_reserve=kind, fixture_ordinal=ordinal,
        record_type=c["lexical_neutrality_contract"]["record_type_catalog_by_phase"][phase][int(family[1])-1],
        within_family_slot=None if reserve else int(index), reserve_family=family if reserve else None,
        lexical_context=dict(phase=phase, risk_round=risk, family=family, fixture_ordinal=ordinal,
                             within_family_slot=None if reserve else int(index),
                             generator_ref=ref("/lexical_neutrality_contract")),
        subtype=copy.deepcopy(subtype),
        operation_plan=dict(nodes=nodes,
                            node_count=len(graph), terminal_operation=ids[-1] if ids else "NONE",
                            structural_wiring_ref=ref("/template_recurrence_contract/structural_wiring"),
                            conversion_id=allocation["unit_conversion_assignment"][context] if "UNIT_CONVERSION" in ids else None),
        schema_plan=dict(source_fact_role_schema_entity_sequence=source_sequence, output_fields=output_fields,
                         output_field_metadata=output_field_metadata,
                         output_schema_role_sequence=output_roles, exact_field_count=len(output_fields),
                         schema_contract_ref=ref("/schema_type_contract")),
        composed_quota_row=composed,
        secondary_features=features(ids,boundary,family,c["family_assignment_contract"]["allowed_secondary_features"]),
        value_shape_profile=helper.value_shape_profile(c,context,slot),
        comparison_allocation=comparison, entity_plan=entity, e7_presentation=e7,
        recurrence=dict(subtype_template_group=slot, fingerprint_class=row["fingerprint_class"],
                        planned_six_components=fp,
                        maximum_class_recurrence=c["template_recurrence_contract"]["fingerprint_classes"][row["fingerprint_class"]]["maximum_recurrence_count"],
                        scope_table_ref=ref("/template_recurrence_contract/scope_table")),
        gate_membership=gate,
        authoring_constraints=dict(semantics_ref=ref("/operation_semantics_contract"),
                                  slot_validation_ref=ref("/subtype_content_validation_contract"),
                                  literal_canonicality_ref=ref("/operation_definition_contract/placeholder_type_system"),
                                  freshness_ref=ref("/contamination_contract/exact_reuse_contract"),
                                  gold_derivation_ref=ref("/operation_semantics_contract/gold_derivation"),
                                  source_value_slots="UNAUTHORED", gold_answer_slots="UNAUTHORED",
                                  content_and_independent_review_required=True),
        scientific_traceability_groups={
            "logical_base_id":"identity", "phase":"identity", "risk_round":"identity", "family":"identity",
            "subtype_slot":"subtype", "primary_or_reserve":"identity", "fixture_ordinal":"identity",
            "record_type":"lexical_context", "within_family_slot":"identity", "reserve_family":"reserve_map",
            "lexical_context":"lexical_context", "subtype":"subtype", "operation_plan":"operation_plan",
            "schema_plan":"schema_plan", "composed_quota_row":"subtype", "secondary_features":"secondary_features",
            "value_shape_profile":"value_shape_profile", "comparison_allocation":"comparison_allocation",
            "entity_plan":"entity_plan", "e7_presentation":"e7_presentation", "recurrence":"recurrence",
            "gate_membership":"gate_membership", "authoring_constraints":"authoring_constraints",
        },
    )


def schedules(positions, variants, c, replacements=None):
    models = c["model_provider"]["models"]
    result = {"A": [], "B": []}
    replacements = replacements or {}
    lookup = {p["logical_base_id"]: p for p in positions}
    by_base = {}
    for v in variants:
        by_base.setdefault(v["logical_base_id"], []).append(v)
    active = [(p["logical_base_id"], lookup[replacements.get(p["logical_base_id"],p["logical_base_id"])])
              for p in positions if p["primary_or_reserve"] == "PRIMARY"]
    active.sort(key=lambda item:item[1]["fixture_ordinal"])
    round_rank = {(phase,risk):0 for phase in ('A','B') for risk in ('R2','R3')}
    # Round-local rank plus the frozen 35-position offset balances both marginals.
    for qualification_slot, p in active:
        phase, ordinal = p["phase"], p["fixture_ordinal"]
        key=(phase,p['risk_round'])
        start = (round_rank[key] + (0 if p['risk_round']=='R2' else 35)) % len(models)
        round_rank[key] += 1
        ordered = models[start:] + models[:start]
        for m in ordered:
            for repeat in range(1, 3 if phase == "A" else 2):
                seed = c["sampling"]["candidate_phase_"+phase.lower()+"_seed_base"] + (ordinal-1)*10+repeat
                for v in by_base[p["logical_base_id"]]:
                    row = dict(template_schedule_position=len(result[phase])+1,
                               call_id=f"{phase}:{m['tier']}:{p['risk_round']}:{p['logical_base_id']}:{v['variant_id']}:{repeat}",
                               cell_id=f"{m['tier']}:{p['risk_round']}", model=m["model"], tier=m["tier"],
                               qualification_slot_id=qualification_slot,
                               logical_base_id=p["logical_base_id"], rendered_variant_id=v["rendered_variant_id"],
                               variant_id=v["variant_id"], repeat=repeat, seed=seed,
                               request_ref=ref("/e5_counterfactual_selector_contract/request_contract") if p["family"]=="E5" else ref("/baseline_binding"))
                    result[phase].append(row)
    return result


def pair_key(left, right):
    return tuple(sorted((left, right), key=lambda x: x.encode('utf-8')))


def materialize_scaffold(c, positions, variants):
    source = c['declared_scaffold_overlap_contract']
    view = dict(source['view'])
    view['ordinary_payload_definition'] = view.pop('input')
    by_base = {p['logical_base_id']: p for p in positions}
    members = {base: [v['rendered_variant_id'] for v in variants if v['logical_base_id'] == base]
               for base in by_base}
    classes = []
    for index, group in enumerate(source['eligible_groups']):
        pairs = [list(pair_key(*pair)) for pair in group['position_pairs']]
        bases = {base for pair in pairs for base in pair}
        same_subtype = group['subtype_pair'][0] == group['subtype_pair'][1]
        classes.append(dict(
            class_id=group['group_id'], subtype_pair=group['subtype_pair'],
            context_scope=sorted({by_base[b]['phase'] + ':' + by_base[b]['risk_round'] for b in bases}),
            primary_reserve_scope=sorted({by_base[b]['primary_or_reserve'] for b in bases}),
            logical_position_pairs=pairs,
            rendered_position_pairs=[list(pair_key(a, b)) for left, right in pairs
                                     for a in members[left] for b in members[right]],
            invariant_five_grams=group['forced_overlapping_five_grams'],
            old_applicable_branch='NEW_DECLARED_SAME_SUBTYPE' if same_subtype else 'NEW_DECLARED_DIFFERENT_SUBTYPE',
            old_minimum_ordinary_jaccard=group['ordinary_minimum'],
            old_minimum_content_jaccard=group['content_minimum'],
            residual_rule='RA=A\\I; RB=B\\I; sets of ordinary normalized five-gram tuples; no rewriting or new adjacency',
            residual_threshold_exclusive='3/25', residual_comparator='<',
            residual_integer_test='25*intersection < 3*union',
            empty_residual_behavior='AUTHORING_ERROR_EMPTY_RESIDUAL',
            design_traceability=ref('/declared_scaffold_overlap_contract/eligible_groups/' + str(index)),
        ))
    scaffold_pairs = {tuple(pair) for group in classes for pair in group['rendered_position_pairs']}
    branch_counts = {'DECLARED_SCAFFOLD': 0, 'DECLARED_SAME_SUBTYPE': 0, 'ORDINARY_NEW_NEW': 0}
    for left, right in itertools.combinations(variants, 2):
        a, b = left['logical_base_id'], right['logical_base_id']
        if a == b: continue
        if pair_key(left['rendered_variant_id'], right['rendered_variant_id']) in scaffold_pairs:
            branch = 'DECLARED_SCAFFOLD'
        elif by_base[a]['subtype_slot'] == by_base[b]['subtype_slot']:
            branch = 'DECLARED_SAME_SUBTYPE'
        else:
            branch = 'ORDINARY_NEW_NEW'
        branch_counts[branch] += 1
    return dict(
        contract_id=source['contract_id'], repair_commit=CONTAMINATION_REPAIR,
        classes=classes,
        cross_base_branch_counts=branch_counts,
        reconciliation=dict(subtype_pair_summaries=12, exact_classes=14,
                            e1_split='E1-05 R2 zero and R3 366 separately',
                            e7_split='E7-02/E7-04 A and B presentation separately', e5_classes=10),
        logical_pair_count=234, rendered_pair_count=906, same_base_e5_excluded=True,
        eligibility=source['eligibility'], freshness_required=source['freshness_required'],
        view=view, historical_unchanged=source['historical'],
        prerequisites_ref=ref('/declared_scaffold_overlap_contract/eligibility'),
        freshness_ref=ref('/declared_scaffold_overlap_contract/freshness_required'),
        residual_ref=ref('/declared_scaffold_overlap_contract/view'),
        decision_precedence=[
            dict(branch='HISTORICAL_NEW', predicate='historical/new domain; existing projection/ordinary rules only'),
            dict(branch='AUTHORING_ERROR_STRUCTURE', predicate='either actual position/subtype/profile/lexical/schema/operation/value/output/fingerprint invalid'),
            dict(branch='SAME_BASE_E5_PAIR_LOCAL', predicate='same base and validated complete CF1/CF2 request/gold pair; unchanged intentional sharing'),
            dict(branch='REJECT_FRESHNESS', predicate='cross-base and any existing freshness or exact-reuse failure'),
            dict(branch='DECLARED_SCAFFOLD', predicate='cross-base exact unordered rendered membership in exactly one listed class'),
            dict(branch='DECLARED_SAME_SUBTYPE', predicate='remaining cross-base exact ledger positions with equal subtype_slot'),
            dict(branch='ORDINARY_NEW_NEW', predicate='remaining validated cross-base pairs'),
        ],
        precedence_equivalence='Pair-local E5 sharing is checked before cross-base freshness; intentional same-base sharing is not rejected by cross-base reuse rules. All scaffold pairs require full freshness first.',
        eligibility_requires_actual_content=True,
        feasibility_limit='Frozen pairwise scaffold feasibility is not proof of simultaneous concrete corpus feasibility or acceptance.',
    )


def reconstructed_membership(positions):
    """Reconstruct frozen scopes from allocations, not the class pair arrays."""
    scopes = {}
    for left, right in itertools.combinations(positions, 2):
        a, b = sorted((left['subtype_slot'], right['subtype_slot']))
        key = None
        if a.startswith('E5-') and b.startswith('E5-') and a != b:
            key = (a, b, 'ALL')
        elif a == b == 'E1-05' and left['primary_or_reserve'] == right['primary_or_reserve'] == 'PRIMARY':
            if left['phase'] != right['phase'] and left['risk_round'] == right['risk_round']:
                key = (a, b, left['risk_round'])
        elif (a, b) == ('E7-02', 'E7-04') and left['phase'] == right['phase']:
            key = (a, b, left['phase'])
        if key is not None:
            scopes.setdefault(key, set()).add(pair_key(left['logical_base_id'], right['logical_base_id']))
    return scopes


def validate_scaffold(bp, c):
    actual = bp['comparison_scope']['scaffold_overlap']
    source = c['declared_scaffold_overlap_contract']
    checks = []
    def require(ok, label):
        if not ok: raise ValueError(label)
        checks.append(label)
    ps, vs = bp['logical_positions'], bp['rendered_variants']
    by_base = {p['logical_base_id']: p for p in ps}
    scopes = reconstructed_membership(ps)
    require(len(scopes) == 14, 'scaffold_independent_scope_reconstruction_14')
    require(actual == materialize_scaffold(c, ps, vs), 'scaffold_exact_accepted_contract_materialization')
    groups = actual['classes']
    require([g['class_id'] for g in groups] == [g['group_id'] for g in source['eligible_groups']], 'scaffold_exact_14_class_ids')
    logical, rendered, scoped = {}, {}, set()
    for group in groups:
        a, b = group['subtype_pair']
        discriminator = 'ALL' if a.startswith('E5-') else group['context_scope'][0].split(':')[1] if a == b else group['context_scope'][0][0]
        key = (a, b, discriminator)
        require(key not in scoped, 'scaffold_unique_scope:' + group['class_id'])
        scoped.add(key)
        pairs = group['logical_position_pairs']
        require(len(pairs) == len({pair_key(*p) for p in pairs}), 'scaffold_no_duplicate_logical:' + group['class_id'])
        require({pair_key(*p) for p in pairs} == scopes[key], 'scaffold_reconstructed_membership:' + group['class_id'])
        for pair in pairs:
            pair = pair_key(*pair)
            require(pair[0] != pair[1] and pair not in logical, 'scaffold_unique_cross_base_logical:' + str(pair))
            logical[pair] = group['class_id']
        members = set()
        for left, right in itertools.combinations(vs, 2):
            if left['logical_base_id'] != right['logical_base_id'] and pair_key(left['logical_base_id'], right['logical_base_id']) in scopes[key]:
                members.add(pair_key(left['rendered_variant_id'], right['rendered_variant_id']))
        require(len(group['rendered_position_pairs']) == len(members) and set(map(tuple, group['rendered_position_pairs'])) == members, 'scaffold_independent_rendered_expansion:' + group['class_id'])
        for pair in sorted(members):
            require(pair not in rendered, 'scaffold_unique_rendered:' + str(pair))
            rendered[pair] = group['class_id']
    require(len(logical) == 234 and len(rendered) == 906, 'scaffold_234_logical_906_rendered')
    counts = {'DECLARED_SCAFFOLD': 0, 'DECLARED_SAME_SUBTYPE': 0, 'ORDINARY_NEW_NEW': 0}
    pair_local = []
    partition = []
    for left, right in itertools.combinations(vs, 2):
        lbase, rbase = left['logical_base_id'], right['logical_base_id']
        pair = pair_key(left['rendered_variant_id'], right['rendered_variant_id'])
        if lbase == rbase:
            require(pair not in rendered and by_base[lbase]['family'] == 'E5', 'pair_local_not_scaffold:' + lbase)
            pair_local.append(list(pair))
            continue
        scaffold = pair in rendered
        same = not scaffold and by_base[lbase]['subtype_slot'] == by_base[rbase]['subtype_slot']
        ordinary = not scaffold and not same
        require(sum((scaffold, same, ordinary)) == 1, 'cross_base_unique_branch:' + str(pair))
        branch = 'DECLARED_SCAFFOLD' if scaffold else 'DECLARED_SAME_SUBTYPE' if same else 'ORDINARY_NEW_NEW'
        counts[branch] += 1
        partition.append(dict(pair=list(pair), branch=branch, class_id=rendered.get(pair)))
    require(sum(counts.values()) == 18312 and len(pair_local) == 24, 'scaffold_full_domain_partition')
    require(actual['cross_base_branch_counts'] == counts, 'scaffold_blueprint_branch_counts_match_independent_partition')
    return checks, dict(class_ids=[g['class_id'] for g in groups], logical_memberships=len(logical),
                        rendered_memberships=len(rendered), branch_counts=counts, pair_local_scopes=pair_local,
                        partition=partition, partition_sha256=digest(encoded(partition)),
                        duplicate_logical_pairs=0, duplicate_rendered_pairs=0, extra_pairs=0,
                        same_base_pairs_in_scaffold=0, actual_content_validated=False)


def checking_residual(group, a, b):
    """Design replay on synthetic gram sets, never a production corpus scorer."""
    invariant = {tuple(g.split(' ')) for g in group['invariant_five_grams']}
    ra, rb = a - invariant, b - invariant
    if not ra or not rb: return 'AUTHORING_ERROR_EMPTY_RESIDUAL'
    return 'PERMITTED_DECLARED_SCAFFOLD' if 25 * len(ra & rb) < 3 * len(ra | rb) else 'REJECT_CONTAMINATION'


def materialize_freshness(c, positions):
    source = c['freshness_canonicalization_contract']
    row_plans = []
    schemas = set()
    for position in positions:
        sequence = position['schema_plan']['source_fact_role_schema_entity_sequence']
        schemas.update(row[1] for row in sequence)
        row_plans.append(dict(logical_base_id=position['logical_base_id'],
                             source_record_indices=[i for i, row in enumerate(sequence) if row[0] != 'EXPLICIT_ABSENCE'],
                             exact_schema_type_sequence=[row[1] for row in sequence if row[0] != 'EXPLICIT_ABSENCE']))
    return dict(amendment_commit=FRESHNESS_AMENDMENT,
                contract_ref=ref('/freshness_canonicalization_contract'),
                existing_freshness_ref=ref('/template_recurrence_contract/freshness_sequence'),
                materialized_contract=copy.deepcopy(source),
                active_source_schema_types=sorted(schemas, key=lambda x: x.encode('utf-8')),
                source_row_plans=row_plans,
                row_plans_are_metadata_not_serialized_freshness_atoms=True,
                historical_side_uses_new_freshness=False,
                other_representations_unchanged=True,
                same_base_e5_exception_unchanged=True,
                scope='NEW VALUE sequence encoding only; existing comparison applicability remains unchanged; no candidate corpus evaluation')


def materialize_whole_answer(c, positions, helper):
    """Schema/field plans only; no candidate answers or corpus comparisons."""
    plans, schemas, tags = [], set(), set()
    for position in positions:
        rows = []
        for field in sorted(position['schema_plan']['output_fields'], key=lambda f: f['name'].encode('utf-8')):
            schema = field['schema_type']
            tag = helper.parse_schema_type(schema, c['schema_type_contract'])['semantic_tag']
            rows.append(dict(field_name=field['name'], historical_schema_type=schema, semantic_tag=tag,
                             canonical_semantic_text='UNAUTHORED'))
            schemas.add(schema)
            tags.add(tag)
        plans.append(dict(logical_base_id=position['logical_base_id'], sorted_output_row_plans=rows,
                          rendered_members_inherit_field_schema_tag_plan=True,
                          answer_values_derived_later_per_variant=True))
    reuse = c['contamination_contract']['exact_reuse_contract']
    return dict(amendment_commit=ACCEPTED, contract_ref=ref('/whole_answer_canonicalization_contract'),
                materialized_contract=copy.deepcopy(c['whole_answer_canonicalization_contract']),
                existing_whole_answer_rule=copy.deepcopy(reuse['whole_answer']),
                existing_scope_names=copy.deepcopy(reuse['scope_names']),
                all_rules_apply_to_every_scope=reuse['all_rules_apply_to_every_scope'],
                active_output_schema_types=sorted(schemas, key=lambda x: x.encode('utf-8')),
                active_semantic_tags=sorted(tags), output_row_plans=plans,
                row_plans_are_metadata_not_serialized_answers=True,
                historical_and_new_use_same_encoding_in_existing_scope=True,
                historical_artifacts_unchanged=True, freshness_plan_unchanged=True,
                other_exact_reuse_and_similarity_rules_unchanged=True,
                scope='Accepted whole-answer encoding only; isolated vectors and value-free row plans, not corpus evaluation or checker repair')


def build(c, helper, hashes):
    ledger = helper.template_ledger(c)
    if ledger["positions"] != c["template_recurrence_contract"]["positions"] or ledger["classes"] != c["template_recurrence_contract"]["fingerprint_classes"]:
        raise ValueError("BLUEPRINT_BLOCKED_BY_DESIGN_AMBIGUITY: recurrence derivation mismatch")
    positions = sorted((position(x,c,helper) for x in ledger["positions"]),key=lambda x:x["fixture_ordinal"])
    variants=[]
    for p in positions:
        members=["CF1","CF2"] if p["family"]=="E5" else ["SINGLE"]
        for i, member in enumerate(members):
            variants.append(dict(rendered_variant_id=p["logical_base_id"]+":"+member,
                                 logical_base_id=p["logical_base_id"], variant_id=member,
                                 selector_index=p["entity_plan"]["selector_transition"][i] if p["entity_plan"] else None,
                                 pair_partner=p["logical_base_id"]+":"+members[1-i] if len(members)==2 else None,
                                 pair_local_exception_eligible=len(members)==2,
                                 applicable_check_catalog="comparison_scope/check_catalog",
                                 seed_relation="same model/base/repeat seed for CF1 and CF2" if len(members)==2 else "one observation per model/repeat",
                                 request_diff_requirement_ref=ref("/e5_counterfactual_selector_contract/request_contract") if len(members)==2 else None,
                                 scientific_metadata_source=p["logical_base_id"],
                                 contamination_rule_ref=ref("/e5_counterfactual_selector_contract/contamination") if len(members)==2 else ref("/contamination_contract")))
    reserve_map=[]
    for p in positions:
        if p["primary_or_reserve"] != "RESERVE":continue
        covered=p["logical_base_id"].replace(":RESERVE",":PRIMARY")
        profile=c["reserve_equivalence_contract"]
        nodes=p['operation_plan']['nodes']
        outputs=sorted(p['schema_plan']['output_schema_role_sequence'],key=lambda item:json.dumps(item,separators=(',',':')).encode())
        comparison=p['comparison_allocation']
        temporal=next((n['operation_id'] for n in nodes if n['operation_id'] in {'CALENDAR_DAY_OFFSET','CLOCK_MINUTE_OFFSET','ELAPSED_MINUTES'}),'NONE')
        preview={
            'primary_family':p['family'],'composed_quota_row':p['composed_quota_row'],
            'secondary_features':p['secondary_features'],'operation_ids':[n['operation_id'] for n in nodes],
            'conversion_ids':[p['operation_plan']['conversion_id'] if n['operation_id']=='UNIT_CONVERSION' else 'NONE' for n in nodes],
            'source_schema_sequence':sorted((x[1] for x in p['schema_plan']['source_fact_role_schema_entity_sequence']),key=lambda x:x.encode()),
            'output_schema_sequence':[x[0] for x in outputs],
            'operation_result_semantic_types':[n['result_semantic_type'] for n in nodes],
            'numeric_promotion_classes':[n['numeric_promotion_class'] for n in nodes],
            'comparison_operator':comparison['operator'] if comparison else 'NONE',
            'comparison_operand_type_pair':comparison['operand_type_pair'] if comparison else [],
            'boundary_relation':p['recurrence']['planned_six_components'][3],
            'temporal_operation':temporal,'temporal_boundary_pattern':p['recurrence']['planned_six_components'][4],
            'explicit_absence':p['family']=='E7','entity_count':p['entity_plan']['entity_count'] if p['entity_plan'] else 0,
            'entity_selector_role':p['entity_plan']['selector_role'] if p['entity_plan'] else 'NONE',
            'output_role_sequence':[x[1] for x in outputs],'consequence_risk':p['risk_round'],
            'field_count':p['schema_plan']['exact_field_count'],'operation_node_count':len(nodes),
            'subtype_slot':p['subtype_slot'],'operation_operand_semantic_types':[n['operand_semantic_types'] for n in nodes],
            'value_shape_profile':p['value_shape_profile'],
        }
        fields=[]
        for name in profile["profile_exact_keys_in_order"]:
            fields.append(dict(name=name, derivation_ref=ref("/value_allocation_contract") if name=="value_shape_profile" else ref("/reserve_equivalence_contract/derivation/"+name),
                               blueprint_preview=preview.get(name),
                               planned_origin="derived from logical blueprint" if name in preview else "derived later from authored fixture",
                               final_origin="always rederive from authored fixture semantics after actual slot validation",
                               exact_match_required=True))
        reserve_map.append(dict(reserve_slot_id=f"RESERVE:{p['phase']}:{p['risk_round']}:{p['family']}",
                                reserve_base_id=p["logical_base_id"], covered_primary_base_id=covered,
                                ordered_primary_ids=[covered.replace("-01:PRIMARY",f"-{i:02d}:PRIMARY") for i in range(1,6)],
                                covered_subtype_slot="01", replacement_unit="CF1_CF2_WHOLE_PAIR" if p["family"]=="E5" else "SINGLE_LOGICAL_BASE",
                                activation_contract_ref=ref("/reserve_activation_contract"),
                                profile_fields=fields, profile_serialization=profile["serialization"],
                                pair_profile_ref=ref("/e5_counterfactual_selector_contract/reserves") if p["family"]=="E5" else None,
                                maximum_consumptions=1, post_contact_activation=False,
                                no_defects="NO_ACTIVATION", one_covered_matching_defect="ACTIVATE_SINGLE_RESERVE",
                                uncovered_or_multiple_or_mismatched="STOP_AUTHORING"))
    schedule=schedules(positions,variants,c)
    all_cells=[m["tier"]+":"+r for m in c["model_provider"]["models"] for r in ("R2","R3")]
    return dict(
        schema_version="g-extract1.blueprint.v1", status="READY_FOR_G_EXTRACT1_BLUEPRINT_WHOLE_ANSWER_REREVIEW",
        accepted_design=dict(commit=ACCEPTED, artifacts_sha256=hashes,
                             scientific_basis_commit=SCIENTIFIC_BASIS,
                             output_field_amendment_commit=OUTPUT_AMENDMENT,
                             contamination_feasibility_repair_commit=CONTAMINATION_REPAIR,
                             freshness_canonicalization_amendment_commit=FRESHNESS_AMENDMENT,
                             whole_answer_canonicalization_amendment_commit=ACCEPTED,
                             prior_blueprint_commit=WHOLE_PRIOR_BLUEPRINT,
                             original_blueprint_commit=ORIGINAL_BLUEPRINT,
                             design_side_digest_rebinding_required=False,
                             design_checker_inventory_scope="accepted whole-answer design preserves prior blueprint 3bf939 as historical checkpoint; standalone design inventory guard is not invoked on rebound blueprint bytes"),
        authority=dict(blueprint_authoring=True, corpus_gold_authoring=False, implementation=False,
                       mechanical_pilot=False, execution_freeze=False, phase_a_execution=False, phase_b_execution=False),
        terminology=dict(logical_base="one scored/reserve position, regardless of pair expansion",
                         rendered_variant="SINGLE or CF1/CF2 member of a logical base",
                         provider_observation="one model/variant/repeat request-response", repeat="one planned repeated observation per variant",
                         pair="exactly CF1 and CF2 of an E5 logical base", cell="model tier x risk round, assessed independently in each phase"),
        logical_positions=positions, rendered_variants=variants, reserve_map=reserve_map,
        freshness_serialization_plan=materialize_freshness(c, positions),
        whole_answer_serialization_plan=materialize_whole_answer(c, positions, helper),
        recurrence_ledger=dict(positions=ledger["positions"], fingerprint_classes=ledger["classes"],
                               subtype_template_groups=c["template_recurrence_contract"]["subtype_template_groups"],
                               permitted_scope_table=c["template_recurrence_contract"]["scope_table"],
                               base_count_unit="logical bases; pair expansion is not independent recurrence"),
        comparison_scope=dict(new_new_order="rendered_variants array order; all unordered i<j pairs",
                              check_catalog=[
                                  dict(check="ordinary_ordinal_neutral_jaccard",rule_ref=ref("/ordinal_neutral_similarity_contract"),when="normal new/new and historical/new decision-table scope"),
                                  dict(check="content_view",rule_ref=ref("/ordinal_neutral_similarity_contract/declared_template_content_view"),when="declared subtype recurrence; exact empty-content behavior from accepted decision table"),
                                  dict(check="shape_view",rule_ref=ref("/ordinal_neutral_similarity_contract/shape_view"),when="accepted comparison decision-table scope"),
                                  dict(check="new_new_fingerprint",rule_ref=ref("/template_recurrence_contract"),when="every new/new comparison except audited pair-local sharing"),
                                  dict(check="historical_three_component_projection",rule_ref=ref("/historical_fingerprint_adapter_contract"),when="every historical/new comparison, including each E5 member"),
                                  dict(check="whole_answer_reuse",rule_ref=ref("/contamination_contract/exact_reuse_contract/whole_answer"),when="all cross-base exact-reuse scopes"),
                                  dict(check="identity_reuse",rule_ref=ref("/contamination_contract/exact_reuse_contract/identity_atom_derivation"),when="all cross-base exact-reuse scopes"),
                                  dict(check="date_number_tuple_reuse",rule_ref=ref("/contamination_contract/exact_reuse_contract/date_number_tuple"),when="all cross-base exact-reuse scopes; accepted tuple applicability rules"),
                              ],
                              pair_local_exception="only validated CF1/CF2 with same E5 logical_base_id",
                              cross_base="all four CF1/CF2 combinations where applicable, no base collapse",
                              historical_order="adapter artifact order, extraction entries in artifact array order; each versus every rendered variant",
                              historical_adapter_ref=ref("/historical_fingerprint_adapter_contract"),
                              pair_exception_ref=ref("/e5_counterfactual_selector_contract/contamination"),
                              ordinary_ordinal_neutral_ref=ref("/ordinal_neutral_similarity_contract"),
                              declared_recurrence_content_and_shape_ref=ref("/ordinal_neutral_similarity_contract/decision_table"),
                              exact_reuse_ref=ref("/contamination_contract/exact_reuse_contract"),
                              new_new_fingerprint_ref=ref("/template_recurrence_contract"),
                              scaffold_overlap=materialize_scaffold(c, positions, variants),
                              comparisons_require_future_content=True),
        schedule_plan=dict(model_order_algorithm="active logical ordinal ascending within phase; cyclic model list rotation by (zero-based active within-round rank + round_offset) modulo3, offsets R2=0/R3=35; within model repeats ascending, then CF1/CF2 or SINGLE",
                           model_order_is_operational_allocation_not_new_science=True,
                           phase_a=schedule["A"], phase_b_maximum_template=schedule["B"],
                           phase_b_cell_order=all_cells,
                           phase_b_instantiation="validate sorted unique A-qualified cell set against phase_b_cell_order; stable-filter maximum template by cell_id; renumber schedule_position from1; retain template_schedule_position/call_id/seed; no execution here",
                           reserve_activation="replace the covered primary's active physical base with its mapped reserve; retain qualification_slot_id for gate accounting; sort active bases by actual ordinal and regenerate model rotation/call IDs/seeds/positions; validate all balances/collisions and refreeze before contact",
                           schedule_authorization=False),
        request_template=dict(baseline_ref=ref("/baseline_binding"), provider_ref=ref("/model_provider"),
                              complete_request_ref=ref("/e5_counterfactual_selector_contract/request_contract"),
                              body_keys=c["e5_counterfactual_selector_contract"]["request_contract"]["body_keys"],
                              serialization=c["e5_counterfactual_selector_contract"]["request_contract"]["serializer"],
                              before_contact_audit_fields=c["e5_counterfactual_selector_contract"]["request_contract"]["report_fields"],
                              final_request_bytes="UNAUTHORED", source_values="UNAUTHORED", answer_values="UNAUTHORED",
                              no_extra_model_facing_blueprint_metadata=True),
        cell_gate_specs=c["cell_gates"],
        scientific_traceability=traceability(),
        implementation_checklist=[
            "Separate independent blueprint review; do not infer corpus authority from this status.",
            "Separate corpus/gold authorization before selecting any concrete source/operand/gold values.",
            "Derive actual typed semantics, check slot/value/lexical allocation, then compute reserve profile; no declaration-only copying.",
            "Independent gold review/adjudication and independent contamination implementations; all scopes including both E5 variants.",
            "Freeze A/B/reserves/gold/gates/prompt/scorer/schedule/transport identities only after separate freeze authorization.",
            "Separate implementation, mechanical pilot, Phase A and conditional Phase B authorization; no provider work here.",
        ],
        governance=dict(provider_model_calls=0, scored_content_authored=0, reserve_content_authored=0,
                        gold_answers_authored=0, runtime_implementation_begun=False, experiment_executed=False,
                        g_route4="CLOSED FAILED unchanged", belief_effects="none", autonomy=False,
                        source_governance_ref=ref("/governance")),
    )


def markdown(bp):
    return """# G-EXTRACT1 Authoring Blueprint

Status: READY_FOR_G_EXTRACT1_BLUEPRINT_WHOLE_ANSWER_REREVIEW. Mechanical rebind only.

## Authority And Scope

Scientific basis: V10 commit `394d24121309ec9dce80e725b50dbe5eb60f6d2a`, plus the
accepted output-field amendment `aef3e0900cba41481904c8a451c4ca28b9d46c53`, and
accepted contamination repair `62c783bd8be708a86c82a9e00c80b0fa6fb5b459`, and
accepted freshness amendment `e12484224cd11cf9c84026eb7deadf8c4eb9bab8`, and
accepted whole-answer amendment `d1b9e2aa5dbe0aeebb74f8226ca8033182f7b3c1`.
The six design artifacts are byte-bound to the whole-answer amendment in BLUEPRINT.json
and remain unchanged. Prior accepted blueprint `3bf939ea3160596d89c64f1feef790477991cf8a`
is lineage only: its allocations are preserved exactly. Original lineage is
`99707b4f13abd6533f1d09313bdb066793996be9`.
BLUEPRINT.json is the complete value-free enumeration; its scientific_traceability
maps every scientific dimension to the accepted JSON contract. The machine artifact
is authoritative for enumerated IDs, schemas, allocations and schedule positions;
this document describes it without adding semantic rules.

No source values, source prose, operand literals, entity source values, answer
objects, final prompts or request bytes are authored. Frozen design expectation
classes (E4 Boolean, enum position and E7 Boolean allocation) are copied constraints,
not newly authored gold answers. Ranges, schema tokens, selector indices and
identifier templates are blueprint metadata, not scored content.

## Canonical Output Fields

Every planned output materializes exactly eight keys: `name`, `schema_type`,
`required`, `binding_kind`, `source_field`, `producer_target`, `label_removal`,
`absence_capable`. Globally required=true and label_removal=false, including all
families, schemas, roles, scored/reserve bases and E5 CF1/CF2 members. No optional
output or label-stripping tolerance exists in G-EXTRACT1. The general historical
comparator capability remains unchanged; this experiment does not exercise it.

SOURCE_COPY: name/source_field equal the generated ordinary non-entity VALUE
fact identifier, exact source schema, producer_target=null, absence_capable=false.
OPERATION_TARGET: name/producer_target equal the generated operation target,
exact producer result schema, source_field=null, absence_capable=false.
EXPLICIT_ABSENCE: name/source_field equal the generated absence fact identifier,
schema provided|not_provided, producer_target=null, absence_capable=true. No gold
is authored here; the existing E7 gold derivation remains for future corpus work.

Output roles stay in separate output_field_metadata, never a ninth canonical key.
Each of the eight fields traces to the accepted amendment's binding construction;
lexical/schema/role derivations retain the existing V10 contracts. Rendered rows
inherit the canonical output array from their scientific_metadata_source base.
Thus CF1/CF2 output objects are identical, even though their future gold differs.

There are 220 logical output definitions: 144 non-E7 one-output bases plus 76 E7
outputs. E7 primaries have 4 contexts x (3+3+3+3+4)=64 outputs; four subtype01
reserves add 12. The 24 E5 CF2 members add 24 output instances: 244 rendered output
instances total, 204 scored and 40 reserve. This is not a new fixture/observation
denominator, and it changes no previous architecture/call/gate count.

## Enumeration

140 scored logical bases plus 28 subtype-01-only logical reserves = 168 bases.
20 scored and 4 reserve E5 bases are pairs: exactly CF1 then CF2. Others are SINGLE.
160 scored plus 32 reserve rendered variants = 192 objects. Ordinals are 1..168,
following the frozen A primaries/A reserves/B primaries/B reserves formulas.
Each position carries subtype, lexical generator, typed graph/operand-reference
shape, schema/output binding plan, value-shape constraints, composed/secondary
features, E4 allocation, E5 population/selector transition, E7 presentation,
recurrence membership, gate membership and authoring-contract references.

Per phase/round: 35 logical bases, 30 determinate plus 5 E7, 40 rendered variants.
Each model/round cell has 80 observations in A, 40 in B. E5 contributes 5 logical
pairs, 20 A observations or 10 B observations, requiring 5/5 semantic pair success.
General denominators remain 30 determinate logical bases, never rendered variants.
E7 remains 10/10 observations in A and 5/5 in B. Positive E5 reductions require all
four A or both B observations; adverse reductions use any observation. All other
gates are referenced/copied exactly from V10; no threshold is changed.

## Schedules

Phase A skeleton: 480 calls, 160 per model. B maximum template: 240 calls, 80 per
model. Maximum total: 720. Schedules are source-only metadata, not run journals.
Bases ascend by ordinal. For each base, rotate the frozen model list cyclically
by (zero-based active within-round ordinal rank + round offset) modulo3, with
offsets R2=0 and R3=35, to instantiate balanced model ordering. Within each model,
repeats ascend, and E5 members are CF1 then CF2. This is an operational allocation
under the design's balanced-order obligation, not a new scientific rule.
Each model occupies each list position 23 or 24 times among a phase's 70 bases,
and 11 or 12 times among a round's 35 bases, including reserve substitutions.
B is a stable filtered template for the sorted unique A-qualified model/round
cell set; all 64 subsets are mechanically checked. This does not create a result
or authorize B. Existing template position, call identity and seed are retained;
active schedule positions are renumbered after filtering.
Seeds use phase_base+(logical_ordinal-1)*10+repeat. Only CF1/CF2 of one model/base/
repeat intentionally collide. Reserve activation replaces the whole covered unit,
retains the primary qualification slot for denominator accounting, sorts the
active bases by actual ordinal and regenerates model rotation, seeds, call IDs
and positions. It requires balance/collision/schedule revalidation and refreeze
pre-contact. It is never a
post-output retry or optional model call.

## Contamination And Reserves

The logical recurrence ledger has 51 fingerprint classes, 35 subtype groups and
14,028 unordered base comparisons. The rendered comparison iterator has 18,336
pairs: exactly 24 eligible same-base E5 sharing scopes and 18,312 cross-base pairs.
Historical scope: 106 historical extraction entries times 192 variants = 20,352.
The comparison iterators and source rule references are frozen, but content
acceptance remains outstanding. The existing untracked 168-base candidate corpus
is preserved incomplete input, not blueprint content or an accepted corpus. Ordinary ordinal-neutral,
declared-template content/shape, fingerprints, projection and exact-reuse checks
apply through the accepted comparison decision table, not a blanket similarity
threshold. Pair masks never alter contamination inputs. Sharing exemptions
require future byte/gold-validity audit and never extend across bases.
All 28 reserve mappings cover subtype01 only. Uncovered, multiple or mismatched
defects stop authoring. E5 replacement unit is the entire CF1/CF2 pair.
Profile fields retain the exact accepted key order and derivation references.
Final profiles must derive from actual validated content, not merely blueprint
declarations. This blueprint carries no concrete value-dependent dimensions;
existing candidate content is not evaluated or finalized in this rebind.

## Request And Gold Boundary

The request template references the exact bound historical system/suffix/provider
configuration and V10 complete-body serializer. Final selector spans, old/new
selector bytes, both request hashes and masked hash are required for every model/
repeat before contact, but cannot be filled before corpus authoring. CF1 retains
anchor checks; CF2 changes only requested selector and mechanically derived gold,
not the population or anchor allocation. No actual requests are rendered here.
Gold derivation is referenced to the frozen typed operation evaluator contract.
No expected answer is selected or computed from authored source values.

## Validation And Governance

Run `python -B experiments/G-EXTRACT1-candidate/blueprint/validate_blueprint.py`.
`--write` deterministically regenerates blueprint documents/report only. Default
mode validates existing bytes without writes. Checks independently count IDs,
ordinals, variants, gates, schedules, seeds, reserve mappings, comparison scopes,
all qualified-cell subsets and traceability; mutation probes reject mismatches.
The report claims structural/design equivalence only, not scientific validity,
future content feasibility, transport correctness or execution readiness.
The accepted whole-answer design checker pins the prior accepted blueprint as historical
checkpoint evidence. That guard is not rebound: no mutable design-side digest of
this later blueprint is required. All six design artifacts remain exact
accepted bytes. This checker loads only their value-free derivation helpers; it
does not invoke the old checkpoint inventory guard on updated blueprint files.
Instead it checks all repair/amendment bindings, exact scaffold membership, canonical outputs,
freshness and whole-answer serialization obligations and preserved candidate/gold/checker digests,
and exact preservation of both prior and original allocations. No design-side changes
or circular design/blueprint digest binding are introduced.

G-ROUTE4 remains CLOSED FAILED. Provider/model calls, scored/reserve content and
gold answers authored in this blueprint task are zero; the existing untracked
candidate corpus and both corpus checkers remain byte-identical. Belief effects
none; no autonomy or runtime work.
Separate authorization remains required for corpus/gold authoring, implementation,
mechanical pilot, execution freeze, Phase A and conditional Phase B. Blueprint
review must occur first; corpus authoring cannot resume before rebind rereview.
Checker repair and corpus finalization also remain separately unauthorized.
This status does not self-authorize any later stage.
""" + scaffold_markdown(bp) + freshness_markdown(bp) + whole_answer_markdown(bp)


def whole_answer_markdown(bp):
    plan = bp['whole_answer_serialization_plan']
    fence = chr(96) * 3
    return '''
## Accepted Whole-Answer Serialization Rebind

This instantiates g-extract1.whole-answer-canonicalization.v1, not a checker
repair or a corpus acceptance. Each completed row is
[field_name,historical_schema_type,[semantic_tag,canonical_semantic_text]].
All four leaves are JSON strings. Field names and exact historical schema bytes
(including full enum option order) are preserved. Tags derive only from the
unchanged schema contract: STRING, NUMBER, INTEGER, BOOLEAN, DATE, TIME, ENUM.
Rows sort by ascending unsigned UTF-8 field-name bytes; duplicate names reject
as AUTHORING_ERROR before serialization. No field-wise, subset or name-insensitive
matching is introduced: the match is whole canonical answer bytes equal.

INTEGER is minimal signed base-10 text, no plus/leading zeros/decimal/exponent;
signed zero becomes "0". NUMBER uses exact terminating plain decimal, no plus,
exponent, unnecessary zeros or empty decimal point; all signed zero becomes "0".
5/5.0/5.00/5e0 all become "5". No binary float or finite-context rounding.
Equivalent exact int/Decimal/Fraction/validated-token values agree where schema
permits. Unsupported wrappers fail closed. INTEGER and NUMBER remain typed-distinct.
BOOLEAN becomes lowercase "true"/"false". DATE/TIME retain validated padded
Gregorian YYYY-MM-DD / 24-hour HH:MM. STRING preserves exact semantic text without
trim/casefold/label removal/whitespace/Unicode/tokenizer normalization. ENUM is
the exact selected option, not an ordinal. Explicit absence is exactly
[field_name,"provided|not_provided",["ENUM","not_provided"]], never null.

Outer serialization is Python json.dumps with ensure_ascii=True,
separators=(',', ':'), UTF-8 encoding and no terminal newline. Freshness remains
separate: [exact_schema_type,canonical_semantic_text], ensure_ascii=False.
The original isolated regression bytes are
[["d016_02","boolean",["BOOLEAN","true"]]]. This is an accepted contract vector,
not corpus-derived authority. All 39 semantic vectors, three equivalence groups,
sorting/host-type/non-ASCII tests and 28 accepted byte-mutation categories are
replayed; prior blueprint/freshness/output mutations remain required.

Validated historical and NEW answers use the same completed encoding only in
the existing whole-answer comparison scope. Historical files are never edited.
Whole-answer is exact full-object replay only; fixture-specific names limit
sensitivity. Freshness, identity/tuple/raw-payload controls, fingerprints,
ordinary/shape/content Jaccard, scaffold residuals, recurrence, gates, schedules
and seeds are unchanged. No contamination campaign runs here.

The 168 row plans specify exact fields/schemas/derived tags, not answer values;
future variants inherit the plan but derive their own semantic answer. Separate
independent blueprint rereview must precede separately authorized checker repair
and finalization. No later authority is granted.

The following co-normative annex copies the complete accepted encoding contract
and exact value-free output plans from BLUEPRINT.json; it adds no semantics.
''' + '\n' + fence + 'json\n' + json.dumps(plan, ensure_ascii=True, indent=2, sort_keys=True) + '\n' + fence + '\n'


def freshness_markdown(bp):
    plan = bp['freshness_serialization_plan']
    return '''
## Accepted Freshness Serialization Rebind

This materializes g-extract1.freshness-canonicalization.v1 without selecting new
semantics. The accepted contamination repair and every prior allocation remain
unchanged. Canonical rows are [exact_schema_type, canonical_semantic_text], both
JSON strings. Schema bytes are string, number, integer, boolean, YYYY-MM-DD,
HH:MM or the exact full finite-enum schema, never generic semantic tags.

INTEGER is minimal signed base-10 text with signed zero normalized to "0".
NUMBER is exact terminating plain decimal with no plus/exponent/unnecessary
leading or trailing fractional zeros, no empty decimal point and signed zero
normalized to "0". Thus 5/5.0/5.00/5e0 all become "5". No binary floats or
finite-context rounding; equivalent exact int/Decimal/Fraction/token semantics
must yield identical bytes, while unsupported wrappers fail closed.
The typed rows ["integer","5"] and ["number","5"] remain different.

Boolean text is lowercase "true"/"false". DATE/TIME use exact validated
zero-padded YYYY-MM-DD/HH:MM. STRING is exact, without trim, casefold, whitespace
collapse, label removal or Unicode normalization. ENUM retains exact schema
order and exact selected option, never its ordinal. Semantic test vectors do not
relax the existing source literal or lexical authoring grammar.

VALUE source facts only, in source-record order, with duplicates preserved.
No field names, fixture IDs, metadata, operation arguments/targets/outputs or
EXPLICIT_ABSENCE facts enter freshness bytes. The 168 source_row_plans bind each
base's existing VALUE source indices and exact schema sequence. Their base IDs
and indices are bookkeeping only, never parts of serialized freshness atoms.
CF1/CF2 share the same base row plan; existing pair-local sharing is unchanged.

Serialize with json.dumps(sequence, ensure_ascii=False, separators=(',', ':'))
followed by UTF-8 encoding, without newline or external whitespace. This freezes
literal UTF-8 rather than treating escaped ASCII as an interchangeable encoding.
The original semantic case must yield exactly:
`[["YYYY-MM-DD","2039-10-05"],["integer","0"]]`.
This is a contract test, not authored corpus content or replay of a scored call.

Only the already-required NEW freshness layer uses this encoding. Freshness
itself does not amend historical projection, Jaccard views/residuals, fingerprints,
whole-answer, identity or date-number encoding/applicability. The later separate
accepted whole-answer amendment is materialized in its own section below;
the other representations remain unchanged.
The separate NUMBER tuple convention of "5.0" is not replaced by freshness "5".
Historical adaptation stays 106/106, rejected 0 with unchanged projection digest.

All nine active source schema forms, all 39 contract vectors, three equivalence
groups and isolated byte mutations are checked. Untracked corpus/checker and gold
hashes are preservation evidence only, not contamination rescoring or gold review.
No checker repair, corpus regeneration/finalization, runtime, pilot, freeze or
Phase A/B execution is authorized here. Independent blueprint rereview and later
separate authorizations remain required; belief effects none.

The exact co-normative accepted encoding contract follows. Concrete values in
this annex are isolated contract vectors only; they are not fixture allocations.

<!-- BLUEPRINT_FRESHNESS_NORMATIVE_BEGIN -->
```json
''' + json.dumps(plan['materialized_contract'], ensure_ascii=True, indent=2, sort_keys=True) + '''
```
<!-- BLUEPRINT_FRESHNESS_NORMATIVE_END -->
'''


def scaffold_markdown(bp):
    scaffold = bp['comparison_scope']['scaffold_overlap']
    rows = ['\n## Accepted Bounded Scaffold Rebind\n',
            'Mandatory grammar made specific old ordinary/content tests infeasible even with fresh values. The accepted repair, not this blueprint, defines the bounded remedy.',
            'Exactly 14 classes cover 234 logical unordered pairs and 906 cross-base rendered pairs. Twelve subtype-pair summaries split into two E1-05 classes (R2 zero/R3 366), ten E5 classes, and two E7-02/E7-04 presentation classes (A/B).',
            'BLUEPRINT.json comparison_scope.scaffold_overlap contains every exact logical/rendered pair, accepted class ID, invariant gram, old branch/minimum, context/reserve scope, and exact design path. There are no subtype wildcards.',
            'Use existing ordinary normalized/tokenized five-gram sets A/B. Subtract the frozen invariant set I separately: RA=A\\I; RB=B\\I. Never rewrite tokens, create adjacency, recompute I from values, or apply subtraction historically. Require nonempty RA and RB and strict 25*intersection < 3*union (Jaccard <0.12). Either empty produces AUTHORING_ERROR_EMPTY_RESIDUAL.',
            'Both actual fixtures must pass position, lexical, schema, operation/gold, subtype, value-shape, output and planned-fingerprint checks; E5 also requires its full request/pair audit. Raw typed VALUE freshness, whole-answer/identity/date-number reuse, raw payload inequality, generated identities and independent A/B checks remain mandatory. Residual success alone never permits a pair.',
            'Precedence: historical rules first; actual structural/profile invalidity errors; validated same-base E5 pair-local sharing; cross-base freshness/reuse rejection; exact scaffold membership; remaining declared same-subtype content/shape rules; remaining ordinary rules. Pair-local sharing precedes cross-base freshness intentionally. The 24 same-base E5 scopes are separate and excluded from scaffold membership. All four cross-base E5 CF combinations inherit only their exact base-pair membership.',
            'Historical/new remains unchanged: ordinary>=0.20, projection3/3, or projection>=2/3 and ordinary>=0.12 reject; 106/106 historical adaptations and 20,352 comparisons remain required. No historical scaffold handling.',
            'Scaffold classes are not recurrence groups. Remaining same-subtype content rules, different-subtype ordinary rules, 51 fingerprint classes, 35 subtype groups, reserves, schedules, seeds and gates are unchanged. The report partitions all 18,312 cross-base rendered pairs; 906 are included within that domain, not additional comparisons.',
            'This materializes frozen pairwise-feasibility rules only. Simultaneous concrete corpus feasibility, actual independence, corpus acceptance and scientific validity are not proven. This blueprint carries no concrete content; the preserved untracked candidate attempt remains incomplete.',
            '\n| Accepted Class ID | Subtypes | Logical | Rendered | Old Branch / Minimum |',
            '|---|---|---:|---:|---|']
    for g in scaffold['classes']:
        rows.append('| ' + g['class_id'] + ' | ' + '/'.join(g['subtype_pair']) + ' | ' +
                    str(len(g['logical_position_pairs'])) + ' | ' + str(len(g['rendered_position_pairs'])) +
                    ' | ' + g['old_applicable_branch'] + ' / ' + g['old_minimum_ordinary_jaccard'] + ' |')
    counts = scaffold['cross_base_branch_counts']
    table_start = next(i for i, row in enumerate(rows) if row.lstrip().startswith('| Accepted'))
    summary = ('Cross-base partition: ' + str(counts['DECLARED_SCAFFOLD']) + ' scaffold + ' +
               str(counts['DECLARED_SAME_SUBTYPE']) + ' remaining same-subtype + ' +
               str(counts['ORDINARY_NEW_NEW']) + ' ordinary = 18,312. All 24 pair-local scopes remain separate.')
    return '\n\n'.join(rows[:table_start] + [summary]) + '\n\n' + '\n'.join(rows[table_start:]) + '\n'


def resolve_pointer(c, reference):
    prefix="DESIGN_CANDIDATE.json#"
    if not reference.startswith(prefix):raise ValueError("unknown authority reference")
    value=c
    for part in reference[len(prefix):].strip("/").split("/"):
        value=value[int(part)] if isinstance(value,list) else value[part.replace("~1","/").replace("~0","~")]
    return value


def check_output_object(field, expected_field, keys):
    if set(field)!=set(keys) or len(field)!=8:
        raise ValueError("canonical_output_exact_eight_keys")
    if field["required"] is not True:
        raise ValueError("canonical_required_true")
    if field["label_removal"] is not False:
        raise ValueError("canonical_label_removal_false")
    if field["absence_capable"] is not expected_field["absence_capable"]:
        raise ValueError("canonical_absence_boolean")
    if field!=expected_field:
        raise ValueError("canonical_output_binding_schema")


def validate_output_plans(bp, c):
    """Check from source/producer plans, independently of canonical_output()."""
    checks = []
    def require(ok, label):
        if not ok:raise ValueError(label)
        checks.append(label)
    amendment = c["output_field_amendment_contract"]
    keys = amendment["exact_output_field_keys"]
    require(amendment["global_constants"] == dict(required=True,label_removal=False), "accepted_output_constants")
    lex = c["lexical_neutrality_contract"]["identifier_generation"]
    by_base = {p["logical_base_id"]:p for p in bp["logical_positions"]}
    logical_count = e7_count = rendered_count = scored_count = reserve_count = pair_count = 0
    schema_coverage = set()
    for p in bp["logical_positions"]:
        label = p["logical_base_id"]
        plan = p["schema_plan"]
        fields = plan["output_fields"]
        metadata = plan["output_field_metadata"]
        source = plan["source_fact_role_schema_entity_sequence"]
        nodes = p["operation_plan"]["nodes"]
        requirements = []
        if p["family"] == "E7":
            require(not nodes, "e7_zero_nodes:"+label)
            row = next(x for x in c["subtype_allocation_contract"]["slot_rows"]["E7"] if x["slot_id"]==p["subtype_slot"])
            require(len(fields)==len(row["domain"])+1, "e7_every_supported_and_absent_output:"+label)
            require(all(entity == -1 for _,_,entity in source), "source_copy_non_entity:"+label)
            for i,(role,schema,_) in enumerate(source,1):
                binding = "EXPLICIT_ABSENCE" if role=="EXPLICIT_ABSENCE" else "SOURCE_COPY"
                identifier = lex["source_field"]["format"].format(fixture_ordinal=p["fixture_ordinal"],source_field_ordinal=i)
                requirements.append((binding,schema,identifier,"absence_sentinel" if role=="EXPLICIT_ABSENCE" else "source_copy",i,None))
            e7_count += len(fields)
        else:
            require(len(fields)==1 and len(nodes) in (1,2), "one_producer_output:"+label)
            producer = nodes[-1]
            identifier = lex["derived_target"]["format"].format(fixture_ordinal=p["fixture_ordinal"],topological_node_ordinal=len(nodes))
            require(producer["target_identifier"]==identifier,"producer_identifier:"+label)
            requirements.append(("OPERATION_TARGET",producer["result_schema_type"],identifier,plan["output_schema_role_sequence"][0][1],None,len(nodes)-1))
        require(len(fields)==len(metadata)==len(requirements), "output_and_metadata_cardinality:"+label)
        require([f["name"] for f in fields]==sorted((f["name"] for f in fields),key=lambda name:name.encode()), "canonical_output_name_order:"+label)
        for f,m,(binding,schema,identifier,role,source_index,producer_index) in zip(fields,metadata,requirements):
            suffix = label+":"+identifier
            require(set(f)==set(keys) and len(f)==8, "canonical_output_exact_eight_keys:"+suffix)
            require(f["required"] is True, "canonical_required_true:"+suffix)
            require(f["label_removal"] is False, "canonical_label_removal_false:"+suffix)
            expected_field = dict(name=identifier,schema_type=schema,required=True,binding_kind=binding,
                                  source_field=None if binding=="OPERATION_TARGET" else identifier,
                                  producer_target=identifier if binding=="OPERATION_TARGET" else None,
                                  label_removal=False,absence_capable=binding=="EXPLICIT_ABSENCE")
            check_output_object(f,expected_field,keys)
            require(f==expected_field, "canonical_output_binding_schema:"+suffix)
            pointer = "/output_field_amendment_contract/binding_construction/"+binding+"/"
            expected_metadata = dict(name=identifier,output_role=role,binding_source_field_ordinal=source_index,
                                     producer_node=producer_index,canonical_field_traceability={key:ref(pointer+key) for key in keys},
                                     output_role_ref=ref("/family_assignment_contract/output_role_derivation"))
            require(m==expected_metadata, "output_roles_and_amendment_trace_separate:"+suffix)
            for key,reference in m["canonical_field_traceability"].items():
                require(resolve_pointer(c,reference)==amendment["binding_construction"][binding][key], "canonical_field_trace:"+suffix+":"+key)
            schema_coverage.add(schema)
        logical_count += len(fields)
    for variant in bp["rendered_variants"]:
        p = by_base[variant["logical_base_id"]]
        require(variant["scientific_metadata_source"]==p["logical_base_id"], "rendered_output_inherits_base:"+variant["rendered_variant_id"])
        fields = by_base[variant["scientific_metadata_source"]]["schema_plan"]["output_fields"]
        rendered_count += len(fields)
        if p["primary_or_reserve"]=="PRIMARY":scored_count+=len(fields)
        else:reserve_count+=len(fields)
        if p["family"]=="E5" and variant["variant_id"]=="CF1":
            partners = [x for x in bp["rendered_variants"] if x["rendered_variant_id"]==variant["pair_partner"]]
            require(len(partners)==1,"e5_exact_pair_partner:"+p["logical_base_id"])
            partner = partners[0]
            other = by_base[partner["scientific_metadata_source"]]["schema_plan"]["output_fields"]
            require(fields==other,"e5_pair_output_equality:"+p["logical_base_id"])
            pair_count += 1
    require((logical_count,rendered_count,scored_count,reserve_count,e7_count)==(220,244,204,40,76),"output_definition_and_rendered_counts")
    require({"integer","number","string","boolean","YYYY-MM-DD","HH:MM","provided|not_provided"} <= schema_coverage
            and any(schema.startswith("option_a|") for schema in schema_coverage), "output_all_schema_categories")
    return checks, dict(logical_output_definitions=logical_count,rendered_output_instances=rendered_count,
                        scored_rendered_output_instances=scored_count,reserve_rendered_output_instances=reserve_count,
                        e7_output_definitions=e7_count,e5_pairs_with_identical_outputs=pair_count,
                        schema_coverage=sorted(schema_coverage),required=True,label_removal=False)


def validate_original_preservation(bp):
    original = json.loads(git("show",ORIGINAL_BLUEPRINT+":experiments/G-EXTRACT1-candidate/blueprint/BLUEPRINT.json"))
    projected = copy.deepcopy(bp)
    projected.pop('whole_answer_serialization_plan')
    projected['scientific_traceability'].pop('whole_answer_serialization')
    projected.pop('freshness_serialization_plan')
    projected['scientific_traceability'].pop('freshness_serialization')
    projected['comparison_scope'].pop('scaffold_overlap')
    projected['scientific_traceability'].pop('scaffold_overlap')
    projected["status"] = original["status"]
    projected["accepted_design"] = original["accepted_design"]
    projected["scientific_traceability"]["schema_plan"].remove(ref("/output_field_amendment_contract"))
    for p in projected["logical_positions"]:
        metadata = p["schema_plan"].pop("output_field_metadata")
        fields = p["schema_plan"]["output_fields"]
        p["schema_plan"]["output_fields"] = [dict(name=f["name"],schema_type=f["schema_type"],binding_kind=f["binding_kind"],
                                                   binding_source_field_ordinal=m["binding_source_field_ordinal"],
                                                   producer_node=m["producer_node"],output_role=m["output_role"])
                                               for f,m in zip(fields,metadata)]
    if projected!=original:raise ValueError("non_output_blueprint_allocation_changed")
    return ["original_blueprint_all_other_allocations_unchanged"]


def validate_output_blueprint_preservation(bp):
    prior = json.loads(git('show', OUTPUT_BLUEPRINT + ':experiments/G-EXTRACT1-candidate/blueprint/BLUEPRINT.json'))
    projected = copy.deepcopy(bp)
    projected.pop('whole_answer_serialization_plan')
    projected['scientific_traceability'].pop('whole_answer_serialization')
    projected.pop('freshness_serialization_plan')
    projected['scientific_traceability'].pop('freshness_serialization')
    projected['status'] = prior['status']
    projected['accepted_design'] = prior['accepted_design']
    projected['comparison_scope'].pop('scaffold_overlap')
    projected['scientific_traceability'].pop('scaffold_overlap')
    if projected != prior: raise ValueError('prior_blueprint_allocation_changed')
    return ['all_prior_blueprint_allocations_exactly_preserved']


def validate_prior_preservation(bp):
    prior = json.loads(git('show', PRIOR_BLUEPRINT + ':experiments/G-EXTRACT1-candidate/blueprint/BLUEPRINT.json'))
    projected = copy.deepcopy(bp)
    projected.pop('whole_answer_serialization_plan')
    projected['scientific_traceability'].pop('whole_answer_serialization')
    projected.pop('freshness_serialization_plan')
    projected['scientific_traceability'].pop('freshness_serialization')
    projected['status'] = prior['status']
    projected['accepted_design'] = prior['accepted_design']
    if projected != prior: raise ValueError('freshness_rebind_changed_prior_scientific_allocation')
    return ['accepted_01aafde_blueprint_preserved_except_freshness_binding_status_and_plan']


def validate_whole_prior_preservation(bp):
    prior = json.loads(git('show', WHOLE_PRIOR_BLUEPRINT + ':experiments/G-EXTRACT1-candidate/blueprint/BLUEPRINT.json'))
    projected = copy.deepcopy(bp)
    projected.pop('whole_answer_serialization_plan')
    projected['scientific_traceability'].pop('whole_answer_serialization')
    projected['status'] = prior['status']
    projected['accepted_design'] = prior['accepted_design']
    if projected != prior: raise ValueError('whole_answer_rebind_changed_prior_allocation_or_freshness')
    return ['accepted_3bf939_blueprint_exactly_preserved_except_whole_answer_binding_status_and_plan']


def validate_whole_answer_plan(bp, c, helper):
    checks = []
    def require(ok, label):
        if not ok: raise ValueError(label)
        checks.append(label)
    plan = bp['whole_answer_serialization_plan']
    require(plan == materialize_whole_answer(c, bp['logical_positions'], helper), 'whole_answer_exact_accepted_contract_and_row_plans')
    require(plan['amendment_commit'] == ACCEPTED, 'whole_answer_accepted_amendment_binding')
    source = plan['materialized_contract']
    require(source['contract_id'] == 'g-extract1.whole-answer-canonicalization.v1', 'whole_answer_contract_identity')
    require(source['row_contract']['outer_length'] == 3 and source['row_contract']['inner_length'] == 2
            and source['row_contract']['all_leaf_elements'] == 'JSON strings only', 'whole_answer_four_string_leaves')
    require(source['outer_serialization']['ensure_ascii'] is True
            and source['outer_serialization']['separators'] == [',', ':']
            and source['outer_serialization']['terminal_newline'] is False, 'whole_answer_compact_ascii_UTF8_no_newline')
    require(source['comparison']['match_rule'] == plan['existing_whole_answer_rule']['match_rule']
            and source['comparison']['per_field_or_subset_matching'] is False, 'whole_answer_exact_full_object_match_only')
    require(plan['historical_and_new_use_same_encoding_in_existing_scope'] is True
            and plan['historical_artifacts_unchanged'] is True, 'whole_answer_historical_NEW_scope_unchanged')
    require(plan['freshness_plan_unchanged'] is True
            and bp['freshness_serialization_plan']['materialized_contract']['byte_serialization']['ensure_ascii'] is False,
            'whole_answer_freshness_separate_encodings')
    require(len(plan['output_row_plans']) == 168, 'whole_answer_168_value_free_row_plans')
    for position, item in zip(bp['logical_positions'], plan['output_row_plans']):
        fields = sorted(position['schema_plan']['output_fields'], key=lambda f: f['name'].encode('utf-8'))
        rows = item['sorted_output_row_plans']
        require(item['logical_base_id'] == position['logical_base_id'] and len(rows) == len(fields),
                'whole_answer_output_row_binding:' + position['logical_base_id'])
        require(len({f['name'] for f in fields}) == len(fields), 'whole_answer_unique_fields:' + position['logical_base_id'])
        require(all(row == dict(field_name=f['name'], historical_schema_type=f['schema_type'],
                                semantic_tag=helper.parse_schema_type(f['schema_type'], c['schema_type_contract'])['semantic_tag'],
                                canonical_semantic_text='UNAUTHORED') for row, f in zip(rows, fields)),
                'whole_answer_exact_field_schema_tag_plan:' + position['logical_base_id'])
    for key, value in source['authority'].items():
        require(value is True if key.endswith('_required') else value == 'none' if key == 'belief_effects'
                else type(value) is int and value == 0 if key == 'provider_calls' else value is False,
                'whole_answer_no_later_authority:' + key)
    return checks


def validate_freshness_plan(bp, c):
    checks = []
    def require(ok, label):
        if not ok: raise ValueError(label)
        checks.append(label)
    plan = bp['freshness_serialization_plan']
    require(plan == materialize_freshness(c, bp['logical_positions']), 'freshness_exact_accepted_contract_and_row_plans')
    require(plan['amendment_commit'] == FRESHNESS_AMENDMENT and plan['historical_side_uses_new_freshness'] is False,
            'freshness_NEW_only_not_historical_reinterpretation')
    require(plan['other_representations_unchanged'] is True and plan['same_base_e5_exception_unchanged'] is True,
            'freshness_no_other_representation_or_pair_scope_change')
    source = plan['materialized_contract']
    require(source['sequence']['row_elements'] == 'JSON strings only' and source['sequence']['row_exact_length'] == 2,
            'freshness_two_string_row_shape')
    require(source['sequence']['included_template_ids'] == ['VALUE'] and source['sequence']['sorting'] is False,
            'freshness_VALUE_only_unsorted')
    require(source['schema_binding']['primitive_spellings'] == c['schema_type_contract']['primitive_schema_tokens'],
            'freshness_exact_schema_spellings')
    require(source['byte_serialization']['ensure_ascii'] is False and source['byte_serialization']['separators'] == [',', ':']
            and source['byte_serialization']['trailing_newline'] is False, 'freshness_compact_UTF8_no_newline')
    require(len(plan['source_row_plans']) == 168, 'freshness_168_metadata_row_plans')
    for position, row in zip(bp['logical_positions'], plan['source_row_plans']):
        require(row['logical_base_id'] == position['logical_base_id'], 'freshness_row_binding:' + row['logical_base_id'])
        sequence = position['schema_plan']['source_fact_role_schema_entity_sequence']
        indices = [i for i, item in enumerate(sequence) if item[0] != 'EXPLICIT_ABSENCE']
        require(row['source_record_indices'] == indices and row['exact_schema_type_sequence'] == [sequence[i][1] for i in indices],
                'freshness_source_order_VALUE_schema:' + row['logical_base_id'])
    require(plan['active_source_schema_types'] == ['HH:MM', 'YYYY-MM-DD', 'boolean', 'integer', 'number',
                                                 'option_a|option_b', 'option_a|option_b|option_c', 'provided|not_provided', 'string'],
            'freshness_nine_active_source_schema_forms')
    for key, value in source['authority'].items():
        if key in {'independent_rereview_required', 'separate_blueprint_rebind_required'}:
            require(value is True, 'freshness_review_boundary:' + key)
        elif key == 'belief_effects': require(value == 'none', 'freshness_belief_none')
        elif key == 'provider_calls': require(value == 0, 'freshness_zero_provider')
        else: require(value is False, 'freshness_no_later_authority:' + key)
    return checks


def validate_freshness_vectors(bp, c, helper, checks):
    """Accepted design helpers, isolated contract vectors; not corpus tooling."""
    source = bp['freshness_serialization_plan']['materialized_contract']
    encode = lambda rows: helper.freshness_sequence_bytes(rows, c)
    def require(ok, label):
        if not ok: raise ValueError(label)
        checks.append(label)
    schemas = set()
    for vector in source['validation_vectors']:
        actual = encode(vector['semantic_rows'])
        require(actual == vector['expected_utf8'].encode('utf-8'), 'freshness_contract_vector:' + vector['id'])
        require(json.loads(actual) == vector['expected_sequence'], 'freshness_contract_rows:' + vector['id'])
        require(all(len(row) == 2 and all(type(x) is str for x in row) for row in json.loads(actual)),
                'freshness_no_host_scalar:' + vector['id'])
        schemas.update(row[0] for row in vector['semantic_rows'])
    require(schemas == set(bp['freshness_serialization_plan']['active_source_schema_types']), 'freshness_all_active_schemas_tested')
    for group in source['equivalence_groups']:
        results = {encode([[group['schema_type'], value]]) for value in group['values']}
        require(results == {group['expected_utf8'].encode('utf-8')}, 'freshness_semantic_equivalence:' + group['id'])
    for schema in ('integer', 'number'):
        for value in (0, 1, -1, 42, 10**70 + 1):
            require(len({encode([[schema, x]]) for x in (value, str(value), Decimal(str(value)), Fraction(value))}) == 1,
                    'freshness_host_independence:' + schema + ':' + str(value))
    for left, right in (('5', '5.0001'), ('0.5', '0.05'), ('-1', '1')):
        require(encode([['number', left]]) != encode([['number', right]]), 'freshness_distinct_values:' + left + ':' + right)
    require(encode([['number', Fraction(1, 8)]]) == b'[["number","0.125"]]', 'freshness_exact_rational_no_float')
    require(encode([['number', Decimal('123456789012345678901234567890.125000')]]) == b'[["number","123456789012345678901234567890.125"]]',
            'freshness_no_Decimal_context_rounding')
    require(encode([['integer', '5']]) != encode([['number', '5']]), 'freshness_typed_numeric_distinction')
    original = source['original_failure_semantic_vector']
    require(encode(list(map(list, zip(original['source_schemas'], original['source_values'])))) == original['expected_utf8'].encode('utf-8'),
            'freshness_original_failure_reconstruction')
    require(encode([['string', '\u00e9']]) != encode([['string', 'e\u0301']]), 'freshness_STRING_no_Unicode_normalization')
    facts = [
        dict(template_id='VALUE', field_identifier='f001_01', schema_type='integer', value=dict(kind='integer_literal', value='42'), entity_selector_value=None),
        dict(template_id='EXPLICIT_ABSENCE', field_identifier='f001_02', schema_type='provided|not_provided', value=None, entity_selector_value=None),
        dict(template_id='VALUE', field_identifier='f001_03', schema_type='integer', value=dict(kind='integer_literal', value='42'), entity_selector_value=None),
        dict(template_id='VALUE', field_identifier='f001_04', schema_type='number', value=dict(kind='integer_literal', value='5'), entity_selector_value=None),
    ]
    require(helper.freshness_from_source_facts(facts, c) == b'[["integer","42"],["integer","42"],["number","5"]]',
            'freshness_VALUE_scope_order_duplicates_and_schema_not_literal_tag')
    packed = lambda rows: json.dumps(rows, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    variants = [
        ('integer_numeric_scalar', [['integer', '0']], [['integer', 0]]),
        ('number_numeric_scalar', [['number', '5']], [['number', 5]]),
        ('number_exponent_retained', [['number', '5e0']], [['number', '5e0']]),
        ('number_trailing_zeroes_retained', [['number', '0.50']], [['number', '0.50']]),
        ('number_empty_fraction_point_retained', [['number', '5.0']], [['number', '5.']]),
        ('negative_zero_retained', [['number', '-0.0']], [['number', '-0']]),
        ('integer_leading_plus', [['integer', '1']], [['integer', '+1']]),
        ('integer_leading_zeroes', [['integer', '1']], [['integer', '01']]),
        ('boolean_capitalized', [['boolean', True]], [['boolean', 'True']]),
        ('date_reformatted', [['YYYY-MM-DD', '2039-10-05']], [['YYYY-MM-DD', '10/05/2039']]),
        ('time_reformatted', [['HH:MM', '23:45']], [['HH:MM', '11:45 PM']]),
        ('string_trimmed', [['string', ' label_001_01 ']], [['string', 'label_001_01']]),
        ('enum_ordinal', [['option_a|option_b', 'option_b']], [['option_a|option_b', 1]]),
        ('atoms_sorted', [['string', 'label_001_01'], ['integer', '42']], [['integer', '42'], ['string', 'label_001_01']]),
        ('duplicate_removed', [['integer', '42'], ['integer', '42']], [['integer', '42']]),
        ('row_missing_element', [['integer', '0']], [['integer']]),
        ('row_extra_element', [['integer', '0']], [['integer', '0', 'extra']]),
        ('null_value', [['integer', '0']], [['integer', None]]),
        ('object_value', [['integer', '0']], [['integer', {}]]),
        ('array_value', [['integer', '0']], [['integer', []]]),
        ('schema_enum_reordered', [['option_a|option_b', 'option_b']], [['option_b|option_a', 'option_b']]),
        ('absence_included', [['integer', '42']], [['integer', '42'], ['provided|not_provided', 'not_provided']]),
        ('derived_output_included', [['integer', '42']], [['integer', '42'], ['integer', '84']]),
        ('integer_number_schema_collapse', [['number', '5']], [['integer', '5']]),
    ]
    for schema, value, tag in (('integer', '0', 'INTEGER'), ('number', '5', 'NUMBER'), ('YYYY-MM-DD', '2039-10-05', 'DATE'),
                               ('HH:MM', '23:45', 'TIME'), ('string', 'label_001_01', 'STRING'), ('boolean', True, 'BOOLEAN'),
                               ('option_a|option_b', 'option_a', 'ENUM')):
        variants.append(('semantic_tag_' + tag.lower(), [[schema, value]], [[tag, 'true' if value is True else value]]))
    byte_mutations = [(label, rows, packed(mutated)) for label, rows, mutated in variants]
    byte_mutations += [
        ('whitespace_formatted_json', [['integer', '0']], b'[["integer", "0"]]'),
        ('ensure_ascii_true_non_ascii', [['string', '\u00e9']], json.dumps([['string', '\u00e9']], ensure_ascii=True, separators=(',', ':')).encode()),
        ('trailing_newline', [['integer', '0']], b'[["integer","0"]]\n'),
    ]
    require({name for name, _, _ in byte_mutations} == set(source['mutation_catalog']) | {'integer_number_schema_collapse'},
            'freshness_all_accepted_mutations_plus_typed_collapse')
    for label, rows, mutated in byte_mutations:
        try: helper.require_freshness_bytes(mutated, rows, c)
        except ValueError: checks.append('freshness_byte_mutation_rejected:' + label)
        else: raise ValueError('freshness_byte_mutation_accepted:' + label)
    for schema, value in (('number', 0.5), ('integer', True), ('number', Fraction(1, 3)), ('number', 'NaN')):
        try: encode([[schema, value]])
        except (ValueError, TypeError): checks.append('freshness_unsupported_semantic_input:' + schema + ':' + str(value))
        else: raise ValueError('freshness_unsupported_input_accepted')
    class DisplayOnlyNumber:
        def __str__(self): return '5'
    for schema in ('integer', 'number'):
        try: encode([[schema, DisplayOnlyNumber()]])
        except (ValueError, TypeError): checks.append('freshness_display_only_numeric_wrapper_rejected:' + schema)
        else: raise ValueError('freshness_display_formatter_used_as_semantic_value')
    return dict(contract_vectors=len(source['validation_vectors']), active_schema_forms=sorted(schemas),
                equivalence_groups=len(source['equivalence_groups']), byte_mutations_rejected=len(byte_mutations),
                byte_mutation_categories=[name for name, _, _ in byte_mutations],
                original_failure_bytes=original['expected_utf8'], corpus_evaluated=False,
                scope='accepted design helpers and isolated contract tests only; no corpus checker implementation or repair')


def validate_whole_answer_vectors(bp, c, helper, checks):
    """Isolated accepted semantics; never call legacy corpus helpers or a campaign."""
    source = bp['whole_answer_serialization_plan']['materialized_contract']
    encode = lambda rows: helper.whole_answer_canonical_bytes(rows, c)
    def require(ok, label):
        if not ok: raise ValueError(label)
        checks.append(label)
    schemas, tags = set(), set()
    for vector in source['validation_vectors']:
        raw = encode(vector['semantic_rows'])
        rows = json.loads(raw)
        require(raw == vector['expected_utf8'].encode('utf-8'), 'whole_answer_golden_bytes:' + vector['id'])
        require(rows == vector['expected_rows'], 'whole_answer_golden_rows:' + vector['id'])
        require(all(len(row) == 3 and type(row[0]) is str and type(row[1]) is str and len(row[2]) == 2
                    and all(type(x) is str for x in row[2]) for row in rows), 'whole_answer_string_leaves:' + vector['id'])
        require(encode(list(reversed(vector['semantic_rows']))) == raw, 'whole_answer_insertion_order_invariant:' + vector['id'])
        schemas.update(row[1] for row in rows)
        tags.update(row[2][0] for row in rows)
    require(schemas == set(bp['whole_answer_serialization_plan']['active_output_schema_types']), 'whole_answer_nine_active_schemas_tested')
    require(tags == set(source['semantic_tags']) == set(bp['whole_answer_serialization_plan']['active_semantic_tags']), 'whole_answer_seven_tags_tested')
    for group in source['equivalence_groups']:
        require({encode([['field', group['schema_type'], value]]) for value in group['values']}
                == {group['expected_utf8'].encode('utf-8')}, 'whole_answer_numeric_equivalence:' + group['id'])
    for schema in ('integer', 'number'):
        distinct = []
        for value in (0, 1, -1, 42, 10**70 + 1):
            results = {encode([['field', schema, x]]) for x in (value, str(value), Decimal(str(value)), Fraction(value))}
            require(len(results) == 1, 'whole_answer_host_independence:' + schema + ':' + str(value))
            distinct.append(next(iter(results)))
        require(len(set(distinct)) == len(distinct), 'whole_answer_distinct_numeric_values:' + schema)
    require(encode([['field', 'number', Fraction(1, 8)]]) == b'[["field","number",["NUMBER","0.125"]]]', 'whole_answer_exact_fraction')
    require(encode([['field', 'number', Decimal('123456789012345678901234567890.125000')]])
            == b'[["field","number",["NUMBER","123456789012345678901234567890.125"]]]', 'whole_answer_no_context_rounding')
    require(encode([['field', 'integer', 5]]) != encode([['field', 'number', 5]]), 'whole_answer_typed_numeric_distinction')
    require(encode([['field', 'string', '\u00e9']]) != encode([['field', 'string', 'e\u0301']]), 'whole_answer_no_unicode_normalization')
    require(b'\\u00e9' in encode([['field', 'string', '\u00e9']])
            and '\u00e9'.encode('utf-8') in helper.freshness_sequence_bytes([['string', '\u00e9']], c), 'whole_answer_ascii_true_freshness_false')
    failure = next(v for v in source['validation_vectors'] if v['id'] == 'original_failure')
    require(encode(failure['semantic_rows']) == b'[["d016_02","boolean",["BOOLEAN","true"]]]', 'whole_answer_original_failure_completed_bytes')
    packed = lambda rows: json.dumps(rows, ensure_ascii=True, separators=(',', ':')).encode('utf-8')
    mutations = []
    for label, schema, semantic, replacement in [
        ('boolean_scalar_true', 'boolean', True, True), ('boolean_scalar_false', 'boolean', False, False),
        ('integer_numeric_scalar', 'integer', '0', 0), ('number_numeric_scalar', 'number', '5', 5),
        ('number_exponent', 'number', '5e0', '5e0'), ('number_trailing_zeroes', 'number', '5.00', '5.00'),
        ('number_negative_zero', 'number', '-0.0', '-0'), ('integer_negative_zero', 'integer', '-0', '-0'),
        ('date_reformatted', 'YYYY-MM-DD', '2039-10-05', '10/05/2039'), ('time_reformatted', 'HH:MM', '23:45', '11:45 PM'),
        ('string_trimmed', 'string', ' label_001_01 ', 'label_001_01'), ('enum_ordinal', 'option_a|option_b', 'option_b', 1),
        ('not_provided_null', 'provided|not_provided', 'not_provided', None), ('null_value', 'integer', '0', None),
        ('array_value', 'integer', '0', []), ('object_value', 'integer', '0', {}),
    ]:
        rows = [['field', schema, semantic]]
        bad = json.loads(encode(rows))
        bad[0][2][1] = replacement
        mutations.append((label, rows, packed(bad)))
    base = [['field', 'integer', '0']]
    golden = json.loads(encode(base))
    for label, part, replacement in [('tag_lowercase', 'tag', 'integer'), ('tag_replaced_by_schema', 'tag', 'integer'),
                                      ('schema_replaced_by_tag', 'schema', 'INTEGER'), ('typed_numeric_collapse', 'tag', 'NUMBER')]:
        bad = copy.deepcopy(golden)
        if part == 'tag': bad[0][2][0] = replacement
        else: bad[0][1] = replacement
        mutations.append((label, base, packed(bad)))
    for label, bad in [
        ('inner_missing_element', [['field', 'integer', ['INTEGER']]]),
        ('inner_extra_element', [['field', 'integer', ['INTEGER', '0', 'extra']]]),
        ('outer_missing_element', [['field', ['INTEGER', '0']]]),
        ('outer_extra_element', [['field', 'integer', ['INTEGER', '0'], 'extra']]),
    ]: mutations.append((label, base, packed(bad)))
    unicode_rows = [['field', 'string', '\u00e9']]
    sort_rows = [['z', 'integer', '0'], ['a', 'integer', '1']]
    mutations.extend([
        ('ensure_ascii_false', unicode_rows, json.dumps(json.loads(encode(unicode_rows)), ensure_ascii=False, separators=(',', ':')).encode('utf-8')),
        ('pretty_JSON', base, json.dumps(golden, indent=2).encode('utf-8')),
        ('terminal_newline', base, packed(golden) + b'\n'),
        ('wrong_field_sorting', sort_rows, packed(list(reversed(json.loads(encode(sort_rows)))))),
    ])
    require({label for label, _, _ in mutations} == set(source['mutation_catalog']), 'whole_answer_exact_accepted_byte_mutation_catalog')
    for label, rows, raw in mutations:
        try: helper.require_whole_answer_bytes(raw, rows, c)
        except ValueError: checks.append('whole_answer_byte_mutation_rejected:' + label)
        else: raise ValueError('whole_answer_byte_mutation_accepted:' + label)
    class DisplayOnlyNumber:
        def __str__(self): return '5'
    invalid = [
        [['field', 'integer', True]], [['field', 'integer', 5.0]], [['field', 'integer', '5e0']],
        [['field', 'integer', '05']], [['field', 'integer', '+5']], [['field', 'integer', Fraction(1, 2)]],
        [['field', 'number', 0.5]], [['field', 'number', True]], [['field', 'number', 'NaN']],
        [['field', 'number', Fraction(1, 3)]], [['field', 'number', object()]],
        [['field', 'number', DisplayOnlyNumber()]], [['field', 'integer', DisplayOnlyNumber()]],
        [['field', 'boolean', 'true']], [['field', 'boolean', 1]], [['field', 'YYYY-MM-DD', '2039-02-29']],
        [['field', 'YYYY-MM-DD', '2039-1-05']], [['field', 'HH:MM', '24:00']], [['field', 'HH:MM', '3:45']],
        [['field', 'option_a|option_b', 0]], [['field', 'option_a|option_b', 'option_c']],
        [['field', 'DATE', '2039-10-05']], [['field', 'date', '2039-10-05']],
        [['field', 'TIME', '23:45']], [['field', 'time', '23:45']], [['field', 'ENUM', 'not_provided']],
        [['field', 'string', None]], [['field', 'string', '\ud800']], [['\ud800', 'string', 'value']],
        [['field', 'integer', '0'], ['field', 'integer', '1']], [['field', 'integer']],
        [['field', 'integer', '0', 'extra']], [[1, 'integer', '0']], [['field', 'integer', {'display': '0'}]],
    ]
    for i, rows in enumerate(invalid):
        try: encode(rows)
        except (ValueError, TypeError, UnicodeEncodeError): checks.append('whole_answer_invalid_semantic_input:' + str(i))
        else: raise ValueError('whole_answer_invalid_input_accepted:' + str(i))
    return dict(contract_vectors=len(source['validation_vectors']), active_schema_forms=sorted(schemas),
                semantic_tags=sorted(tags), equivalence_groups=len(source['equivalence_groups']),
                byte_mutations_rejected=len(mutations), byte_mutation_categories=[label for label, _, _ in mutations],
                invalid_semantic_inputs_rejected=len(invalid), original_failure_bytes=failure['expected_utf8'],
                corpus_evaluated=False, checker_repair=False,
                scope='isolated accepted contract helpers and test vectors; not production checker or contamination campaign')


def whole_answer_plan_mutations():
    plan = lambda bp: bp['whole_answer_serialization_plan']
    source = lambda bp: plan(bp)['materialized_contract']
    return [
        ('whole_answer_wrong_amendment', lambda bp: plan(bp).update(amendment_commit=FRESHNESS_AMENDMENT)),
        ('whole_answer_native_value_permission', lambda bp: source(bp)['row_contract'].update(canonical_value='native JSON scalar')),
        ('whole_answer_ascii_false', lambda bp: source(bp)['outer_serialization'].update(ensure_ascii=False)),
        ('whole_answer_terminal_newline', lambda bp: source(bp)['outer_serialization'].update(terminal_newline=True)),
        ('whole_answer_lowercase_tag', lambda bp: plan(bp)['output_row_plans'][0]['sorted_output_row_plans'][0].update(semantic_tag='date')),
        ('whole_answer_schema_replaced_by_tag', lambda bp: plan(bp)['output_row_plans'][0]['sorted_output_row_plans'][0].update(historical_schema_type='DATE')),
        ('whole_answer_missing_output_plan', lambda bp: plan(bp)['output_row_plans'].pop()),
        ('whole_answer_output_plan_reordered', lambda bp: plan(bp)['output_row_plans'].reverse()),
        ('whole_answer_subset_match', lambda bp: source(bp)['comparison'].update(per_field_or_subset_matching=True)),
        ('whole_answer_historical_scope_disabled', lambda bp: plan(bp).update(historical_and_new_use_same_encoding_in_existing_scope=False)),
        ('whole_answer_freshness_altered', lambda bp: plan(bp).update(freshness_plan_unchanged=False)),
        ('whole_answer_checker_authorized', lambda bp: source(bp)['authority'].update(checker_repair=True)),
    ]


def preservation_snapshot():
    """Digest existing artifacts only; never evaluate corpus semantics or gold."""
    accepted = json.loads(git('show', ACCEPTED + ':experiments/G-EXTRACT1-candidate/DESIGN_VALIDATION_REPORT.json'))
    pinned = accepted['whole_answer_canonicalization_amendment']
    directory = DESIGN / 'corpus'
    names = pinned['preserved_corpus_files']
    if {path.name for path in directory.iterdir()} != {Path(name).name for name in names}:
        raise ValueError('preserved_corpus_inventory_changed')
    hashes = {}
    for name, item in names.items():
        hashes[name] = digest((DESIGN / name).read_bytes())
        if hashes[name] != item['after_sha256']: raise ValueError('preserved_corpus_digest_changed:' + name)
    candidates = json.loads((directory / 'AUTHORING_CANDIDATES.json').read_bytes())
    projection = [[row['logical_base_id'], row['fixture']['gold_values']] for row in candidates['accepted']]
    gold = digest(json.dumps(projection, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('utf-8'))
    if gold != pinned['preserved_gold_projection']['after_sha256']: raise ValueError('preserved_gold_projection_changed')
    designs = {}
    for name in SOURCE_NAMES:
        raw = (DESIGN / name).read_bytes()
        if raw != git('show', ACCEPTED + ':' + (DESIGN / name).relative_to(ROOT).as_posix()):
            raise ValueError('accepted_design_mutated_during_rebind:' + name)
        designs[name] = digest(raw)
    return dict(corpus_sha256=hashes, gold_projection_sha256=gold, design_sha256=designs)


def freshness_plan_mutations():
    plan = lambda bp: bp['freshness_serialization_plan']
    source = lambda bp: plan(bp)['materialized_contract']
    return [
        ('freshness_historical_side_enabled', lambda bp: plan(bp).update(historical_side_uses_new_freshness=True)),
        ('freshness_checker_authority_elevated', lambda bp: source(bp)['authority'].update(checker_repair=True)),
        ('freshness_amendment_commit_wrong', lambda bp: plan(bp).update(amendment_commit=CONTAMINATION_REPAIR)),
        ('freshness_other_representation_changed', lambda bp: plan(bp).update(other_representations_unchanged=False)),
        ('freshness_source_rows_sorted', lambda bp: plan(bp)['source_row_plans'].reverse()),
        ('freshness_absence_included_in_plan', lambda bp: next(x for x in plan(bp)['source_row_plans'] if ':E7-' in x['logical_base_id'])['source_record_indices'].append(0)),
        ('freshness_schema_tag_in_plan', lambda bp: plan(bp)['source_row_plans'][0]['exact_schema_type_sequence'].__setitem__(0, 'DATE')),
        ('freshness_branch_count_changed', lambda bp: bp['comparison_scope']['scaffold_overlap']['cross_base_branch_counts'].update(ORDINARY_NEW_NEW=16889)),
    ]


def validate(bp, expected, c, helper):
    checks=[]
    def require(ok,label):
        if not ok:raise ValueError(label)
        checks.append(label)
    require(set(bp)==set(expected),"exact_blueprint_top_level_keys")
    checks.extend(validate_whole_answer_plan(bp, c, helper))
    checks.extend(validate_freshness_plan(bp, c))
    scaffold_checks, _ = validate_scaffold(bp, c)
    checks.extend(scaffold_checks)
    output_checks,_ = validate_output_plans(bp,c)
    checks.extend(output_checks)
    checks.extend(validate_original_preservation(bp))
    checks.extend(validate_output_blueprint_preservation(bp))
    checks.extend(validate_prior_preservation(bp))
    checks.extend(validate_whole_prior_preservation(bp))
    for key in expected:require(bp[key]==expected[key],"accepted_derivation:"+key)
    ps=bp["logical_positions"];vs=bp["rendered_variants"]
    require(len(ps)==168,"168_logical_bases")
    require(len({p['logical_base_id'] for p in ps})==168,"unique_base_ids")
    require(sorted(p['fixture_ordinal'] for p in ps)==list(range(1,169)),"ordinals_1_through_168")
    require(len(vs)==192 and len({v['rendered_variant_id'] for v in vs})==192,"192_unique_rendered_variants")
    by_base={p['logical_base_id']:p for p in ps}
    for p in ps:
        members=[v for v in vs if v['logical_base_id']==p['logical_base_id']]
        require([v['variant_id'] for v in members]==(['CF1','CF2'] if p['family']=='E5' else ['SINGLE']),"exact_members:"+p['logical_base_id'])
        require(p['schema_plan']['exact_field_count']==len(p['schema_plan']['output_fields']),"output_field_count:"+p['logical_base_id'])
        require(set(p['scientific_traceability_groups'])==set(p)-{'scientific_traceability_groups'},'position_field_traceability:'+p['logical_base_id'])
        require(all(group in bp['scientific_traceability'] for group in p['scientific_traceability_groups'].values()),'position_trace_groups:'+p['logical_base_id'])
    for phase in ('A','B'):
        for risk in ('R2','R3'):
            cell=[p for p in ps if p['phase']==phase and p['risk_round']==risk and p['primary_or_reserve']=='PRIMARY']
            require(len(cell)==35,"35_logical:"+phase+':'+risk)
            for family in ('E1','E2','E3','E4','E5','E6','E7'):
                require(sorted(p['subtype_slot'] for p in cell if p['family']==family)==[f'{family}-{i:02d}' for i in range(1,6)],"five_slots:"+phase+':'+risk+':'+family)
            for name,total in [('determinate_semantic',30),('determinate_structural',30),('useful',30),('family_floor',30),('e7',5),('e5_pair',5),('binding_error',10),('malformed_determinate',30),('false_clean',35)]:
                require(sum(p['gate_membership'][name] for p in cell)==total,"gate_denominator:"+phase+':'+risk+':'+name)
            require(sum(len([v for v in vs if v['logical_base_id']==p['logical_base_id']]) for p in cell)==40,"40_rendered_cell:"+phase+':'+risk)
            require(sum(p['composed_quota_row']!='NONE' for p in cell)==8,"eight_composed_positions:"+phase+':'+risk)
    exceptions=0;cross=0
    for left,right in itertools.combinations(vs,2):
        if left['logical_base_id']==right['logical_base_id']:
            require(by_base[left['logical_base_id']]['family']=='E5' and {left['variant_id'],right['variant_id']}=={'CF1','CF2'},"pair_scope:"+left['logical_base_id'])
            exceptions+=1
        else:cross+=1
    require((exceptions,cross)==(24,18312),"rendered_comparison_scope")
    require(106*len(vs)==20352,"historical_comparison_scope")
    require(len(bp['reserve_map'])==28,"28_reserve_maps")
    for mapping in bp['reserve_map']:
        require(mapping['covered_primary_base_id'].endswith('-01:PRIMARY'),"reserve_slot01:"+mapping['reserve_slot_id'])
        require(mapping['reserve_base_id'] in by_base and mapping['covered_primary_base_id'] in by_base,"reserve_referential_integrity:"+mapping['reserve_slot_id'])
    for phase, rows in [('A',bp['schedule_plan']['phase_a']),('B',bp['schedule_plan']['phase_b_maximum_template'])]:
        require(len(rows)==(480 if phase=='A' else 240),'schedule_count:'+phase)
        require(len({r['call_id'] for r in rows})==len(rows),'call_id_unique:'+phase)
        require([r['template_schedule_position'] for r in rows]==list(range(1,len(rows)+1)),'schedule_contiguous:'+phase)
        for model in c['model_provider']['models']:
            mr=[r for r in rows if r['tier']==model['tier']]
            require(len(mr)==(160 if phase=='A' else 80),'per_tier_calls:'+phase+':'+model['tier'])
            seeds={}
            for row in mr:seeds.setdefault(row['seed'],[]).append(row)
            for seed,group in seeds.items():
                require(len(group)==1 or len(group)==2 and len({r['logical_base_id'] for r in group})==1 and {r['variant_id'] for r in group}=={'CF1','CF2'} and len({r['repeat'] for r in group})==1,'seed_collision_scope:'+phase+':'+model['tier']+':'+str(seed))
    cells=bp['schedule_plan']['phase_b_cell_order'];template=bp['schedule_plan']['phase_b_maximum_template']
    for bits in itertools.product((False,True),repeat=6):
        chosen={cell for cell,bit in zip(cells,bits) if bit};rows=[r for r in template if r['cell_id'] in chosen]
        require(len(rows)==40*len(chosen),'conditional_b_subset:'+''.join(str(int(x)) for x in bits))
    for name,refs in bp['scientific_traceability'].items():
        for reference in refs:resolve_pointer(c,reference);require(True,'traceable:'+name+':'+reference)
    forbidden={'source_fact_records','gold_values','input','source_text','operand_values','request_bytes','journal','response'}
    def walk(value, path=()):
        if isinstance(value,dict):
            banned = forbidden.intersection(value)
            if path == ('whole_answer_serialization_plan', 'materialized_contract'):
                require(value.get('input') == c['whole_answer_canonicalization_contract']['input']
                        and type(value.get('input')) is str, 'whole_answer_input_contract_description_not_fixture_content')
                banned.discard('input')
            require(not banned,'no_content_keys:'+str(len(checks)))
            for key, child in value.items():walk(child, path + (key,))
        elif isinstance(value,list):
            for i, child in enumerate(value):walk(child, path + (i,))
        elif isinstance(value,str) and value.startswith('DESIGN_CANDIDATE.json#'):
            resolve_pointer(c,value);require(True,'all_contract_references_resolve:'+str(len(checks)))
    walk(bp)
    require(bp['governance']['provider_model_calls']==bp['governance']['gold_answers_authored']==0,'zero_provider_gold')
    return checks


def validate_reserve_schedules(bp,c,checks):
    maps=bp['reserve_map']
    substitutions=[{x['covered_primary_base_id']:x['reserve_base_id']} for x in maps]
    substitutions.append({x['covered_primary_base_id']:x['reserve_base_id'] for x in maps})
    for index,replacement in enumerate(substitutions):
        plan=schedules(bp['logical_positions'],bp['rendered_variants'],c,replacement)
        lookup={p['logical_base_id']:p for p in bp['logical_positions']}
        for phase,rows in plan.items():
            if len(rows)!=(480 if phase=='A' else 240):raise ValueError('reserve_schedule_count')
            ordinals=[lookup[r['logical_base_id']]['fixture_ordinal'] for r in rows]
            if ordinals!=sorted(ordinals):raise ValueError('reserve_schedule_ordinal_order')
            positions={m['tier']:[0,0,0] for m in c['model_provider']['models']}
            risk_positions={(m['tier'],risk):[0,0,0] for m in c['model_provider']['models'] for risk in ('R2','R3')}
            group=[];last=None;seeds={}
            for row in rows:
                key=row['logical_base_id']
                if key!=last:
                    if group:
                        for place,tier in enumerate(group):
                            positions[tier][place]+=1
                            risk_positions[(tier,lookup[last]['risk_round'])][place]+=1
                    group=[];last=key
                if row['tier'] not in group:group.append(row['tier'])
                seeds.setdefault((row['tier'],row['seed']),[]).append(row)
                expected=replacement.get(row['qualification_slot_id'],row['qualification_slot_id'])
                if row['logical_base_id']!=expected:raise ValueError('reserve_qualification_binding')
            for place,tier in enumerate(group):
                positions[tier][place]+=1
                risk_positions[(tier,lookup[last]['risk_round'])][place]+=1
            if any(max(n)-min(n)>1 for n in list(positions.values())+list(risk_positions.values())):raise ValueError('reserve_model_balance')
            for key,observations in seeds.items():
                if len(observations)>1 and not (len(observations)==2 and len({r['logical_base_id'] for r in observations})==1 and {r['variant_id'] for r in observations}=={'CF1','CF2'} and len({r['repeat'] for r in observations})==1):
                    raise ValueError('reserve_seed_collision')
            checks.append('precontact_reserve_schedule:'+str(index)+':'+phase)


def scaffold_mutations():
    path = lambda x: x['comparison_scope']['scaffold_overlap']
    first = lambda x: path(x)['classes'][0]
    e5 = lambda x: next(g for g in path(x)['classes'] if g['subtype_pair'] == ['E5-01', 'E5-02'])
    def merge(x, family):
        groups = path(x)['classes']
        selected = [g for g in groups if g['subtype_pair'][0].startswith(family)]
        selected[0]['logical_position_pairs'].extend(selected[1]['logical_position_pairs'])
        groups.remove(selected[1])
    def same_base(x):
        base = e5(x)['logical_position_pairs'][0][0]
        e5(x)['rendered_position_pairs'].append([base + ':CF1', base + ':CF2'])
    def altered_recurrence(x):
        x['recurrence_ledger']['positions'][0]['fingerprint_class'] = 'UNAUTHORIZED'
    return [
        ('missing_scaffold_class', lambda x: path(x)['classes'].pop()),
        ('extra_scaffold_class', lambda x: path(x)['classes'].append(copy.deepcopy(first(x)))),
        ('wrong_class_id', lambda x: first(x).update(class_id='WRONG')),
        ('missing_logical_pair', lambda x: first(x)['logical_position_pairs'].pop()),
        ('extra_logical_pair', lambda x: first(x)['logical_position_pairs'].append(['A:R2:E2-01:PRIMARY', 'B:R2:E2-02:PRIMARY'])),
        ('duplicate_logical_pair', lambda x: first(x)['logical_position_pairs'].append(first(x)['logical_position_pairs'][0][:])),
        ('wrong_invariant_gram', lambda x: first(x)['invariant_five_grams'].__setitem__(0, 'wrong fixed invariant gram here')),
        ('added_mutable_gram', lambda x: first(x)['invariant_five_grams'].append('mutable authored value gram here')),
        ('removed_invariant_gram', lambda x: first(x)['invariant_five_grams'].pop()),
        ('wrong_residual_threshold', lambda x: first(x).update(residual_threshold_exclusive='1/5')),
        ('inclusive_residual_comparator', lambda x: first(x).update(residual_comparator='<=')),
        ('allow_empty_residual', lambda x: first(x).update(empty_residual_behavior='PERMITTED')),
        ('same_base_e5_in_scaffold', same_base),
        ('unrelated_e5_pair', lambda x: e5(x)['logical_position_pairs'].append(['A:R2:E5-03:PRIMARY', 'B:R2:E5-04:PRIMARY'])),
        ('merged_e7_ab_classes', lambda x: merge(x, 'E7')),
        ('merged_e1_zero_366_classes', lambda x: merge(x, 'E1')),
        ('historical_in_scaffold', lambda x: first(x)['logical_position_pairs'].append(['HISTORICAL:EXTRACTION', 'A:R2:E1-05:PRIMARY'])),
        ('altered_recurrence_membership', altered_recurrence),
        ('elevated_corpus_authority', lambda x: x['authority'].update(corpus_gold_authoring=True)),
        ('missing_rendered_pair', lambda x: e5(x)['rendered_position_pairs'].pop()),
        ('duplicate_rendered_pair', lambda x: e5(x)['rendered_position_pairs'].append(e5(x)['rendered_position_pairs'][0][:])),
        ('wrong_precedence', lambda x: path(x)['decision_precedence'].reverse()),
        ('missing_freshness_prerequisite', lambda x: path(x)['freshness_required'].pop()),
    ]


def checking_comparison_branch(bp, left, right, facts):
    """Replay the structural branch table using explicit test facts, not fixtures."""
    if facts['historical']:
        return 'HISTORICAL_NEW'
    if not facts['actual_structure_valid']:
        return 'AUTHORING_ERROR_STRUCTURE'
    variants = {v['rendered_variant_id']: v for v in bp['rendered_variants']}
    a, b = variants[left], variants[right]
    if a['logical_base_id'] == b['logical_base_id']:
        return 'SAME_BASE_E5_PAIR_LOCAL' if facts['pair_local_valid'] else 'AUTHORING_ERROR_STRUCTURE'
    if not facts['all_freshness_checks_pass']:
        return 'REJECT_FRESHNESS'
    pair = pair_key(left, right)
    for g in bp['comparison_scope']['scaffold_overlap']['classes']:
        if list(pair) in g['rendered_position_pairs']:
            return checking_residual(g, facts['ordinary_grams_left'], facts['ordinary_grams_right'])
    bases = {p['logical_base_id']: p for p in bp['logical_positions']}
    return 'DECLARED_SAME_SUBTYPE' if bases[a['logical_base_id']]['subtype_slot'] == bases[b['logical_base_id']]['subtype_slot'] else 'ORDINARY_NEW_NEW'


def validate_scaffold_replay(bp, checks):
    groups = bp['comparison_scope']['scaffold_overlap']['classes']
    def require(ok, label):
        if not ok: raise ValueError(label)
        checks.append(label)
    # Synthetic five-gram tuples test exact set algebra without authoring content.
    shared = {(str(i), 'test', 'gram', 'shared', 'only') for i in range(3)}
    left_unique = {(str(i), 'test', 'gram', 'left', 'only') for i in range(11)}
    right_unique = {(str(i), 'test', 'gram', 'right', 'only') for i in range(11)}
    for group in groups:
        invariant = {tuple(g.split(' ')) for g in group['invariant_five_grams']}
        a, b = shared | left_unique, shared | right_unique
        # intersection=3, union=25; exactly 0.12 must reject.
        require(checking_residual(group, a | invariant, b | invariant) == 'REJECT_CONTAMINATION', 'residual_boundary_strict:' + group['class_id'])
        b = b | {('extra', 'test', 'gram', 'right', 'only')}
        require(checking_residual(group, a | invariant, b | invariant) == 'PERMITTED_DECLARED_SCAFFOLD', 'residual_below_boundary:' + group['class_id'])
        require(checking_residual(group, a, b) == checking_residual(group, a | invariant, b | invariant), 'residual_exact_frozen_subtraction:' + group['class_id'])
        for x, y, label in [(set(), set(), 'both'), (set(), a, 'left'), (a, set(), 'right')]:
            require(checking_residual(group, x | invariant, y | invariant) == 'AUTHORING_ERROR_EMPTY_RESIDUAL', 'residual_empty_' + label + ':' + group['class_id'])
        require(checking_residual(group, a | invariant, a | invariant) == 'REJECT_CONTAMINATION', 'residual_copy_rejected:' + group['class_id'])
    left, right = groups[0]['rendered_position_pairs'][0]
    facts = dict(historical=False, actual_structure_valid=True, pair_local_valid=True,
                 all_freshness_checks_pass=True, ordinary_grams_left=left_unique, ordinary_grams_right=right_unique)
    probes = [
        ('scaffold_valid', left, right, {}, 'PERMITTED_DECLARED_SCAFFOLD'),
        ('historical_never_subtract', left, right, {'historical': True, 'actual_structure_valid': False}, 'HISTORICAL_NEW'),
        ('structure_before_permission', left, right, {'actual_structure_valid': False}, 'AUTHORING_ERROR_STRUCTURE'),
        ('freshness_before_permission', left, right, {'all_freshness_checks_pass': False}, 'REJECT_FRESHNESS'),
        ('pair_local_intentional_sharing', 'A:R2:E5-01:PRIMARY:CF1', 'A:R2:E5-01:PRIMARY:CF2', {'all_freshness_checks_pass': False}, 'SAME_BASE_E5_PAIR_LOCAL'),
        ('invalid_pair_local', 'A:R2:E5-01:PRIMARY:CF1', 'A:R2:E5-01:PRIMARY:CF2', {'pair_local_valid': False}, 'AUTHORING_ERROR_STRUCTURE'),
        ('same_subtype_preserved', 'A:R2:E2-01:PRIMARY:SINGLE', 'B:R2:E2-01:PRIMARY:SINGLE', {}, 'DECLARED_SAME_SUBTYPE'),
        ('ordinary_preserved', 'A:R2:E2-01:PRIMARY:SINGLE', 'B:R2:E3-02:PRIMARY:SINGLE', {}, 'ORDINARY_NEW_NEW'),
    ]
    for label, a, b, changes, outcome in probes:
        require(checking_comparison_branch(bp, a, b, dict(facts, **changes)) == outcome, 'scaffold_precedence_replay:' + label)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    before = preservation_snapshot()
    c,helper,hashes=load_authority();expected=build(c,helper,hashes)
    if args.write:
        (HERE/'BLUEPRINT.json').write_bytes(encoded(expected))
        (HERE/'BLUEPRINT.md').write_text(markdown(expected),encoding='utf-8',newline='\n')
    if (HERE/'BLUEPRINT.json').read_bytes()!=encoded(expected):raise ValueError('blueprint_canonical_bytes_or_derivation_mismatch')
    actual=json.loads((HERE/'BLUEPRINT.json').read_text(encoding='utf-8'));checks=validate(actual,expected,c,helper)
    freshness_checks = validate_freshness_vectors(actual, c, helper, checks)
    whole_answer_checks = validate_whole_answer_vectors(actual, c, helper, checks)
    validate_scaffold_replay(actual, checks)
    validate_reserve_schedules(actual,c,checks)
    if (HERE/'BLUEPRINT.md').read_bytes()!=markdown(expected).encode():raise ValueError('human_machine_blueprint_mismatch')
    mutations=[('extra_top_key',lambda x:x.update(unauthorized_rule=True)),
               ('extra_cf2',lambda x:x['rendered_variants'].append(copy.deepcopy(next(v for v in x['rendered_variants'] if v['variant_id']=='CF2')))),
               ('e5_transition',lambda x:next(v for v in x['rendered_variants'] if v['variant_id']=='CF2').update(selector_index=2)),
               ('missing_cf2',lambda x:x['rendered_variants'].remove(next(v for v in x['rendered_variants'] if v['variant_id']=='CF2'))),
               ('ordinal',lambda x:x['logical_positions'][0].update(fixture_ordinal=168)),
               ('threshold',lambda x:x['cell_gate_specs']['phase_a']['e5_counterfactual_pairs'].update(minimum_correct_pairs=4)),
               ('recurrence_class',lambda x:x['recurrence_ledger']['fingerprint_classes'].pop(next(iter(x['recurrence_ledger']['fingerprint_classes'])))),
               ('gate_membership',lambda x:x['logical_positions'][0]['gate_membership'].update(false_clean=False)),
               ('seed',lambda x:x['schedule_plan']['phase_a'][0].update(seed=1)),
               ('b_eligibility',lambda x:x['schedule_plan']['phase_b_maximum_template'][0].update(cell_id='UNQUALIFIED:R2')),
               ('pair_exception_leakage',lambda x:x['comparison_scope'].update(pair_local_exception='all same-family pairs')),
               ('inserted_gold',lambda x:x['logical_positions'][0].update(gold_values={'x':1})),
               ('inserted_source',lambda x:x['logical_positions'][0].update(source_fact_records=[])),
               ('unauthorized_authority',lambda x:x['authority'].update(corpus_gold_authoring=True)),
               ('reserve',lambda x:x['reserve_map'][0].update(covered_subtype_slot='03'))] + scaffold_mutations() + freshness_plan_mutations() + whole_answer_plan_mutations()
    for label,change in mutations:
        bad=copy.deepcopy(actual);change(bad)
        try:validate(bad,expected,c,helper)
        except ValueError:checks.append('mutation_rejected:'+label)
        else:raise ValueError('mutation_accepted:'+label)
    output_mutations=[('required_false',lambda f:f.update(required=False)),
                      ('label_removal_true',lambda f:f.update(label_removal=True)),
                      ('missing_required',lambda f:f.pop('required')),
                      ('missing_label_removal',lambda f:f.pop('label_removal')),
                      ('embedded_output_role',lambda f:f.update(output_role='source_copy')),
                      ('wrong_binding_kind',lambda f:f.update(binding_kind='UNKNOWN')),
                      ('wrong_source_field',lambda f:f.update(source_field='f999_99')),
                      ('wrong_producer_target',lambda f:f.update(producer_target='d999_99')),
                      ('wrong_absence_capable',lambda f:f.update(absence_capable=not f['absence_capable'])),
                      ('wrong_schema_type',lambda f:f.update(schema_type='string' if f['schema_type']!='string' else 'number'))]
    keys=c['output_field_amendment_contract']['exact_output_field_keys']
    for p in actual['logical_positions']:
        for field in p['schema_plan']['output_fields']:
            for label,change in output_mutations:
                bad=copy.deepcopy(field);change(bad)
                try:check_output_object(bad,field,keys)
                except ValueError:checks.append('output_mutation_rejected:'+p['logical_base_id']+':'+field['name']+':'+label)
                else:raise ValueError('output_mutation_accepted:'+label)
    if {p.name for p in HERE.iterdir()}-set(FILES):raise ValueError('unexpected_blueprint_file')
    if (HERE/'.gitattributes').read_bytes()!=b'*.json text eol=lf\n*.md text eol=lf\n*.py text eol=lf\n.gitattributes text eol=lf\n':
        raise ValueError('blueprint_line_ending_policy_mismatch')
    checks.append('blueprint_local_lf_policy')
    history={}
    for filename,key in [('G_ROUTE4_CLOSURE.json','closure_sha256'),('PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json','diagnostic_sha256')]:
        path=ROOT/'experiments/G-ROUTE4-candidate/closure'/filename
        if digest(path.read_bytes())!=c['historical_binding'][key]:raise ValueError('historical_digest_mismatch')
        history[filename]=digest(path.read_bytes())
    positions=actual['logical_positions'];variants=actual['rendered_variants']
    primary_ids={p['logical_base_id'] for p in positions if p['primary_or_reserve']=='PRIMARY'}
    scored_e5=sum(p['logical_base_id'] in primary_ids and p['family']=='E5' for p in positions)
    reserve_e5=sum(p['logical_base_id'] not in primary_ids and p['family']=='E5' for p in positions)
    rendered_scored=sum(v['logical_base_id'] in primary_ids for v in variants)
    total_pairs=len(variants)*(len(variants)-1)//2
    pair_local=scored_e5+reserve_e5
    counts=dict(scored_logical=len(primary_ids),reserve_logical=len(positions)-len(primary_ids),total_logical=len(positions),
                scored_rendered=rendered_scored,reserve_rendered=len(variants)-rendered_scored,total_rendered=len(variants),
                scored_e5_pairs=scored_e5,reserve_e5_pairs=reserve_e5,
                fingerprint_classes=len(actual['recurrence_ledger']['fingerprint_classes']),
                subtype_groups=len(actual['recurrence_ledger']['subtype_template_groups']),
                logical_comparisons=len(positions)*(len(positions)-1)//2,
                rendered_comparisons=total_pairs,pair_local_scopes=pair_local,cross_base_comparisons=total_pairs-pair_local,
                historical_rendered_comparisons=106*len(variants),
                phase_a_calls=len(actual['schedule_plan']['phase_a']),phase_b_maximum_calls=len(actual['schedule_plan']['phase_b_maximum_template']),
                reserve_maps=len(actual['reserve_map']))
    gate_counts={}
    for phase in ('A','B'):
        gate_counts[phase]={}
        for risk in ('R2','R3'):
            cell=[p for p in positions if p['logical_base_id'] in primary_ids and p['phase']==phase and p['risk_round']==risk]
            membership={key:sum(p['gate_membership'][key] for p in cell) for key in cell[0]['gate_membership']}
            membership.update(rendered_variants=sum(sum(v['logical_base_id']==p['logical_base_id'] for v in variants) for p in cell),
                              provider_observations=80 if phase=='A' else 40,e5_observations=20 if phase=='A' else 10,e7_observations=10 if phase=='A' else 5)
            gate_counts[phase][risk]=membership
    _,output_counts=validate_output_plans(actual,c)
    prior_report=json.loads(git('show', WHOLE_PRIOR_BLUEPRINT + ':experiments/G-EXTRACT1-candidate/blueprint/BLUEPRINT_VALIDATION_REPORT.json'))
    if counts != prior_report['counts'] or output_counts != prior_report['output_field_counts']:
        raise ValueError('prior_blueprint_counts_changed')
    checks.append('all_prior_blueprint_counts_unchanged')
    _,scaffold_audit=validate_scaffold(actual,c)
    historical_adapter=helper.historical_adaptation_summary(c)
    accepted_adapter=json.loads((DESIGN/'DESIGN_VALIDATION_REPORT.json').read_bytes())['historical_adapter']
    if historical_adapter != accepted_adapter or (historical_adapter['examined'], historical_adapter['adapted'], historical_adapter['rejected']) != (106,106,0):
        raise ValueError('historical_adapter_changed')
    checks.append('historical_adapter_106_unchanged')
    after = preservation_snapshot()
    if before != after: raise ValueError('protected_corpus_gold_or_design_changed_during_rebind')
    checks.append('ten_corpus_artifacts_gold_and_six_design_artifacts_byte_identical_before_after')
    report=dict(schema_version='g-extract1.blueprint-validation.v1', verdict='PASS',check_count=len(checks),
                validation_scope='deterministic structural/design-equivalence only; not scientific or corpus approval',
                accepted_design_commit=ACCEPTED, scientific_validity_proven=False,
                counts=counts,gate_membership_counts=gate_counts,output_field_counts=output_counts,
                amendment_binding=actual['accepted_design'],
                freshness_serialization_audit=freshness_checks,
                whole_answer_serialization_audit=whole_answer_checks,
                preservation_evidence=dict(before=before, after=after, all_byte_identical=True,
                                           corpus_content_used_for_rule_choice=False, corpus_rescored=False,
                                           corpus_checkers_repaired=False, corpus_finalized=False),
                design_checker_scope='accepted 3bf939 historical blueprint guard preserved unchanged; only isolated accepted helpers loaded, not standalone design checkpoint validation',
                all_non_output_allocations_equal_original_blueprint=True,
                all_prior_blueprint_allocations_preserved=True,
                scaffold_comparison_audit=scaffold_audit,
                historical_adapter=historical_adapter,
                design_side_artifacts_changed=False,
                blueprint_mutation_categories=[label for label,_ in mutations],
                output_mutation_categories=[label for label,_ in output_mutations],
                output_mutations_checked=output_counts['logical_output_definitions']*len(output_mutations),
                equivalence_report=actual['scientific_traceability'],
                seed_collision_audit='PASS: only same-model/base/repeat CF1/CF2 sharing',phase_b_qualified_cell_subsets_checked=64,
                reserve_schedule_cases_checked=29,
                source_artifact_hashes=hashes,historical_hashes=history,checks=checks,
                artifacts_sha256={name:digest((HERE/name).read_bytes()) for name in FILES if name!='BLUEPRINT_VALIDATION_REPORT.json'},
                authority=actual['authority'],governance=actual['governance'])
    if args.write:(HERE/'BLUEPRINT_VALIDATION_REPORT.json').write_bytes(encoded(report))
    elif json.loads((HERE/'BLUEPRINT_VALIDATION_REPORT.json').read_text())!=report:raise ValueError('validation_report_stale')
    print(json.dumps({key:report[key] for key in ('verdict','check_count','counts','seed_collision_audit')},indent=2))


if __name__=='__main__':
    main()
