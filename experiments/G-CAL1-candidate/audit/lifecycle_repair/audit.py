"""One independent, external-only, no-network G-CAL1 closure audit.

Reproduce with: python -B audit.py --repo C:/Users/marcu/Eidolon-g4adj
Use a fresh copy of this script in ONE fresh external directory for reproduction.
Never run against repository output directories. All outputs are write-once.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import date, timedelta
from itertools import combinations
from collections import Counter
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
tempfile.tempdir = str(OUT)
os.environ['TMP'] = os.environ['TEMP'] = str(OUT)
DENIED = []

def safe_write_path(value):
    if isinstance(value, (str, bytes, os.PathLike)):
        p = Path(os.fsdecode(value)).absolute()
        if not p.is_relative_to(OUT):
            raise RuntimeError('EXTERNAL_ONLY_WRITE_BOUNDARY:' + str(p))

def deny_hook(event, args):
    if event.startswith('socket.'):
        DENIED.append(event)
        raise RuntimeError('AUDIT_NETWORK_DENIED:' + event)
    if event == 'open':
        mode, flags = args[1], args[2]
        if (isinstance(mode, str) and any(x in mode for x in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
            safe_write_path(args[0])
    if event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime'):
        safe_write_path(args[0])
    if event in ('os.rename','os.link','os.symlink'):
        safe_write_path(args[0]); safe_write_path(args[1])

sys.addaudithook(deny_hook)
parser = argparse.ArgumentParser()
parser.add_argument('--repo', required=True)
parser.add_argument('--child', nargs=4)
parser.add_argument('--continue-after-core', action='store_true', help='Continue this SAME audit after a logger-only stage handoff; do not rerun attacks')
args = parser.parse_args()
REPO = Path(args.repo).resolve()
sys.path.insert(0, str(REPO/'tools'))
import g_cal1_contract as contract
import g_cal1_lab as lab
from g_cal1_lab import Run
from g_extract1_contract import IntegrityError, canonical, digest, file_digest, load
from g_extract1_journal import Journal, write_once, SCHEMA

OMISSION = 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT'
DATA = REPO/'experiments/G-CAL1-candidate'
RAW = OUT/'raw'

def put(path, obj):
    write_once(path, obj)

def tree(path):
    return {p.relative_to(path).as_posix():file_digest(p) for p in sorted(path.rglob('*')) if p.is_file()}

def synthetic(fn):
    fn.synthetic_only = True
    return fn

def answer(p, row):
    return {'raw_output':canonical(p.members[row['fixture_id']]['gold']).decode(),
            'provider_truncated':False,'receipt':{'call_id':row['call_id'],
            'request_sha256':row['request_sha256'],'synthetic_only':True}}

if args.child:
    directory, run_id, bad, ready = args.child
    p = contract.Package()
    r = Run(p, directory, run_id, resume=True)
    original_lock = lab.run_lock
    @contextmanager
    def announced_lock(directory):
        # Package construction and Run reconstruction are DONE before readiness.
        put(Path(ready), {'pid':os.getpid(),'package_loaded':True,'run_loaded':True,
                         'next_instruction':'attempt same OS lock for verify_resume'})
        with original_lock(directory):
            put(Path(ready).with_name('child-acquired.json'), {'pid':os.getpid()})
            yield
    lab.run_lock = announced_lock
    try:
        r.verify_resume(bad)
    except IntegrityError as exc:
        put(Path(ready).with_name('child-result.json'), {'event':exc.event,'incidents':r.incidents.read()})
        sys.exit(0)
    sys.exit(3)

class Blocker(Exception): pass
class Control(BaseException): pass

checks = []
findings = []
coverage = {}
class AuditChain:
    """Append O(1) for audit assertions, then independently verify the full chain.

    This is ONLY the auditor's ledger. Product journals are never patched.
    """
    def __init__(self, directory):
        self.directory=directory
        existing=Journal(directory).read()
        self.count=len(existing)
        self.tip=existing[-1]['sha256'] if existing else '0'*64
        if args.continue_after_core:checks.extend(r['payload'] for r in existing)
        elif existing:raise RuntimeError('Fresh audit requires fresh output directory')
    def append(self, payload):
        row={'sequence':self.count+1,'previous_sha256':self.tip,'payload':payload}
        row['sha256']=digest(canonical(row))
        write_once(self.directory/f'{self.count+1:06d}.json',row)
        self.count+=1;self.tip=row['sha256']
    def prefix(self):
        records=Journal(self.directory).read()
        if len(records)!=self.count or (records[-1]['sha256'] if records else '0'*64)!=self.tip:raise RuntimeError('Audit chain replay disagrees')
        return {'record_count':self.count,'last_sha256':self.tip}

timeline = AuditChain(RAW/'audit_hash_chain')
current = {'category':'setup','file':'tools/g_cal1_lab.py','line':1}
counter = 0
calls = []

def check(ok, detail, data=None):
    row = {'category':current['category'],'detail':detail,'passed':bool(ok)}
    if data is not None: row['data'] = data
    checks.append(row)
    timeline.append(row)
    if not ok:
        findings.append({'severity':'P1','blocking':True,'title':detail,
                         'file':str(REPO/current['file']),'line':current['line'],
                         'evidence':data})
        raise Blocker(detail)

def category(name, file='tools/g_cal1_lab.py', line=1):
    current.update(category=name,file=file,line=line)
    print('AUDIT_STAGE '+name, flush=True)

def reject(action, detail, event=None):
    try: action()
    except IntegrityError as exc:
        check(event is None or event == exc.event, detail, {'event':exc.event})
        return exc
    check(False, 'Forbidden action accepted: '+detail)

def fresh(p, name):
    global counter
    counter += 1
    return Run(p, RAW/'attacks'/f'{counter:03d}-{name}',f'INDEPENDENT-{counter:03d}-{name}')

def kinds(r):
    return [x['payload']['kind'] for x in r.journal.read()]

def good_for(p):
    @synthetic
    def good(request, row):
        calls.append({'call_id':row['call_id'],'request_sha256':digest(request)})
        return answer(p,row)
    return good

def terminal(r, p, event):
    good = good_for(p)
    before = len(calls); starts = kinds(r).count('START')
    reject(lambda:r.perform(copy.deepcopy(p.schedule[min(len(r.attempted),79)]),good),'caught exception cannot continue',event)
    check(len(calls)==before and kinds(r).count('START')==starts,'zero next-call transports and START')
    check(event in r.events and any(x['payload']['event']==event for x in r.incidents.read()),'same terminal event in memory and durable chain')
    reject(lambda:Run(p,r.directory,r.run_id,resume=True),'restart terminal',event)

def bad_checkpoint(r):
    path = r.directory/'invalid-checkpoint.json'
    put(path, {'payload':[],'sha256':digest(canonical([]))})
    return path

def attacks_a(p):
    category('P1-A-stale-public-paths', line=135)
    for operation in ('perform','checkpoint','verify_resume','final_report'):
        b = fresh(p,'stale-'+operation); cp = b.checkpoint()
        a = Run(p,b.directory,b.run_id,resume=True)
        a.verify_resume(cp)
        bad = bad_checkpoint(a)
        reject(lambda:a.verify_resume(bad),'A persists terminal INVALID through public resume','CORRUPTED_CHECKPOINT')
        check(b.events==[],'B actually stale before operation')
        before = len(calls); start = kinds(b).count('START')
        actions = {'perform':lambda:b.perform(p.schedule[0],good_for(p)),
                   'checkpoint':b.checkpoint,'verify_resume':lambda:b.verify_resume(cp),
                   'final_report':b.final_report}
        reject(actions[operation],'stale B '+operation+' synchronizes terminal','CORRUPTED_CHECKPOINT')
        check(len(calls)==before and kinds(b).count('START')==start,'stale operation zero calls/START')
        terminal(b,p,'CORRUPTED_CHECKPOINT')
    category('P1-A-coordinated-object-race', line=21)
    b = fresh(p,'thread-race'); cp=b.checkpoint()
    a = Run(p,b.directory,b.run_id,resume=True); a.verify_resume(cp)
    bad = bad_checkpoint(a)
    attempting=threading.Event();finished=threading.Event();result=[];workers=[]
    original_lock = lab.run_lock
    @contextmanager
    def observed_lock(directory):
        if threading.current_thread().name=='independent-invalidator':
            attempting.set()
        with original_lock(directory): yield
    def invalidator():
        try: a.verify_resume(bad)
        except IntegrityError as exc: result.append(exc.event)
        except BaseException as exc: result.append(type(exc).__name__)
        finally: finished.set()
    ready=b._ready
    def coordinated_ready():
        ready()
        t=threading.Thread(target=invalidator,name='independent-invalidator');workers.append(t);t.start()
        check(attempting.wait(10),'invalidator reached actual lock acquisition boundary')
        check(not finished.wait(.3) and not b.incidents.read(),'INVALID cannot persist between operability and transport')
    with patch.object(lab,'run_lock',observed_lock),patch.object(b,'_ready',coordinated_ready):
        b.perform(p.schedule[0],good_for(p))
    workers[0].join(15)
    check(finished.is_set() and result==['CORRUPTED_CHECKPOINT'],'invalidator persists only after governed COMPLETE')
    check(kinds(b)[-1]=='COMPLETE','serialized parent call durable before invalidity')
    terminal(b,p,'CORRUPTED_CHECKPOINT')
    category('P1-A-separate-process-lock',file='tools/g_cal1_lock.py',line=13)
    b=fresh(p,'process-race');cp=b.checkpoint();bad=bad_checkpoint(b)
    sync=b.directory/'coordination';sync.mkdir();ready_file=sync/'child-ready.json'
    gate=threading.Event();locked=threading.Event();finished=threading.Event();thread_errors=[]
    ready=b._ready
    def paused_ready():
        ready();locked.set()
        if not gate.wait(30): raise RuntimeError('parent release not signalled')
    def collector():
        try:
            with patch.object(b,'_ready',paused_ready):b.perform(p.schedule[0],good_for(p))
        except BaseException as exc:thread_errors.append(type(exc).__name__+':'+str(exc))
        finally:finished.set()
    # Load the separate process fully BEFORE the parent holds the lock. It then
    # waits for a release-file immediately before its public verify_resume call.
    child_script=OUT/'process_probe.py'
    # This companion module is authored below and uses the same deny hook.
    child=subprocess.Popen([sys.executable,'-B',str(child_script),'--repo',str(REPO),
                            '--directory',str(b.directory),'--run-id',b.run_id,'--bad',str(bad),
                            '--sync',str(sync)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                            cwd=str(OUT),env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    def wait_file(path, timeout=30):
        end=time.monotonic()+timeout
        while not path.exists() and child.poll() is None and time.monotonic()<end:time.sleep(.01)
        return path.exists()
    try:
        check(wait_file(sync/'loaded.json'),'child Package AND Run fully loaded before parent lock')
        t=threading.Thread(target=collector);t.start()
        check(locked.wait(15),'parent holds OS lock after operability check')
        put(sync/'go.json',{'go':True})
        check(wait_file(sync/'attempting.json'),'child reached lock call after loading, explicit handshake')
        time.sleep(.4)
        check(child.poll() is None and not (sync/'acquired.json').exists() and not b.incidents.read(),
              'separate process actually blocked on same lock, not Package startup')
    finally:
        gate.set()
        stdout,stderr=child.communicate(timeout=45)
        if 't' in locals():t.join(15)
        put(sync/'process-output.json',{'returncode':child.returncode,'stdout':stdout,'stderr':stderr,'thread_errors':thread_errors})
    check(finished.is_set() and not thread_errors and child.returncode==0,'both independent actors exit normally')
    check((sync/'acquired.json').exists() and load(sync/'result.json')['event']=='CORRUPTED_CHECKPOINT',
          'child acquires and retains after parent durable closure')
    terminal(b,p,'CORRUPTED_CHECKPOINT')
    coverage['P1_A']={'stale_authority_operations':4,'coordinated_thread_races':1,'separate_process_lock_tests':1,
        'lock_order':'parent acquire -> synchronize -> ready -> child attempting lock -> parent transport/COMPLETE -> unlock -> child acquire/synchronize/INVALID',
        'child_startup_excluded_from_blocking_inference':True}

def attacks_b(p):
    category('P1-B-post-START-control-flow',line=200)
    vectors=[]
    for signal_type in (KeyboardInterrupt,SystemExit,GeneratorExit,Control):
        for point in ('transport','normalization','receipt','scoring','diagnostic','before_complete','after_complete'):
            r=fresh(p,signal_type.__name__+'-'+point);signal=signal_type('exact-original',17)
            normal=lab.transport_outcome;eval_fn=lab.evaluate;diag=lab.diagnosis;append=r.journal.append
            returned=[]
            @synthetic
            def transport(request,row):
                if point=='transport': raise signal
                value=answer(p,row)
                if point=='receipt':
                    class ReceiptBomb(list):
                        def __iter__(self):raise signal
                    value['receipt']['nested-audit-control']=ReceiptBomb([1])
                returned.append(True)
                return value
            def normalize(row,result):
                if point=='normalization':raise signal
                return normal(row,result)
            def scoring(*a,**kw):
                if point=='scoring':raise signal
                return eval_fn(*a,**kw)
            def diagnostic(*a,**kw):
                if point=='diagnostic':raise signal
                return diag(*a,**kw)
            def app(payload):
                if payload['kind']=='COMPLETE' and point=='before_complete':raise signal
                value=append(payload)
                if payload['kind']=='COMPLETE' and point=='after_complete':raise signal
                return value
            caught=None
            with patch.object(lab,'transport_outcome',normalize),patch.object(lab,'evaluate',scoring),patch.object(lab,'diagnosis',diagnostic),patch.object(r.journal,'append',app):
                try:r.perform(p.schedule[0],transport)
                except BaseException as exc:caught=exc
            check(caught is signal and caught.args==('exact-original',17),'exact signal object and arguments propagated',{'type':signal_type.__name__,'point':point})
            check(point=='transport' or returned==[True],'post-return injections actually follow valid return')
            if point=='after_complete':
                check(kinds(r)==['RUN_CREATED','START','COMPLETE'] and not r.incidents.read(),'durable COMPLETE never relabeled omission')
                check(not r.evidence,'in-memory update intentionally interrupted')
                r.perform(p.schedule[1],good_for(p))
                check(len(r.evidence)==2 and len(r.attempted)==2,'safe live replay synchronizes before next invocation')
                cp=r.checkpoint();replay=Run(p,r.directory,r.run_id,resume=True);replay.verify_resume(cp)
                check(replay.evidence==r.evidence and replay.state()==r.state(),'restart replay/live agreement after durable closure')
            else:
                check(kinds(r)==['RUN_CREATED','START'] and r.events==[OMISSION] and r.state()['verdict']=='INVALID',
                      'durable terminal omission BEFORE propagation, no fabricated closure')
                check(r.event_scopes==[{'event':OMISSION,'phase':'CAL','cell':p.schedule[0]['cell_id']}],'exact omission scope')
                terminal(r,p,OMISSION)
            vectors.append({'signal':signal_type.__name__,'point':point,'directory':str(r.directory),'closed':point=='after_complete'})
    put(RAW/'control_flow_vectors.json',vectors)
    coverage['P1_B']={'vectors':len(vectors),'preclosure_terminal':24,'postclosure_safe_replay':4,'exact_identity_propagation':28}

def attacks_c(p):
    category('P1-C-authoritative-memory-cache',file='tools/g_cal1_contract.py',line=201)
    mutations=('order','seed','request_hash','source_date','offset','gold','fixture_gold','request','design','baseline','historical_design','pins')
    for kind in mutations:
        q=contract.Package();r=fresh(q,'memory-'+kind);row=copy.deepcopy(q.schedule[0]);m=q.members[row['fixture_id']]
        if kind=='order':q.schedule[0],q.schedule[1]=q.schedule[1],q.schedule[0]
        elif kind=='seed':q.schedule[0]['seed']=0
        elif kind=='request_hash':q.schedule[0]['request_sha256']='f'*64
        elif kind=='source_date':m['source_date']='2077-01-02'
        elif kind=='offset':m['offset']+=1
        elif kind=='gold':m['gold'][next(iter(m['gold']))]='2077-01-02'
        elif kind=='fixture_gold':m['fixture']['gold_values'][next(iter(m['gold']))]='2077-01-02'
        elif kind=='request':m['request']['input']['text']='tampered'
        elif kind=='design':q.design['generation_configuration']['retry_limit']=1
        elif kind=='baseline':q.baseline['system_text']='tampered'
        elif kind=='historical_design':q.historical.design['baseline_binding']['system_text']='tampered'
        elif kind=='pins':q.pins.clear()
        before=len(calls)
        reject(lambda:r.perform(row,good_for(q)),'cache mutation '+kind,'PRE_ARTIFACT_DIGEST_MISMATCH')
        check(len(calls)==before and kinds(r)==['RUN_CREATED'],'precontact cache drift zero transport and START')
    r=fresh(p,'detached-callback');science=canonical(p._derived_state())
    @synthetic
    def alias(request,row):
        value=answer(p,row);row['seed']=0;row['generation_configuration']['num_ctx']=1
        return value
    r.perform(p.schedule[0],alias);r.perform(p.schedule[1],good_for(p))
    check(canonical(p._derived_state())==science and len(r.evidence)==2,'callback row/nested config no longer aliases schedule')
    category('P1-C-actual-external-disk-drift',file='tools/g_cal1_contract.py',line=205)
    for target in ('corpus/CORPUS.json','schedule/SCHEDULE.json','DESIGN.json'):
        shadow=RAW/'cloned_packages'/target.replace('/','-');shadow.mkdir(parents=True)
        for rel in p.pins:
            dst=shadow/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/rel,dst)
        manifest=shadow/'experiments/G-CAL1-candidate/LAB_MANIFEST.json';shutil.copyfile(DATA/'LAB_MANIFEST.json',manifest)
        with patch.object(contract,'ROOT',shadow),patch.object(contract,'DATA',manifest.parent):
            q=contract.Package();r=fresh(q,'disk-'+target.replace('/','-'));row=copy.deepcopy(q.schedule[0]);cached=canonical(q._derived_state())
            path=manifest.parent/target;path.write_bytes(path.read_bytes()+b' ')
            check(canonical(q._derived_state())==cached,'actual cloned disk altered with valid stale cache')
            before=len(calls)
            reject(lambda:r.perform(row,good_for(q)),'actual disk drift '+target,'PRE_ARTIFACT_DIGEST_MISMATCH')
            check(len(calls)==before and kinds(r)==['RUN_CREATED'],'disk drift denied before contact')
    coverage['P1_C']={'memory_mutations':len(mutations),'external_actual_disk_mutations':3,'detached_nested_callback_alias':True}

def attacks_d(p):
    category('P1-D-mechanical-boundary',line=40)
    class ProviderLike:
        synthetic_only=False
        def __call__(self,*a):calls.append('FORBIDDEN-PROVIDER-LIKE');return answer(p,p.schedule[0])
    provider=ProviderLike()
    for name,marker in (('unmarked','ABSENT'),('false',False),('integer-one',1),('string-true','true'),('none',None),('provider-like','PROVIDER'),('wrapper','WRAPPER')):
        r=fresh(p,name)
        def fake(request,row):calls.append('FORBIDDEN');return answer(p,row)
        if marker=='PROVIDER':fake=provider
        elif marker=='WRAPPER':fake=lambda *a:provider(*a)
        elif marker!='ABSENT':fake.synthetic_only=marker
        before=len(calls)
        reject(lambda:r.perform(p.schedule[0],fake),'transport boundary '+name,'PROVENANCE_MISMATCH')
        check(len(calls)==before and kinds(r)==['RUN_CREATED'],'mechanical rejects before invocation/START')
    r=fresh(p,'explicit-True');r.perform(p.schedule[0],good_for(p))
    check(len(r.evidence)==1,'exact Boolean True synthetic admitted')
    category('live-authority-inactive-no-grant',line=51)
    check(not (DATA/'execution/ACTIVE_FREEZE.json').exists() and not (DATA/'execution/EXECUTION_FREEZE_ACTIVATION.json').exists(),'freeze actually inactive')
    for grant in (None, {'status':'EXECUTION_FREEZE_CANDIDATE_ONLY'},
                  {'status':'EXPLICIT_OPERATOR_PHASE_AUTHORIZATION','phase':'CAL','run_id':'wrong','binding':{},'synthetic_evidence_allowed':False}):
        directory=RAW/'never-live'
        reject(lambda:Run(p,directory,'INDEPENDENT-NO-AUTHORITY',mechanical=False,authorization=grant),'live public constructor denies inactive/no-grant','PROVENANCE_MISMATCH')
        check(not directory.exists(),'live denial before evidence directory')
    for marker in ('ABSENT',True,1):
        def fake(*a):raise AssertionError('must never invoke')
        if marker!='ABSENT':fake.synthetic_only=marker
        reject(lambda:lab.transport_boundary(fake,False),'real boundary rejects synthetic/unmarked','PROVENANCE_MISMATCH')
    coverage['P1_D']={'negative_actual_Run_transports':7,'explicit_True_positive':1,'inactive_live_constructor_denials':3,
                     'positive_active_live_authority_not_created_or_exercised':True}

def regressions(p):
    category('generic-append-checkpoint-resume-receipt-no-retry-replay',line=266)
    good=good_for(p)
    r=fresh(p,'successful-resume');cp=r.checkpoint();r.perform(p.schedule[0],good)
    cp=r.checkpoint();records=r.journal.read();s=Run(p,r.directory,r.run_id,resume=True);s.verify_resume(cp)
    s.perform(p.schedule[1],good)
    check(s.journal.read()[:len(records)]==records,'append-only prefix unchanged across resume and collection')
    check(len(s.evidence)==2,'resume reconstructs exact next position')
    before=len(calls);reject(lambda:r.perform(p.schedule[0],good),'stale duplicate/no retry','SCHEDULE_POSITION_MISMATCH')
    check(len(calls)==before,'no duplicate transport')
    terminal(r,p,'SCHEDULE_POSITION_MISMATCH')
    for op in ('perform','checkpoint','final_report'):
        r=fresh(p,'unverified-'+op);r.checkpoint();s=Run(p,r.directory,r.run_id,resume=True)
        reject({'perform':lambda:s.perform(p.schedule[0],good),'checkpoint':s.checkpoint,'final_report':s.final_report}[op],
               'unverified resume '+op,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT')
        terminal(s,p,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT')
    for value in (None,False,1,[],{}, {'payload':None}, {'payload':[],'sha256':'0'*64},
                  {'payload':{},'sha256':digest(canonical({}))}):
        r=fresh(p,'bad-checkpoint');r.checkpoint();s=Run(p,r.directory,r.run_id,resume=True);path=r.directory/'bad.json';put(path,value)
        reject(lambda:s.verify_resume(path),'checkpoint envelope/payload malformed')
        terminal(s,p,s.events[0])
    for kind in ('timeout','error','missing','ordinary','malformed','wrong-receipt'):
        r=fresh(p,'receipt-'+kind);invoked=[]
        @synthetic
        def fake(request,row):
            invoked.append(row['call_id'])
            if kind=='ordinary':raise ValueError('ordinary callback exception')
            if kind=='malformed':return None
            if kind=='wrong-receipt':
                result=answer(p,row);result['receipt']['request_sha256']='0'*64;return result
            return {'failure':kind,'receipt':{'call_id':row['call_id'],'request_sha256':row['request_sha256'],'failure_kind':kind}}
        reject(lambda:r.perform(p.schedule[0],fake),'failure receipting '+kind)
        check(len(invoked)==1 and kinds(r)==['RUN_CREATED','START','FAILURE'],'one attempt durable FAILURE, no retry/fallback')
        terminal(r,p,r.events[0])
    for key,value in (('schedule_position',2),('call_id','wrong'),('seed',1),('model','wrong'),('provider_version','wrong'),('request_sha256','0'*64)):
        r=fresh(p,'row-'+key);row=copy.deepcopy(p.schedule[0]);row[key]=value;before=len(calls)
        reject(lambda:r.perform(row,good),'schedule exact row '+key)
        check(len(calls)==before and kinds(r)==['RUN_CREATED'],'schedule mutation denied before START')
    r=fresh(p,'journal-corruption');r.perform(p.schedule[0],good)
    path=r.directory/'journal/000002.json';data=load(path);data['payload']['row']['seed']=0;path.write_bytes(canonical(data))
    reject(r.checkpoint,'hash-chain corruption retained','CORRUPTED_OR_UNPARSEABLE_JOURNAL')
    before=len(calls)
    reject(lambda:r.perform(p.schedule[1],good),'corrupt journal cannot continue','CORRUPTED_OR_UNPARSEABLE_JOURNAL')
    check(len(calls)==before and bool(r.incidents.read()),'corrupt journal has durable terminality, no further transport')
    reject(lambda:Run(p,r.directory,r.run_id,resume=True),'corrupt journal restart terminal','CORRUPTED_OR_UNPARSEABLE_JOURNAL')
    j=Journal(RAW/'write-once-probe');j.append({'probe':1});original=(j.directory/'000001.json').read_bytes()
    reject(lambda:write_once(j.directory/'000001.json',{'overwrite':True}),'exclusive evidence create collision','PROVENANCE_MISMATCH')
    check((j.directory/'000001.json').read_bytes()==original,'write-once existing bytes preserved')
    coverage['generic_regression']={'public_lifecycle_paths':True,'append_only':True,'resume_lineage':True,'unverified_resume_modes':3,
            'checkpoint_bad_shapes':8,'failure_receipt_and_no_retry_cases':6,'schedule_mutations':6,'journal_corruption':True}

def gregorian_ordinal(text):
    y,m,d=map(int,text.split('-'));n=y-1
    days=365*n+n//4-n//100+n//400
    lengths=[31,28+(y%4==0 and (y%100!=0 or y%400==0)),31,30,31,30,31,31,30,31,30,31]
    return days+sum(lengths[:m-1])+d

def gold_by_ordinal(text, offset):
    wanted=gregorian_ordinal(text)+offset
    low,high=1,9999
    while low<high:
        mid=(low+high+1)//2
        if gregorian_ordinal(f'{mid:04d}-01-01')<=wanted:low=mid
        else:high=mid-1
    for m in range(12,0,-1):
        start=gregorian_ordinal(f'{low:04d}-{m:02d}-01')
        if start<=wanted:return f'{low:04d}-{m:02d}-{wanted-start+1:02d}'
    raise ValueError('out of range')

def science(p):
    category('independent-gold-exact-requests-schedule',file='tools/g_cal1_contract.py',line=146)
    members=list(p.members.values());design=p.design;baseline=p.baseline;manifest=load(DATA/'schedule/REQUEST_MANIFEST.json')
    check(len(members)==40 and Counter(m['stratum'] for m in members)=={'C1':10,'C2':10,'C3':10,'C4':10},'40 frozen fixtures, 10 per stratum')
    gold=[]
    for m in members:
        expected=gold_by_ordinal(m['source_date'],m['offset']);field=f'd{m["ordinal"]:03d}_01'
        check(m['gold']=={field:expected} and m['fixture']['gold_values']=={field:expected},'independent closed-form ordinal gold '+m['fixture_id'])
        check((date.fromisoformat(m['source_date'])+timedelta(days=m['offset'])).isoformat()==expected,'independent library/ordinal agreement')
        check(m['ordinal']==4*(m['slot']-1)+int(m['stratum'][1:]),'frozen ID ordinal rule')
        gold.append({'fixture_id':m['fixture_id'],'source_date':m['source_date'],'offset':m['offset'],'gold':expected})
    for s in ('C1','C2','C3','C4'):
        check(sum(m['offset']>0 for m in members if m['stratum']==s)==5,'five positive and negative '+s)
    check(len({m['source_date'] for m in members})==40 and len({next(iter(m['gold'].values())) for m in members})==40,'source and answer uniqueness')
    check(not {m['source_date'] for m in members}&{next(iter(m['gold'].values())) for m in members},'source/answer disjoint')
    rows=[];requests=[]
    for repeat in (1,2):
        for m in sorted(members,key=lambda x:(hashlib.sha256(f'G-CAL1/order/{repeat}/{x["fixture_id"]}'.encode()).hexdigest(),x['fixture_id'])):
            ordinal=m['ordinal'];source=f'f{ordinal:03d}_01';nuisance=f'f{ordinal:03d}_02';target=f'd{ordinal:03d}_01'
            subject='Extract the record record. '+f'{target} is {source} plus {m["offset"]} calendar days'
            request={'prompt':baseline['structured_extraction_assembled_template'].replace('{SUBJECT}',subject),
                     'input':{'schema':{target:'YYYY-MM-DD'},'text':f'{source} is {m["source_date"]}. {nuisance} is "code_{ordinal:03d}_99".'}}
            check(request==m['request'],'independent fixture request construction '+m['fixture_id'])
            seed=820000+10*ordinal+repeat
            options={k:design['generation_configuration'][k] for k in ('temperature','top_p','top_k','repeat_penalty','num_ctx','num_predict')};options['seed']=seed
            body={'model':design['model'],'system':baseline['system_text'],'prompt':request['prompt']+'\n\nINPUT:\n'+canonical(request['input']).decode(),
                  'stream':False,'think':False,'options':options}
            wire=canonical(body)
            row={'schedule_position':len(rows)+1,'call_id':f'{m["fixture_id"]}:REPEAT{repeat}','fixture_id':m['fixture_id'],'stratum':m['stratum'],
                 'repeat':repeat,'cell_id':m['stratum'],'phase':'CAL','seed':seed,'model':design['model'],'provider_version':design['provider_version'],
                 'generation_configuration':design['generation_configuration'],'request_sha256':digest(wire)}
            rows.append(row);requests.append({'call_id':row['call_id'],'body':body,'sha256':digest(wire)})
            check(p.wire(row)==wire,'all exact wire bytes independently materialized '+row['call_id'])
    check(rows==p.schedule and requests==manifest['wire_requests'],'all 80 exact frozen rows/request manifest agreement')
    check(digest(canonical(rows))=='b4d4a5a7ba37961dcfbbe0c6aa6101fbbeb40dcf2dad0c54c8680d216c2e1858','frozen 80-call canonical schedule SHA')
    check(design['interpretation']['mode']=='DESCRIPTIVE_ONLY' and design['interpretation']['pass_threshold'] is None and design['interpretation']['routing_authority'] is False,
          'descriptive-only science, no threshold or routing authority')
    put(RAW/'independent_gold.json',gold);put(RAW/'independent_requests.json',requests)
    coverage['science']={'fixtures':40,'independent_ordinal_gold_agreements':40,'exact_requests':80,'schedule_sha256':digest(canonical(rows)),
                         'descriptive_only':True,'real_scientific_observations':0}
    contamination(p)

def contamination(p):
    category('independent-contamination-replay',file='tools/g_cal1_stage.py',line=150)
    # Frozen primary AND independent encoders are read-only, not producer tests.
    import g_cal1_stage as stage
    primary,independent=stage.old_checkers()
    hist,history_pins,source_dates,gold_dates,counts=stage.history_records(p.historical,primary,independent)
    new=[stage.evidence(m,p.historical.design,primary,independent) for m in p.members.values()]
    original=load(DATA/'corpus/CONTAMINATION_REPORT.json');historical=[];new_pairs=[];na=0;typed=0
    for m,a in zip(p.members.values(),new):
        check(m['source_date'] not in source_dates|gold_dates and next(iter(m['gold'].values())) not in source_dates|gold_dates,'historical date freshness '+m['fixture_id'])
        for h in hist:
            if h['id'].startswith('G-EXTRACT1/'):
                check(h['tuple_applicability']=='APPLIES','typed historical tuple applicability APPLIES')
                typed+=1
            else:
                check(h['tuple_applicability']=='NOT_APPLICABLE_UNREPRESENTABLE_HISTORICAL_PROVENANCE' and h['tuple'] is None,
                      'unrepresentable legacy provenance explicitly N/A, not pass credit')
                na+=1
            i=len(a['ordinary']&h['ordinary']);u=len(a['ordinary']|h['ordinary']);matches=sum(x==y for x,y in zip(a['projection'],h['projection']))
            okay=a['raw_payload']!=h['raw_payload'] and a['answer']!=h['answer'] and ('raw_values' not in h or a['raw_values']!=h['raw_values'])
            if h['tuple_applicability']=='APPLIES':okay=okay and (h['tuple'] is None or a['tuple']!=h['tuple'])
            okay=okay and u>0 and 5*i<u and matches<3 and (matches<2 or 25*i<3*u)
            if h['fp'] is not None:
                same=sum(x==y for x,y in zip(a['fp'],h['fp']));okay=okay and same<6 and (same<5 or 25*i<3*u)
            check(okay,'independently implemented historical decision '+a['id']+'/'+h['id'])
            historical.append({'new':a['id'],'historical':h['id'],'ordinary_i_u':[i,u],'projection_matches':matches,
                               'tuple_applicability':h['tuple_applicability'],'gate':True})
    dummy=copy.deepcopy(next(iter(p.members.values()))['request'])
    dummy['input']['text']=dummy['input']['text'].replace(next(iter(p.members.values()))['source_date'],'SCaffoldDATE')
    invariant={g for g in independent.grams(dummy,p.historical.design) if not any('scaffolddate' in t for t in g)}
    check(invariant=={tuple(x) for x in original['invariant_five_grams']},'symbolic scaffold invariants, no date grams removed')
    for a,b in combinations(new,2):
        left,right=a['ordinary']-invariant,b['ordinary']-invariant;i=len(left&right);u=len(left|right)
        check(bool(left and right) and 25*i<3*u and all(a[k]!=b[k] for k in ('raw_payload','raw_values','answer','tuple')),
              'independent NEW/NEW residual and exact reuse '+a['id']+'/'+b['id'])
        new_pairs.append({'left':a['id'],'right':b['id'],'mode':'DECLARED_SCAFFOLD_RESIDUAL',
            'ordinary_i_u':[len(a['ordinary']&b['ordinary']),len(a['ordinary']|b['ordinary'])],
            'shape_i_u':[len(a['shape']&b['shape']),len(a['shape']|b['shape'])],
            'content_i_u':[len(a['content']&b['content']),len(a['content']|b['content'])],
            'residual_i_u':[i,u],'residual_gate':True,'ordinary_gate_credited':False,
            'full_fingerprint_equal':a['fp']==b['fp'],'tuple_applicability':'APPLIES'})
    check(len(historical)==12720 and historical==original['historical_pairs'],'all 12,720 historical decision records exactly frozen')
    check(len(new_pairs)==780 and new_pairs==original['new_pairs'],'all 780 NEW/NEW records exactly frozen')
    check(na==5040 and typed==7680 and original['not_applicable_credited_as_pass'] is False,'5,040 unavailable tuple comparisons N/A with ZERO pass credit')
    put(RAW/'contamination_replay.json',{'historical':historical,'new_pairs':new_pairs,'history_counts':counts,'legacy_tuple_NA':na,'typed_history':typed,
        'NA_label':'NOT_APPLICABLE_UNREPRESENTABLE_HISTORICAL_PROVENANCE','NA_pass_credit':0,'history_source_pins':history_pins})
    coverage['contamination']={'historical_applicable_non_tuple_comparisons':12720,'new_pairs':780,'unavailable_legacy_tuple_NA':5040,
                               'unavailable_tuple_pass_credit':0,'typed_history_comparisons':7680,'frozen_primary_and_independent_encoders_used':True}

def pilots_and_bindings(p):
    category('two-clean-independent-synthetic-pilot-trees',file='tools/g_cal1_pilot.py',line=51)
    from g_cal1_pilot import full_pilot
    class CheckAdapter:
        def check(self,ok,cat,detail):check(ok,'pilot '+detail)
    results=[];trees=[]
    for name in ('pilot_one','pilot_two'):
        directory=RAW/name
        result=full_pilot(p,directory,CheckAdapter());results.append(result);trees.append(tree(directory))
        check(result['state']['completed_observations']==80 and result['state']['verdict']=='VALID_COMPLETE','fresh pilot exactly 80/80 synthetic')
        # Independently recompute every hash-chain seal, sequence, and score.
        records=[json.loads(x.read_bytes()) for x in sorted((directory/'journal').glob('*.json'))];prev='0'*64;complete=0
        for n,row in enumerate(records,1):
            seal={k:v for k,v in row.items() if k!='sha256'}
            check(row['sequence']==n and row['previous_sha256']==prev and row['sha256']==digest(canonical(seal)),'independent raw journal hash chain '+str(n))
            prev=row['sha256']
            payload=row['payload']
            if payload['kind']=='COMPLETE':
                schedule=p.schedule[complete];m=p.members[schedule['fixture_id']]
                score=lab.evaluate(m,payload['result']['raw_output'],truncated=payload['result']['provider_truncated'])
                check(payload['call_id']==schedule['call_id'] and payload['score']==score and score['semantic_correct'],'independent frozen-order scorer replay')
                complete+=1
        check(complete==80,'independent journal has exactly 80 COMPLETE')
    check(results[0]==results[1] and trees[0]==trees[1],'two external complete authority trees byte identical',{'files_each':len(trees[0])})
    producer_trees=[tree(DATA/'preexecution/lifecycle_repair'/n) for n in ('pilot_one','pilot_two')]
    check(trees[0]==producer_trees[0]==producer_trees[1],'fresh independent pilot matches BOTH candidate-bound supplied trees')
    put(RAW/'pilot_comparison.json',{'trees':trees,'byte_identical':trees[0]==trees[1],'files_each':len(trees[0]),'results':results})
    coverage['pilots']={'complete_clean_external_pilots':2,'synthetic_observations_each':80,'files_each_recomputed':len(trees[0]),
                        'all_bytes_identical':True,'candidate_supplied_tree_matches':True,'independent_hash_chain_replay':True}
    category('candidate-pins-source-evidence-bindings',file='tools/g_cal1_contract.py',line=185)
    directory=DATA/'preexecution/lifecycle_repair';candidate=load(directory/'EXECUTION_FREEZE_CANDIDATE.json')
    check(file_digest(directory/'EXECUTION_FREEZE_CANDIDATE.json')=='f45825a0165f23b78da13fb0fec8dcade010b37fadbe7cdc8c2020a05b0f0336','exact new freeze candidate SHA')
    check(candidate['binding']==p.binding and candidate['protected_artifacts']==p.pins and len(p.pins)==97,'candidate binding and 97 pins exact')
    for rel,expected in p.pins.items():check(file_digest(REPO/rel)==expected,'protected source/evidence pin '+rel)
    check(candidate['journal_checkpoint_schema']==SCHEMA and candidate['journal_checkpoint_schema_sha256']==digest(canonical(SCHEMA)),'journal/checkpoint schema exact binding')
    for key,name in (('pilot_report_sha256','PILOT_REPORT.json'),('preservation_report_sha256','PRESERVATION_REPORT.json')):
        check(candidate[key]==file_digest(directory/name),'candidate evidence hash '+name)
    producer=load(directory/'PILOT_REPORT.json')
    check(producer['pilot_tree']==trees[0] and producer['synthetic_observations_each_pilot']==80,'producer report hashes agree with independently computed pilot trees')
    check(candidate['prior_blocked_audit_sha256']==file_digest(DATA/'audit/INDEPENDENT_PREREGISTRATION_AUDIT.json'),'prior blocked audit remains bound')
    for key,rel in (('prior_blocked_candidate_sha256','preexecution/final/EXECUTION_FREEZE_CANDIDATE.json'),
                    ('supersedes_unactivated_initial_candidate_sha256','preexecution/EXECUTION_FREEZE_CANDIDATE.json')):
        check(candidate[key]==file_digest(DATA/rel),'unactivated candidate ancestry '+key)
    check(candidate['status']=='EXECUTION_FREEZE_CANDIDATE_ONLY' and candidate['activated'] is False and candidate['execution_authorized'] is False,
          'candidate is NOT active and grants NO authority')
    receipts=p.historical.receipts();receipts=dict(receipts,models=[receipts['models'][2]])
    check(candidate['provider_binding']==receipts,'candidate frozen provider identity/config binding READ ONLY')
    git=['git','-c','safe.directory='+REPO.as_posix(),'-C',str(REPO)]
    changed=subprocess.check_output(git+['diff','--name-only','b64f0e46d4287a92a8723e8873007c5ee795534e','HEAD','--','tools/g_cal1_contract.py','tools/g_cal1_lab.py','tools/g_cal1_lock.py','tools/g_cal1_pilot.py','tools/g_cal1_repair_tests.py'],text=True)
    check(changed.strip()=='','repair sources identical to implementation commit b64f0e46')
    coverage['bindings']={'package_pins':97,'candidate_sha256':file_digest(directory/'EXECUTION_FREEZE_CANDIDATE.json'),'repair_implementation_commit':'b64f0e46d4287a92a8723e8873007c5ee795534e'}

def repository_snapshot():
    # Includes all repository regular files except Git metadata (external worktree
    # admin data are outside this checkout). No writes, imports or provider calls.
    result={}
    for directory,subdirs,files in os.walk(REPO):
        subdirs[:]=[x for x in subdirs if x!='.git']
        for name in files:
            if name=='.git':continue
            path=Path(directory)/name
            result[path.relative_to(REPO).as_posix()]=file_digest(path)
    return result

def git_identity():
    prefix=['git','-c','safe.directory='+REPO.as_posix(),'-C',str(REPO)]
    return {key:subprocess.check_output(prefix+command,text=True).strip() for key,command in
            [('HEAD',['rev-parse','HEAD']),('branch',['branch','--show-current']),('status',['status','--porcelain=v1','--untracked-files=all'])]}

def validate_preservation(before):
    category('recorded-preexisting-preservation',file='tools/g_cal1_stage.py',line=38)
    document=load(DATA/'preexecution/lifecycle_repair/PRESERVATION_BEFORE.json')
    maps={k:v for k,v in document.items() if isinstance(v,dict) and v and all(isinstance(x,str) and len(x)==64 for x in v.values())}
    for name,expected in maps.items():
        check(all(before.get(rel)==sha for rel,sha in expected.items()),'recorded lifecycle preservation '+name,{'files':len(expected)})
    old=load(DATA/'PRESERVATION_BEFORE.json')
    check(all(before.get(rel)==sha for rel,sha in old.items()),'main old-closure preservation exact',{'files':len(old)})
    coverage['preservation']={'whole_checkout_files':len(before),'repair_baseline_groups':{k:len(v) for k,v in maps.items()},'main_old_closure_files':len(old),'old_untracked_artifacts':7}

before=None;identity=None;verdict='BLOCKED'
try:
    identity=git_identity()
    if identity['HEAD']!='499b7b0d8db625dc13ecdab32f0723ae21bca20a' or identity['branch']!='g-extract1/design':raise RuntimeError('checkout identity differs from requested audit')
    if args.continue_after_core:
        saved=load(OUT/'REPOSITORY_BEFORE.json');before=saved['files']
        if saved['identity']!=identity:raise RuntimeError('Same-audit handoff changed checkout identity')
        if not checks or not all(x['passed'] for x in checks):raise RuntimeError('Cannot continue blocked evidence')
        required=('P1-A-stale-public-paths','P1-A-coordinated-object-race','P1-A-separate-process-lock',
                  'P1-B-post-START-control-flow','P1-C-authoritative-memory-cache','P1-C-actual-external-disk-drift',
                  'P1-D-mechanical-boundary','live-authority-inactive-no-grant',
                  'generic-append-checkpoint-resume-receipt-no-retry-replay')
        if not all(any(x['category']==cat for x in checks) for cat in required):raise RuntimeError('Missing core stage evidence')
        if not any(x['detail']=='write-once existing bytes preserved' for x in checks):raise RuntimeError('Generic stage did not finish')
        vectors=load(RAW/'control_flow_vectors.json')
        if len(vectors)!=28:raise RuntimeError('Incomplete control-flow vectors')
        coverage.update(P1_A={'stale_authority_operations':4,'coordinated_thread_races':1,'separate_process_lock_tests':1,
            'lock_order':'parent acquire -> synchronize -> ready -> child attempting lock -> parent transport/COMPLETE -> unlock -> child acquire/synchronize/INVALID',
            'child_startup_excluded_from_blocking_inference':True},
            P1_B={'vectors':28,'preclosure_terminal':24,'postclosure_safe_replay':4,'exact_identity_propagation':28},
            P1_C={'memory_mutations':12,'external_actual_disk_mutations':3,'detached_nested_callback_alias':True},
            P1_D={'negative_actual_Run_transports':7,'explicit_True_positive':1,'inactive_live_constructor_denials':3,
                  'positive_active_live_authority_not_created_or_exercised':True},
            generic_regression={'public_lifecycle_paths':True,'append_only':True,'resume_lineage':True,'unverified_resume_modes':3,
                'checkpoint_bad_shapes':8,'failure_receipt_and_no_retry_cases':6,'schedule_mutations':6,'journal_corruption':True})
        put(OUT/'SAME_AUDIT_LOGGER_HANDOFF.json',{'audit_count':1,'independent_reviewer_unchanged':True,
            'reason':'Auditor assertion logger was quadratic; optimize logger only before large contamination replay.',
            'product_sources_or_behavior_changed':False,'core_attacks_rerun':False,'core_and_generic_complete':True,
            'initial_assertion_count':len(checks),'validated_initial_chain_tip':timeline.prefix(),
            'initial_driver_sha256':file_digest(OUT/'INITIAL_DRIVER.py'),
            'continuation_driver_sha256':file_digest(OUT/'audit.py'),
            'initial_driver_stopped_after_complete_generic_stage_during_nonmutating_science_checks':True})
    else:
        before=repository_snapshot();put(OUT/'REPOSITORY_BEFORE.json',{'identity':identity,'files':before})
    p=contract.Package()
    # Exactly this one audit: former blockers FIRST, then wider closure review.
    if not args.continue_after_core:
        attacks_a(p);attacks_b(p);attacks_c(p);attacks_d(p);regressions(p)
    science(p);pilots_and_bindings(p);validate_preservation(before)
    verdict='PASS'
except Blocker:
    print('AUDIT_STOP_BLOCKER '+findings[-1]['title'],flush=True)
except BaseException as exc:
    findings.append({'severity':'P2','blocking':True,'title':'Audit incomplete at '+current['category'],
                     'file':str(REPO/current['file']),'line':current['line'],
                     'exception':type(exc).__name__+':'+str(exc),'traceback':traceback.format_exc(),
                     'classification':'audit harness/infrastructure or unexpected product exception; not assumed product defect'})
    print('AUDIT_STOP_ERROR '+str(exc),flush=True)
finally:
    after=repository_snapshot();final_identity=git_identity()
    preserved=before is not None and before==after and identity==final_identity
    put(OUT/'REPOSITORY_AFTER.json',{'identity':final_identity,'files':after,'exact_before_match':preserved})
    if not preserved:
        findings.append({'severity':'P1','blocking':True,'title':'Repository preservation not verified','file':str(REPO),'line':None})
        verdict='BLOCKED'
    if findings:verdict='BLOCKED'
    report={'schema_version':'g-cal1.independent-closure-audit.v1','audit_count':1,'verdict':verdict,
        'reviewed_HEAD':identity,'final_checkout_identity':final_identity,'findings':findings,'coverage':coverage,
        'assertion_count':len(checks),'assertions':checks,'repository_bytes_and_status_unchanged':preserved,
        'independent_attacks_authored_here':True,'producer_main_called':False,'additional_agents_spawned':0,
        'same_audit_logger_handoff':args.continue_after_core,'core_attacks_rerun':False,
        'network_deny_hook':'all socket.* events denied in parent and child, installed before product imports',
        'denied_network_events':DENIED,'raw_evidence_directory':str(RAW),'hash_manifest':str(OUT/'HASH_MANIFEST.json'),
        'reproduce':'python -B audit.py --repo C:/Users/marcu/Eidolon-g4adj (copy script pair to a fresh external directory)',
        'limitations':['No active freeze or grant created; active-authority positive execution deliberately untested.',
                       'No provider/model/socket query performed; real provider option honoring unattested.',
                       'Synthetic results are mechanical validation, NOT scientific observations.',
                       'In-process injection tests do not claim protection against arbitrary Python code replacement.',
                       'If BLOCKED, later stages unexecuted by mandatory stop rule.'],
        'governance':{'provider_model_calls':0,'real_requests':0,'freeze_active':False,'execution_authorized':False,
                      'repository_edits':0,'repairs':0,'new_commits':0,'push':False,'autonomy':False,'belief_effects':'none',
                      'G_EXTRACT1_and_G_ROUTE4_unchanged':preserved}}
    put(OUT/'INDEPENDENT_CLOSURE_AUDIT.json',report)
    members=tree(OUT)
    put(OUT/'HASH_MANIFEST.json',{'schema':'external-audit.sha256.v1','files':members,'file_count':len(members),
        'self_excluded':True,'raw_audit_chain_tip':timeline.prefix(),'report_sha256':members['INDEPENDENT_CLOSURE_AUDIT.json']})
    print(json.dumps({'verdict':verdict,'assertions':len(checks),'findings':findings,'report':str(OUT/'INDEPENDENT_CLOSURE_AUDIT.json'),
                      'manifest':str(OUT/'HASH_MANIFEST.json'),'raw':str(RAW),'preserved':preserved}),flush=True)
sys.exit(0 if verdict=='PASS' else 2)
