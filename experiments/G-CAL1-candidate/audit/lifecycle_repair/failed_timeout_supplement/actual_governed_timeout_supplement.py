"""Only the pending supplement of the existing G-CAL1 independent review.

Real configured 120-second timeout, independent Run A/B/C, no clock patch.
No core replay, repository scan, previous evidence replacement, or network.
"""
import copy
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
REPO=Path('C:/Users/marcu/Eidolon-g4adj')
sys.dont_write_bytecode=True
tempfile.tempdir=str(OUT)
os.environ['TMP']=os.environ['TEMP']=str(OUT)
def deny(event,args):
    if event.startswith('socket.'):
        raise RuntimeError('SUPPLEMENT_NETWORK_DENIED:'+event)
    if event=='open':
        mode,flags=args[1],args[2]
        writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and isinstance(args[0],(str,bytes,os.PathLike)) and not Path(os.fsdecode(args[0])).absolute().is_relative_to(OUT):
            raise RuntimeError('SUPPLEMENT_EXTERNAL_ONLY')
    if event in ('os.mkdir','os.remove','os.rmdir','os.utime','os.chmod') and not Path(args[0]).absolute().is_relative_to(OUT):
        raise RuntimeError('SUPPLEMENT_EXTERNAL_ONLY')
sys.addaudithook(deny)
sys.path.insert(0,str(REPO/'tools'))
from g_cal1_contract import Package
from g_cal1_lab import Run
from g_extract1_contract import IntegrityError, canonical, file_digest
from g_extract1_journal import Journal, write_once
from g_extract1_scoring import event_category

RAW=OUT/'raw'/'actual_governed_timeout_supplement'
chain=Journal(RAW/'observations')
RUN_ID='SAME-AUDIT-ACTUAL-GOVERNED-TIMEOUT'
p=Package()
category=event_category(p.historical.design,'PROVENANCE_MISMATCH')
if category!='INVALID':
    raise RuntimeError('Ambiguous or changed frozen category; stop without running supplement')
A=Run(p,RAW/'run',RUN_ID)
cp=A.checkpoint()
B=Run(p,A.directory,RUN_ID,resume=True);B.verify_resume(cp)
C=Run(p,A.directory,RUN_ID,resume=True);C.verify_resume(cp)
chain.append({'kind':'PRECONTENTION_OBJECTS','independent_A_B_C':len({id(A),id(B),id(C)})==3,
              'same_directory':A.directory==B.directory==C.directory,'run_id':RUN_ID,
              'binding':B.binding,'phase':'CAL','next_row':p.schedule[0],
              'frozen_timeout_event':'PROVENANCE_MISMATCH','frozen_category':category,
              'all_resume_objects_verified_before_contention':True})
before=A.journal.read()
held=threading.Event();release=threading.Event();done=threading.Event();holder_result=[]
class HolderCleanup(BaseException):
    """Unwind paused pre-START holder after release without a later mutation."""
ready=A._ready
def held_ready():
    ready()
    held.set()
    if not release.wait(180):raise HolderCleanup('watchdog release')
    raise HolderCleanup('authorized cleanup after observed timeout')
def holder():
    try:
        with patch.object(A,'_ready',held_ready):
            A.checkpoint()
    except HolderCleanup as exc:
        holder_result.append({'cleanup':str(exc),'checkpoint_not_appended':True})
    except BaseException as exc:
        holder_result.append({'unexpected':type(exc).__name__+':'+str(exc)})
    finally:done.set()
thread=threading.Thread(target=holder,name='governed-Run-A-lock-holder')
thread.start()
if not held.wait(15):
    release.set();thread.join(15)
    raise RuntimeError('A failed to reach actual governed locked region')
chain.append({'kind':'A_GOVERNED_LOCK_HELD','public_method':'Run.checkpoint',
              'paused_at':'_ready after genuine synchronization and readiness under unchanged governed OS lock',
              'B_method':'Run.perform','C_predates_timeout':True,'deadline_or_lock_implementation_patched':False})
counter=[]
def transport(request,row):
    counter.append(row['call_id'])
    return {'raw_output':canonical(p.members[row['fixture_id']]['gold']).decode(),
            'provider_truncated':False,'receipt':{'call_id':row['call_id'],
            'request_sha256':row['request_sha256'],'synthetic_only':True}}
transport.synthetic_only=True
error=None;finding=None;verdict='INCOMPLETE'
continuations={key:'NOT_PERFORMED' for key in ('external_catch_same_object','stale_C','restart_reconstruction','after_release_same_object')}
start=time.monotonic()
print('ACTUAL_GOVERNED_TIMEOUT_STARTED: unmodified 120-second deadline',flush=True)
try:
    try:B.perform(copy.deepcopy(p.schedule[0]),transport)
    except IntegrityError as exc:error=exc
    elapsed=time.monotonic()-start
    incidents=B.incidents.read();records=B.journal.read()
    observed={'elapsed_monotonic_seconds':elapsed,'actual_lock_holder_still_active':not done.is_set(),
              'exception':None if error is None else {'event':error.event,'detail':error.detail},
              'transport_invocations':len(counter),'state_B_at_external_catch':B.state(),
              'events_B':list(B.events),'incidents':incidents,'journal':records,
              'journal_unchanged_from_before_contention':records==before}
    chain.append({'kind':'EXTERNAL_CATCH_OBSERVATION','observed':observed})
    real_timeout=error is not None and error.event=='PROVENANCE_MISMATCH' and error.detail=='run operation lock unavailable' and elapsed>=119.9 and not done.is_set()
    retained=bool(incidents) and any(r['payload']['event']=='PROVENANCE_MISMATCH' and
        r['payload']['run_id']==RUN_ID and r['payload']['binding']==B.binding and
        r['payload']['phase']=='CAL' and r['payload']['cell'] in (None,p.schedule[0]['cell_id']) for r in incidents)
    if not real_timeout or counter or not retained:
        verdict='BLOCKED'
        finding={'id':'F-ACTUAL-GOVERNED-LOCK-TIMEOUT','severity':'P1','blocking':True,
            'title':'Actual configured governed-lock timeout lacks the required terminal INVALID incident' if real_timeout and not retained else 'Actual governed timeout required property failed',
            'file':str(REPO/'tools/g_cal1_lab.py'),'line':24,'end_line':30,
            'related_location':{'file':str(REPO/'tools/g_cal1_lock.py'),'line':35,'end_line':36},
            'frozen_event':'PROVENANCE_MISMATCH','frozen_category':category,
            'observed':observed,'cause':'run_lock entry is outside governed try/except IntegrityError retention block',
            'post_finding_product_tests':0}
        continuations={key:'NOT_PERFORMED_STOP_ON_FIRST_P1' for key in continuations}
        print('SUPPLEMENT_BLOCKED: '+finding['title'],flush=True)
    else:
        verdict='PASS'
finally:
    release.set();thread.join(15)
    chain.append({'kind':'A_LOCK_RELEASE_CLEANUP','holder_done':done.is_set(),'holder_result':holder_result,
                  'no_holder_checkpoint_mutation_after_timeout':A.journal.read()==before,
                  'cleanup_only_not_post_finding_product_test':True})

# No further governed product operation after a demonstrated P1. The pass-only
# branch completes the expressly requested terminality checks if retention exists.
if verdict=='PASS':
    def terminal(action,name):
        try:action()
        except IntegrityError as exc:
            continuations[name]={'rejected':True,'event':exc.event,'transport_invocations':len(counter)}
            return exc.event=='PROVENANCE_MISMATCH' and not counter
        continuations[name]={'rejected':False,'transport_invocations':len(counter)}
        return False
    for name,action in (
        ('external_catch_same_object',lambda:B.perform(copy.deepcopy(p.schedule[0]),transport)),
        ('stale_C',lambda:C.perform(copy.deepcopy(p.schedule[0]),transport)),
        ('restart_reconstruction',lambda:Run(p,A.directory,RUN_ID,resume=True)),
        ('after_release_same_object',lambda:B.perform(copy.deepcopy(p.schedule[0]),transport))):
        if not terminal(action,name):
            verdict='BLOCKED';finding={'severity':'P1','blocking':True,'title':'Continuation accepted after frozen INVALID timeout',
                'file':str(REPO/'tools/g_cal1_lab.py'),'line':133,'failed_check':name}
            break
final_records=B.journal.read()
starts=[r['payload'] for r in final_records if r['payload'].get('kind')=='START']
result={'schema_version':'g-cal1.same-audit.actual-governed-timeout-supplement.v1',
    'independent_audits_total':1,'new_independent_audits':0,'core_audit_verdict':'PASS','core_assertions':28209,
    'local_review_history_basis':'00f15f88ffec6295e1c14917f85df9970489b8c3',
    'candidate_sha256':'f45825a0165f23b78da13fb0fec8dcade010b37fadbe7cdc8c2020a05b0f0336',
    'candidate_rebound':False,'supplement_verdict':verdict,'overall_review_verdict':verdict,
    'finding':finding,'actual_configured_timeout_observed':real_timeout,'configured_timeout_seconds':120,
    'clock_or_timeout_exception_injection':False,'independent_objects_A_B_C_preconstructed':True,
    'timeout_event':None if error is None else error.event,'frozen_timeout_category':category,
    'retained_incident_count':len(incidents),'contractually_bound_timeout_incident_retained':retained,
    'transport_invocations':len(counter),'timeout_observation':observed,'continuation_results':continuations,
    'lock_released':done.is_set(),'lock_release_continuation_tested':continuations['after_release_same_object']!='NOT_PERFORMED_STOP_ON_FIRST_P1',
    'START_count':len(starts),'open_START_count':0 if not starts else 'NOT_INFERRED',
    'fabricated_provider_receipts':False,'raw_evidence_directory':str(RAW),'observation_chain_tip':chain.prefix(),
    'repository_scan_or_rehash_performed':False,'old_reports_or_evidence_modified':False,
    'repository_writes':0,'implementation_edits':0,'post_finding_product_tests':0,
    'provider_model_calls':0,'provider_network_queries':0,'freeze_active':False,'execution_authorized':False,
    'completion_commit_created':False,'push_performed':False,'autonomy':False,'belief_effects':'none',
    'limitations':['Stopped at first P1; same-object/stale/restart continuation properties marked unperformed when blocked.',
                   'Parent handles fresh preservation verification and completion/status artifacts; no stale snapshot comparison.',
                   'Holder uses a pre-START readiness pause and BaseException cleanup to release its actual governed lock without a later checkpoint mutation.']}
write_once(RAW/'SUPPLEMENT_RESULT.json',result)
files={str(Path(__file__).name):file_digest(Path(__file__))}
files.update({f'raw/actual_governed_timeout_supplement/{x.relative_to(RAW).as_posix()}':file_digest(x) for x in sorted(RAW.rglob('*')) if x.is_file()})
write_once(RAW/'SUPPLEMENT_HASH_MANIFEST.json',{'schema':'same-audit.minimal-supplement.sha256.v1',
    'files':files,'self_excluded':True,'result_sha256':file_digest(RAW/'SUPPLEMENT_RESULT.json'),
    'observation_chain_tip':chain.prefix()})
print(canonical({'supplement_verdict':verdict,'event':None if error is None else error.event,'category':category,
    'elapsed_seconds':elapsed,'retained_incidents':len(incidents),'transport_invocations':len(counter),
    'START_count':len(starts),'result':str(RAW/'SUPPLEMENT_RESULT.json'),
    'result_sha256':file_digest(RAW/'SUPPLEMENT_RESULT.json'),
    'manifest':str(RAW/'SUPPLEMENT_HASH_MANIFEST.json'),
    'manifest_sha256':file_digest(RAW/'SUPPLEMENT_HASH_MANIFEST.json')}).decode(),flush=True)
sys.exit(2 if verdict=='BLOCKED' else 0)
