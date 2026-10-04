"""Offline mechanical certification. Synthetic outputs are never research data."""
from __future__ import annotations

import copy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import tempfile

import g_cal1_contract as contract
from g_cal1_contract import DATA, ROOT, Package, allocation_ok, diagnosis, manual_date, primary_date, summarize
from g_cal1_lab import Run, authority, transport_boundary
from g_cal1_stage import preservation_snapshot
from g_extract1_contract import canonical, digest, file_digest, load, require, IntegrityError
from g_extract1_journal import SCHEMA, Journal, write_once
from g_extract1_scoring import evaluate, synthetic_gold


class Checks:
    def __init__(self): self.rows=[]
    def check(self,condition,category,detail):
        self.rows.append({'category':category,'detail':detail,'passed':bool(condition)})
        if not condition: raise AssertionError(category+':'+detail)
    def reject(self,action,category,detail,event=None):
        try: action()
        except IntegrityError as exc:
            self.check(event is None or exc.event==event,category,detail+':'+exc.event)
            return exc
        raise AssertionError('accepted forbidden action:'+detail)


def synthetic(transport):
    """Explicit marker for this no-provider test module's local stub functions."""
    transport.synthetic_only = True
    return transport


def success(package,request,row):
    return {'raw_output':synthetic_gold(package.members[row['fixture_id']]),'provider_truncated':False,
            'receipt':{'call_id':row['call_id'],'request_sha256':row['request_sha256'],'synthetic_only':True}}


def tree(directory):
    return {p.relative_to(directory).as_posix():file_digest(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def full_pilot(package,directory,checks):
    run = Run(package,directory,'G-CAL1-SYNTHETIC-REPLAY')
    run.checkpoint()
    for index,row in enumerate(package.schedule,1):
        score = run.perform(row,synthetic(lambda request,r:success(package,request,r)))
        checks.check(score['semantic_correct'] and score['structural_valid'] and not score['false_clean'],
                     'full_pilot',row['call_id'])
        checkpoint = run.checkpoint()
        if index==40:
            del run
            run = Run(package,directory,'G-CAL1-SYNTHETIC-REPLAY',resume=True)
            run.verify_resume(checkpoint)
    result = run.final_report()
    checks.check(result['state']['verdict']=='VALID_COMPLETE' and result['summary']['complete'],'full_pilot','80 complete')
    checks.check(all(x['both_repeat_correct']==10 for x in result['summary']['strata'].values()),'full_pilot','four strata preserved')
    write_once(directory/'FINAL_REPORT.json',result)
    # Independently replay the entire journal and the last sealed checkpoint.
    replay = Run(package,directory,'G-CAL1-SYNTHETIC-REPLAY',resume=True)
    replay.verify_resume(checkpoint)
    checks.check(replay.final_report()==result,'full_pilot','complete journal/checkpoint/scorer replay')
    # Verification appends a resume marker, so the manifest is sealed afterwards.
    members = tree(directory)
    write_once(directory/'EVIDENCE_MANIFEST.json',{'mode':'SYNTHETIC_ONLY','files':members,'member_count':len(members)})
    return result


def adversarial(package,checks,root):
    calls = []
    def unused(request,row):
        calls.append(row['call_id'])
        return success(package,request,row)
    synthetic(unused)
    index=0
    def fresh():
        nonlocal index
        index+=1
        return Run(package,root/f'attack{index:03d}',f'G-CAL1-SYNTHETIC-ATTACK-{index:03d}')
    def terminal(run,category):
        before = len(calls); starts=sum(r['payload'].get('kind')=='START' for r in run.journal.read())
        row = package.schedule[min(len(run.attempted),79)]
        checks.reject(lambda:run.perform(row,unused),category,'external catch cannot continue')
        checks.check(len(calls)==before and starts==sum(r['payload'].get('kind')=='START' for r in run.journal.read()),
                     category,'zero subsequent transport and START')
        checks.check(bool(run.incidents.read()),category,'incident durable before return/rethrow')
        checks.reject(lambda:Run(package,run.directory,run.run_id,resume=True),category,'restart terminal')
    class CustomControl(BaseException): pass
    for signal in (KeyboardInterrupt('stop'),SystemExit(7),GeneratorExit('close'),CustomControl('custom')):
        run=fresh()
        def thrown(request,row,signal=signal): raise signal
        synthetic(thrown)
        try: run.perform(package.schedule[0],thrown)
        except BaseException as caught:
            checks.check(caught is signal and caught.args==signal.args,'control_flow',type(signal).__name__+' original propagated')
        else: raise AssertionError('control-flow swallowed')
        checks.check(run.events==['SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT'] and
                     run.state()['verdict']=='INVALID' and run.event_scopes[0]['cell']==package.schedule[0]['cell_id'],
                     'control_flow','INVALID omission scoped before rethrow')
        checks.check([x['payload']['kind'] for x in run.journal.read()]==['RUN_CREATED','START'],
                     'control_flow','no fabricated provider receipt')
        terminal(run,'control_flow')
    for error in (RuntimeError('ordinary'),ValueError('ordinary'),OSError('ordinary')):
        run=fresh()
        def thrown(request,row,error=error): raise error
        synthetic(thrown)
        checks.reject(lambda:run.perform(package.schedule[0],thrown),'ordinary_transport',type(error).__name__,'PROVIDER_FAILURE_WITHOUT_RECEIPT')
        checks.check(run.journal.read()[-1]['payload']['kind']=='FAILURE','ordinary_transport','START governed closure')
        terminal(run,'ordinary_transport')
    malformed = [None,[], '',0,False,object(),{}, {'failure':None}, {'raw_output':None},
                 {'raw_output':'{}'}, {'provider_truncated':False}, {'failure':'timeout','receipt':{}},
                 {'raw_output':'{}','provider_truncated':False,'receipt':{'call_id':'wrong','request_sha256':'wrong'}}]
    for value in malformed:
        run=fresh()
        checks.reject(lambda:run.perform(package.schedule[0],synthetic(lambda *_:value)),'malformed_transport',type(value).__name__,
                      'PROVIDER_FAILURE_WITHOUT_RECEIPT')
        checks.check(run.journal.read()[-1]['payload']['kind']=='FAILURE','malformed_transport','no continuable open START')
        terminal(run,'malformed_transport')
    for kind,event in [('timeout','PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT'),('error','PROVIDER_ERROR_WITH_FAILURE_RECEIPT'),
                       ('missing','MISSING_RESPONSE_WITH_FAILURE_RECEIPT')]:
        run=fresh(); row=package.schedule[0]
        result={'failure':kind,'receipt':{'call_id':row['call_id'],'request_sha256':row['request_sha256'],'failure_kind':kind}}
        checks.reject(lambda:run.perform(row,synthetic(lambda *_:result)),'valid_failure_receipts',kind,event)
        checks.check(run.state()['verdict']=='INCOMPLETE','valid_failure_receipts','not relabeled INVALID')
        terminal(run,'valid_failure_receipts')
    for payload in ([],None,0,1,'string',True,{}, {'journal_prefix':{}}, {'next_schedule_position':'1'}):
        run=fresh(); good=run.checkpoint()
        resumed=Run(package,run.directory,run.run_id,resume=True)
        bad=run.directory/'bad-checkpoint.json'
        write_once(bad,{'payload':payload,'sha256':digest(canonical(payload))})
        checks.reject(lambda:resumed.verify_resume(bad),'malformed_checkpoint',repr(payload),'CORRUPTED_CHECKPOINT')
        checks.reject(lambda:resumed.verify_resume(good),'malformed_checkpoint','later original cannot erase invalidity')
        terminal(resumed,'malformed_checkpoint')
    run=fresh(); cp=run.checkpoint(); resumed=Run(package,run.directory,run.run_id,resume=True)
    checks.reject(lambda:resumed.perform(package.schedule[0],unused),'resume_boundary','collection before verification')
    terminal(resumed,'resume_boundary')
    for key,value in [('schedule_position',2),('seed',0),('request_sha256','0'*64),('call_id','other')]:
        run=fresh(); row=copy.deepcopy(package.schedule[0]);row[key]=value
        checks.reject(lambda:run.perform(row,unused),'schedule_integrity',key)
        terminal(run,'schedule_integrity')
    run=fresh();run.perform(package.schedule[0],unused)
    checks.reject(lambda:run.perform(package.schedule[0],unused),'schedule_integrity','duplicate')
    terminal(run,'schedule_integrity')
    # Read-only fault injection exercises drift detection without changing protected bytes.
    run=fresh(); original=contract.file_digest
    target=next(iter(package.pins))
    contract.file_digest=lambda p:('0'*64 if Path(p)==ROOT/target else original(p))
    try:
        checks.reject(lambda:run.perform(package.schedule[0],unused),'manifest','precontact digest drift','PRE_ARTIFACT_DIGEST_MISMATCH')
    finally: contract.file_digest=original
    checks.check(run.state()['verdict']=='PRE_CONTACT_BLOCKED','manifest','precontact distinct')
    terminal(run,'manifest')
    for authorization in (None, {'status':'EXECUTION_FREEZE_CANDIDATE_ONLY'},
                          {'status':'EXPLICIT_OPERATOR_PHASE_AUTHORIZATION','phase':'A','run_id':'wrong','binding':{}}):
        checks.reject(lambda:authority(package,'CAL-NOT-A-REAL-RUN',None,authorization,None),
                      'live_authority','inactive G-CAL1 denies every live collection boundary')
    checks.check(not (DATA/'execution/ACTIVE_FREEZE.json').exists(),'live_authority','no activation artifact created')
    checks.reject(lambda:transport_boundary(lambda *_:None,False),'live_authority','unmarked synthetic callable cannot be live')
    unused.synthetic_only=True
    checks.reject(lambda:transport_boundary(unused,False),'live_authority','explicit synthetic callable cannot be live')
    unused.synthetic_only=False
    transport_boundary(unused,False)
    checks.check(True,'live_authority','only explicit non-synthetic transport reaches live boundary')
    checks.reject(lambda:transport_boundary(unused,'false'),'live_authority','truthy non-Boolean mode rejected')


def science_checks(package,checks):
    design=package.design
    for m in package.members.values():
        checks.check(allocation_ok(design,m['stratum'],m['slot'],m['source_date'],m['offset']),'allocation',m['fixture_id'])
        checks.check(primary_date(m['source_date'],m['offset'])==manual_date(m['source_date'],m['offset']),
                     'gold',m['fixture_id'])
        checks.check('.. Copy names' not in m['request']['prompt'] and not m['subject'].endswith('.'),
                     'prompt','periodless '+m['fixture_id'])
    # Century exceptions and signed stepping on a complete 400-year cycle.
    for year in range(2001,2401):
        for source in (f'{year:04d}-02-28',f'{year:04d}-03-01',f'{year:04d}-12-31'):
            for offset in (-367,-366,-365,-2,0,2,365,366,367):
                checks.check(primary_date(source,offset)==manual_date(source,offset),'gold_reference_cycle',source+'/'+str(offset))
    for offset in (-368,368):
        try: manual_date('2400-02-29',offset)
        except ValueError: checks.check(True,'gold_domain','reject '+str(offset))
        else: raise AssertionError('offset domain')
    observations={}
    for row in package.schedule:
        m=package.members[row['fixture_id']]
        raw=synthetic_gold(m); score=evaluate(m,raw)
        observations[row['call_id']]=score
        body=json.loads(package.wire(row))
        checks.check(digest(package.wire(row))==row['request_sha256'],'wire',row['call_id'])
        checks.check(set(body)=={'model','system','prompt','stream','think','options'} and
                     body['system']==package.baseline['system_text'] and body['options']['seed']==row['seed'] and
                     body['prompt']==m['request']['prompt']+'\n\nINPUT:\n'+canonical(m['request']['input']).decode(),
                     'wire','exact baseline materialization')
        checks.check(not any(label in body['prompt'] for label in ('WITHIN_MONTH_CONTROL','YEAR_BOUNDARY','LEAP_BOUNDARY','LONG_YEAR_OFFSET','G-CAL1')),
                     'wire','no difficulty or experiment labels')
    checks.check(len(package.schedule)==80 and len({x['call_id'] for x in package.schedule})==80 and
                 len({x['seed'] for x in package.schedule})==80,'schedule','80 unique requests/seeds')
    checks.check(all(sum(m['offset']>0 for m in package.members.values() if m['stratum']==s)==5 for s in ('C1','C2','C3','C4')),
                 'allocation','positive/negative balance')
    m=next(iter(package.members.values())); field=next(iter(m['gold']));gold=m['gold'][field]
    wrong=(date.fromisoformat(gold)+timedelta(days=1)).isoformat()
    wrong_raw=json.dumps({field:wrong})
    wrong_score=evaluate(m,wrong_raw)
    checks.check(wrong_score['false_clean'] and wrong_score['structural_valid'] and not wrong_score['semantic_correct'],'scorer','accepted wrong separate')
    checks.check('OFF_BY_ONE_DAY' in diagnosis(m,wrong_raw,wrong_score)['categories'],'taxonomy','observable one day difference')
    for raw in ('', 'not JSON','[]',json.dumps({field:3}),json.dumps({field:'2025-02-30'}), '{}', json.dumps({field:gold,'extra':'x'})):
        score=evaluate(m,raw)
        checks.check(not score['semantic_correct'],'scorer','reject wrong schema or syntax')
    duplicate='{"'+field+'":"'+gold+'","'+field+'":"'+gold+'"}'
    checks.check(evaluate(m,duplicate)['duplicate_key_present'] and not evaluate(m,duplicate)['semantic_correct'],
                 'scorer','duplicates have no semantic credit')
    checks.check(evaluate(m,synthetic_gold(m),truncated=True)['false_clean'],'scorer','accepted truncation false clean')
    checks.check(summarize(package,observations)['contrasts']['control_minus_boundary_fixture_accuracy']=={'numerator':0,'denominator':1},
                 'reduction','perfect all-strata baseline')
    for row in package.schedule:
        if row['stratum']=='C3': observations[row['call_id']]=dict(observations[row['call_id']],semantic_correct=False,false_clean=True)
    summary=summarize(package,observations)
    checks.check(summary['strata']['C3']['both_repeat_correct']==0 and summary['strata']['C3']['correlated_false_clean_pairs']==10 and
                 summary['strata']['C3']['false_clean_observations']==20 and summary['strata']['C3']['false_clean_fixtures']==10,
                 'reduction','both vs either vs correlated')
    checks.check(summary['contrasts']['control_minus_boundary_fixture_accuracy']=={'numerator':1,'denominator':3} and
                 summary['qualification_gates'] is None,'reduction','exact descriptive contrast, no inherited gates')


def main():
    from g_cal1_repair_tests import attacks, deny_network, science_replay
    import sys
    sys.addaudithook(deny_network)
    package=Package();checks=Checks()
    science_checks(package,checks)
    out=DATA/'preexecution/lifecycle_repair'
    adversarial(package,checks,out/'established_regression_attempt02')
    attacks(package,checks,out/'targeted_attacks_attempt02')
    science_replay(package,checks)
    a=out/'pilot_one';b=out/'pilot_two'
    full_pilot(package,a,checks);full_pilot(package,b,checks)
    ta,tb=tree(a),tree(b)
    checks.check(ta==tb,'determinism','complete two-pilot trees byte-identical')
    after=preservation_snapshot();before=load(DATA/'PRESERVATION_BEFORE.json')
    checks.check(before==after,'preservation','protected science, complete prior real execution, closure and seven untracked artifacts byte-identical')
    write_once(out/'PRESERVATION_REPORT.json',{'files':len(before),'before':before,'after':after,'byte_identical':before==after,
        'G-EXTRACT1':'CLOSED VALID NEGATIVE','G-ROUTE4':'CLOSED FAILED'})
    categories={k:sum(x['category']==k for x in checks.rows) for k in sorted({x['category'] for x in checks.rows})}
    report={'schema_version':'g-cal1.mechanical-pilot.v1','verdict':'PASS','checks':len(checks.rows),'categories':categories,
            'assertions':checks.rows,'synthetic_observations_each_pilot':80,'two_pilot_trees_identical':ta==tb,
            'authority_evidence_files_each_tree':len(ta),'pilot_tree':ta,'provider_model_calls':0,'real_observations':0,
            'freeze_active':False,'execution_authorized':False,'audit_pending':True}
    write_once(out/'PILOT_REPORT.json',report)
    receipts=package.historical.receipts()
    candidate={'schema_version':'g-cal1.execution-freeze-candidate.v1','experiment':'G-CAL1','status':'EXECUTION_FREEZE_CANDIDATE_ONLY',
        'activated':False,'binding':package.binding,'protected_artifacts':package.pins,
        'schedule':{'count':80,'sha256':digest(canonical(package.schedule))},
        'provider_binding':dict(receipts,models=[receipts['models'][2]]),
        'journal_checkpoint_schema':SCHEMA,'journal_checkpoint_schema_sha256':digest(canonical(SCHEMA)),
        'pilot_report_sha256':file_digest(out/'PILOT_REPORT.json'),
        'preservation_report_sha256':file_digest(out/'PRESERVATION_REPORT.json'),
        'supersedes_unactivated_initial_candidate_sha256':file_digest(DATA/'preexecution/EXECUTION_FREEZE_CANDIDATE.json'),
        'prior_blocked_candidate_sha256':file_digest(DATA/'preexecution/final/EXECUTION_FREEZE_CANDIDATE.json'),
        'prior_blocked_audit_sha256':file_digest(DATA/'audit/INDEPENDENT_PREREGISTRATION_AUDIT.json'),
        'authority':'candidate only; separate independent audit, freeze review, explicit activation and CAL authorization required',
        'execution_authorized':False,'provider_model_calls':0,'autonomy':False,'belief_effects':'none'}
    write_once(out/'EXECUTION_FREEZE_CANDIDATE.json',candidate)
    print(json.dumps({'verdict':'PASS','checks':len(checks.rows),'two_pilots':ta==tb,'files_each':len(ta),
                      'schedule_sha256':digest(canonical(package.schedule)),
                      'candidate_sha256':file_digest(out/'EXECUTION_FREEZE_CANDIDATE.json')}))


if __name__=='__main__': main()
