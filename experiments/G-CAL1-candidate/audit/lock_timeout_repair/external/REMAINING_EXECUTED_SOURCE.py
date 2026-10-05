"""One independent read-only G-CAL1 audit. Never import producer main/certify."""
import sys
sys.dont_write_bytecode = True
import os
import socket
import json
import hashlib
import time
import threading
import traceback
import subprocess
import copy
import shutil
import tempfile
from collections import Counter
from itertools import combinations
from datetime import date, timedelta
from unittest.mock import patch
from pathlib import Path
from contextlib import contextmanager

REPO = Path('C:/Users/marcu/Eidolon-g4adj')
OUT = Path(__file__).resolve().parent
os.environ['GIT_OPTIONAL_LOCKS'] = '0'
NETWORK_ATTEMPTS = []
def deny_network(*args, **kwargs):
    NETWORK_ATTEMPTS.append(repr(args))
    raise RuntimeError('AUDIT_SOCKET_NETWORK_DENIED')
socket.socket = deny_network
socket.create_connection = deny_network
socket.getaddrinfo = deny_network
socket.gethostbyname = deny_network
def isolation_hook(event, args):
    if event.startswith('socket.'):
        deny_network(event, args)
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, (str, bytes, os.PathLike)) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            p = Path(os.fsdecode(path)).resolve()
            if p.is_relative_to(REPO):
                raise RuntimeError('AUDIT_REPOSITORY_WRITE_DENIED:' + str(p))
    if event in ('os.remove', 'os.rmdir', 'os.mkdir', 'os.rename', 'os.link', 'os.symlink'):
        for arg in args[:2 if event in ('os.rename', 'os.link', 'os.symlink') else 1]:
            if isinstance(arg, (str, bytes, os.PathLike)) and Path(os.fsdecode(arg)).resolve().is_relative_to(REPO):
                raise RuntimeError('AUDIT_REPOSITORY_MUTATION_DENIED:' + event)
sys.addaudithook(isolation_hook)
sys.path.insert(0, str(REPO / 'tools'))
import g_cal1_lab as lab
import g_cal1_contract as contract
from g_extract1_contract import IntegrityError

ROWS = []
DETAIL = {}
class AuditBlocker(Exception):
    pass
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
def save(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canon(value))
        stream.flush()
        os.fsync(stream.fileno())
def check(ok, name, severity='P1', file='tools/g_cal1_lab.py', line=25):
    row = dict(name=name, passed=bool(ok), severity=severity, file=file, line=line)
    ROWS.append(row)
    if len(ROWS)<=5 or len(ROWS)%500==0 or not ok:
        print(json.dumps(row), flush=True)
    if not ok:
        raise AuditBlocker(name)
def reject(action, name, event=None, prompt=False):
    start = time.monotonic()
    try:
        action()
    except IntegrityError as exc:
        check(event is None or exc.event == event, name + ':event')
        if prompt:
            check(time.monotonic() - start < 3, name + ':prompt rejection')
        return exc
    check(False, name + ':forbidden action accepted')
def records(directory):
    return [json.loads(p.read_bytes())['payload'] for p in sorted((directory / 'journal').glob('*.json'))]
def tree(directory):
    return {p.relative_to(directory).as_posix(): sha(p.read_bytes()) for p in sorted(directory.rglob('*')) if p.is_file()}
def git(*args):
    result = subprocess.run(['git', '-c', 'safe.directory=' + REPO.as_posix(), *args], cwd=REPO, capture_output=True, check=True)
    return result.stdout
def transport(package, calls):
    def invoke(request, row):
        calls.append(row['call_id'])
        return {'raw_output':canon(package.members[row['fixture_id']]['gold']).decode(), 'provider_truncated':False,
                'receipt':{'call_id':row['call_id'], 'request_sha256':sha(request), 'synthetic_only':True}}
    invoke.synthetic_only = True
    return invoke

def first_timeout():
    save('initial_git.json', {'head':git('rev-parse', 'HEAD').decode().strip(),
                             'branch':git('branch', '--show-current').decode().strip(),
                             'status':git('status', '--porcelain=v1', '--untracked-files=all').decode()})
    package = contract.Package()
    directory = OUT / 'raw/actual_timeout'
    run_id = 'G-CAL1-SYNTHETIC-INDEPENDENT-TIMEOUT-7b32e6a1'
    a = lab.Run(package, directory, run_id)
    b = lab.Run(package, directory, run_id, resume=True)
    c = lab.Run(package, directory, run_id, resume=True)
    # Readiness is paused before the unverified-resume guard; no START is possible.
    ready_entered, release = threading.Event(), threading.Event()
    class PreStartCleanup(BaseException):
        pass
    cleanup = PreStartCleanup('external pre-START cleanup')
    observed = []
    calls = []
    tx = transport(package, calls)
    a_result = []
    def paused_ready():
        ready_entered.set()
        release.wait(150)
        raise cleanup
    a._ready = paused_ready
    real_lock = lab.run_lock
    @contextmanager
    def observe_lock(path):
        try:
            with real_lock(path):
                yield
        except IntegrityError as exc:
            if threading.current_thread() is threading.main_thread():
                observed.append((exc, type(exc), exc.args))
            raise
    lab.run_lock = observe_lock
    def hold():
        try:
            a.perform(package.schedule[0], tx)
        except BaseException as exc:
            a_result.append(exc)
    thread = threading.Thread(target=hold, name='A-governed-real-lock')
    thread.start()
    try:
        check(ready_entered.wait(5) and thread.is_alive(), 'timeout:A holds lock inside public perform')
        begun = time.monotonic()
        try:
            b.perform(package.schedule[0], tx)
        except IntegrityError as exc:
            caught = exc
        else:
            check(False, 'timeout:B did not naturally time out')
        elapsed = time.monotonic() - begun
        check(120 <= elapsed < 140, 'timeout:unmodified real 120-second wait', file='tools/g_cal1_lock.py', line=27)
        check(bool(observed) and caught is observed[0][0] and type(caught) is observed[0][1] and caught.args == observed[0][2],
              'timeout:original lock exception object/type/args re-raised')
        check(caught.event == 'PROVENANCE_MISMATCH' and caught.detail == 'run operation lock unavailable', 'timeout:actual lock path event/detail')
        check(thread.is_alive() and not release.is_set(), 'timeout:persisted before A releases lock')
        paths = sorted((directory / 'lock_boundary_incidents').glob('*.json'))
        check(len(paths) == 1, 'timeout:exactly one authoritative published boundary incident', line=145)
        raw = paths[0].read_bytes()
        envelope = json.loads(raw)
        payload = envelope['payload']
        check(raw == canon(envelope) and envelope['sha256'] == sha(canon(payload)) and
              envelope['schema_version'] == lab.BOUNDARY_INCIDENT_SCHEMA, 'timeout:canonical sealed envelope', line=114)
        check(payload == {'event':'PROVENANCE_MISMATCH', 'detail':caught.detail, 'phase':'CAL',
                          'cell':package.schedule[0]['cell_id'], 'run_id':run_id, 'binding':b.binding}, 'timeout:all incident bindings', line=115)
        catalog = package.historical.design['event_catalog'] if 'event_catalog' in package.historical.design else package.historical.design
        from g_extract1_scoring import event_category
        check(event_category(package.historical.design, payload['event']) == 'INVALID', 'timeout:frozen inherited category INVALID')
        check(b.state()['verdict'] == 'INVALID', 'timeout:B same-object state INVALID')
        check(not calls and records(directory) == [{'kind':'RUN_CREATED', 'run_id':run_id, 'binding':b.binding,
                                                    'mode':'SYNTHETIC_ONLY', 'authority':None}], 'timeout:zero transport zero START no fake receipts')
        check(b.incidents.read() == [], 'timeout:ordinary incident journal is not substituted for boundary evidence')
        incident_before = tree(directory / 'lock_boundary_incidents')
        for label, obj in [('B', b), ('stale C', c)]:
            reject(lambda obj=obj: obj.perform(package.schedule[0], tx), 'held:' + label, 'PROVENANCE_MISMATCH', prompt=True)
            check(obj.state()['verdict'] == 'INVALID', 'held:' + label + ':INVALID')
        reject(lambda: lab.Run(package, directory, run_id, resume=True), 'held:fresh constructor/resume', 'PROVENANCE_MISMATCH', prompt=True)
        check(thread.is_alive() and not calls and len(records(directory)) == 1, 'held:all rejections before reacquiring contended lock')
        release.set()
        thread.join(5)
        check(not thread.is_alive() and a_result == [cleanup], 'release:A pre-START exact cleanup')
        for label, obj in [('B', b), ('stale C', c)]:
            reject(lambda obj=obj: obj.perform(package.schedule[0], tx), 'released:' + label, 'PROVENANCE_MISMATCH', prompt=True)
        reject(lambda: lab.Run(package, directory, run_id, resume=True), 'released:fresh constructor/resume', 'PROVENANCE_MISMATCH', prompt=True)
        check(incident_before == tree(directory / 'lock_boundary_incidents'), 'timeout:published incident immutable through retries')
        check(not calls and len(records(directory)) == 1 and not any(p['kind'] == 'START' for p in records(directory)),
              'released:zero new/open START zero transport no fabricated receipts')
        DETAIL['actual_timeout'] = {'elapsed_seconds':elapsed, 'event':caught.event, 'category':'INVALID',
                                   'original_type':type(caught).__name__, 'original_args':caught.args,
                                   'incident_file':str(paths[0]), 'incident_sha256':sha(raw), 'transport':0, 'START':0,
                                   'open_START':False, 'same_stale_fresh_held_and_released':'REJECTED'}
    finally:
        release.set()
        thread.join(5)
        lab.run_lock = real_lock

OMISSION = 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT'
COUNTER = 0
def fresh(package, name):
    global COUNTER
    COUNTER += 1
    return lab.Run(package, OUT / 'raw' / f'{COUNTER:03d}-{name}', f'G-CAL1-SYNTHETIC-INDEPENDENT-{COUNTER:03d}')
def terminal(run, tx, calls, event, name):
    before = list(calls), records(run.directory)
    reject(lambda:run.perform(run.package.schedule[min(len(run.attempted),79)], tx), name + ':same-object terminal', event)
    check(before == (calls, records(run.directory)), name + ':no later contact/START/receipt')
    reject(lambda:lab.Run(run.package, run.directory, run.run_id, resume=True), name + ':fresh resume terminal', event)
    check(any(r['payload']['event'] == event for r in run.incidents.read()), name + ':ordinary incident durable')
def bad_checkpoint(run, payload=None):
    path = run.directory / 'invalid-checkpoint.json'
    save(path.relative_to(OUT).as_posix(), {'payload':payload, 'sha256':sha(canon(payload))})
    return path
def await_file(path, timeout=10):
    start = time.monotonic()
    while not path.exists():
        if time.monotonic() - start > timeout:
            raise RuntimeError('QA child coordination timeout:' + str(path))
        time.sleep(0.01)
def child_worker(role, directory, run_id, ready, go, attempted, argument):
    p = contract.Package()
    r = lab.Run(p, directory, run_id, resume=True)
    save(Path(ready).relative_to(OUT).as_posix(), {'ready':True})
    await_file(Path(go), 40)
    save(Path(attempted).relative_to(OUT).as_posix(), {'attempted':True})
    if role == 'invalidate':
        try:
            r.verify_resume(Path(argument))
        except IntegrityError as exc:
            save(Path(ready).with_suffix('.result.json').relative_to(OUT).as_posix(), {'event':exc.event, 'state':r.state()})
            return
        raise RuntimeError('child unexpectedly accepted bad checkpoint')
    if role == 'publish':
        r._error_cell = argument
        r._retain_boundary_incident(IntegrityError('PROVENANCE_MISMATCH', 'independent publication race'))
        save(Path(ready).with_suffix('.result.json').relative_to(OUT).as_posix(), {'state':r.state()})
        return
    raise ValueError(role)
def launch_child(run, role, tag, argument):
    base = OUT / 'coordination' / tag
    ready, go, attempted = base.with_suffix('.ready'), base.with_suffix('.go'), base.with_suffix('.attempted')
    process = subprocess.Popen([sys.executable, '-B', str(__file__), 'child', role, str(run.directory), run.run_id,
                                str(ready), str(go), str(attempted), str(argument)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await_file(ready)
    return process, ready, go, attempted
def complete_child(child, name):
    process, ready, go, attempted = child
    stdout, stderr = process.communicate(timeout=20)
    save('coordination/' + name + '-output.json', {'returncode':process.returncode, 'stdout':stdout.decode(), 'stderr':stderr.decode()})
    if process.returncode != 0:
        raise RuntimeError('QA child failure:' + stderr.decode())
    return json.loads(ready.with_suffix('.result.json').read_bytes())

def former_blockers(p):
    calls = []
    tx = transport(p, calls)
    # Every authority-bearing entry must synchronize stale incident state.
    for op in ('perform', 'checkpoint', 'verify_resume', 'final_report'):
        owner = fresh(p, 'P1A-stale-' + op)
        cp = owner.checkpoint()
        stale = lab.Run(p, owner.directory, owner.run_id, resume=True)
        reject(lambda:owner.verify_resume(bad_checkpoint(owner)), 'P1A:owner corrupt checkpoint', 'CORRUPTED_CHECKPOINT')
        action = {'perform':lambda:stale.perform(p.schedule[0],tx), 'checkpoint':stale.checkpoint,
                  'verify_resume':lambda:stale.verify_resume(cp), 'final_report':stale.final_report}[op]
        reject(action, 'P1A:stale public ' + op, 'CORRUPTED_CHECKPOINT')
        terminal(stale, tx, calls, 'CORRUPTED_CHECKPOINT', 'P1A:' + op)
    r = fresh(p, 'P1A-duplicate')
    cp = r.checkpoint()
    stale = lab.Run(p, r.directory, r.run_id, resume=True)
    stale.verify_resume(cp)
    stale.perform(p.schedule[0],tx)
    before = len(calls)
    reject(lambda:r.perform(p.schedule[0],tx), 'P1A:stale duplicate rejects')
    check(len(calls) == before and sum(x['kind']=='START' for x in records(r.directory)) == 1, 'P1A:one exact authoritative attempt')
    r = fresh(p, 'P1A-thread-race')
    cp = r.checkpoint()
    other = lab.Run(p, r.directory, r.run_id, resume=True)
    bad = bad_checkpoint(r)
    attempted, done = threading.Event(), threading.Event()
    result = []
    def invalidate():
        attempted.set()
        try:
            other.verify_resume(bad)
        except IntegrityError as exc:
            result.append(exc.event)
        finally:
            done.set()
    t = threading.Thread(target=invalidate)
    original = lab.transport_boundary
    def at_boundary(tport, mechanical):
        original(tport,mechanical)
        t.start()
        check(attempted.wait(5) and not done.wait(0.2) and not r.incidents.read(), 'P1A:thread blocked across readiness/contact critical section')
    with patch.object(lab,'transport_boundary',at_boundary):
        r.perform(p.schedule[0],tx)
    t.join(5)
    check(done.is_set() and result == ['CORRUPTED_CHECKPOINT'] and records(r.directory)[-1]['kind']=='COMPLETE',
          'P1A:thread retention occurs after durable call closure')
    terminal(r,tx,calls,'CORRUPTED_CHECKPOINT','P1A:thread race')
    r = fresh(p, 'P1A-process-race')
    r.checkpoint()
    bad = bad_checkpoint(r)
    child = launch_child(r,'invalidate','P1A-process',bad)
    def process_boundary(tport, mechanical):
        original(tport,mechanical)
        save(child[2].relative_to(OUT).as_posix(), {'go':True})
        await_file(child[3])
        time.sleep(0.2)
        check(child[0].poll() is None and not r.incidents.read(), 'P1A:independent process cannot enter held lifecycle lock')
    with patch.object(lab,'transport_boundary',process_boundary):
        r.perform(p.schedule[0],tx)
    result = complete_child(child,'P1A-process')
    check(result['event']=='CORRUPTED_CHECKPOINT' and records(r.directory)[-1]['kind']=='COMPLETE', 'P1A:cross-process retention follows durable closure')
    terminal(r,tx,calls,'CORRUPTED_CHECKPOINT','P1A:process race')
    class AuditControl(BaseException):
        pass
    vectors = []
    for signal_type in (KeyboardInterrupt, SystemExit, GeneratorExit, AuditControl):
        for point in ('transport','normalization','receipt','scoring','before_COMPLETE','after_durable_COMPLETE'):
            r = fresh(p, 'P1B-' + signal_type.__name__ + '-' + point)
            signal = signal_type('independently observed original signal')
            old_outcome, old_evaluate, old_append = lab.transport_outcome, lab.evaluate, r.journal.append
            def returned(request,row):
                calls.append(row['call_id'])
                if point == 'transport':
                    raise signal
                value = transport(p,[])(request,row)
                if point == 'receipt':
                    class ReceiptTraversalBomb(list):
                        def __iter__(self):
                            raise signal
                    value['receipt']['extra'] = ReceiptTraversalBomb([1])
                return value
            returned.synthetic_only = True
            def outcome(row,value):
                if point=='normalization':
                    raise signal
                return old_outcome(row,value)
            def scoring(*args,**kwargs):
                if point=='scoring':
                    raise signal
                return old_evaluate(*args,**kwargs)
            def append(value):
                if value['kind']=='COMPLETE' and point=='before_COMPLETE':
                    raise signal
                result = old_append(value)
                if value['kind']=='COMPLETE' and point=='after_durable_COMPLETE':
                    raise signal
                return result
            with patch.object(lab,'transport_outcome',outcome), patch.object(lab,'evaluate',scoring), patch.object(r.journal,'append',append):
                try:
                    r.perform(p.schedule[0],returned)
                except BaseException as caught:
                    check(caught is signal and type(caught) is signal_type and caught.args==signal.args, 'P1B:' + signal_type.__name__ + '/' + point + ':exact signal propagated', line=306)
                else:
                    check(False,'P1B:signal swallowed',line=306)
            kinds = [x['kind'] for x in records(r.directory)]
            if point=='after_durable_COMPLETE':
                check(kinds==['RUN_CREATED','START','COMPLETE'] and not r.incidents.read(), 'P1B:durable COMPLETE no false omission', line=309)
                r.perform(p.schedule[1],tx)
                check(len(r.evidence)==len(r.attempted)==2, 'P1B:completed replay safely advances only to next observation')
                cp = r.checkpoint()
                replay = lab.Run(p,r.directory,r.run_id,resume=True)
                replay.verify_resume(cp)
                check(replay.evidence==r.evidence,'P1B:durable COMPLETE restart replay exact')
            else:
                check(kinds==['RUN_CREATED','START'] and r.events==[OMISSION] and r.state()['verdict']=='INVALID',
                      'P1B:preclosure INVALID omission, no fabricated receipt', line=320)
                check(r.event_scopes==[{'event':OMISSION,'phase':'CAL','cell':p.schedule[0]['cell_id']}], 'P1B:exact terminal scope')
                terminal(r,tx,calls,OMISSION,'P1B:' + signal_type.__name__ + '/' + point)
            vectors.append({'signal':signal_type.__name__,'point':point,'directory':str(r.directory)})
    save('raw/control_flow_vectors.json',vectors)
    mutations = ('schedule_order','seed','wire_hash','source_date','offset','gold','fixture_gold','design','baseline','pins','historical_design','binding')
    for mutation in mutations:
        q = contract.Package()
        r = fresh(q,'P1C-cache-' + mutation)
        row = copy.deepcopy(q.schedule[0])
        member = q.members[row['fixture_id']]
        if mutation=='schedule_order':q.schedule.reverse()
        elif mutation=='seed':q.schedule[0]['seed'] = 0
        elif mutation=='wire_hash':q.schedule[0]['request_sha256'] = '0'*64
        elif mutation=='source_date':member['source_date'] = '2001-01-01'
        elif mutation=='offset':member['offset'] = 0
        elif mutation=='gold':member['gold'][next(iter(member['gold']))] = '2001-01-01'
        elif mutation=='fixture_gold':member['fixture']['gold_values'][next(iter(member['gold']))] = '2001-01-01'
        elif mutation=='design':q.design['generation_configuration']['temperature'] = 0
        elif mutation=='baseline':q.baseline['system_text'] = 'changed'
        elif mutation=='pins':q.pins.clear()
        elif mutation=='historical_design':q.historical.design['baseline_binding']['system_text'] = 'changed'
        elif mutation=='binding':q.binding['schedule_sha256'] = '0'*64
        before = len(calls)
        reject(lambda:r.perform(row,tx),'P1C:authority cache drift ' + mutation)
        check(len(calls)==before and [x['kind'] for x in records(r.directory)]==['RUN_CREATED'], 'P1C:cache drift no START/contact ' + mutation)
    r = fresh(p,'P1C-callback-alias')
    original_schedule = canon(p.schedule)
    def alias(request,row):
        value = transport(p,[])(request,row)
        row['seed'] = 0
        row['generation_configuration']['temperature'] = 0
        return value
    alias.synthetic_only = True
    r.perform(p.schedule[0],alias)
    r.perform(p.schedule[1],tx)
    check(canon(p.schedule)==original_schedule and len(r.evidence)==2,'P1C:callback row/config alias cannot mutate frozen schedule')
    shadow = OUT / 'raw/clone-package'
    for relative in p.pins:
        target = shadow / relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(REPO / relative,target)
    clone_data = shadow / 'experiments/G-CAL1-candidate'
    shutil.copyfile(contract.DATA / 'LAB_MANIFEST.json',clone_data / 'LAB_MANIFEST.json')
    for relative in ('corpus/CORPUS.json','DESIGN.json','schedule/SCHEDULE.json'):
        target = clone_data / relative
        original_bytes = target.read_bytes()
        with patch.object(contract,'ROOT',shadow), patch.object(contract,'DATA',clone_data):
            q = contract.Package()
            r = fresh(q,'P1C-disk-' + target.stem)
            before = len(calls)
            with target.open('wb') as stream:
                stream.write(b'{}')
            reject(lambda:r.perform(p.schedule[0],tx), 'P1C:actual cloned disk mutation ' + relative, 'PRE_ARTIFACT_DIGEST_MISMATCH')
            check(len(calls)==before and len(records(r.directory))==1, 'P1C:cloned stale cache cannot conceal disk mutation')
            with target.open('wb') as stream:
                stream.write(original_bytes)
    for marker in ('ABSENT',False,1,None,'true'):
        r = fresh(p,'P1D-marker-' + repr(marker))
        invoked = []
        def marked(request,row):
            invoked.append(1)
            return transport(p,[])(request,row)
        if marker!='ABSENT':marked.synthetic_only = marker
        reject(lambda:r.perform(p.schedule[0],marked), 'P1D:explicit True only ' + repr(marker),'PROVENANCE_MISMATCH')
        check(not invoked and len(records(r.directory))==1,'P1D:unacceptable marker no START/contact')
    class NonSynthetic:
        synthetic_only = False
        def __call__(self,*args):
            raise RuntimeError('forbidden adapter contacted')
    for adapter in (NonSynthetic(), lambda *args:NonSynthetic()(*args)):
        r = fresh(p,'P1D-wrapper')
        reject(lambda:r.perform(p.schedule[0],adapter),'P1D:unmarked wrapper/provider-like callable rejects','PROVENANCE_MISMATCH')
        check(len(records(r.directory))==1,'P1D:wrapper no START')
    r = fresh(p,'uncontended-positive')
    r.perform(p.schedule[0],tx)
    check(len(r.evidence)==1 and not r.events and not r.incidents.read() and not r._boundary_records(),'normal uncontended:explicit True succeeds no spurious incidents')
    r.perform(p.schedule[1],tx)
    check(len(r.evidence)==2,'normal uncontended:lock released and acquired again')
    for grant in (None, {'status':'EXECUTION_FREEZE_CANDIDATE_ONLY'}, {'status':'EXPLICIT_OPERATOR_PHASE_AUTHORIZATION','phase':'CAL'}):
        directory = OUT / 'raw/forbidden-live'
        reject(lambda:lab.Run(p,directory,'NOT-A-REAL-RUN',mechanical=False,authorization=grant), 'P1D:inactive live authority denied','PROVENANCE_MISMATCH')
        check(not directory.exists(),'P1D:no live authority/run directory created')
    DETAIL['former_blockers'] = {'P1A':'PASS:four stale public methods, duplicate, coordinated thread/process',
                                'P1B':{'signals':4,'points':6,'vectors':24,'exact_propagation':True},
                                'P1C':{'cache_mutations':12,'actual_cloned_disk_mutations':3,'callback_alias':'detached'},
                                'P1D':{'positive_explicit_True':True,'unmarked_false_1_wrapper_reject':True,'live_authority':'inactive rejected'}}

def boundary_publication(p):
    r = fresh(p,'boundary-process-publication')
    children = [launch_child(r,'publish','boundary-' + cell,cell) for cell in ('C1','C2')]
    old_ready = r._ready
    def publish_while_held():
        for child in children:
            save(child[2].relative_to(OUT).as_posix(),{'go':True})
        results = [complete_child(child,'boundary-' + str(i)) for i,child in enumerate(children)]
        check(all(x['state']['verdict']=='INVALID' for x in results),'boundary:independent processes publish while lifecycle lock held',line=176)
        check(len(r._boundary_records())==2,'boundary:concurrent distinct sealed incidents preserved',line=176)
        old_ready()
    r._ready = publish_while_held
    reject(lambda:r.perform(p.schedule[0],transport(p,[])),'boundary:holder observes independently published terminality','PROVENANCE_MISMATCH')
    check(len(records(r.directory))==1,'boundary:publication adds no ordinary START or fake receipts')
    published = tree(r.directory / 'lock_boundary_incidents')
    r._error_cell = 'C3'
    fixed_name = next(iter(published))[:-5]
    class FixedUUID:
        hex = fixed_name
    try:
        with patch.object(lab.uuid,'uuid4',lambda:FixedUUID()):
            r._retain_boundary_incident(IntegrityError('PROVENANCE_MISMATCH','collision test'))
    except FileExistsError:
        check(True,'boundary:no-replace hardlink collision fails rather than overwrites',line=176)
    else:
        check(False,'boundary:collision overwrote published incident',line=176)
    check(all(sha((r.directory/'lock_boundary_incidents'/name).read_bytes())==digest for name,digest in published.items()),'boundary:all original incident bytes unchanged after publication collision')
    paths = sorted((r.directory/'lock_boundary_incidents').glob('*.json'))
    template = json.loads(paths[0].read_bytes())
    for field, value, reseal in [('run_id','WRONG',True),('binding',{},True),('phase','A',True),('cell',1,True),('event','UNKNOWN',True),('detail',1,True),('detail','corrupt',False)]:
        q = fresh(p,'boundary-tamper-' + field + '-' + str(reseal))
        envelope = copy.deepcopy(template)
        envelope['payload'].update(run_id=q.run_id,binding=q.binding)
        envelope['payload'][field] = value
        envelope['sha256'] = sha(canon(envelope['payload'])) if reseal else '0'*64
        save((q.directory/'lock_boundary_incidents'/('a'*32+'.json')).relative_to(OUT).as_posix(),envelope)
        reject(lambda:q._boundary_records(),'boundary:seal/binding tamper ' + field,'CORRUPTED_OR_UNPARSEABLE_JOURNAL')
    q = fresh(p,'boundary-noncanonical')
    envelope = copy.deepcopy(template)
    envelope['payload'].update(run_id=q.run_id,binding=q.binding)
    envelope['sha256'] = sha(canon(envelope['payload']))
    path = q.directory/'lock_boundary_incidents'/('b'*32+'.json')
    path.parent.mkdir()
    with path.open('xb') as stream:
        stream.write(json.dumps(envelope,indent=2).encode())
    reject(q._boundary_records,'boundary:noncanonical correctly sealed envelope rejects','CORRUPTED_OR_UNPARSEABLE_JOURNAL')
    DETAIL['boundary_publication'] = {'concurrent_processes':2,'atomic_no_replace':'PASS','no_overwrite':'PASS','binding_seal_mutations':8}

def storage_review(p):
    calls = []
    tx = transport(p,calls)
    r = fresh(p,'checkpoint-success')
    r.perform(p.schedule[0],tx)
    cp = r.checkpoint()
    replay = lab.Run(p,r.directory,r.run_id,resume=True)
    replay.verify_resume(cp)
    replay.perform(p.schedule[1],tx)
    check(len(replay.evidence)==2 and replay.state()['qualified']==[],'checkpoint:verified exact restart continues at next observation only')
    for operation in ('perform','checkpoint','final_report'):
        r = fresh(p,'unverified-' + operation)
        r.checkpoint()
        replay = lab.Run(p,r.directory,r.run_id,resume=True)
        action = {'perform':lambda:replay.perform(p.schedule[0],tx),'checkpoint':replay.checkpoint,'final_report':replay.final_report}[operation]
        reject(action,'resume:unverified ' + operation,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT')
        terminal(replay,tx,calls,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT','resume:' + operation)
    for payload in ([],None,0,'bad',True,{}, {'journal_prefix':{}}, {'next_schedule_position':'1'}):
        r = fresh(p,'malformed-checkpoint')
        good = r.checkpoint()
        replay = lab.Run(p,r.directory,r.run_id,resume=True)
        bad = bad_checkpoint(r,payload)
        reject(lambda:replay.verify_resume(bad),'checkpoint:malformed shape','CORRUPTED_CHECKPOINT')
        reject(lambda:replay.verify_resume(good),'checkpoint:later original cannot erase retained invalidity','CORRUPTED_CHECKPOINT')
        terminal(replay,tx,calls,'CORRUPTED_CHECKPOINT','checkpoint:malformed')
    for mutation in ('run_id','frozen_binding','schedule_sha256','next_schedule_position','journal_prefix','state'):
        r = fresh(p,'checkpoint-binding-' + mutation)
        cp = r.checkpoint()
        value = json.loads(cp.read_bytes())
        value['payload'][mutation] = None
        value['sha256'] = sha(canon(value['payload']))
        bad = r.directory/'resealed-bad.json'
        save(bad.relative_to(OUT).as_posix(),value)
        reject(lambda:r.verify_resume(bad),'checkpoint:resealed lineage corruption ' + mutation)
    row = p.schedule[0]
    for kind, expected in [('timeout','PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT'),('error','PROVIDER_ERROR_WITH_FAILURE_RECEIPT'),
                           ('missing','MISSING_RESPONSE_WITH_FAILURE_RECEIPT'),('unreceipted','PROVIDER_FAILURE_WITHOUT_RECEIPT')]:
        r = fresh(p,'failure-' + kind)
        receipt = None if kind=='unreceipted' else {'call_id':row['call_id'],'request_sha256':row['request_sha256'],'failure_kind':kind}
        def failure(*args):
            calls.append('failure')
            return {'failure':kind,'receipt':receipt}
        failure.synthetic_only = True
        reject(lambda:r.perform(row,failure),'receipt:failure governed closure ' + kind,expected)
        check([x['kind'] for x in records(r.directory)]==['RUN_CREATED','START','FAILURE'], 'receipt:exact START/FAILURE closure no COMPLETE')
        terminal(r,tx,calls,expected,'receipt:no retry ' + kind)
    for value in (None,[],{}, {'raw_output':'{}'}, {'failure':'timeout','receipt':{'call_id':'wrong'}},
                  {'raw_output':'{}','provider_truncated':1,'receipt':{}}, {'raw_output':'{}','provider_truncated':False,'receipt':{'call_id':'wrong','request_sha256':'wrong'}}):
        r = fresh(p,'malformed-outcome')
        def invalid(*args):return value
        invalid.synthetic_only = True
        reject(lambda:r.perform(row,invalid),'receipt:malformed outcome fails closed','PROVIDER_FAILURE_WITHOUT_RECEIPT')
        terminal(r,tx,calls,'PROVIDER_FAILURE_WITHOUT_RECEIPT','receipt:malformed no retry')
    for key,value in [('schedule_position',2),('seed',0),('request_sha256','0'*64),('model','wrong'),('provider_version','wrong'),('generation_configuration',{})]:
        r = fresh(p,'schedule-drift-' + key)
        bad = copy.deepcopy(row)
        bad[key] = value
        before = len(calls)
        reject(lambda:r.perform(bad,tx),'schedule:field drift ' + key)
        check(len(calls)==before and len(records(r.directory))==1,'schedule:drift before START/contact')
    r = fresh(p,'journal-corruption')
    r.perform(row,tx)
    target = r.directory/'journal/000002.json'
    value = json.loads(target.read_bytes())
    value['payload']['request_sha256'] = '0'*64
    with target.open('wb') as stream:stream.write(canon(value))
    reject(r.checkpoint,'journal:hash-chain corruption retained','CORRUPTED_OR_UNPARSEABLE_JOURNAL')
    terminal(r,tx,calls,'CORRUPTED_OR_UNPARSEABLE_JOURNAL','journal:corruption')
    DETAIL['storage'] = {'unverified_public_methods':3,'malformed_checkpoint_shapes':8,'resealed_checkpoint_mutations':6,
                         'failure_receipt_kinds':4,'malformed_outcomes':7,'schedule_field_mutations':6,'hash_chain_corruption':'rejected'}

def full_review():
    check(json.loads((OUT/'timeout_result.json').read_bytes())['verdict']=='PASS','first unmodified timeout gate passed before broad tests')
    tempfile.tempdir = str(OUT)
    os.environ['TMP'] = os.environ['TEMP'] = str(OUT)
    before = repository_snapshot()
    save('REPOSITORY_BEFORE.json',before)
    p = contract.Package()
    former_blockers(p)
    boundary_publication(p)
    storage_review(p)
    science_review(p)
    pilots_bindings_preservation(p,before)

def remaining_review():
    global COUNTER
    COUNTER = 61
    previous = json.loads((OUT/'full_result.json').read_bytes())
    prior_assertions = json.loads((OUT/'full_assertions.json').read_bytes())
    check(len(prior_assertions)==259 and all(x['passed'] for x in prior_assertions[:-1]) and
          prior_assertions[-1]['name']=='boundary:seal/binding tamper event:event' and
          'PROVENANCE_MISMATCH:unfrozen event:UNKNOWN' in previous['error'],
          'same audit:only unsupported harness expectation interrupted preceding coverage')
    check(json.loads((OUT/'HARNESS_EXPECTATION_ADJUDICATION.json').read_bytes())['product_repair'] is False,
          'same audit:raw stop adjudicated without product changes')
    DETAIL.update(previous['details'])
    tempfile.tempdir = str(OUT)
    os.environ['TMP'] = os.environ['TEMP'] = str(OUT)
    before = json.loads((OUT/'REPOSITORY_BEFORE.json').read_bytes())
    check(before==repository_snapshot(),'same audit:checkout bytes unchanged across harness-only handoff')
    p = contract.Package()
    template_path = next((OUT/'raw/056-boundary-process-publication/lock_boundary_incidents').glob('*.json'))
    template = json.loads(template_path.read_bytes())
    for field,value,reseal,expected in [('event','UNKNOWN',True,'PROVENANCE_MISMATCH'),
                                        ('detail',1,True,'CORRUPTED_OR_UNPARSEABLE_JOURNAL'),
                                        ('detail','corrupt',False,'CORRUPTED_OR_UNPARSEABLE_JOURNAL')]:
        q = fresh(p,'remaining-boundary-' + field + '-' + str(reseal))
        envelope = copy.deepcopy(template)
        envelope['payload'].update(run_id=q.run_id,binding=q.binding)
        envelope['payload'][field] = value
        envelope['sha256'] = sha(canon(envelope['payload'])) if reseal else '0'*64
        save((q.directory/'lock_boundary_incidents'/('a'*32+'.json')).relative_to(OUT).as_posix(),envelope)
        reject(q._boundary_records,'boundary:correct frozen rejection ' + field,expected)
        calls = []
        reject(lambda:q.perform(p.schedule[0],transport(p,calls)),'boundary:public entry rejects tampered envelope ' + field,expected)
        check(not calls and len(records(q.directory))==1,'boundary:tampered envelope no public START/contact')
    q = fresh(p,'remaining-boundary-noncanonical')
    envelope = copy.deepcopy(template)
    envelope['payload'].update(run_id=q.run_id,binding=q.binding)
    envelope['sha256'] = sha(canon(envelope['payload']))
    path = q.directory/'lock_boundary_incidents'/('b'*32+'.json')
    path.parent.mkdir()
    with path.open('xb') as stream:stream.write(json.dumps(envelope,indent=2).encode())
    reject(q._boundary_records,'boundary:correct seal but noncanonical envelope rejects','CORRUPTED_OR_UNPARSEABLE_JOURNAL')
    DETAIL['boundary_publication'] = {'concurrent_processes':2,'atomic_no_replace':'PASS','no_overwrite':'PASS',
                                      'binding_seal_mutations':8,'harness_expectation_error':'preserved and adjudicated; no product finding'}
    storage_review(p)
    science_review(p)
    pilots_bindings_preservation(p,before)

def repository_snapshot():
    result = {}
    for directory, subdirs, names in os.walk(REPO):
        subdirs[:] = [x for x in subdirs if x!='.git']
        for name in names:
            if name!='.git':
                path = Path(directory)/name
                result[path.relative_to(REPO).as_posix()] = sha(path.read_bytes())
    return result

def independent_gregorian(source, offset):
    year, month, day = map(int,source.split('-'))
    shift = (14-month)//12
    y, m = year+4800-shift, month+12*shift-3
    julian = day+(153*m+2)//5+365*y+y//4-y//100+y//400-32045+offset
    a = julian+32044
    b = (4*a+3)//146097
    c = a-(146097*b)//4
    d = (4*c+3)//1461
    e = c-(1461*d)//4
    m = (5*e+2)//153
    day = e-(153*m+2)//5+1
    month = m+3-12*(m//10)
    year = 100*b+d-4800+m//10
    return f'{year:04d}-{month:02d}-{day:02d}'

def science_review(p):
    members = list(p.members.values())
    check(len(members)==40 and Counter(m['stratum'] for m in members)=={'C1':10,'C2':10,'C3':10,'C4':10},'science:40 fixtures 10 per C1-C4',file='experiments/G-CAL1-candidate/DESIGN.json',line=11)
    gold_rows = []
    for m in members:
        gold = independent_gregorian(m['source_date'],m['offset'])
        check(m['gold']==m['fixture']['gold_values']=={f'd{m["ordinal"]:03d}_01':gold},'science:independent Gregorian integer-cycle gold ' + m['fixture_id'])
        source, target = date.fromisoformat(m['source_date']),date.fromisoformat(gold)
        check((source+timedelta(days=m['offset'])).isoformat()==gold,'science:integer-cycle/library agreement')
        check(m['ordinal']==4*(m['slot']-1)+int(m['stratum'][1:]) and m['offset']==p.design['allocation'][m['stratum']]['offsets'][m['slot']-1], 'science:ordinal and frozen offset allocation')
        if m['stratum']=='C1':
            check((source.year,source.month)==(target.year,target.month),'science:C1 within-month control')
        elif m['stratum']=='C2':
            check((source.month,target.month,target.year-source.year)==((12,1,1) if m['offset']>0 else (1,12,-1)),'science:C2 exact year boundary')
        elif m['stratum']=='C3':
            months_days = [(2,28),(2,29),(3,1),(2,28),(3,1),(2,28),(3,1),(2,28),(3,1),(2,29)]
            is_leap = source.year%4==0 and (source.year%100!=0 or source.year%400==0)
            check((source.month,source.day)==months_days[m['slot']-1] and is_leap==(m['slot'] in (1,2,3,8,9,10)),'science:C3 leap/common century allocation')
        else:
            walk = [source+timedelta(days=(1 if m['offset']>0 else -1)*i) for i in range(abs(m['offset'])+1)]
            check(source.year!=target.year and any((x.month,x.day)==(2,29) for x in walk)==p.design['allocation']['C4']['path_contains_feb29'][m['slot']-1], 'science:C4 long offset and Feb29 allocation')
        gold_rows.append({'fixture_id':m['fixture_id'],'source_date':m['source_date'],'offset':m['offset'],'independent':gold})
    for s in ('C1','C2','C3','C4'):
        check(sum(m['offset']>0 for m in members if m['stratum']==s)==5,'science:five positive/five negative ' + s)
    sources = {m['source_date'] for m in members}
    golds = {next(iter(m['gold'].values())) for m in members}
    check(len(sources)==len(golds)==40 and not sources & golds,'science:new source/gold unique and disjoint')
    rows, wires = [], []
    for repeat in (1,2):
        for m in sorted(members,key=lambda x:(sha(f'G-CAL1/order/{repeat}/{x["fixture_id"]}'.encode()),x['fixture_id'])):
            n = m['ordinal']
            subject = f'Extract the record record. d{n:03d}_01 is f{n:03d}_01 plus {m["offset"]} calendar days'
            request = {'prompt':p.baseline['structured_extraction_assembled_template'].replace('{SUBJECT}',subject),
                       'input':{'schema':{f'd{n:03d}_01':'YYYY-MM-DD'},'text':f'f{n:03d}_01 is {m["source_date"]}. f{n:03d}_02 is "code_{n:03d}_99".'}}
            check(request==m['request'],'science:independently reconstructed request ' + m['fixture_id'])
            seed = 820000+10*n+repeat
            options = {k:p.design['generation_configuration'][k] for k in ('temperature','top_p','top_k','repeat_penalty','num_ctx','num_predict')}
            options['seed'] = seed
            body = {'model':p.design['model'],'system':p.baseline['system_text'],'prompt':request['prompt']+'\n\nINPUT:\n'+canon(request['input']).decode(),
                    'stream':False,'think':False,'options':options}
            wire = canon(body)
            row = {'schedule_position':len(rows)+1,'call_id':m['fixture_id']+f':REPEAT{repeat}','fixture_id':m['fixture_id'],'stratum':m['stratum'],
                   'repeat':repeat,'cell_id':m['stratum'],'phase':'CAL','seed':seed,'model':p.design['model'],'provider_version':p.design['provider_version'],
                   'generation_configuration':p.design['generation_configuration'],'request_sha256':sha(wire)}
            check(p.wire(row)==wire,'science:exact independent wire/seed ' + row['call_id'])
            check(next(iter(m['gold'].values())).encode() not in wire and m['fixture_id'].encode() not in wire,'science:gold/fixture difficulty identity excluded from model wire')
            rows.append(row)
            wires.append({'call_id':row['call_id'],'body':body,'sha256':sha(wire)})
    request_manifest = json.loads((contract.DATA/'schedule/REQUEST_MANIFEST.json').read_bytes())
    check(rows==p.schedule and request_manifest['wire_requests']==wires and request_manifest['request_count']==80,'science:all 80 schedule rows/request manifest exact')
    check(sha(canon(rows))=='b4d4a5a7ba37961dcfbbe0c6aa6101fbbeb40dcf2dad0c54c8680d216c2e1858','science:frozen schedule SHA')
    check(p.design['interpretation']['mode']=='DESCRIPTIVE_ONLY' and p.design['interpretation']['pass_threshold'] is None and
          p.design['interpretation']['routing_authority'] is False,'science:descriptive only no qualification gates')
    save('raw/independent_gold.json',gold_rows)
    save('raw/independent_wires.json',wires)
    # Frozen dual encoders provide representations, not the audit decision logic.
    import g_cal1_stage as stage
    primary, secondary = stage.old_checkers()
    histories, history_pins, source_dates, gold_dates, counts = stage.history_records(p.historical,primary,secondary)
    new = [stage.evidence(m,p.historical.design,primary,secondary) for m in members]
    original = json.loads((contract.DATA/'corpus/CONTAMINATION_REPORT.json').read_bytes())
    historical, new_pairs = [], []
    na, typed = 0, 0
    for member, a in zip(members,new):
        check(member['source_date'] not in source_dates|gold_dates and next(iter(member['gold'].values())) not in source_dates|gold_dates,'science:historical source/gold freshness ' + member['fixture_id'])
        for h in histories:
            applicable = h['tuple_applicability']=='APPLIES'
            if applicable:
                typed += 1
                check(h['id'].startswith('G-EXTRACT1/'),'science:typed applicability exact')
            else:
                na += 1
                check(h['tuple'] is None and h['tuple_applicability']=='NOT_APPLICABLE_UNREPRESENTABLE_HISTORICAL_PROVENANCE','science:legacy unavailable tuple N/A zero credit')
            i,u = len(a['ordinary'] & h['ordinary']),len(a['ordinary'] | h['ordinary'])
            matches = sum(x==y for x,y in zip(a['projection'],h['projection']))
            okay = all(a[k]!=h[k] for k in ('raw_payload','answer')) and ('raw_values' not in h or a['raw_values']!=h['raw_values'])
            okay = okay and (not applicable or h['tuple'] is None or a['tuple']!=h['tuple'])
            okay = okay and u>0 and i*5<u and matches<3 and (matches<2 or i*25<u*3)
            if h['fp'] is not None:
                same = sum(x==y for x,y in zip(a['fp'],h['fp']))
                okay = okay and same<6 and (same<5 or i*25<u*3)
            check(okay,'science:independent historical controls ' + a['id'] + '/' + h['id'],file='tools/g_cal1_stage.py',line=185)
            historical.append({'new':a['id'],'historical':h['id'],'ordinary_i_u':[i,u],'projection_matches':matches,'tuple_applicability':h['tuple_applicability'],'gate':True})
    dummy = copy.deepcopy(members[0]['request'])
    dummy['input']['text'] = dummy['input']['text'].replace(members[0]['source_date'],'SCaffoldDATE')
    invariants = {g for g in secondary.grams(dummy,p.historical.design) if not any('scaffolddate' in t for t in g)}
    check(invariants=={tuple(x) for x in original['invariant_five_grams']},'science:symbolic fixed scaffold recomputed without masking dates')
    for a,b in combinations(new,2):
        left,right = a['ordinary']-invariants,b['ordinary']-invariants
        i,u = len(left & right),len(left | right)
        check(bool(left and right) and i*25<u*3 and all(a[k]!=b[k] for k in ('raw_payload','raw_values','answer','tuple')),'science:independent NEW/NEW controls ' + a['id'] + '/' + b['id'],file='tools/g_cal1_stage.py',line=310)
        new_pairs.append({'left':a['id'],'right':b['id'],'mode':'DECLARED_SCAFFOLD_RESIDUAL',
                          'ordinary_i_u':[len(a['ordinary']&b['ordinary']),len(a['ordinary']|b['ordinary'])],
                          'shape_i_u':[len(a['shape']&b['shape']),len(a['shape']|b['shape'])],
                          'content_i_u':[len(a['content']&b['content']),len(a['content']|b['content'])],
                          'residual_i_u':[i,u],'residual_gate':True,'ordinary_gate_credited':False,
                          'full_fingerprint_equal':a['fp']==b['fp'],'tuple_applicability':'APPLIES'})
    check(len(historical)==12720 and historical==original['historical_pairs'],'science:12720 exact frozen applicable historical decision records')
    check(len(new_pairs)==780 and new_pairs==original['new_pairs'],'science:780 exact frozen NEW/NEW decision records')
    check(na==5040 and typed==7680 and original['not_applicable_credited_as_pass'] is False,'science:5040 unavailable legacy tuples N/A no pass credit')
    save('raw/independent_contamination.json',{'historical':historical,'new_pairs':new_pairs,'source_pins':history_pins,'history_counts':counts,'unavailable_NA':na,'NA_pass_credit':0,'typed_history':typed})
    DETAIL['science'] = {'fixtures':40,'strata':{'C1':10,'C2':10,'C3':10,'C4':10},'independent_Gregorian_gold':40,'wire_requests':80,
                         'historical':12720,'NEW_NEW':780,'unavailable_legacy_tuple_NA':5040,'NA_pass_credit':0,
                         'schedule_sha256':sha(canon(rows)),'interpretation':'DESCRIPTIVE_ONLY','real_observations':0}

def independent_journal_tree(directory):
    previous, pending, start_count, complete_count = '0'*64,None,0,0
    for sequence, path in enumerate(sorted((directory/'journal').glob('*.json')),1):
        raw = path.read_bytes()
        envelope = json.loads(raw)
        seal = {k:v for k,v in envelope.items() if k!='sha256'}
        check(path.name==f'{sequence:06d}.json' and raw==canon(envelope) and envelope['sequence']==sequence and envelope['previous_sha256']==previous and sha(canon(seal))==envelope['sha256'], 'pilot:independent canonical chain ' + directory.name + '/' + path.name)
        previous = envelope['sha256']
        payload = envelope['payload']
        if payload['kind']=='START':
            check(pending is None,'pilot:no overlapping START')
            pending = payload['row']['call_id']
            start_count += 1
        elif payload['kind']=='COMPLETE':
            check(payload['call_id']==pending and payload['result']['receipt']['call_id']==pending and payload['result']['receipt']['synthetic_only'] is True,'pilot:exact synthetic receipt/COMPLETE lineage')
            pending = None
            complete_count += 1
    check(pending is None and start_count==complete_count==80,'pilot:80 closed unique synthetic observations no open START')
    return start_count,complete_count

def pilots_bindings_preservation(p,before):
    from g_cal1_pilot import full_pilot
    class PilotChecks:
        def check(self,ok,category,detail):
            check(ok,'independent pilot:' + detail,file='tools/g_cal1_pilot.py',line=51)
    trees = []
    for name in ('independent_pilot_one','independent_pilot_two'):
        directory = OUT/'raw'/name
        check(not directory.exists(),'pilot:clean external tree ' + name)
        report = full_pilot(p,directory,PilotChecks())
        independent_journal_tree(directory)
        check(report['state']['completed_observations']==80 and report['state']['qualified']==[] and report['summary']['qualification_gates'] is None and not report['summary']['phase_b'],'pilot:complete descriptive-only no qualification')
        check(not list((directory/'integrity').glob('*.json')) and not (directory/'lock_boundary_incidents').exists(),'pilot:no spurious ordinary/boundary incident')
        trees.append(tree(directory))
        check(len(trees[-1])==327,'pilot:complete authority-bearing tree 327 files')
    check(trees[0]==trees[1],'pilot:two fresh full independent trees byte deterministic')
    candidate_dir = contract.DATA/'preexecution/lock_timeout_repair'
    producer = json.loads((candidate_dir/'PILOT_REPORT.json').read_bytes())
    for name in ('pilot_one','pilot_two'):
        supplied = tree(candidate_dir/name)
        check(supplied==trees[0],'pilot:independent tree equals candidate-bound supplied ' + name)
    check(producer['pilot_tree']==trees[0] and producer['synthetic_observations_each_pilot']==80,'pilot:producer report verified against independently hashed trees')
    candidate_path = candidate_dir/'EXECUTION_FREEZE_CANDIDATE.json'
    candidate = json.loads(candidate_path.read_bytes())
    check(sha(candidate_path.read_bytes())=='59924e2546dc103ed84bc298c489de40e6a63a1815985af0b3b78f0ad7a0dbc9','candidate:exact requested SHA',file=str(candidate_path.relative_to(REPO)),line=1)
    check(candidate['binding']==p.binding and candidate['protected_artifacts']==p.pins and len(p.pins)==99,'candidate:exact binding and 99 protected pins')
    for relative, expected in p.pins.items():
        check(sha((REPO/relative).read_bytes())==expected,'candidate:actual protected bytes ' + relative)
    from g_extract1_journal import SCHEMA
    check(candidate['journal_checkpoint_schema']==SCHEMA and candidate['journal_checkpoint_schema_sha256']==sha(canon(SCHEMA)),'candidate:journal checkpoint schema exact')
    check(candidate['lock_boundary_incident_schema']==lab.BOUNDARY_INCIDENT_SCHEMA,'candidate:boundary schema exact')
    for key,relative in [('pilot_report_sha256','PILOT_REPORT.json'),('preservation_report_sha256','PRESERVATION_REPORT.json'),('timeout_targeted_report_sha256','timeout_attacks/TIMEOUT_REPORT.json')]:
        path = candidate_dir/relative
        if not path.exists() and key=='timeout_targeted_report_sha256':
            matching = [x for x in (candidate_dir/'timeout_attacks').rglob('*.json') if sha(x.read_bytes())==candidate[key]]
            check(len(matching)==1,'candidate:targeted timeout report resolves uniquely')
            path = matching[0]
        check(sha(path.read_bytes())==candidate[key],'candidate:evidence binding ' + key)
    for key,relative in [('failed_lock_timeout_review_sha256','audit/lifecycle_repair/LOCK_TIMEOUT_REVIEW_COMPLETION.json'),
                         ('prior_blocked_audit_sha256','audit/INDEPENDENT_PREREGISTRATION_AUDIT.json'),
                         ('prior_blocked_candidate_sha256','preexecution/final/EXECUTION_FREEZE_CANDIDATE.json'),
                         ('supersedes_unactivated_initial_candidate_sha256','preexecution/EXECUTION_FREEZE_CANDIDATE.json'),
                         ('supersedes_blocked_lock_timeout_candidate_sha256','preexecution/lifecycle_repair/EXECUTION_FREEZE_CANDIDATE.json')]:
        check(sha((contract.DATA/relative).read_bytes())==candidate[key],'candidate:immutable predecessor binding ' + key)
    check(candidate['status']=='EXECUTION_FREEZE_CANDIDATE_ONLY' and candidate['activated'] is False and candidate['execution_authorized'] is False,'candidate:unactivated candidate grants no authority')
    receipts = p.historical.receipts()
    expected_receipts = dict(receipts,models=[receipts['models'][2]])
    check(candidate['provider_binding']==expected_receipts and p.design['generation_configuration']==receipts['generation_configuration'],'candidate:offline-only frozen model/blob/config exact')
    check(not (contract.DATA/'execution/ACTIVE_FREEZE.json').exists() and not (contract.DATA/'execution/EXECUTION_FREEZE_ACTIVATION.json').exists(),'candidate:no active freeze or activation')
    check(git('rev-parse','HEAD').decode().strip()=='ae7902c72384a65d65db53a56fc6afc5b119f8d9' and git('branch','--show-current').decode().strip()=='g-extract1/design','candidate:requested HEAD and branch exact')
    implementation = 'c01706ca04f14e88819b26bdd148a3d61b5688ec'
    for relative in [x for x in p.pins if x.startswith('tools/')]:
        check(sha(git('show',implementation+':'+relative))==sha((REPO/relative).read_bytes()),'candidate:working source equals exact implementation ' + relative)
    check(subprocess.run(['git','-c','safe.directory='+REPO.as_posix(),'merge-base','--is-ancestor',implementation,'HEAD'],cwd=REPO).returncode==0,'candidate:implementation preserved in local history')
    evidence = json.loads((candidate_dir/'EVIDENCE_MANIFEST.json').read_bytes())
    for relative,expected in evidence['files'].items():
        check(sha((candidate_dir/relative).read_bytes())==expected,'candidate:actual producer evidence member ' + relative)
    baseline = json.loads((candidate_dir/'PRESERVATION_BEFORE.json').read_bytes())
    check({name:len(group) for name,group in baseline.items()}=={'science':91,'prior_evidence':33513,'closed_history':2961},'preservation:baseline scopes/counts actual')
    preservation_actual = {}
    for group, pins in baseline.items():
        mismatches = []
        for relative,expected in pins.items():
            actual = sha((REPO/relative).read_bytes())
            if actual!=expected:mismatches.append(relative)
            check(actual==expected,'preservation:' + group + '/' + relative,file=relative,line=1)
        preservation_actual[group] = {'files':len(pins),'mismatches':mismatches}
    old_manifest = json.loads((candidate_dir/'PRIOR_LAB_MANIFEST.json').read_bytes())
    current_manifest = json.loads((contract.DATA/'LAB_MANIFEST.json').read_bytes())
    old_pins = old_manifest['protected_artifacts']
    new_pins = current_manifest['protected_artifacts']
    allowed = {'tools/g_cal1_lab.py','tools/g_cal1_timeout_tests.py','tools/g_cal1_timeout_repair.py'}
    delta = {k for k in set(old_pins)|set(new_pins) if old_pins.get(k)!=new_pins.get(k)}
    check(delta==allowed,'preservation:manifest changes only repaired implementation hashes/additions')
    prior_manifest_fields = {k:v for k,v in old_manifest.items() if k!='protected_artifacts'}
    current_manifest_fields = {k:v for k,v in current_manifest.items() if k!='protected_artifacts'}
    check(prior_manifest_fields==current_manifest_fields,'preservation:manifest non-pin scientific/governance fields unchanged')
    supersession = json.loads((candidate_dir/'CANDIDATE_SUPERSESSION.json').read_bytes())
    check(supersession['blocked_predecessor']['status']=='BLOCKED_UNACTIVATED_SUPERSEDED' and supersession['superseding_candidate']['sha256']==sha(candidate_path.read_bytes()),'history:old f458 candidate remains BLOCKED unactivated superseded')
    old_review = json.loads((contract.DATA/'audit/lifecycle_repair/LOCK_TIMEOUT_REVIEW_COMPLETION.json').read_bytes())
    check(old_review['overall_review_verdict']=='BLOCKED' and old_review['retained_incident_count']==0 and old_review['state_B_after_external_catch']=='RUNNING','history:failed timeout review remains failed, never reinterpreted')
    prior_audit = json.loads((contract.DATA/'audit/INDEPENDENT_PREREGISTRATION_AUDIT.json').read_bytes())
    check(prior_audit['verdict']=='BLOCKED','history:prior independent audit remains BLOCKED')
    stop = json.loads((candidate_dir/'PREPARATION_STOP_01.json').read_bytes())
    check(stop['status']=='PREPARATION_STOP' and stop['test_operations']==0 and stop['provider_model_calls']==0 and stop['independent_audit_started'] is False,'history:initial encoding guard stop preserved no tests')
    closure_commit = '1757155387af122d126f6db9fd03477e2823c2bb'
    for path in (REPO/'experiments/G-EXTRACT1-candidate/closure').glob('*'):
        if path.is_file():
            relative = path.relative_to(REPO).as_posix()
            check(sha(path.read_bytes())==sha(git('show',closure_commit+':'+relative)),'history:accepted G-EXTRACT1 closure exact commit bytes ' + path.name)
    status = json.loads((contract.DATA/'STAGE_STATUS.json').read_bytes())
    check(status['G_EXTRACT1']=='CLOSED VALID NEGATIVE; NO_PHASE_A_CELL_QUALIFIED unchanged' and status['G_ROUTE4']=='CLOSED FAILED unchanged','history:accepted closed histories remain closed')
    untracked = [line[3:] for line in git('status','--porcelain=v1','--untracked-files=all').decode().splitlines() if line.startswith('?? ')]
    check(len(untracked)==7 and all(x.startswith('experiments/G-EXTRACT1-candidate/corpus/') for x in untracked),'preservation:seven unrelated untracked artifacts remain')
    check(all(before[x]==sha((REPO/x).read_bytes()) for x in untracked),'preservation:seven untracked files exact bytes unchanged')
    after = repository_snapshot()
    check(before==after,'preservation:entire checkout exact before/after byte identity')
    check(git('status','--porcelain=v1','--untracked-files=all').decode()==json.loads((OUT/'initial_git.json').read_bytes())['status'],'preservation:git status unchanged from before timeout')
    check(not NETWORK_ATTEMPTS,'governance:zero socket/metadata/provider attempts')
    save('raw/preservation_verification.json',{'groups':preservation_actual,'whole_checkout_files':len(before),'whole_checkout_tree_sha256':sha(canon(before)),'untracked':{x:before[x] for x in untracked},'baseline_sha256':sha((candidate_dir/'PRESERVATION_BEFORE.json').read_bytes())})
    save('raw/independent_pilot_tree.json',trees[0])
    DETAIL['pilots'] = {'fresh_complete_runs':2,'observations_each':80,'files_each':327,'byte_determinism':True,'supplied_pilots_match':True,'tree_sha256':sha(canon(trees[0]))}
    DETAIL['bindings'] = {'candidate_sha256':sha(candidate_path.read_bytes()),'implementation':implementation,'HEAD':git('rev-parse','HEAD').decode().strip(),'protected_pins':99,'producer_assertions_reported':producer['assertions'],'producer_count_is_not_authority':True}
    DETAIL['preservation'] = {'groups':preservation_actual,'whole_checkout_files':len(before),'all_bytes_unchanged':True,'untracked':7}

def finish(phase, verdict, error=None):
    save(phase + '_assertions.json', ROWS)
    save(phase + '_result.json', {'verdict':verdict, 'assertions':len(ROWS), 'passed':sum(r['passed'] for r in ROWS),
                                'details':DETAIL, 'network_attempts':NETWORK_ATTEMPTS, 'error':error,
                                'provider_model_calls':0, 'activation':False, 'execution_authorized':False})
    if verdict == 'BLOCKED':
        failures = [r for r in ROWS if not r['passed']]
        report = '# Independent G-CAL1 Audit\n\nBLOCKED. Stopped at first finding; no repair or further product tests.\n\n' + json.dumps(failures, indent=2) + '\n\n' + str(error)
        with (OUT / 'AUDIT_REPORT.md').open('x', encoding='utf-8') as stream:
            stream.write(report)
        save('SHA256_MANIFEST.json', tree(OUT))

if __name__ == '__main__':
    phase = sys.argv[1]
    try:
        if phase == 'child':
            child_worker(*sys.argv[2:])
            sys.exit(0)
        elif phase == 'timeout':
            first_timeout()
        elif phase == 'full':
            full_review()
        elif phase == 'remaining':
            remaining_review()
        else:
            raise ValueError('unknown audit phase')
        finish(phase, 'PASS')
    except SystemExit:
        raise
    except BaseException as exc:
        finish(phase, 'BLOCKED', traceback.format_exc())
        sys.exit(2)
