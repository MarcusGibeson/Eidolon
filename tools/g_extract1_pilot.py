"""No-provider certification. Synthetic evidence never qualifies a real cell."""
from __future__ import annotations

import argparse
import copy
import itertools
import json
from pathlib import Path
import shutil
import socket
import tempfile

from g_extract1_contract import (ROOT, DATA, Package, IntegrityError, canonical, digest, require,
                                 source_pins, verify_source)
from g_extract1_journal import SCHEMA, write_once, seal_checkpoint, load, Journal
from g_extract1_runner import Run, reserve_replacements, actual_reserve_profile, check_call, PILOT
from g_extract1_scoring import (evaluate, synthetic_gold, aggregate, transition, primary_verdict,
                                event_category, NumericToken, typed, equal)
from g_extract1_lifecycle_tests import lifecycle_tests
from g_extract1_final_lifecycle_tests import final_lifecycle_tests, completed_state_regressions


class Checks:
    def __init__(self):
        self.rows = []

    def check(self, group, name, condition):
        if not condition:
            raise AssertionError(group + ':' + name)
        self.rows.append(dict(group=group, test=name, result='PASS'))

    def rejects(self, group, name, event, action):
        try:
            action()
        except IntegrityError as exc:
            self.check(group,name,exc.event == event)
            return
        raise AssertionError('mutation survived:' + name)


class SyntheticTransport:
    synthetic_only = True
    def __init__(self, package, kind=None):
        self.package, self.kind = package, kind

    def __call__(self, wire, row):
        if self.kind:
            return dict(failure=self.kind, receipt=None if self.kind == 'unreceipted' else
                        dict(call_id=row['call_id'],request_sha256=digest(wire),synthetic_only=True,failure_kind=self.kind))
        return dict(raw_output=synthetic_gold(self.package.variants[row['rendered_variant_id']]),
                    provider_truncated=False, receipt=dict(synthetic_only=True,call_id=row['call_id'],request_sha256=digest(wire)))


def schedule_tests(p, t):
    a = p.schedule('A')
    b = p.schedule('B',sorted(p.blueprint['schedule_plan']['phase_b_cell_order']))
    t.check('schedule','480/240/720',len(a) == 480 and len(b) == 240 and len(a+b) == 720)
    t.check('schedule','repeated byte identity',canonical(a) == canonical(p.schedule('A')))
    cells = sorted(p.blueprint['schedule_plan']['phase_b_cell_order'])
    for bits in itertools.product((False,True),repeat=6):
        qualified = [x for x,v in zip(cells,bits) if v]
        result = p.schedule('B',qualified)
        expected = [dict(row,schedule_position=i) for i,row in enumerate((x for x in b if x['cell_id'] in qualified),1)]
        t.check('schedule','conditional subset:' + ''.join(map(lambda x:str(int(x)),bits)),result == expected)
    t.rejects('schedule','invalid B inclusion','PROVENANCE_MISMATCH',lambda:p.schedule('B',['other:R2']))
    t.rejects('schedule','duplicate B inclusion','PROVENANCE_MISMATCH',lambda:p.schedule('B',[cells[0],cells[0]]))
    # Compare the production materializer directly with the pinned historical builder.
    from g_route4_contract import request_body
    for row in a+b:
        member = p.variants[row['rendered_variant_id']]
        historical = request_body(dict(validator_profile='extraction.v1',**member['request']),row)
        t.check('request',row['call_id'],p.wire(row) == canonical(historical))
    t.check('request','12 elapsed clarifications preserved',
            sum('If the end time is earlier' in x['request']['prompt'] for x in p.variants.values()) == 12)
    audits = p.e5_wire_audit()
    t.check('E5','108 wire invariance audits',len(audits) == 108)
    broken = copy.copy(p); broken.variants = copy.deepcopy(p.variants)
    key = next(x for x in broken.variants if ':E5-' in x and x.endswith('CF2'))
    broken.variants[key]['request']['input']['text'] += ' '
    t.rejects('E5','non-selector request drift','UNAUTHORIZED_PROMPT_MUTATION',broken.e5_wire_audit)
    for key,event in [('seed','SEED_MISMATCH'),('schedule_position','SCHEDULE_POSITION_MISMATCH'),
                      ('model','MODEL_IDENTITY_MISMATCH_AFTER_CONTACT'),('provider_version','PROVIDER_VERSION_MISMATCH_AFTER_CONTACT'),
                      ('request_sha256','UNAUTHORIZED_PROMPT_MUTATION'),('generation_configuration','GENERATION_CONFIGURATION_MISMATCH')]:
        mutated = copy.deepcopy(a[0]); mutated[key] = 'changed'
        t.rejects('call_binding',key,event,lambda m=mutated:check_call(a[0],m))
    return a,b,audits


def response_tests(p,t):
    for name, member in p.variants.items():
        exact = synthetic_gold(member)
        result = evaluate(member,exact)
        t.check('scorer','exact:' + name,result['semantic_correct'] and result['useful'] and not result['false_clean'])
        t.check('scorer','malformed:' + name,not evaluate(member,'{')['semantic_correct'])
        t.check('scorer','partial:' + name,not evaluate(member,'{}')['structural_valid'])
        fenced = evaluate(member,'```json\n' + exact + '\n```')
        t.check('normalization',name,fenced['semantic_correct'] and fenced['normalization']['normalized'])
        obj = json.loads(exact)
        field = next(iter(obj))
        value = obj[field]
        obj[field] = not value if type(value) is bool else value + 1 if type(value) is int else value + 1.0 if type(value) is float else 'invalid'
        t.check('scorer','wrong:' + name,not evaluate(member,json.dumps(obj))['semantic_correct'])
    schema = dict(status='provided|not_provided',name='string',count='integer')
    fixture = dict(request=dict(input=dict(schema=schema)),gold=dict(status='not_provided',name='Aster',count=3),
                   fixture=dict(output_fields=[dict(name='status',binding_kind='EXPLICIT_ABSENCE')]))
    for vector in p.design['ambiguity_contract']['classifier_test_vectors']:
        r = evaluate(fixture,vector['raw_output'],truncated=vector.get('provider_truncated',False))
        t.check('E7_classifier',vector['id'],r['outcome'] == vector['expected_outcome'] and
                r['false_clean'] == vector['expected_false_clean'] and
                r['duplicate_key_present'] == vector['expected_duplicate_key_present'] and
                r['operationally_accepted'] == vector['expected_operationally_accepted'])
    additional = [('null','{"status":null,"name":"Aster","count":3}','operational_schema_invalid'),
                  ('extra','{"status":"not_provided","name":"Aster","count":3,"extra":1}','operational_schema_invalid'),
                  ('integer_decimal','{"status":"not_provided","name":"Aster","count":3.0}','operational_schema_invalid'),
                  ('duplicate_supported','{"status":"not_provided","name":"Wrong","name":"Aster","count":3}','semantic_schema_invalid'),
                  ('unsupported_and_wrong','{"status":"provided","name":"Wrong","count":3}','exact_valid_unsupported_value')]
    for name,raw,outcome in additional:
        t.check('E7_classifier',name,evaluate(fixture,raw)['outcome'] == outcome)
    r = evaluate(fixture,synthetic_gold(fixture),infrastructure=True)
    t.check('E7_classifier','infrastructure',r['outcome'] == 'infrastructure_missing' and r['safe_containment'] is None)
    for text in ('5','5.0','5.00','5e0'):
        t.check('comparator','NUMBER:' + text,equal(NumericToken(text),'5.0','number'))
        t.check('comparator','INTEGER:' + text,typed(NumericToken(text),'integer') == (text == '5'))
    t.check('comparator','integer -0',equal(NumericToken('-0'),0,'integer'))
    t.check('comparator','large exact number',not equal(NumericToken('9007199254740993'),'9007199254740992','number'))
    for schema,value in [('YYYY-MM-DD','2028-02-30'),('YYYY-MM-DD','2028-2-03'),('HH:MM','24:00'),('HH:MM','1:05')]:
        t.check('comparator',schema + ':' + value,not typed(value,schema))
    for value in ('Aster ','aster','the Aster'):
        t.check('comparator','no label/space/case repair:' + value,not equal(value,'Aster','string'))
    duplicate = dict(request=dict(input=dict(schema=dict(a='integer'))),gold=dict(a=5),fixture=dict(output_fields=[]))
    for raw in ('{"a":0,"a":5}','{"a":5,"a":0}'):
        r = evaluate(duplicate,raw)
        t.check('comparator','duplicate:' + raw,r['operationally_accepted'] and not r['semantic_correct'] and r['false_clean'])
    date_member = dict(request=dict(input=dict(schema=dict(a='YYYY-MM-DD'))),gold=dict(a='2028-02-29'),fixture=dict(output_fields=[]))
    r = evaluate(date_member,'{"a":"2028-02-30"}')
    t.check('comparator','historical regex accepts invalid calendar date',r['operationally_accepted'] and r['false_clean'])
    for trunc in (False,True):
        r = evaluate(fixture,synthetic_gold(fixture),truncated=trunc)
        t.check('truncation','accepted:' + str(trunc),r['false_clean'] == trunc and r['semantic_credit'] != trunc)
    r = evaluate(fixture,'{',truncated=True)
    t.check('truncation','rejected',r['outcome'] == 'provider_truncated' and r['safe_containment'] and not r['false_clean'])


def gates_tests(p,a,b,t):
    for phase,schedule in [('A',a),('B',b)]:
        evidence = {row['call_id']:evaluate(p.variants[row['rendered_variant_id']],synthetic_gold(p.variants[row['rendered_variant_id']])) for row in schedule}
        cell = 'small:R2'
        exact = aggregate(p,schedule,evidence,phase,cell)
        t.check('gates',phase + ':all exact',exact['passed'] and exact['statistics']['semantic'] == 30)
        rows = [x for x in schedule if x['cell_id'] == cell]
        first = next(x for x in rows if x['family'] == 'E1')
        changed = copy.deepcopy(evidence)
        for row in rows:
            if row['qualification_slot_id'] == first['qualification_slot_id']:
                changed[row['call_id']] = evaluate(p.variants[row['rendered_variant_id']],'{')
        result = aggregate(p,schedule,changed,phase,cell)
        t.check('gates',phase + ':29/30 exact boundary',result['passed'] and result['statistics']['semantic'] == 29 and result['statistics']['malformed'] == 1)
        second = next(x for x in rows if x['family'] == 'E1' and x['qualification_slot_id'] != first['qualification_slot_id'])
        for row in rows:
            if row['qualification_slot_id'] == second['qualification_slot_id']:
                changed[row['call_id']] = evaluate(p.variants[row['rendered_variant_id']],'{')
        result = aggregate(p,schedule,changed,phase,cell)
        t.check('gates',phase + ':28/30 below boundary',not result['passed'] and not result['gates']['determinate_semantic_correctness'] and not result['gates']['family_semantic_floor'])
        changed = copy.deepcopy(evidence); changed.pop(first['call_id'])
        result = aggregate(p,schedule,changed,phase,cell)
        t.check('gates',phase + ':incomplete',not result['complete'] and not result['gates']['denominator_integrity'])
        for family in ('E5','E6','E7'):
            row = next(x for x in rows if x['family'] == family)
            changed = copy.deepcopy(evidence)
            changed[row['call_id']] = evaluate(p.variants[row['rendered_variant_id']],'{')
            result = aggregate(p,schedule,changed,phase,cell)
            t.check('gates',phase + ':single failure:' + family,not result['passed'] if family != 'E6' else result['passed'])
        # Independent Boolean gate reductions, not claims of realizable model outputs.
        for bits in itertools.product((False,True),repeat=2 if phase == 'A' else 1):
            changed = copy.deepcopy(evidence)
            for row,bit in zip([x for x in rows if x['qualification_slot_id'] == first['qualification_slot_id']],bits):
                changed[row['call_id']]['semantic_correct'] = bit
                changed[row['call_id']]['false_clean'] = not bit
            result = aggregate(p,schedule,changed,phase,cell)
            t.check('reduction',phase + ':' + str(bits),result['statistics']['semantic'] == 29 + int(all(bits)) and
                    result['statistics']['false_clean_fixtures'] == int(not all(bits)))
        for useful in (27,26):
            changed = copy.deepcopy(evidence)
            bases = sorted({x['qualification_slot_id'] for x in rows if x['family'] != 'E7'})
            for row in rows:
                if row['qualification_slot_id'] in bases[:30-useful]:
                    changed[row['call_id']]['useful'] = False
            result = aggregate(p,schedule,changed,phase,cell)
            t.check('gates',phase + ':useful Boolean boundary:' + str(useful),result['gates']['useful_correct_acceptance'] == (useful == 27))
        changed = {x:evaluate(p.variants[row['rendered_variant_id']],'{') for row in rows for x in [row['call_id']]}
        t.check('gates',phase + ':complete fail',not aggregate(p,schedule,changed,phase,cell)['passed'])
    for vector in p.design['result_state_machine']['deterministic_test_vectors']:
        t.check('verdict',vector['id'],primary_verdict(p.design,vector['facts']) == vector['expected'])
    for row in p.design['cell_state_machine']['transitions']:
        flags = dict(blocked=row[2] == 'A_BLOCKED',complete=row[2] in ('A_FAILED','A_QUALIFIED_FOR_B','FINALLY_QUALIFIED','B_FAILED_VALIDATION'),
                     passed=row[2] in ('A_QUALIFIED_FOR_B','FINALLY_QUALIFIED'),incomplete=row[2] in ('A_INCOMPLETE','B_INCOMPLETE'),eligible=row[2] == 'B_SCHEDULED')
        t.check('state_machine',row[0] + ':' + row[2],transition(p.design,row[0],row[2],**flags) == row[2])
    for origin,target in [('A_FAILED','B_SCHEDULED'),('B_FAILED_VALIDATION','FINALLY_QUALIFIED'),('A_SCHEDULED','FINALLY_QUALIFIED')]:
        t.rejects('state_machine','illegal:' + origin + ':' + target,'PROVENANCE_MISMATCH',lambda o=origin,d=target:transition(p.design,o,d,eligible=True,complete=True,passed=True))


def integrity_tests(p,a,t,temp):
    for key,event in [('models','PRE_MODEL_IDENTITY_MISMATCH'),('provider_version','PRE_PROVIDER_VERSION_MISMATCH'),
                      ('generation_configuration','PRE_GENERATION_CONFIG_MISMATCH')]:
        receipts = copy.deepcopy(p.receipts()); receipts[key] = 'mutated'
        t.rejects('precontact',key,event,lambda r=receipts:p.verify_receipts(r))
    for name,event in [('SCORED_CORPUS.json','PRE_ARTIFACT_DIGEST_MISMATCH'),('GOLD.json','PRE_GOLD_DIGEST_MISMATCH')]:
        isolated = copy.copy(p); isolated.root = temp / name; isolated.root.mkdir()
        relative = 'experiments/G-EXTRACT1-candidate/corpus/' + name
        path = isolated.root / relative; path.parent.mkdir(parents=True)
        original = (p.root / relative).read_bytes(); path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        isolated.pins = {relative:p.pins[relative]}
        t.rejects('precontact','one byte:' + name,event,isolated.verify)
        post = 'GOLD_DIGEST_MISMATCH' if name == 'GOLD.json' else 'PROTECTED_ARTIFACT_DIGEST_MISMATCH'
        t.rejects('postcontact','one byte:' + name,post,lambda i=isolated:i.verify(True))
    pins = source_pins()
    for name,event in [('tools/g_extract1_runner.py','PRE_SCORER_DIGEST_MISMATCH'),('tools/g_extract1_scoring.py','PRE_COMPARATOR_DIGEST_MISMATCH')]:
        changed = dict(pins); changed[name] = '0'*64
        t.rejects('precontact','source:' + name,event,lambda c=changed:verify_source(c))
    changed = copy.copy(p); changed.blueprint = copy.deepcopy(p.blueprint)
    changed.blueprint['schedule_plan']['phase_a'][0]['seed'] += 1
    t.rejects('precontact','schedule mutation','PRE_SCHEDULE_DIGEST_MISMATCH',lambda:changed.skeleton('A'))
    changed = copy.copy(p); changed.pins = dict(p.pins)
    # Verify that audit failure is not hidden by a matching synthetic receipt.
    t.check('precontact','contamination audit event inventory','PRE_CONTAMINATION_AUDIT_FAILURE' in p.design['integrity_event_contract']['precontact_blocking_events'])
    directory = temp / 'receipt_run'
    run = Run(p,directory,'receipt')
    t.rejects('precontact','run collision','PRE_EXISTING_RUN_COLLISION',lambda:Run(p,directory,'receipt'))
    for kind,event in [('timeout','PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT'),('error','PROVIDER_ERROR_WITH_FAILURE_RECEIPT'),
                       ('missing','MISSING_RESPONSE_WITH_FAILURE_RECEIPT'),('unreceipted','PROVIDER_FAILURE_WITHOUT_RECEIPT')]:
        r = Run(p,temp / kind,kind)
        r.perform(r.a[0],SyntheticTransport(p,kind),p.receipts())
        t.check('failure_receipt',kind,r.events == [event] and primary_verdict(p.design,dict(events=r.events)) == event_category(p.design,event))
        t.rejects('retry','failed call:' + kind,event,lambda:r.perform(r.a[0],SyntheticTransport(p),p.receipts()))
    run.perform(run.a[0],SyntheticTransport(p),p.receipts())
    t.rejects('retry','duplicate call','UNAUTHORIZED_RETRY',lambda:run.perform(run.a[0],SyntheticTransport(p),p.receipts()))
    t.rejects('journal','exclusive entry collision','PROVENANCE_MISMATCH',lambda:write_once(directory / 'journal/000001.json',{}))
    run = Run(p,temp/'cleanresume','cleanresume')
    directory = run.directory
    run.perform(run.a[0],SyntheticTransport(p),p.receipts())
    cp = run.checkpoint('one')
    resumed = Run(p,directory,'cleanresume',resume=True)
    t.check('resume','clean',resumed.resume(directory / 'CHECKPOINT_one.json') == 'MACHINE_INTERRUPTION_WITH_SEALED_CHECKPOINT')
    record_path = directory / 'journal/000002.json'
    raw = record_path.read_bytes(); record_path.write_bytes(raw.replace(b'RESPONSE_CAPTURED',b'RESPONSE_TAMPERED'))
    t.rejects('journal','tampered payload','CORRUPTED_OR_UNPARSEABLE_JOURNAL',resumed.journal.read)
    record_path.write_bytes(raw)
    pending = Run(p,temp / 'pending','pending')
    pending.journal.append(dict(type='START',call=pending.a[0],wire_sha256=digest(p.wire(pending.a[0])),checkpoint_lineage=None,mode=PILOT))
    t.rejects('journal','unreceipted interruption','SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT',lambda:Run(p,temp / 'pending','pending',resume=True))
    for vector in p.design['integrity_event_contract']['classification_test_vectors']:
        t.check('integrity_catalog',vector['id'],event_category(p.design,vector['event']) == vector['expected_category'])
    # All frozen integrity events exercise the real first-match verdict interpreter.
    for key,category in [('precontact_blocking_events','PRE_CONTACT_BLOCKED'),('invalid_events','INVALID'),('incomplete_events','INCOMPLETE')]:
        for event in p.design['integrity_event_contract'][key]:
            t.check('integrity_catalog',event,primary_verdict(p.design,dict(events=[event],provider_generation_calls=0)) == category)
    t.rejects('authority','candidate cannot authorize live','PROVENANCE_MISMATCH',lambda:Run(p,temp/'live','live',mechanical=False,
        authorization=dict(status='EXECUTION_FREEZE_CANDIDATE_ONLY')))


def reserve_tests(p,t):
    refreeze = dict(synthetic_only=True,contamination=True,gold_review=True,balance=True,profiles=True)
    for mapping in p.blueprint['reserve_map']:
        primary, reserve = mapping['covered_primary_base_id'], mapping['reserve_base_id']
        claim = dict(primary_base_id=primary,reserve_base_id=reserve,reason='mechanical_schema_defect',
                     rendered_variant_ids=sorted(x for x in p.variants if p.variants[x]['logical_base_id'] == reserve))
        t.check('reserve',primary,reserve_replacements(p,[claim],approved_refreeze=refreeze) == {primary:reserve})
        t.rejects('reserve','postcontact:' + primary,'POST_CONTACT_FIXTURE_MUTATION',lambda c=claim:reserve_replacements(p,[c],contacted=True,approved_refreeze=refreeze))
        t.rejects('reserve','consumed:' + primary,'PROVENANCE_MISMATCH',lambda c=claim,r=reserve:reserve_replacements(p,[c],consumed=[r],approved_refreeze=refreeze))
    mapping = p.blueprint['reserve_map'][4]
    claim = dict(primary_base_id=mapping['covered_primary_base_id'],reserve_base_id=mapping['reserve_base_id'],
                 reason='mechanical_schema_defect',rendered_variant_ids=sorted(x for x in p.variants if p.variants[x]['logical_base_id'] == mapping['reserve_base_id']))
    half = copy.deepcopy(claim); half['rendered_variant_ids'] = half['rendered_variant_ids'][:1]
    t.rejects('reserve','E5 half-pair','PROVENANCE_MISMATCH',lambda:reserve_replacements(p,[half],approved_refreeze=refreeze))
    for suffix in ('02','03','04','05'):
        changed = copy.deepcopy(claim); changed['primary_base_id'] = changed['primary_base_id'].replace('E5-01','E5-' + suffix)
        t.rejects('reserve','uncovered:' + suffix,'PROVENANCE_MISMATCH',lambda c=changed:reserve_replacements(p,[c],approved_refreeze=refreeze))
    for wrong in ('B:R2:E5-01:RESERVE','A:R3:E5-01:RESERVE','A:R2:E4-01:RESERVE'):
        changed = copy.deepcopy(claim); changed['reserve_base_id'] = wrong
        t.rejects('reserve','wrong slot:' + wrong,'PROVENANCE_MISMATCH',lambda c=changed:reserve_replacements(p,[c],approved_refreeze=refreeze))
    t.rejects('reserve','duplicate activation','PROVENANCE_MISMATCH',lambda:reserve_replacements(p,[claim,claim],approved_refreeze=refreeze))


def full_pilot(p,directory,t,label):
    run = Run(p,directory,'mechanical-only')
    transport = SyntheticTransport(p)
    # Clean qualification rehearsals are uninterrupted. Separate real-path tests
    # retain the sealed-interruption INCOMPLETE event instead of clearing it.
    for row in run.a:
        run.perform(row,transport,p.receipts())
    run.enter_b()
    for row in run.b:
        run.perform(row,transport,p.receipts())
    run.checkpoint('final')
    report = run.final_report()
    t.check('pilot',label + ':720 synthetic observations',report['synthetic_observations'] == 720 and
            report['synthetic_primary_verdict'] == 'TARGETED_REQUALIFICATION_SUPPORTED' and
            all(x['passed'] for cells in report['state']['reports'].values() for x in cells.values()))
    write_once(directory / 'FINAL_REPORT.json',report)
    write_once(directory / 'PHASE_A_SCHEDULE.json',run.a)
    write_once(directory / 'PHASE_B_SCHEDULE.json',run.b)
    return report


def certify(output):
    # A hard socket tripwire applies to all pilot paths, including imports.
    def forbidden(*args,**kwargs):
        raise AssertionError('NO_PROVIDER_PILOT_NETWORK_ATTEMPT')
    socket.socket, socket.create_connection = forbidden, forbidden
    p,t = Package(),Checks()
    protected_before = {name:digest((p.root/name).read_bytes()) for name in p.pins}
    preserved_before = {x.name:digest(x.read_bytes()) for x in (p.data/'corpus').glob('*.json')}
    a,b,audits = schedule_tests(p,t)
    response_tests(p,t)
    gates_tests(p,a,b,t)
    with tempfile.TemporaryDirectory(prefix='g-extract1-mechanical-') as temporary:
        root = Path(temporary)
        integrity_tests(p,a,t,root)
        reserve_tests(p,t)
        final_targeted = final_lifecycle_tests(p,t,root/'final_lifecycle',SyntheticTransport)
        print(json.dumps(dict(stage='LR1_LR3_TARGETED_PASS',checks=len(t.rows))),flush=True)
        targeted = lifecycle_tests(p,t,root/'lifecycle',SyntheticTransport)
        print(json.dumps(dict(stage='I1_I6_TARGETED_PASS',checks=len(t.rows))),flush=True)
        first = full_pilot(p,root/'pilot1',t,'first')
        print(json.dumps(dict(stage='FIRST_FULL_PILOT_PASS',observations=720)),flush=True)
        final_targeted['completed_state_regressions'] = completed_state_regressions(
            p,t,root/'final_lifecycle/completed_states',root/'pilot1',SyntheticTransport)
        second = full_pilot(p,root/'pilot2',t,'second')
        hashes1 = {x.relative_to(root/'pilot1').as_posix():digest(x.read_bytes()) for x in (root/'pilot1').rglob('*') if x.is_file()}
        hashes2 = {x.relative_to(root/'pilot2').as_posix():digest(x.read_bytes()) for x in (root/'pilot2').rglob('*') if x.is_file()}
        t.check('replay','all authority-bearing files byte-identical',hashes1 == hashes2)
        p.verify()
        t.check('preservation','accepted scientific bytes',protected_before == {name:digest((p.root/name).read_bytes()) for name in p.pins})
        t.check('preservation','all corpus/failure evidence',preserved_before == {x.name:digest(x.read_bytes()) for x in (p.data/'corpus').glob('*.json')})
        output.mkdir(parents=True,exist_ok=True)
        # Copy only mechanical evidence, never any run/apply/release pointer.
        require(not (output/'mechanical_pilot').exists(), 'PRE_EXISTING_RUN_COLLISION', 'pilot evidence')
        shutil.copytree(root/'pilot1',output/'mechanical_pilot')
        shutil.copytree(root/'pilot2',output/'mechanical_pilot_replay')
        shutil.copytree(root/'lifecycle',output/'targeted_evidence')
        shutil.copytree(root/'final_lifecycle',output/'final_targeted_evidence')
    report = dict(schema_version='g-extract1.mechanical-pilot-report.v1',verdict='PASS',
        scope='Deterministic implementation checks and synthetic mechanical replay only; not scientific qualification.',
        test_count=len(t.rows),tests=t.rows,phase_a_count=len(a),phase_b_maximum=len(b),maximum_calls=len(a+b),
        phase_a_schedule_sha256=digest(canonical(a)),phase_b_maximum_schedule_sha256=digest(canonical(b)),
        e5_wire_audits=len(audits),request_materializations=720,conditional_b_subsets=64,
        first_pilot='PASS',second_pilot='PASS',interrupt_resume='PASS_RETAINED_INCOMPLETE',authority_bytes_equal=True,
        replay_file_count=len(hashes1),replay_files_sha256=hashes1,
        protected_artifacts_before_after=protected_before,preserved_corpus_before_after=preserved_before,
        activity_integration='NOT_APPLICABLE: accepted isolated experiment architecture requires no Activity integration; no runtime changes.',
        provider_model_calls=0,phase_a_calls=0,phase_b_calls=0,phase_a_authorized=False,phase_b_authorized=False,
        corpus_regeneration=0,gold_changes=0,autonomy=False,belief_effects='none',g_route4='CLOSED FAILED unchanged')
    write_once(output/'MECHANICAL_PILOT_REPORT.json',report)
    write_once(output/'E5_HARNESS_WIRE_AUDIT.json',dict(verdict='PASS',audits=audits,provider_model_calls=0))
    write_once(output/'LIFECYCLE_REPAIR_REPORT.json',dict(verdict='PASS',closure=targeted,
        tests=[x for x in t.rows if x['group'].startswith('I')],provider_model_calls=0,
        scope='Implementation regression only; accepted scientific rules unchanged.'))
    group_counts = {group:sum(x['group'] == group for x in t.rows) for group in ('LR1','LR2','LR3','I1','I2','I3','I4','I5','I6')}
    write_once(output/'FINAL_LIFECYCLE_REPAIR_REPORT.json',dict(verdict='PASS',closure=final_targeted,
        test_counts=group_counts,tests=[x for x in t.rows if x['group'].startswith(('LR','I'))],
        provider_model_calls=0,scope='LR1-LR3 real-path attacks and I1-I6 regression; no scientific changes.'))
    source = source_pins()
    freeze = dict(schema_version='g-extract1.execution-freeze-candidate.v1',status='EXECUTION_FREEZE_CANDIDATE_ONLY',
        activated=False,phase_a_authorized=False,phase_b_authorized=False,source_sha256=source,
        accepted_binding=first['binding'],model_provider=p.receipts(),
        phase_a_schedule_sha256=digest(canonical(a)),phase_b_maximum_schedule_sha256=digest(canonical(b)),
        schedule_algorithm_sha256=source['tools/g_extract1_contract.py'],scorer_sha256=source['tools/g_extract1_scoring.py'],
        comparator_sha256=source['tools/g_extract1_scoring.py'],qualification_logic_sha256=source['tools/g_extract1_scoring.py'],
        response_validator_sha256=next(x['sha256'] for x in p.design['baseline_binding']['existing_behavior_artifacts'] if x['role']=='operational_wrapper'),
        journal_checkpoint_schema=SCHEMA,journal_checkpoint_schema_sha256=digest(canonical(SCHEMA)),
        integrity_event_contract_sha256=digest(canonical(p.design['integrity_event_contract'])),
        lifecycle_repair_report_sha256=digest((output/'LIFECYCLE_REPAIR_REPORT.json').read_bytes()),
        final_lifecycle_repair_report_sha256=digest((output/'FINAL_LIFECYCLE_REPAIR_REPORT.json').read_bytes()),
        accepted_science_closure_commit='6c85b10930cefe410a1965c0924e4fd9f47eb4ef',
        complete_manifest_verification=dict(file_count=len(p.pins),protected_files=p.pins,
            pin_categories=p.pin_categories,gold_projection_recomputed=True),
        supersedes_blocked_candidate_sha256=[
            '14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f',
            '6e7295b3c79ee95930fee7231265e342905b7848d261ae716d1ef1546ca785ab'],
        supersession_reason='LR1-LR3 targeted closure with I1-I6 regression; both old candidates remain blocked/unactivated.',
        pilot_report_sha256=digest((output/'MECHANICAL_PILOT_REPORT.json').read_bytes()),
        e5_wire_report_sha256=digest((output/'E5_HARNESS_WIRE_AUDIT.json').read_bytes()),
        authority='Separate execution-freeze review/activation and separate Phase A/conditional Phase B authorization remain required.',
        provider_model_calls=0,autonomy=False,belief_effects='none')
    write_once(output/'EXECUTION_FREEZE_CANDIDATE.json',freeze)
    print(json.dumps(dict(verdict='PASS',tests=len(t.rows),phase_a=len(a),phase_b_maximum=len(b),
        provider_model_calls=0,freeze_sha256=digest(canonical(freeze)))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    certify(args.output.resolve())
