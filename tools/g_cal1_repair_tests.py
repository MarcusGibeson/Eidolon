"""Direct offline regression for the four G-CAL1 independent audit findings."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from unittest.mock import patch

import g_cal1_contract as contract
import g_cal1_lab as lab
from g_cal1_contract import DATA, ROOT, Package
from g_cal1_lab import Run
from g_cal1_pilot import Checks, success, synthetic
from g_cal1_stage import evidence, historical_rejection, history_records, independent_historical_rejection, old_checkers
from g_extract1_contract import IntegrityError, canonical, digest, file_digest, load
from g_extract1_journal import write_once

OMISSION = 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT'


def deny_network(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.bind'):
        raise RuntimeError('NO_PROVIDER_NETWORK_BOUNDARY')


def attacks(package,checks,root):
    calls=[]; counter=0
    @synthetic
    def good(request,row):
        calls.append(row['call_id'])
        return success(package,request,row)
    def fresh(name,p=None):
        nonlocal counter
        counter+=1
        return Run(p or package,root/f'{counter:03d}-{name}',f'G-CAL1-SYNTHETIC-{name}-{counter}')
    def kinds(run):return [r['payload']['kind'] for r in run.journal.read()]
    def terminal(run,category,event):
        before=len(calls); starts=kinds(run).count('START')
        checks.reject(lambda:run.perform(package.schedule[min(len(run.attempted),79)],good),category,'post-catch collection',event)
        checks.check(len(calls)==before and kinds(run).count('START')==starts,category,'zero later calls/START')
        checks.check(event in run.events and any(r['payload']['event']==event for r in run.incidents.read()),category,'retained in memory and on disk')
        checks.reject(lambda:Run(run.package,run.directory,run.run_id,resume=True),category,'restart rejects',event)

    # Exact former stale-object finding; also verify every guarded boundary.
    for operation in ('perform','checkpoint','verify_resume','final_report'):
        a=fresh('stale-'+operation); cp=a.checkpoint()
        b=Run(package,a.directory,a.run_id,resume=True)
        bad=a.directory/'bad-checkpoint.json'
        write_once(bad,{'payload':[],'sha256':digest(canonical([]))})
        checks.reject(lambda:b.verify_resume(bad),'P1_A',operation+' corrupt owner','CORRUPTED_CHECKPOINT')
        actions={'perform':lambda:a.perform(package.schedule[0],good),'checkpoint':a.checkpoint,
                 'verify_resume':lambda:a.verify_resume(cp),'final_report':a.final_report}
        checks.reject(actions[operation],'P1_A','stale '+operation,'CORRUPTED_CHECKPOINT')
        terminal(a,'P1_A','CORRUPTED_CHECKPOINT')
    a=fresh('stale-duplicate');cp=a.checkpoint();b=Run(package,a.directory,a.run_id,resume=True)
    b.verify_resume(cp);b.perform(package.schedule[0],good)
    before=len(calls)
    checks.reject(lambda:a.perform(package.schedule[0],good),'P1_A','stale duplicate')
    checks.check(len(calls)==before and kinds(a).count('START')==1,'P1_A','authoritative position prevents duplicate')
    a=fresh('stale-checkpoint');cp=a.checkpoint();b=Run(package,a.directory,a.run_id,resume=True)
    a.perform(package.schedule[0],good)
    checks.reject(lambda:b.verify_resume(cp),'P1_A','checkpoint cannot verify stale state')
    terminal(b,'P1_A',b.events[0])

    # Second object cannot retain invalidity between ready and transport.
    a=fresh('thread-race');cp=a.checkpoint();b=Run(package,a.directory,a.run_id,resume=True)
    bad=a.directory/'bad-checkpoint.json';write_once(bad,{'payload':None,'sha256':digest(canonical(None))})
    attempted=threading.Event();done=threading.Event();errors=[]
    def invalidator():
        attempted.set()
        try:b.verify_resume(bad)
        except IntegrityError as exc:errors.append(exc.event)
        finally:done.set()
    original=lab.transport_boundary;workers=[]
    def coordinated(transport,mechanical):
        original(transport,mechanical)
        t=threading.Thread(target=invalidator);workers.append(t);t.start()
        checks.check(attempted.wait(10),'P1_A_RACE','other object attempts mutation')
        checks.check(not done.wait(0.1) and not a.incidents.read(),'P1_A_RACE','lock holds ready-to-transport region')
    with patch.object(lab,'transport_boundary',coordinated):a.perform(package.schedule[0],good)
    workers[0].join(10)
    checks.check(done.is_set() and errors==['CORRUPTED_CHECKPOINT'],'P1_A_RACE','invalidity persists only after call closure')
    terminal(a,'P1_A_RACE','CORRUPTED_CHECKPOINT')

    # Separate-process serialization uses the same stable OS lock namespace.
    a=fresh('process-race');a.checkpoint();children=[]
    def process_boundary(transport,mechanical):
        original(transport,mechanical)
        child=subprocess.Popen([sys.executable,'-B',__file__,'--retain',str(a.directory),a.run_id],
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        children.append(child)
        checks.check(child.stdout.readline().strip()=='ATTEMPTING','P1_A_PROCESS','child starts independent boundary')
        try:child.wait(timeout=0.15)
        except subprocess.TimeoutExpired:checks.check(not a.incidents.read(),'P1_A_PROCESS','child cannot retain inside parent critical section')
        else:raise AssertionError('child crossed active lock')
    with patch.object(lab,'transport_boundary',process_boundary):a.perform(package.schedule[0],good)
    stdout,stderr=children[0].communicate(timeout=30)
    checks.check(children[0].returncode==0 and 'RETAINED' in stdout,'P1_A_PROCESS','child acquires after closure:'+stderr)
    terminal(a,'P1_A_PROCESS','CORRUPTED_CHECKPOINT')

    class Control(BaseException):pass
    for exception_type in (KeyboardInterrupt,SystemExit,GeneratorExit,Control):
        for point in ('transport','normalization','receipt','scoring','before_complete','after_complete'):
            r=fresh(exception_type.__name__+'-'+point);signal=exception_type('original-control-signal')
            old_normalize=lab.transport_outcome;old_evaluate=lab.evaluate;old_append=r.journal.append
            @synthetic
            def returned(request,row):
                if point=='transport':raise signal
                value=success(package,request,row)
                if point=='receipt':
                    class Bomb(list):
                        def __iter__(self):raise signal
                    value['receipt']['extra']=Bomb([1])
                return value
            def normalize(row,value):
                if point=='normalization':raise signal
                return old_normalize(row,value)
            def scoring(*args,**kwargs):
                if point=='scoring':raise signal
                return old_evaluate(*args,**kwargs)
            def append(payload):
                if payload['kind']=='COMPLETE' and point=='before_complete':raise signal
                value=old_append(payload)
                if payload['kind']=='COMPLETE' and point=='after_complete':raise signal
                return value
            with patch.object(lab,'transport_outcome',normalize),patch.object(lab,'evaluate',scoring),patch.object(r.journal,'append',append):
                try:r.perform(package.schedule[0],returned)
                except BaseException as caught:
                    checks.check(caught is signal and caught.args==signal.args,'P1_B',exception_type.__name__+'/'+point+' original propagation')
                else:raise AssertionError('signal not raised')
            if point=='after_complete':
                checks.check(kinds(r)==['RUN_CREATED','START','COMPLETE'] and not r.incidents.read(),'P1_B_POST_COMPLETE','no false omission')
                # Disk closure must be replayed before using in-memory position.
                r.perform(package.schedule[1],good)
                checks.check(len(r.evidence)==2 and len(r.attempted)==2,'P1_B_POST_COMPLETE','safe synchronization permits next call')
                cp=r.checkpoint();restart=Run(package,r.directory,r.run_id,resume=True);restart.verify_resume(cp)
                checks.check(restart.evidence==r.evidence,'P1_B_POST_COMPLETE','restart and live replay agree')
            else:
                checks.check(r.events==[OMISSION] and kinds(r)==['RUN_CREATED','START'],'P1_B','omission before escape; no fake receipt')
                checks.check(r.event_scopes==[{'event':OMISSION,'phase':'CAL','cell':package.schedule[0]['cell_id']}],
                             'P1_B','exact phase/cell scope')
                terminal(r,'P1_B',OMISSION)

    for mutation in ('order','seed','hash','date','offset','gold','fixture','design','baseline','pins'):
        p=Package();r=fresh('cache-'+mutation,p);row=copy.deepcopy(p.schedule[0]);member=p.members[row['fixture_id']]
        if mutation=='order':p.schedule.reverse()
        elif mutation=='seed':p.schedule[0]['seed']=0
        elif mutation=='hash':p.schedule[0]['request_sha256']='0'*64
        elif mutation=='date':member['source_date']='2051-01-01'
        elif mutation=='offset':member['offset']=1
        elif mutation=='gold':member['gold'][next(iter(member['gold']))]='2051-01-01'
        elif mutation=='fixture':member['fixture']['gold_values'][next(iter(member['gold']))]='2051-01-01'
        elif mutation=='design':p.design['generation_configuration']['temperature']=0
        elif mutation=='baseline':p.baseline['system_text']='mutated'
        elif mutation=='pins':p.pins.clear()
        checks.reject(lambda:r.perform(row,good),'P1_C','cache '+mutation,'PRE_ARTIFACT_DIGEST_MISMATCH')
        checks.check(kinds(r)==['RUN_CREATED'],'P1_C',mutation+' zero START')
    r=fresh('callback-alias');before=canonical(package.schedule)
    @synthetic
    def callback(request,row):
        result=success(package,request,row);row['seed']=0;row['generation_configuration']['temperature']=0
        return result
    score=r.perform(package.schedule[0],callback)
    checks.check(canonical(package.schedule)==before and score['semantic_correct'],'P1_C','callback gets detached row/config')
    r.perform(package.schedule[1],good)
    checks.check(len(r.evidence)==2,'P1_C','detached alias preserves next request')
    # Real disk drift is injected into an external shadow package only.
    shadow=root/'shadow';shadow.mkdir()
    for name in package.pins:
        path=shadow/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    shutil.copyfile(DATA/'LAB_MANIFEST.json',shadow/'experiments/G-CAL1-candidate/LAB_MANIFEST.json')
    with patch.object(contract,'ROOT',shadow),patch.object(contract,'DATA',shadow/'experiments/G-CAL1-candidate'):
        p=Package();r=fresh('disk-stale-cache',p)
        (contract.DATA/'corpus/CORPUS.json').write_bytes(b'{}')
        before=len(calls)
        checks.reject(lambda:r.perform(package.schedule[0],good),'P1_C_DISK','external cloned disk changed/cache valid','PRE_ARTIFACT_DIGEST_MISMATCH')
        checks.check(len(calls)==before and kinds(r)==['RUN_CREATED'],'P1_C_DISK','zero transport on actual disk drift')

    for marker in ('ABSENT',False,1,'true',None):
        r=fresh('mechanical-marker');invoked=[]
        def fake(request,row):invoked.append(1);return success(package,request,row)
        if marker!='ABSENT':fake.synthetic_only=marker
        checks.reject(lambda:r.perform(package.schedule[0],fake),'P1_D','marker '+repr(marker),'PROVENANCE_MISMATCH')
        checks.check(not invoked and kinds(r)==['RUN_CREATED'],'P1_D','no START/transport')
    class ProviderLike:
        synthetic_only=False
        def __call__(self,*args):raise AssertionError('provider-like adapter was invoked')
    for fake in (ProviderLike(),lambda *args:ProviderLike()(*args)):
        r=fresh('mechanical-wrapper');checks.reject(lambda:r.perform(package.schedule[0],fake),'P1_D','adapter/wrapper denied')
        checks.check(kinds(r)==['RUN_CREATED'],'P1_D','adapter/wrapper zero START')
    r=fresh('positive-synthetic');r.perform(package.schedule[0],good)
    checks.check(len(r.evidence)==1,'P1_D','explicit True synthetic accepted')
    for grant in (None,{'status':'EXECUTION_FREEZE_CANDIDATE_ONLY'},
                  {'status':'EXPLICIT_OPERATOR_PHASE_AUTHORIZATION','phase':'CAL','run_id':'wrong','binding':{}}):
        checks.reject(lambda:Run(package,root/'forbidden-live','NOT-A-REAL-RUN',mechanical=False,authorization=grant),
                      'REAL_AUTHORITY','inactive freeze denies collection before directory creation')
    checks.check(not (root/'forbidden-live').exists(),'REAL_AUTHORITY','no real run/transport/authority created')


def science_replay(package,checks):
    primary,independent=old_checkers()
    histories,_,source_dates,gold_dates,counts=history_records(package.historical,primary,independent)
    c=package.historical.design
    new=[evidence(m,c,primary,independent) for m in package.members.values()]
    original=load(DATA/'corpus/CONTAMINATION_REPORT.json');actual=[]
    for member,a in zip(package.members.values(),new):
        gold=next(iter(member['gold'].values()))
        checks.check(member['source_date'] not in source_dates|gold_dates and gold not in source_dates|gold_dates,'science_freshness',member['fixture_id'])
        for h in histories:
            left,right=historical_rejection(a,h),independent_historical_rejection(a,h)
            checks.check(left is None and left==right,'historical_contamination',a['id']+'/'+h['id'])
            actual.append({'new':a['id'],'historical':h['id'],'ordinary_i_u':[len(a['ordinary']&h['ordinary']),len(a['ordinary']|h['ordinary'])],
                           'projection_matches':sum(x==y for x,y in zip(a['projection'],h['projection'])),
                           'tuple_applicability':h['tuple_applicability'],'gate':True})
    checks.check(actual==original['historical_pairs'],'science_replay','12,720 exact pair results unchanged')
    invariant={tuple(x) for x in original['invariant_five_grams']};pairs=[]
    from itertools import combinations
    for a,b in combinations(new,2):
        left,right=a['ordinary']-invariant,b['ordinary']-invariant;i,u=len(left&right),len(left|right)
        checks.check(bool(left and right) and 25*i<3*u and all(a[k]!=b[k] for k in ('tuple','raw_values','answer','raw_payload')),
                     'new_contamination',a['id']+'/'+b['id'])
        pairs.append({'left':a['id'],'right':b['id'],'mode':'DECLARED_SCAFFOLD_RESIDUAL',
                      'ordinary_i_u':[len(a['ordinary']&b['ordinary']),len(a['ordinary']|b['ordinary'])],
                      'shape_i_u':[len(a['shape']&b['shape']),len(a['shape']|b['shape'])],
                      'content_i_u':[len(a['content']&b['content']),len(a['content']|b['content'])],
                      'residual_i_u':[i,u],'residual_gate':True,'ordinary_gate_credited':False,
                      'full_fingerprint_equal':a['fp']==b['fp'],'tuple_applicability':'APPLIES'})
    checks.check(pairs==original['new_pairs'] and len(pairs)==780,'science_replay','NEW/NEW exact results unchanged')
    checks.check(sum(h['tuple_applicability']=='NOT_APPLICABLE_UNREPRESENTABLE_HISTORICAL_PROVENANCE' for h in histories)*40==5040 and original['not_applicable_credited_as_pass'] is False,
                 'science_replay','5,040 unavailable tuple controls receive no pass credit')
    checks.check(counts['G-ROUTE4-candidate']==106,'science_replay','historical adapter 106/106, no rejection')
    checks.check(digest(canonical(package.schedule))=='b4d4a5a7ba37961dcfbbe0c6aa6101fbbeb40dcf2dad0c54c8680d216c2e1858',
                 'science_replay','80-call schedule byte identity')


if __name__=='__main__':
    sys.addaudithook(deny_network)
    if sys.argv[1:2]==['--retain']:
        print('ATTEMPTING',flush=True)
        run=Run(Package(),Path(sys.argv[2]),sys.argv[3],resume=True)
        run._retain(IntegrityError('CORRUPTED_CHECKPOINT','cross-process synthetic incident'))
        print('RETAINED',flush=True)
    else:
        raise SystemExit('test functions are invoked by g_cal1_pilot.py')
