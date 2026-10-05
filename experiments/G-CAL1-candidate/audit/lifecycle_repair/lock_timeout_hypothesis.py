"""User-requested extra hypothesis in the SAME independent audit, not a second review.

Run after audit.py's initial closure stages finish. No provider/network activity.
For a standalone reproduction, copy this script to a fresh external directory;
the product reproduction does not require the prior report, only final reporting does.
"""
import copy
import json
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
    if event.startswith('socket.'):raise RuntimeError('AUDIT_NETWORK_DENIED:'+event)
    if event=='open':
        mode,flags=args[1],args[2]
        if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            if isinstance(args[0],(str,bytes,os.PathLike)) and not Path(os.fsdecode(args[0])).absolute().is_relative_to(OUT):raise RuntimeError('WRITE_OUTSIDE_AUDIT')
    if event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime'):
        if not Path(args[0]).absolute().is_relative_to(OUT):raise RuntimeError('MUTATION_OUTSIDE_AUDIT')
sys.addaudithook(deny)
sys.path.insert(0,str(REPO/'tools'))
import g_cal1_lock as lock
from g_cal1_contract import Package
from g_cal1_lab import Run
from g_extract1_contract import IntegrityError, canonical, file_digest, load
from g_extract1_journal import Journal, write_once
from g_extract1_scoring import event_category

RAW=OUT/'raw'
chain=Journal(RAW/'lock_timeout_hypothesis_chain')
package=Package()
run=Run(package,RAW/'busy-lock-timeout','SAME-INDEPENDENT-AUDIT-BUSY-LOCK')
held=threading.Event();release=threading.Event();holder_done=threading.Event();holder_errors=[]
def holder():
    try:
        with lock.run_lock(run.directory):
            held.set()
            if not release.wait(15):raise RuntimeError('holder release timeout')
    except BaseException as exc:holder_errors.append(type(exc).__name__+':'+str(exc))
    finally:holder_done.set()

thread=threading.Thread(target=holder,name='actual-OS-lock-holder')
thread.start()
if not held.wait(10):raise RuntimeError('real OS lock not acquired by holder')
chain.append({'kind':'HOLDER_CONFIRMED','second_thread_holds_real_OS_lock':True,'platform':os.name})
calls=[]
def synthetic(request,row):
    calls.append(row['call_id'])
    return {'raw_output':canonical(package.members[row['fixture_id']]['gold']).decode(),'provider_truncated':False,
            'receipt':{'call_id':row['call_id'],'request_sha256':row['request_sha256'],'synthetic_only':True}}
synthetic.synthetic_only=True
clock_reads=[]
def bounded_clock():
    value=0.0 if not clock_reads else 121.0
    clock_reads.append({'thread':threading.current_thread().name,'value':value})
    return value
error=None
start=time.perf_counter()
try:
    with patch.object(lock.time,'monotonic',bounded_clock):
        try:run.perform(copy.deepcopy(package.schedule[0]),synthetic)
        except IntegrityError as exc:error=exc
    after_timeout={'exception':None if error is None else {'event':error.event,'detail':error.detail},
        'clock_reads':clock_reads,'elapsed_real_seconds':time.perf_counter()-start,
        'holder_still_holds_lock':not holder_done.is_set(),'transport_calls':len(calls),
        'state':run.state(),'incidents':run.incidents.read(),'journal':run.journal.read()}
    chain.append({'kind':'TIMED_OUT_PUBLIC_PERFORM','observed':after_timeout})
finally:
    release.set();thread.join(15)
if not holder_done.is_set() or holder_errors:raise RuntimeError('holder not released normally:'+str(holder_errors))
chain.append({'kind':'REAL_OS_LOCK_RELEASED','holder_done':True,'holder_errors':holder_errors})
if error is None or error.event!='PROVENANCE_MISMATCH' or error.detail!='run operation lock unavailable' or len(clock_reads)!=2:
    raise RuntimeError('Did not exercise the specific actual busy-lock timeout branch')
frozen_category=event_category(package.historical.design,error.event)

# This single post-catch collection is the minimal reproduction of the hypothesized
# lifecycle escape. Stop all product operations immediately once it establishes P1.
continued_error=None
try:run.perform(copy.deepcopy(package.schedule[0]),synthetic)
except IntegrityError as exc:continued_error={'event':exc.event,'detail':exc.detail}
after_release={'continued_error':continued_error,'transport_calls':len(calls),'call_ids':calls,
               'state':run.state(),'incidents':run.incidents.read(),'journal':run.journal.read()}
chain.append({'kind':'POST_CATCH_COLLECTION_AFTER_RELEASE','observed':after_release,'frozen_event_category':frozen_category})
blocked=frozen_category=='INVALID' and not after_timeout['incidents'] and len(calls)==1 and continued_error is None
finding=None
if blocked:
    finding={'id':'F-LOCK-TIMEOUT','severity':'P1','blocking':True,
      'title':'Busy-lock timeout escapes terminal retention; catching it permits later collection on the same run',
      'file':str(REPO/'tools/g_cal1_lab.py'),'line':24,'end_line':30,
      'related_locations':[{'file':str(REPO/'tools/g_cal1_lock.py'),'line':35,'end_line':36},
                           {'file':str(REPO/'experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json'),'line':7807}],
      'reproduction':'Construct mechanical Run in fresh external directory; second thread acquires actual OS run lock. '
                     'Fault-inject only monotonic deadline reads 0 then 121; call public perform. Catch PROVENANCE_MISMATCH '
                     '(run operation lock unavailable). Restore clock, release holder, call public perform on the same row.',
      'observed':'Timeout propagates with no retained incident, no START and RUNNING state. After OS lock release, the '
                 'same Run invokes its marked synthetic callback once and durably appends START/COMPLETE, still with '
                 'zero incidents and RUNNING state.',
      'frozen_semantics':'PROVENANCE_MISMATCH is INVALID in the inherited frozen integrity_event_contract, not a retryable '
                         'busy/incomplete event. G-CAL1 preserves that event catalog. This is loss of terminal integrity '
                         'evidence, not a claim of duplicate provider contact or authorized live execution.',
      'cause':'governed() enters run_lock outside its try/except IntegrityError retention boundary. A __enter__ timeout '
              'never reaches self._retain(); subsequent synchronization sees no terminal evidence.',
      'evidence':str(RAW/'lock_timeout_hypothesis_chain'),
      'post_finding_product_operations':0}
result={'audit_count':1,'same_audit_user_requested_hypothesis':True,'verdict':'BLOCKED' if blocked else 'PASS',
        'finding':finding,'after_timeout':after_timeout,'after_release':after_release,
        'frozen_event_category':frozen_category,'raw_hash_chain_tip':chain.prefix(),
        'provider_model_calls':0,'freeze_active':False,'execution_authorized':False,'repository_writes':0,
        'patch_scope':'monotonic clock only; real OS lock implementation, Run public perform and incident persistence unpatched'}
write_once(RAW/'LOCK_TIMEOUT_REPRODUCTION.json',result)
print(json.dumps({'verdict':result['verdict'],'event':error.event,'frozen_category':frozen_category,
                  'incidents_after_timeout':len(after_timeout['incidents']),'calls_after_release':len(calls),
                  'reproduction':str(RAW/'LOCK_TIMEOUT_REPRODUCTION.json')}),flush=True)

prior_path=OUT/'INDEPENDENT_CLOSURE_AUDIT.json'
if prior_path.exists():
    prior=load(prior_path)
    before=load(OUT/'REPOSITORY_BEFORE.json')['files']
    after={}
    for directory,subdirs,files in os.walk(REPO):
        subdirs[:]=[x for x in subdirs if x!='.git']
        for name in files:
            if name=='.git':continue
            path=Path(directory)/name;after[path.relative_to(REPO).as_posix()]=file_digest(path)
    preserved=before==after
    write_once(OUT/'REPOSITORY_AFTER_HYPOTHESIS.json',{'files':after,'exact_before_match':preserved})
    final=dict(prior)
    final.update(verdict='BLOCKED' if blocked or not preserved else prior['verdict'],
                 audit_count=1,final_report=True,prior_stage_report_sha256=file_digest(prior_path),
                 prior_stage_report_status='Superseded by this same-audit user-requested hypothesis assessment; not a final PASS.',
                 same_audit_hypothesis_result_sha256=file_digest(RAW/'LOCK_TIMEOUT_REPRODUCTION.json'),
                 findings=prior['findings']+([finding] if finding else []),
                 repository_bytes_and_status_unchanged=prior['repository_bytes_and_status_unchanged'] and preserved,
                 hash_manifest=str(OUT/'FINAL_HASH_MANIFEST.json'),raw_evidence_directory=str(RAW),
                 stop_on_first_product_P1_P2_blocker=True,no_post_finding_repairs_or_further_product_tests=True)
    final['coverage']=dict(prior['coverage'],busy_lock_timeout={'real_OS_lock_held_by_second_thread':True,
        'bounded_deadline_clock_injection':True,'event':'PROVENANCE_MISMATCH','category':frozen_category,
        'terminal_incidents_before_propagation':len(after_timeout['incidents']),
        'post_release_same_run_transport_calls':len(calls),'original_four_blockers_remain_tested_closed':True})
    final['reproduction_scripts']=[str(OUT/'audit.py'),str(OUT/'process_probe.py'),str(OUT/'lock_timeout_hypothesis.py')]
    final['limitations']=prior['limitations']+['Lock timeout was accelerated by monotonic clock injection; actual Windows OS lock contention was real.',
        'The prior PASS-valued closure-stage report is superseded; the final verdict of this ONE audit is BLOCKED.']
    write_once(OUT/'FINAL_INDEPENDENT_CLOSURE_AUDIT.json',final)
    members={p.relative_to(OUT).as_posix():file_digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
    write_once(OUT/'FINAL_HASH_MANIFEST.json',{'schema':'same-independent-audit.final-sha256.v1','audit_count':1,
        'files':members,'file_count':len(members),'self_excluded':True,
        'final_report_sha256':file_digest(OUT/'FINAL_INDEPENDENT_CLOSURE_AUDIT.json'),
        'prior_stage_manifest_sha256':file_digest(OUT/'HASH_MANIFEST.json'),
        'hypothesis_hash_chain_tip':chain.prefix(),'verdict':final['verdict']})
    print(json.dumps({'verdict':final['verdict'],'repository_preserved':preserved,
                      'final_report':str(OUT/'FINAL_INDEPENDENT_CLOSURE_AUDIT.json'),
                      'final_manifest':str(OUT/'FINAL_HASH_MANIFEST.json')}),flush=True)
sys.exit(2 if blocked else 0)
