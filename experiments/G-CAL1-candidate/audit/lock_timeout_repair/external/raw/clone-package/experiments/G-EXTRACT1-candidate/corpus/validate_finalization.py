"""Offline immutable-candidate finalization. No authoring or provider transport."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import itertools
import json
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
ROOT = DESIGN.parent.parent
CORRECTION = '7b80ae041c74af9965662ea1aaf0d374950640f4'
PRIOR_PACKAGE = 'a276c73ba5b89d944997a6a82cba4508729653c8'
CHECKER_PARENT = 'b7fd33eacbd46df7be5274a0e3d5e2dbe34efe1a'
CANDIDATE_SHA = 'f575c8d86ca82f2c5ea7727404d0c8bbb5a72f7b472abfd244471edb3180d068'
GOLD_SHA = '803e8e4c57b63c7edb22f02194cbefdbf6be3fc964a0d77f65faa658f8904aec'
CHECKER_NAMES = ('validate_corpus.py','independent_contamination.py')
ADDITIONS = ({'tuple_applicability','historical_evidence','historical_pair','differential_record'},
             {'tuple_scope_record','historical_record','historical_pair_result','differential_record'})
PRESERVED = {
    'AUTHORING_ATTEMPTS.json':'b9860b6bd4f662c46935773463bf6caf78035a1c2aa01c0b6a55e5100b9aa8da',
    'AUTHORING_CANDIDATES.json':CANDIDATE_SHA,
    'AUTHORING_FEASIBILITY_REPORT.json':'8767a025c1123541cc858873aff41b60ecc1f8b0186d72ccc738761a24771433',
    'FINALIZATION_FAILURE_REPORT.json':'588b6141e3c25b561dff49d7b004ca508468ed39f4dbef8a8e16c54f69918730',
    'FRESHNESS_CANONICALIZATION_DIAGNOSIS_REPORT.json':'7395408dcf283821d19ed81f6986d64c47b4d31f9dd76d1c72481f7dff48a442',
    'FINALIZATION_CONTAMINATION_DISAGREEMENT_REPORT.json':'d9ff96223d36cd2c92d92361be028820d6955b82712f1ed2152178958c8765dc',
    'FINALIZATION_HISTORICAL_REUSE_CONTRACT_STOP_REPORT.json':'a011317172165d16569a78a975b861e8ccb7c374a68248da23f9c47498a8984d',
    'FRESHNESS_CHECKER_REPAIR_REPORT.json':'3c57078b5ea88b5fc994252cec52307e5b213969797eaa222bb623ef989e262f',
    'WHOLE_ANSWER_CHECKER_REPAIR_REPORT.json':'a9c5bc5533b2e3d61025576fd91b1f1e57cd2d74c4db675147e3df7a9a2e94a9',
    'validate_freshness_repair.py':'9d66678d1fa8b62e820b25cc50305ba91ed112d6add57d63f9f5dc734bea70ae',
    'validate_whole_answer_repair.py':'a389c97681e9630ea4f0c7aa102a02dff76def320412f0dc455eeeb6ff0ab513',
}
FINAL_NAMES = ('SCORED_CORPUS.json','RESERVE_CORPUS.json','GOLD.json','CONTAMINATION_REPORT.json',
               'GOLD_DERIVATION_REPORT.json','E5_REQUEST_INVARIANCE_REPORT.json','CORPUS_VALIDATION_REPORT.json','CORPUS_MANIFEST.json',
               'ELAPSED_REQUEST_ENTAILMENT_REPORT.json','INTERMEDIATE_DIFFERENTIAL_REPORT.json',
               'MUTATION_CERTIFICATION_REPORT.json','CORPUS_GOLD_REVIEW_CLOSURE.json')
GOVERNANCE = dict(provider_model_calls=0, corpus_regeneration=0, gold_modifications=0,
    runtime_implementation=False, mechanical_pilot_authorized=False, execution_freeze_authorized=False,
    phase_a_authorized=False, phase_b_authorized=False, execution='none', autonomy=False,
    G_ROUTE4='CLOSED FAILED unchanged', belief_effects='none', external_gold_review='NOT YET PERFORMED')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def packed(obj): return (json.dumps(obj,ensure_ascii=True,indent=2,sort_keys=True)+'\n').encode()


def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def require(ok,label,checks):
    if not ok: raise ValueError(label)
    checks.append(label)


def snapshot():
    hashes={n:sha((HERE/n).read_bytes()) for n in PRESERVED}
    if hashes != PRESERVED:raise ValueError('immutable_authoring_or_failure_evidence_changed')
    candidates=json.loads((HERE/'AUTHORING_CANDIDATES.json').read_bytes())
    gold=[[r['logical_base_id'],r['fixture']['gold_values']] for r in candidates['accepted']]
    gold_hash=sha(json.dumps(gold,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode())
    if gold_hash != GOLD_SHA:raise ValueError('immutable_gold_changed')
    authority={}
    for path in list(DESIGN.glob('*'))+list((DESIGN/'blueprint').glob('*')):
        if path.is_file() and path.suffix in {'.json','.md','.py'}:
            relative=path.relative_to(ROOT).as_posix()
            if path.read_bytes() != git('show',CORRECTION+':'+relative):raise ValueError('corrected_authority_changed:'+relative)
            authority[relative]=sha(path.read_bytes())
    return dict(preserved=hashes,gold_projection_sha256=gold_hash,corrected_authority_sha256=authority,
        checkers_sha256={n:sha((HERE/n).read_bytes()) for n in CHECKER_NAMES})


def checker_scope():
    result={}
    for name,additions in zip(CHECKER_NAMES,ADDITIONS):
        path=HERE/name
        old=ast.parse(git('show',CHECKER_PARENT+':'+path.relative_to(ROOT).as_posix()).decode('utf-8-sig'))
        now=ast.parse(path.read_text(encoding='utf-8-sig'))
        old_names={n.name for n in old.body if isinstance(n,ast.FunctionDef)}
        new_names={n.name for n in now.body if isinstance(n,ast.FunctionDef)}
        if new_names-old_names != additions:raise ValueError('checker_addition_scope:'+name)
        now.body=[n for n in now.body if not(isinstance(n,ast.FunctionDef) and n.name in additions)]
        if ast.dump(old,include_attributes=False) != ast.dump(now,include_attributes=False):
            raise ValueError('prior_checker_mechanics_changed:'+name)
        result[name]=dict(only_added_functions=sorted(additions),every_prior_AST_node_unchanged=True)
    return result


def replay_repairs():
    w=load('whole_replay',HERE/'validate_whole_answer_repair.py')
    original_snapshot=w.snapshot;original_git=w.git_bytes
    def rebound_snapshot():
        snapshot();report_reads=0
        def rebound_bytes(commit,path):
            nonlocal report_reads
            if commit in {w.DESIGN_COMMIT,w.BLUEPRINT_COMMIT}:
                if path == DESIGN/'DESIGN_VALIDATION_REPORT.json':
                    report_reads+=1
                    if report_reads == 1:return original_git(commit,path)
                if path.parent in {DESIGN,DESIGN/'blueprint'}:return path.read_bytes()
            return original_git(commit,path)
        w.git_bytes=rebound_bytes
        try:return original_snapshot()
        finally:w.git_bytes=original_git
    w.snapshot=rebound_snapshot
    w.scope_audit=checker_scope
    report=w.validate()
    previous=json.loads((HERE/'WHOLE_ANSWER_CHECKER_REPAIR_REPORT.json').read_bytes())
    for key in ('checks','check_count','base_results','variant_results','semantic_vector_results',
                'mutation_results','historical_encoding_results','original_failure_replay'):
        if report[key]!=previous[key]:raise ValueError('prior_whole_result_changed:'+key)
    if report['check_count']!=1828 or report['freshness_certification']['check_count']!=811:
        raise ValueError('repair_suite_count_changed')
    return dict(whole_answer_checks=1828,freshness_checks=811,logical_bases=168,rendered_variants=192,
        historical_answers=106,disagreements=0,all_prior_behavioral_results_exact=True,
        lineage_method='Original behavioral bodies unchanged; obsolete authority snapshots rebound in memory after exact design/blueprint projection validation and addition-only checker AST audit.',
        original_failure_replay=report['original_failure_replay'])


def independent_gold(f,i,c,p):
    nodes,derived,resolve,_,_=i.evaluate(f,c)
    gold={}
    for out in f['output_fields']:
        if out['binding_kind']=='EXPLICIT_ABSENCE':value='not_provided'
        elif out['binding_kind']=='SOURCE_COPY':value=resolve(dict(kind='field_identifier',value=out['source_field']))[1]
        else:value=derived[out['producer_target']][1]
        t=i.schema_tag(out['schema_type'])
        if t=='INTEGER':value=int(value)
        elif t=='NUMBER':value=i.decimal(value)
        elif t=='DATE':value=value.isoformat()
        elif t=='TIME':value=f'{value//60:02d}:{value%60:02d}'
        gold[out['name']]=value
    return gold,dict(nodes=[dict(target=n['target'],operation=n['id'],semantic_type=derived[n['target']][0],
        canonical_value=gold.get(n['target'],i.canon(*derived[n['target']]))) for n in nodes])


def applicability_tests(p,i,checks):
    c=p.C;d=p.D
    current=d.validate_review_closure_design(c,(DESIGN/'DESIGN_CANDIDATE.md').read_text(encoding='utf-8'))
    for scope,status in d.TUPLE_APPLICABILITY['scope_status'].items():
        require(p.tuple_applicability(scope)==i.tuple_scope_record(scope,c),'dual_applicability:'+scope,checks)
        require(p.tuple_applicability(scope)['status']==status,'status:'+scope,checks)
    mutants=[]
    for status in ('PASS','FAIL'):
        x=copy.deepcopy(c);x['date_number_tuple_applicability_contract']['scope_status']['historical_new']=status
        mutants.append(('historical_'+status,x))
    for name in c['date_number_tuple_applicability_contract']['prohibited_surrogates']:
        x=copy.deepcopy(c);x['date_number_tuple_applicability_contract']['historical_tuple_bytes']=name
        mutants.append((name,x))
    for key in ('atom','serialization','match_rule'):
        x=copy.deepcopy(c);x['contamination_contract']['exact_reuse_contract']['date_number_tuple'][key]='altered'
        mutants.append(('new_tuple_'+key,x))
    for scope in ('phase_a_phase_a','phase_a_phase_b','phase_b_phase_b','scored_reserve','reserve_reserve'):
        x=copy.deepcopy(c);x['date_number_tuple_applicability_contract']['scope_status'][scope]='DISABLED'
        mutants.append(('disabled_'+scope,x))
    x=copy.deepcopy(c);x['date_number_tuple_applicability_contract']['other_historical_controls']=[]
    mutants.append(('other_historical_disabled',x))
    x=copy.deepcopy(c);x['date_number_tuple_applicability_contract']['authority']['phase_a']=True
    mutants.append(('authority_elevated',x))
    for label,mutant in mutants:
        try:d.validate_tuple_applicability(mutant,(DESIGN/'DESIGN_CANDIDATE.md').read_text(encoding='utf-8'))
        except (ValueError,AssertionError):checks.append('actual_contract_mutation_rejected:'+label)
        else:raise ValueError('contract_mutation_survived:'+label)
    # Exercise the plural-fixture tuple vector omitted in the narrow design report.
    for v in c['contamination_contract']['exact_reuse_contract']['fixture_tuple_extraction_vectors']:
        if 'fixtures' in v:
            atoms=[d.extract_date_number_atoms(f,c['operation_definition_contract'],c['schema_type_contract'],c['operation_semantics_contract'],c['entity_population_contract']) for f in v['fixtures']]
            require([x[0][1:] for x in atoms]==v['expected_atoms_by_fixture'],'plural_tuple_schema_typing_vector',checks)
    return current


def bound_inputs(p):
    disk = json.loads((DESIGN/'blueprint/BLUEPRINT.json').read_bytes())
    if p.B['recurrence_ledger'] != disk['recurrence_ledger']:
        raise ValueError('bound_recurrence_memory_drift')
    if p.B != disk or p.POSITIONS != {r['logical_base_id']:r for r in disk['logical_positions']}:
        raise ValueError('bound_blueprint_memory_drift')
    expected = {frozenset(pair):row for row in disk['comparison_scope']['scaffold_overlap']['classes']
                for pair in row['rendered_position_pairs']}
    if p.SCAFFOLD != expected:
        raise ValueError('bound_scaffold_memory_drift')
    if p.C != json.loads((DESIGN/'DESIGN_CANDIDATE.json').read_bytes()):
        raise ValueError('bound_design_memory_drift')


def certify_intermediates(p,i,fixture,request,record_id,historical,checks):
    left = p.differential_record(fixture,request,p.C,historical)
    right = i.differential_record(fixture,request,p.C,historical)
    stage = 'projection' if historical else 'fingerprint'
    require(left['normalized_payload_bytes'] == right['normalized_payload_bytes'],
            'differential_normalized_payload:'+record_id,checks)
    require(left['token_sequence'] == right['token_sequence'] and
            left['token_sequence_bytes'] == right['token_sequence_bytes'],
            'differential_token_sequence:'+record_id,checks)
    require(left['structural_bytes'] == right['structural_bytes'],
            'differential_'+stage+'_bytes:'+record_id,checks)
    return dict(record_id=record_id,scope='HISTORICAL' if historical else 'NEW',
        direct_normalized_payload_equality=True,direct_token_sequence_equality=True,direct_structural_byte_equality=True,
        normalized_payload_sha256=sha(left['normalized_payload_bytes']),
        token_sequence_sha256=sha(left['token_sequence_bytes']),structural_kind=stage,
        **{stage+'_sha256':sha(left['structural_bytes'])})


def request_entailment_report(p,i,rendered,checks):
    prior = {}
    for name in ('SCORED_CORPUS.json','RESERVE_CORPUS.json'):
        old = json.loads(git('show',PRIOR_PACKAGE+':'+(HERE/name).relative_to(ROOT).as_posix()))
        prior.update({r['rendered_variant_id']:r for r in old['rendered_variants']})
    encode = lambda obj:json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    convention = p.C['corpus_gold_review_closure_contract']['elapsed_minutes']['exact_convention_text']
    suffix = p.C['baseline_binding']['structured_extraction_assembled_template'].replace('{SUBJECT}','')
    changes = [];unchanged = []
    for row in rendered:
        old = prior[row['rendered_variant_id']];fixture=row['fixture']
        require(fixture == old['fixture'] and row['gold'] == old['gold'],
                'prior_fixture_and_gold_exact:'+row['rendered_variant_id'],checks)
        require(encode(row['request']['input']) == encode(old['request']['input']),
                'prior_input_and_schema_bytes_exact:'+row['rendered_variant_id'],checks)
        nodes = [n for n in fixture['operation_nodes'] if n['id']=='ELAPSED_MINUTES']
        expected = copy.deepcopy(old['request'])
        if nodes:
            require(expected['prompt'].endswith(suffix),'elapsed_old_suffix:'+row['rendered_variant_id'],checks)
            expected['prompt'] = expected['prompt'][:-len(suffix)]+'. '+convention[:-1]+suffix
        require(encode(row['request']) == encode(expected),'only_permitted_request_delta:'+row['rendered_variant_id'],checks)
        if not nodes:
            unchanged.append(row['rendered_variant_id']);continue
        _,_,resolve,_,_ = i.evaluate(fixture,p.C)
        start=resolve(nodes[0]['arguments']['start'])[1];end=resolve(nodes[0]['arguments']['end'])[1]
        result=(end-start)%1440;gold=fixture['gold_values'][next(f['name'] for f in fixture['output_fields'] if f['producer_target']==nodes[0]['target'])]
        require(result == gold and 0 <= result <= 1439 and row['request']['prompt'].count(convention)==1,
                'elapsed_one_cycle_entailment:'+row['rendered_variant_id'],checks)
        changes.append(dict(base_id=row['logical_base_id'],rendered_variant_id=row['rendered_variant_id'],operation='ELAPSED_MINUTES',
            convention_text=convention,start=f'{start//60:02d}:{start%60:02d}',end=f'{end//60:02d}:{end%60:02d}',
            derived_gold=result,existing_gold=gold,entailment_check='PASS_EXPLICIT_FORWARD_CYCLE',
            excluded_additional_day_answer=result+1440,
            old_request_sha256=sha(encode(old['request'])),new_request_sha256=sha(encode(row['request'])),
            unaffected_fixture_data_sha256=sha(encode(fixture)),input_schema_sha256=sha(encode(row['request']['input']))))
    require(len(changes)==12 and len(unchanged)==180 and all(':E2-0' in r['base_id'] and ':PRIMARY' in r['base_id'] for r in changes),
            'exact_twelve_elapsed_and_180_unchanged',checks)
    return dict(verdict='PASS',prior_package=PRIOR_PACKAGE,request_hash_encoding='UTF-8 JSON ensure_ascii=false sort_keys=true compact no newline',
        exact_convention_text=convention,affected_count=len(changes),affected_requests=changes,unaffected_count=len(unchanged),
        unaffected_request_ids=unchanged,gold_projection_sha256=GOLD_SHA,source_candidate_sha256=CANDIDATE_SHA,
        facts_schemas_values_entities_selectors_and_gold_unchanged=True,provider_model_calls=0)


def approval_record(required=False):
    path = HERE/'REVIEW_CLOSURE_PREPUBLICATION_AUDIT.json'
    if not path.exists():
        if required:raise ValueError('independent_prepublication_audit_missing')
        return None
    record = json.loads(path.read_bytes())
    if record['verdict'] != 'PASS' or not record['independent'] or not all(record['closure_checks'].values()):
        raise ValueError('independent_prepublication_audit_failed')
    for relative,expected in record['implementation_and_authority_sha256'].items():
        if sha((ROOT/relative).read_bytes()) != expected:
            raise ValueError('independent_audit_source_drift:'+relative)
    return record


def real_path_mutations(p,i,replay):
    results=[]
    first=p.B['rendered_variants'][0]['rendered_variant_id']
    cases=[('normalized_punctuation','differential_normalized_payload:'+first),
           ('token_sequence','differential_token_sequence:'+first),
           ('fingerprint_bytes','differential_fingerprint_bytes:'+first),
           ('scaffold_class','bound_scaffold_memory_drift'),
           ('scaffold_member','bound_scaffold_memory_drift'),
           ('scaffold_invariant','bound_scaffold_memory_drift'),
           ('recurrence_member','bound_recurrence_memory_drift')]
    for label,expected in cases:
        old_payload=i.payload;old_differential=i.differential_record;old_scaffold=p.SCAFFOLD;old_blueprint=p.B
        try:
            if label=='normalized_punctuation':
                i.payload=lambda request,historical=False:old_payload(request,historical)+'!'
            elif label in {'token_sequence','fingerprint_bytes'}:
                def altered(*args,**kwargs):
                    out=old_differential(*args,**kwargs)
                    if label=='token_sequence':
                        out['token_sequence']=out['token_sequence']+['mutation']
                        out['token_sequence_bytes']=json.dumps(out['token_sequence'],ensure_ascii=False,separators=(',',':')).encode()
                    else:out['structural_bytes']=out['structural_bytes']+b' '
                    return out
                i.differential_record=altered
            elif label.startswith('scaffold'):
                p.SCAFFOLD=copy.deepcopy(p.SCAFFOLD)
                row=next(iter(p.SCAFFOLD.values()))
                if label=='scaffold_class':row['class_id']='MUTATED'
                elif label=='scaffold_member':row['rendered_position_pairs'].append(['MUTATED','MEMBER'])
                else:row['invariant_five_grams'].append('mutated invariant five gram bytes')
            else:
                p.B=copy.deepcopy(p.B)
                next(iter(p.B['recurrence_ledger']['fingerprint_classes'].values()))['members'].append('MUTATED')
            try:run_finalization(p,i,replay,certify_real=False)
            except ValueError as error:
                if str(error)!=expected:raise ValueError('incidental_mutation_failure:'+label+':'+str(error)) from error
                results.append(dict(mutation=label,classification='REAL_FINALIZATION_PATH',rejected=True,targeted_rejection=str(error)))
            else:raise ValueError('real_path_mutation_survived:'+label)
        finally:
            i.payload=old_payload;i.differential_record=old_differential;p.SCAFFOLD=old_scaffold;p.B=old_blueprint
    return results


def certify_mutations(p,i,bases,variants,checks):
    results=[]
    def rejects(label,call):
        try:call()
        except (ValueError,AssertionError,KeyError,TypeError,IndexError):
            results.append(dict(mutation=label,rejected=True));checks.append('mutation:'+label)
        else:raise ValueError('mutation_survived:'+label)
    def mutated_fixture(label,base,change,position_change=None):
        f=copy.deepcopy(bases[base]);pos=copy.deepcopy(p.POSITIONS[base]);change(f)
        if position_change:position_change(pos)
        rejects(label,lambda:p.check_fixture(f,pos))
    one='A:R2:E3-01:PRIMARY';e4='A:R2:E4-01:PRIMARY';e7='A:R2:E7-01:PRIMARY';e5='A:R2:E5-01:PRIMARY'
    mutated_fixture('wrong_gold',one,lambda f:f['gold_values'].update({f['output_fields'][0]['name']:0}))
    mutated_fixture('wrong_schema',one,lambda f:f['output_fields'][0].update(schema_type='string'))
    mutated_fixture('wrong_family',one,lambda f:f['lexical_context'].update(primary_family_slot='E4'))
    mutated_fixture('wrong_subtype',one,lambda f:None,lambda pos:pos.update(subtype=dict(pos['subtype'],slot_id='E3-02')))
    mutated_fixture('wrong_operation',one,lambda f:f['operation_nodes'][0].update(id='DIVIDE'))
    mutated_fixture('wrong_E4_truth',e4,lambda f:f['gold_values'].update({f['output_fields'][0]['name']:not f['gold_values'][f['output_fields'][0]['name']]}))
    mutated_fixture('wrong_E5_selector',e5,lambda f:f['operation_nodes'][0]['arguments']['selector_value'].update(value='Entity 999 A'))
    mutated_fixture('wrong_E7_absence_placement',e7,lambda f:f['source_fact_records'].reverse())
    mutated_fixture('wrong_absence_gold',e7,lambda f:f['gold_values'].update({next(x['name'] for x in f['output_fields'] if x['binding_kind']=='EXPLICIT_ABSENCE'):'provided'}))
    mutated_fixture('value_shape_mismatch',one,lambda f:f['source_fact_records'][0]['value'].update(value='1'))
    mutated_fixture('label_removal_true',one,lambda f:f['output_fields'][0].update(label_removal=True))
    mutated_fixture('required_false',one,lambda f:f['output_fields'][0].update(required=False))
    mutated_fixture('wrong_fingerprint',one,lambda f:None,lambda pos:pos['recurrence']['planned_six_components'].__setitem__(3,'ABOVE'))
    slot=lambda pos:dict(pos['subtype'],phase=pos['phase'],risk_round=pos['risk_round'])
    members=p.D.counterfactual_members(bases[e5],slot(p.POSITIONS[e5]),p.C)
    same_gold=copy.deepcopy(members[1]);same_gold['gold_values']=copy.deepcopy(members[0]['gold_values'])
    rejects('identical_E5_gold',lambda:p.D.audit_counterfactual(members[0],same_gold,slot(p.POSITIONS[e5]),p.C,p.C['model_provider']['models'][0]['model'],1))
    altered=copy.deepcopy(members[1]);altered['source_fact_records'][0]['value']['value']='label_999_01'
    rejects('nonselector_E5_request_difference',lambda:p.D.audit_counterfactual(members[0],altered,slot(p.POSITIONS[e5]),p.C,p.C['model_provider']['models'][0]['model'],1))
    a,b=next((copy.deepcopy(x),copy.deepcopy(y)) for x,y in itertools.combinations(variants,2) if x['base']!=y['base'] and x['tuple'] and y['tuple'])
    for key,label in [('raw_payload','raw_payload_replay'),('raw_values','freshness_replay'),('answer','whole_answer_replay'),('tuple','date_number_replay')]:
        x=copy.deepcopy(a);y=copy.deepcopy(b);y[key]=x[key]
        require(p.pair_decision(x,y)[0]=='FAIL' and i.independent_pair(x,y,p.SCAFFOLD)[0]=='FAIL','dual_mutation:'+label,checks)
        results.append(dict(mutation=label,rejected=True,dual_checker=True))
    x=copy.deepcopy(a);y=copy.deepcopy(b);x['identities']={'["IDENTIFIER","same"]'};y['identities']=set(x['identities'])
    require(p.pair_decision(x,y)[0]=='FAIL' and i.independent_pair(x,y,p.SCAFFOLD)[0]=='FAIL','dual_mutation:identity_replay',checks)
    results.append(dict(mutation='identity_replay',rejected=True,dual_checker=True))
    # Wrong membership/gram certificates reject against the frozen blueprint before pair evaluation.
    def scaffold_guard(candidate):
        expected={frozenset(pair):row for row in p.B['comparison_scope']['scaffold_overlap']['classes'] for pair in row['rendered_position_pairs']}
        if candidate!=expected:raise ValueError('scaffold_certificate_drift')
    for label in ('wrong_scaffold_class','wrong_invariant_gram'):
        mapping=copy.deepcopy(p.SCAFFOLD);row=next(iter(mapping.values()))
        if label=='wrong_scaffold_class':row['class_id']='wrong'
        else:row['invariant_five_grams'].append('wrong invariant gram here now')
        rejects(label,lambda:scaffold_guard(mapping))
    pair,row=next(iter(p.SCAFFOLD.items()));ids=list(pair);cache={v['id']:v for v in variants}
    for label,boundary in [('empty_residual',False),('residual_at_threshold',True)]:
        x=copy.deepcopy(cache[ids[0]]);y=copy.deepcopy(cache[ids[1]])
        invariant={tuple(g.split(' ')) for g in row['invariant_five_grams']}
        shared={(str(k),'mutation','shared','gram','only') for k in range(3)}
        left={(str(k),'mutation','left','gram','only') for k in range(11)}
        right={(str(k),'mutation','right','gram','only') for k in range(11)}
        x['ordinary']=invariant|(shared|left if boundary else set());y['ordinary']=invariant|shared|right
        require(p.pair_decision(x,y)[0]=='FAIL' and i.independent_pair(x,y,p.SCAFFOLD)[0]=='FAIL','dual_mutation:'+label,checks)
        results.append(dict(mutation=label,rejected=True,dual_checker=True))
    # Collision outside the scaffold/same-subtype branches.
    x,y=next((copy.deepcopy(x),copy.deepcopy(y)) for x,y in itertools.combinations(variants,2) if x['base']!=y['base'] and x['slot']!=y['slot'] and frozenset([x['id'],y['id']]) not in p.SCAFFOLD)
    y['ordinary']=set(x['ordinary']);y['fp']=copy.deepcopy(x['fp'])
    require(p.pair_decision(x,y)[0]=='FAIL' and i.independent_pair(x,y,p.SCAFFOLD)[0]=='FAIL','dual_mutation:contamination_collision',checks)
    results.append(dict(mutation='contamination_collision',rejected=True,dual_checker=True))
    # Actual profile validation rejects content/schema drift before byte comparison.
    reserve=p.B['reserve_map'][0];rf=copy.deepcopy(bases[reserve['reserve_base_id']]);rf['output_fields'][0]['schema_type']='number'
    rejects('wrong_reserve_profile',lambda:p.D.reserve_profile_bytes(rf,slot(p.POSITIONS[reserve['reserve_base_id']]),p.C,True))
    planned=p.B['recurrence_ledger']['fingerprint_classes']
    actual={k:list(v['members']) for k,v in planned.items()};key=next(iter(actual));actual[key].append('extra')
    def recurrence_guard(rows):
        if any(sorted(rows[k])!=sorted(planned[k]['members']) for k in planned):raise ValueError('recurrence_overflow_or_membership')
    rejects('recurrence_overflow',lambda:recurrence_guard(actual))
    # Both encoders reject scalar, tag, text and byte-serializer mutations.
    for label,rows,raw in [
        ('wrong_freshness_schema_type',[['integer','0']],b'[["INTEGER","0"]]'),
        ('wrong_freshness_canonical_text',[['number','5.0']],b'[["number","5.0"]]'),
        ('freshness_scalar',[['integer','0']],b'[["integer",0]]'),
        ('freshness_ensure_ascii_drift',[['string','\u00e9']],b'[["string","\\u00e9"]]')]:
        rejects('primary_'+label,lambda:p.require_freshness_bytes(raw,rows))
        rejects('independent_'+label,lambda:i.require_freshness_bytes(raw,rows,p.C))
    rows=[['field','boolean',True]]
    for label,raw in [('whole_answer_Boolean_scalar',b'[["field","boolean",["BOOLEAN",true]]]'),
        ('wrong_whole_answer_tag',b'[["field","boolean",["STRING","true"]]]'),
        ('wrong_whole_answer_text',b'[["field","boolean",["BOOLEAN","True"]]]')]:
        rejects('primary_'+label,lambda:p.require_whole_answer_bytes(raw,rows))
        rejects('independent_'+label,lambda:i.require_whole_answer_bytes(raw,rows,p.C))
    unicode_rows=[['field','string','\u00e9']];raw=json.dumps([['field','string',['STRING','\u00e9']]],ensure_ascii=False,separators=(',',':')).encode()
    rejects('primary_whole_ensure_ascii_drift',lambda:p.require_whole_answer_bytes(raw,unicode_rows))
    rejects('independent_whole_ensure_ascii_drift',lambda:i.require_whole_answer_bytes(raw,unicode_rows,p.C))
    return results


def run_finalization(p,i,replay,certify_real=True):
    checks=[];before=snapshot();bound_inputs(p);checker_scope();applicability_tests(p,i,checks)
    candidates=json.loads((HERE/'AUTHORING_CANDIDATES.json').read_bytes())
    bases={r['logical_base_id']:r['fixture'] for r in candidates['accepted']}
    require(len(bases)==len(candidates['accepted'])==168 and set(bases)==set(p.POSITIONS),'168_exact_bases',checks)
    require(len(candidates['failed_attempts'])==480 and max(r['attempt'] for r in candidates['accepted'])==194,'authoring_history_preserved',checks)
    traces=[];variants=[];rendered=[];e5_audits=[];class_members=defaultdict(list);family_counts=Counter();output_count=0
    differential_records=[]
    e4=defaultdict(list);e7=[]
    for pos in p.B['logical_positions']:
        base=pos['logical_base_id'];f=bases[base];slot=dict(pos['subtype'],phase=pos['phase'],risk_round=pos['risk_round'])
        fp=p.check_fixture(f,pos)
        g1,t1=p.independent_gold(f);g2,t2=independent_gold(f,i,p.C,pos)
        require(g1==g2==f['gold_values'],'two_independent_gold:'+base,checks)
        require(i.fingerprint(f,p.C)==fp,'independent_base_fingerprint:'+base,checks)
        class_id=sha(p.compact(fp).encode())
        require(class_id==pos['recurrence']['fingerprint_class'],'actual_recurrence_class:'+base,checks)
        class_members[class_id].append(base);family_counts[(pos['primary_or_reserve'],pos['family'])]+=1;output_count+=len(f['output_fields'])
        members=p.D.counterfactual_members(f,slot,p.C) if pos['family']=='E5' else [f]
        if pos['family']=='E5':
            audits=[]
            for model in p.C['model_provider']['models']:
                for repeat in range(1,3 if pos['phase']=='A' else 2):
                    audit=p.D.audit_counterfactual(*members,slot,p.C,model['model'],repeat)
                    require(audit['masked_bytes_equal'] and audit['gold_distinct'],'E5_request:'+base+':'+model['tier']+':'+str(repeat),checks)
                    audits.append(audit)
            e5_audits.append(dict(logical_base_id=base,checks=audits,verdict='PASS'))
        if pos['family']=='E4' and pos['primary_or_reserve']=='PRIMARY':e4[pos['phase']+':'+pos['risk_round']].append(next(iter(g1.values())))
        if pos['family']=='E7':e7.append(base)
        variant_ids=[]
        for index,member in enumerate(members):
            variant='CF'+str(index+1) if pos['family']=='E5' else 'SINGLE'
            a=p.cache(member,pos,variant);other=i.evidence(member,a['request'],p.C)
            differential_records.append(certify_intermediates(p,i,member,a['request'],a['id'],False,checks))
            require(all(a[k]==other[k] for k in other),'dual_evidence:'+a['id'],checks)
            require(p.independent_gold(member)[0]==independent_gold(member,i,p.C,pos)[0]==member['gold_values'],'rendered_gold:'+a['id'],checks)
            variants.append(a);variant_ids.append(a['id'])
            rendered.append(dict(rendered_variant_id=a['id'],logical_base_id=base,variant_id=variant,
                fixture=member,request=a['request'],gold=member['gold_values'],primary_or_reserve=pos['primary_or_reserve'],
                request_input_sha256=sha(p.compact(a['request']['input']).encode())))
        traces.append(dict(logical_base_id=base,blueprint_position_id=base,fixture=copy.deepcopy(f),
            gold=g1,primary_gold_trace=t1,independent_gold_trace=t2,gold_agreement=True,
            actual_fingerprint=fp,fingerprint_class=class_id,subtype=pos['subtype'],
            validated_value_shape=p.D.value_shape_profile(p.C,pos['phase']+':'+pos['risk_round'],pos['subtype_slot']),rendered_variant_ids=variant_ids,
            reserve_mapping=[r['reserve_slot_id'] for r in p.B['reserve_map'] if base in (r['covered_primary_base_id'],r['reserve_base_id'])]))
    require(len(variants)==192 and {v['id'] for v in variants}=={v['rendered_variant_id'] for v in p.B['rendered_variants']},'192_exact_variants',checks)
    require(output_count==220 and sum(len(r['fixture']['output_fields']) for r in rendered)==244,'220_244_outputs',checks)
    require(all(family_counts[(role,'E'+str(f))]==(20 if role=='PRIMARY' else 4) for role in ('PRIMARY','RESERVE') for f in range(1,8)),'per_family_20_4',checks)
    for context,values in e4.items():require(Counter(values)==Counter({True:3,False:2}),'E4_3_true_2_false:'+context,checks)
    require(len(e7)==24,'24_E7_integrated_checks',checks)
    planned=p.B['recurrence_ledger']['fingerprint_classes']
    require(set(class_members)==set(planned) and all(sorted(class_members[k])==sorted(planned[k]['members']) for k in planned),'51_exact_recurrence_classes_and_members',checks)
    reserve_results=[]
    for row in p.B['reserve_map']:
        profiles=[]
        for base in (row['covered_primary_base_id'],row['reserve_base_id']):
            pos=p.POSITIONS[base];slot=dict(pos['subtype'],phase=pos['phase'],risk_round=pos['risk_round'])
            profiles.append(p.D.counterfactual_reserve_profile(bases[base],slot,p.C) if pos['family']=='E5' else p.D.reserve_profile_bytes(bases[base],slot,p.C,True))
        require(profiles[0]==profiles[1],'reserve_profile:'+row['reserve_slot_id'],checks)
        reserve_results.append(dict(slot=row['reserve_slot_id'],covered_primary=row['covered_primary_base_id'],reserve=row['reserve_base_id'],
            profile_sha256=sha(profiles[0]),profile=json.loads(profiles[0]),verdict='PASS',activation_performed=False))
    entailment=request_entailment_report(p,i,rendered,checks)
    pair_records=[];branches=Counter();content_counts=defaultdict(Counter)
    for a,b in itertools.combinations(variants,2):
        first=p.pair_decision(a,b);second=i.independent_pair(a,b,p.SCAFFOLD)
        require(first==second and first[1] is None,'dual_pair:'+a['id']+'|'+b['id'],checks)
        branches[first[0]]+=1
        scaffold=p.SCAFFOLD.get(frozenset([a['id'],b['id']]))
        residual=None
        if scaffold:
            grams={tuple(s.split(' ')) for s in scaffold['invariant_five_grams']}
            residual=p.ratio(a['ordinary']-grams,b['ordinary']-grams)
        content_status='NOT_APPLICABLE_BOTH_EMPTY' if not a['content'] and not b['content'] else 'APPLIES'
        content_counts[first[0]][content_status]+=1
        pair_records.append(dict(left=a['id'],right=b['id'],primary_disposition=first[0],independent_disposition=second[0],
            agreement=True,ordinary_intersection_union=p.ratio(a['ordinary'],b['ordinary']),content_intersection_union=p.ratio(a['content'],b['content']),
            content_status=content_status,content_similarity=None if content_status!='APPLIES' else p.ratio(a['content'],b['content']),
            content_dissimilarity_credit=content_status=='APPLIES' and first[0]=='CONTENT',
            shape_intersection_union=p.ratio(a['shape'],b['shape']),scaffold_class=scaffold['class_id'] if scaffold else None,
            residual_intersection_union=residual,exact_reuse='PAIR_LOCAL_VALIDATED_E5' if first[0]=='SAME_BASE_E5' else 'PASS',
            eligible_date_number_comparison=bool(a['tuple'] and b['tuple'])))
    require(branches==Counter(SCAFFOLD=906,CONTENT=518,ORDINARY=16888,SAME_BASE_E5=24),'comparison_partition_exact',checks)
    historic=[]
    for binding in p.C['historical_fingerprint_adapter_contract']['artifact_bindings']:
        path=ROOT/binding['path'];gold=json.loads(path.with_name(path.name.replace('corpus','gold')).read_bytes(),parse_float=Decimal)['items']
        gold_by_id={r['fixture_id']:r['expected'] for r in gold}
        for fixture in json.loads(path.read_bytes())['fixtures']:
            if fixture['task_class']!='structured_extraction':continue
            h=p.historical_evidence(fixture,gold_by_id[fixture['fixture_id']]);other=i.historical_record(fixture,gold_by_id[fixture['fixture_id']],p.C)
            require(h==other,'dual_historical_evidence:'+h['id'],checks);historic.append(h)
            differential_records.append(certify_intermediates(p,i,fixture,fixture,h['id'],True,checks))
    require(len(historic)==106,'106_historical_records',checks)
    historical_records=[]
    for h in historic:
        for a in variants:
            left=p.historical_pair(h,a);right=i.historical_pair_result(h,a,p.C)
            require(left==right and left[0]=='PASS' and left[1] is None,'dual_historical_pair:'+h['id']+'|'+a['id'],checks)
            historical_records.append(dict(historical=h['id'],new=a['id'],primary_disposition=left[0],independent_disposition=right[0],agreement=True,
                similarity_intersection_union=p.ratio(h['grams'],a['ordinary']),projection_components_equal=sum(x==y for x,y in zip(h['projection'],a['projection'])),
                whole_answer_replay='PASS',raw_payload_replay='PASS',structured_identifier_overlap='PASS',
                unstructured_entity_semantics=h['unstructured_entity_semantics'],date_number=left[2]))
    require(len(historical_records)==20352,'20352_supported_historical_controls_not_tuple_passes',checks)
    mutation_results=certify_mutations(p,i,bases,variants,checks)
    local_names={'wrong_scaffold_class','wrong_invariant_gram','recurrence_overflow'}
    for row in mutation_results:
        row['classification']='TEST_LOCAL_GUARD' if row['mutation'] in local_names else 'CHECKER_COMPONENT_PATH'
    real_mutations=real_path_mutations(p,i,replay) if certify_real else []
    for row in real_mutations:checks.append('real_path_mutation:'+row['mutation'])
    require(len(differential_records)==192+106,'298_complete_intermediate_records',checks)
    require(all(r['content_similarity'] is None and r['content_dissimilarity_credit'] is False
                for r in pair_records if r['content_status']=='NOT_APPLICABLE_BOTH_EMPTY'),
            'not_applicable_receives_no_dissimilarity_credit',checks)
    old_contamination=json.loads(git('show',PRIOR_PACKAGE+':'+(HERE/'CONTAMINATION_REPORT.json').relative_to(ROOT).as_posix()))
    added_content_fields={'content_status','content_similarity','content_dissimilarity_credit'}
    require([{k:v for k,v in row.items() if k not in added_content_fields} for row in pair_records]
            ==old_contamination['new_new_decisions'],'all_prior_new_new_scientific_decisions_unchanged',checks)
    old_historical=old_contamination['historical_new_decisions']
    require([{k:v for k,v in row.items() if k!='projection_components_equal'} for row in historical_records]
            ==[{k:v for k,v in row.items() if k!='projection_components_equal'} for row in old_historical],
            'all_prior_historical_scientific_decisions_unchanged',checks)
    elapsed_ids={r['rendered_variant_id'] for r in entailment['affected_requests']}
    projection_deltas=[dict(historical=new['historical'],new=new['new'],
        prior_components_equal=old['projection_components_equal'],
        corrected_components_equal=new['projection_components_equal'])
        for new,old in zip(historical_records,old_historical)
        if new['projection_components_equal']!=old['projection_components_equal']]
    require(all(row['new'] in elapsed_ids for row in projection_deltas),
            'historical_surface_diagnostic_changes_only_authorized_elapsed_requests',checks)
    after=snapshot();require(before==after,'all_preservation_before_after_exact',checks)
    counts=dict(logical_bases=168,scored_logical=140,reserve_logical=28,rendered_variants=192,scored_rendered=160,reserve_rendered=32,
        logical_outputs=220,rendered_outputs=244,scaffold_classes=14,logical_scaffold_memberships=234,rendered_scaffold_memberships=906,
        same_subtype=518,ordinary=16888,same_base_e5=24,fingerprint_classes=len(class_members),subtype_groups=35,
        phase_a_calls=480,max_phase_b_calls=240,max_total_calls=720)
    accounting={branch:dict(content_applies=counts['APPLIES'],
        content_not_applicable_both_empty=counts['NOT_APPLICABLE_BOTH_EMPTY']) for branch,counts in content_counts.items()}
    accounting['TOTAL']=dict(content_applies=sum(v['APPLIES'] for v in content_counts.values()),
        content_not_applicable_both_empty=sum(v['NOT_APPLICABLE_BOTH_EMPTY'] for v in content_counts.values()))
    contamination=dict(verdict='PASS_SUPPORTED_CONTROLS',checkers_agree=True,disagreements=0,new_new_partition=dict(branches),
        content_applicability=accounting,not_applicable_is_dissimilarity_evidence=False,
        exact_reuse_accounting=dict(new_new_cross_base_scopes=18312,raw_payload_scopes=18312,
            freshness_scopes=18312,whole_answer_scopes=18312,identity_scopes=18312,
            eligible_new_new_date_number_scopes=sum(r['eligible_date_number_comparison'] for r in pair_records if r['primary_disposition']!='SAME_BASE_E5'),
            historical_supported_control_scopes=20352,historical_structured_identifier_atoms=sum(len(h['identities']) for h in historic),
            historical_unstructured_identity_semantics='UNAVAILABLE_NOT_GUESSED',
            historical_freshness='NEW freshness contract does not define historical source sequences; not fabricated'),
        new_new_decisions=pair_records,historical_new_decisions=historical_records,
        historical_new_date_number=dict(status=p.tuple_applicability('historical_new')['status'],historical_fixtures=106,
            historical_new_scopes=20352,tuple_comparisons_performed=0,pass_count=0,fail_count=0,reason='frozen provenance unavailable'),
        historical_adapter=p.D.historical_adaptation_summary(p.C),
        historical_projection_diagnostic_changes=dict(count=len(projection_deltas),
            reason='Frozen SUBJECT surface parser observes the authorized elapsed convention; no adapter, threshold or scientific disposition change.',
            scientific_decisions_unchanged=True,records=projection_deltas),
        recurrence=dict(verdict='PASS',class_members=dict(class_members)),
        reserve_results=reserve_results)
    approved=approval_record()
    review_state='TARGETED_INDEPENDENT_CLOSURE_AUDIT_PASS' if approved else 'PRIOR_NOT_READY_TARGETED_CLOSURE_AUDIT_PENDING'
    governance=dict(GOVERNANCE,external_gold_review=review_state)
    differential=dict(verdict='PASS',new_records=192,historical_records=106,total_records=len(differential_records),
        normalized_payload_equalities=298,token_sequence_equalities=298,new_fingerprint_byte_equalities=192,
        historical_projection_byte_equalities=106,
        disagreements=dict(normalized_payload=0,token_sequence=0,new_fingerprint_bytes=0,historical_projection_bytes=0),
        actual_equality_required=True,hashes_are_evidence_only=True,records=differential_records)
    mutation_report=dict(real_path_mutations=real_mutations,
        local_guard_tests=[r for r in mutation_results if r['classification']=='TEST_LOCAL_GUARD'],
        checker_component_tests=[r for r in mutation_results if r['classification']=='CHECKER_COMPONENT_PATH'],
        contract_local_guard_tests=[dict(test=x,classification='TEST_LOCAL_GUARD') for x in checks if x.startswith('actual_contract_mutation')],
        real_path_count=len(real_mutations),local_guard_count=sum(r['classification']=='TEST_LOCAL_GUARD' for r in mutation_results),
        checker_component_count=sum(r['classification']=='CHECKER_COMPONENT_PATH' for r in mutation_results),
        contract_local_guard_count=sum(x.startswith('actual_contract_mutation') for x in checks),
        all_real_path_mutations_rejected=all(r['rejected'] for r in real_mutations),
        local_tests_are_not_real_finalizer_certification=True)
    closure=dict(prior_review_verdict='NOT_READY_FOR_NEXT_G_EXTRACT1_STAGE',prior_package=PRIOR_PACKAGE,
        prospective_correction_commit=CORRECTION,
        closure_matrix=[
            dict(finding='P1 elapsed-time entailment',status='RESOLVED',evidence='ELAPSED_REQUEST_ENTAILMENT_REPORT.json;12 exact requests;gold unchanged'),
            dict(finding='P2 content applicability reporting',status='RESOLVED',evidence='CONTAMINATION_REPORT.json explicit statuses and no-credit field'),
            dict(finding='P2 intermediate differential certification',status='RESOLVED',evidence='INTERMEDIATE_DIFFERENTIAL_REPORT.json;298 direct payload/token comparisons;192 fingerprints;106 historical projections'),
            dict(finding='mutation-certification labeling',status='RESOLVED',evidence='MUTATION_CERTIFICATION_REPORT.json;real path versus local/component separation')],
        independent_prepublication_audit='PASS' if approved else 'PENDING',
        final_read_only_closure_audit='REQUIRED_AFTER_REPUBLICATION',
        final_read_only_audit_binding='Separate audit commit binds the exact republished package commit; no circular manifest/audit self-digest.',
        candidate_source_sha256=CANDIDATE_SHA,gold_projection_sha256=GOLD_SHA,governance=governance)
    validation=dict(verdict='DETERMINISTIC_VALIDATION_PASS',external_corpus_gold_review=review_state,provider_execution='NOT AUTHORIZED',
        check_count=len(checks),checks=checks,counts=counts,repair_replay=replay,preservation=dict(before=before,after=after,byte_identical=True),
        E4_truth_matrix={k:dict(true=v.count(True),false=v.count(False)) for k,v in e4.items()},E7_integrated_validated=e7,
        E5_pairs=24,E5_request_audits=sum(len(x['checks']) for x in e5_audits),reserve_compatible=28,
        mutation_results=mutation_results,mutation_count=len(mutation_results),contract_mutation_tests=[x for x in checks if x.startswith('actual_contract_mutation')],
        real_path_mutation_count=len(real_mutations),mutation_classification=mutation_report,
        content_applicability=accounting,intermediate_differential_summary={k:v for k,v in differential.items() if k!='records'},
        elapsed_corrected_requests=12,non_elapsed_requests_unchanged=180,
        authoring_history=dict(rejected_candidates=480,maximum_accepted_attempt=194,search_rerun=False),governance=governance)
    output={
        'SCORED_CORPUS.json':dict(schema_version='g-extract1.corpus.v1',source_sha256=CANDIDATE_SHA,projection_only=True,rendered_variants=[r for r in rendered if r['primary_or_reserve']=='PRIMARY']),
        'RESERVE_CORPUS.json':dict(schema_version='g-extract1.reserve-corpus.v1',source_sha256=CANDIDATE_SHA,projection_only=True,rendered_variants=[r for r in rendered if r['primary_or_reserve']=='RESERVE'],reserve_maps=p.B['reserve_map']),
        'GOLD.json':dict(schema_version='g-extract1.gold.v1',source_gold_projection_sha256=GOLD_SHA,logical=[dict(logical_base_id=r['logical_base_id'],gold=r['gold']) for r in traces],rendered=[dict(rendered_variant_id=r['rendered_variant_id'],gold=r['gold']) for r in rendered]),
        'CONTAMINATION_REPORT.json':contamination,
        'GOLD_DERIVATION_REPORT.json':dict(verdict='PASS',independent_logical_agreement=168,independent_rendered_agreement=192,external_gold_review=review_state,logical_traces=traces),
        'E5_REQUEST_INVARIANCE_REPORT.json':dict(verdict='PASS',logical_pairs=24,provider_model_calls=0,request_audits=e5_audits),
        'CORPUS_VALIDATION_REPORT.json':validation,
        'ELAPSED_REQUEST_ENTAILMENT_REPORT.json':entailment,
        'INTERMEDIATE_DIFFERENTIAL_REPORT.json':differential,
        'MUTATION_CERTIFICATION_REPORT.json':mutation_report,
        'CORPUS_GOLD_REVIEW_CLOSURE.json':closure,
    }
    for name in ('GOLD.json','RESERVE_CORPUS.json','E5_REQUEST_INVARIANCE_REPORT.json'):
        require(packed(output[name])==git('show',PRIOR_PACKAGE+':'+(HERE/name).relative_to(ROOT).as_posix()),
                'byte_identical_prior_artifact:'+name,checks)
    validation['check_count']=len(checks)
    checker_commit=git('log','-1','--format=%H','--','experiments/G-EXTRACT1-candidate/corpus/validate_corpus.py').decode().strip()
    manifest=dict(schema_version='g-extract1.corpus-manifest.v1',status='READY_FOR_FINAL_READ_ONLY_CLOSURE_AUDIT',
        design_commit=CORRECTION,blueprint_commit=CORRECTION,checker_applicability_commit=checker_commit,
        prior_package_commit=PRIOR_PACKAGE,
        prior_design_blueprint_correction='62de5dbdb6a646e21640f55e1565e1121ce675a3',
        prior_checker_applicability_repair='158ba41860b004b51e57aadd77ed278c8861581e',
        implementation_correction_commit=git('log','-1','--format=%H','--',Path(__file__).relative_to(ROOT).as_posix()).decode().strip(),
        final_republished_package_commit_binding='The Git commit publishing this manifest and its exact hashed artifacts; recorded literally by the separate final read-only audit commit.',
        prior_checker_repairs=['6fb3f2af5806760c034006a8561ce08e938c210a',CHECKER_PARENT],
        candidate_source_sha256=CANDIDATE_SHA,gold_projection_sha256=GOLD_SHA,
        authority_artifacts_sha256=after['corrected_authority_sha256'],checker_artifacts_sha256=after['checkers_sha256'],
        checker_applicability_report_sha256=sha((HERE/'TUPLE_APPLICABILITY_CHECKER_REPORT.json').read_bytes()),
        preserved_authoring_failure_and_repair_artifacts_sha256=after['preserved'],
        finalizer_sha256=sha(Path(__file__).read_bytes()),final_artifacts_sha256={n:sha(packed(v)) for n,v in output.items()},
        manifest_self_binding='No circular self-digest; final commit binds manifest Git blob. All other final artifacts hashed here.',
        independent_prepublication_audit_sha256=sha((HERE/'REVIEW_CLOSURE_PREPUBLICATION_AUDIT.json').read_bytes()) if approved else None,
        prior_external_review_history_sha256=sha((HERE/'CORPUS_GOLD_REREVIEW_HISTORY.json').read_bytes()),
        content_applicability=accounting,intermediate_differential_summary={k:v for k,v in differential.items() if k!='records'},
        counts=counts,date_number_applicability=p.C['date_number_tuple_applicability_contract'],governance=governance)
    output['CORPUS_MANIFEST.json']=manifest
    return output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--checker-repair',action='store_true')
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args();snapshot();scope=checker_scope()
    p=load('final_primary',HERE/CHECKER_NAMES[0]);i=load('final_independent',HERE/CHECKER_NAMES[1])
    before=snapshot();checks=[];applicability_tests(p,i,checks);replay=replay_repairs()
    if args.checker_repair:
        report=dict(verdict='PASS',scope=scope,applicability_checks=checks,repair_replay=replay,
            before=before,after=snapshot(),scientific_correction_commit=CORRECTION,governance=GOVERNANCE,
            corpus_finalized=False,final_contamination_campaign_run=False)
        if report['before']!=report['after']:raise ValueError('checker_validation_mutated_input')
        (HERE/'TUPLE_APPLICABILITY_CHECKER_REPORT.json').write_bytes(packed(report))
        print(json.dumps(dict(verdict='PASS',applicability_checks=len(checks),repair_replay=replay),indent=2));return
    output=run_finalization(p,i,replay)
    if args.publish:
        approval_record(required=True)
        for name in FINAL_NAMES:
            path=HERE/name
            if path.exists() and path.read_bytes()!=packed(output[name]):
                old=subprocess.run(['git','show',PRIOR_PACKAGE+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT,capture_output=True)
                if old.returncode or path.read_bytes()!=old.stdout:raise ValueError('unexpected_publication_artifact_drift:'+name)
        for name in FINAL_NAMES:(HERE/name).write_bytes(packed(output[name]))
        snapshot()
    print(json.dumps(dict(verdict=output['CORPUS_VALIDATION_REPORT.json']['verdict'],
        check_count=output['CORPUS_VALIDATION_REPORT.json']['check_count'],
        mutation_count=output['CORPUS_VALIDATION_REPORT.json']['mutation_count'],
        counts=output['CORPUS_MANIFEST.json']['counts'],published=args.publish,
        artifact_hashes={n:sha(packed(v)) for n,v in output.items()}),indent=2))


if __name__=='__main__':main()
