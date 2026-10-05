"""Synthetic real-path lock-timeout tests; includes the default 120-second case."""
from __future__ import annotations

import copy
from contextlib import contextmanager, nullcontext
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import g_cal1_lab as lab
import g_cal1_lock as locks
from g_cal1_contract import Package
from g_cal1_lab import Run
from g_cal1_pilot import synthetic, success
from g_cal1_repair_tests import deny_network
from g_extract1_contract import IntegrityError, canonical, digest, load
from g_extract1_journal import write_once
from g_extract1_scoring import event_category


def sealed_records(run):
    return [load(p) for p in sorted((run.directory/'lock_boundary_incidents').glob('*.json'))]


def timeout_tests(package,checks,root,*,actual):
    root.mkdir(parents=True,exist_ok=False)
    for operation in ('perform','checkpoint','verify_resume','final_report'):
        directory = root/operation
        a = Run(package,directory,'G-CAL1-SYNTHETIC-TIMEOUT-'+operation)
        cp = a.checkpoint()
        b = Run(package,directory,a.run_id,resume=True); b.verify_resume(cp)
        c = Run(package,directory,a.run_id,resume=True); c.verify_resume(cp)
        baseline = a.journal.read()
        held,release,done = threading.Event(),threading.Event(),threading.Event()
        holder_errors = []
        class Cleanup(BaseException): pass
        original_ready = a._ready
        def paused_ready():
            original_ready()
            held.set()
            if not release.wait(180):
                raise Cleanup('holder watchdog')
            raise Cleanup('pre-START holder cleanup')
        def holder():
            try:
                with patch.object(a,'_ready',paused_ready):
                    a.checkpoint()
            except Cleanup:
                pass
            except BaseException as exc:
                holder_errors.append(type(exc).__name__+':'+str(exc))
            finally:
                done.set()
        thread = threading.Thread(target=holder,name='governed-lock-holder')
        thread.start()
        checks.check(held.wait(15),'LOCK_TIMEOUT','A holds actual governed lock '+operation)
        calls = []
        @synthetic
        def transport(request,row):
            calls.append(row['call_id'])
            return success(package,request,row)
        row = copy.deepcopy(package.schedule[0])
        actions = {'perform':lambda:b.perform(row,transport),'checkpoint':b.checkpoint,
                   'verify_resume':lambda:b.verify_resume(cp),'final_report':b.final_report}
        captured,reads = [],[]
        original_lock = lab.run_lock
        @contextmanager
        def observed_lock(path):
            try:
                with original_lock(path):
                    yield
            except IntegrityError as exc:
                captured.append(exc)
                raise
        original_clock = locks.time.monotonic
        owner = threading.get_ident()
        def deadline_clock():
            if threading.get_ident()!=owner:
                return original_clock()
            reads.append(len(reads))
            return 0.0 if len(reads)==1 else 121.0
        default = actual and operation=='perform'
        clock = nullcontext() if default else patch.object(locks.time,'monotonic',deadline_clock)
        caught = None
        results = {}
        started = time.perf_counter()
        try:
            with patch.object(lab,'run_lock',observed_lock),clock:
                try:
                    actions[operation]()
                except IntegrityError as exc:
                    caught = exc
            elapsed = time.perf_counter()-started
            checks.check(caught is not None and caught.event=='PROVENANCE_MISMATCH' and
                         caught.detail=='run operation lock unavailable','LOCK_TIMEOUT','real lock exception '+operation)
            checks.check(len(captured)==1 and caught is captured[0] and caught.args==captured[0].args,
                         'LOCK_TIMEOUT','original object/type/args propagated '+operation)
            checks.check(not done.is_set(),'LOCK_TIMEOUT','incident persisted while A still holds lock '+operation)
            records = sealed_records(b)
            checks.check(len(records)==1,'LOCK_TIMEOUT','one durable independent incident '+operation)
            payload = records[0]['payload']
            cell = row['cell_id'] if operation=='perform' else None
            checks.check(payload=={'event':'PROVENANCE_MISMATCH','detail':caught.detail,'phase':'CAL','cell':cell,
                         'run_id':b.run_id,'binding':b.binding},'LOCK_TIMEOUT','exact bound phase/cell incident '+operation)
            checks.check(event_category(package.historical.design,payload['event'])=='INVALID' and
                         b.state()['verdict']=='INVALID','LOCK_TIMEOUT','same object terminal '+operation)
            checks.check(not calls and a.journal.read()==baseline,'LOCK_TIMEOUT','zero transport/START/journal mutation '+operation)
            if default:
                checks.check(elapsed>=119.9 and not reads,'LOCK_TIMEOUT_DEFAULT','unmodified 120-second timeout')
            else:
                checks.check(reads==[0,1],'LOCK_TIMEOUT','only monotonic deadline reads shortened '+operation)
            # These denials must complete even while A still holds the lock.
            before = time.perf_counter()
            for name,action in (
                ('B_same_object',lambda:b.perform(row,transport)),
                ('C_stale_object',lambda:c.perform(row,transport)),
                ('fresh_reconstruction',lambda:Run(package,directory,b.run_id,resume=True))):
                error = checks.reject(action,'LOCK_TIMEOUT','held-lock terminal '+name,'PROVENANCE_MISMATCH')
                results[name] = {'rejected':True,'event':error.event}
            checks.check(time.perf_counter()-before<5,'LOCK_TIMEOUT','retention/denial never waits for A '+operation)
            checks.check(not calls and len(sealed_records(b))==1,'LOCK_TIMEOUT','no new call or duplicate incident '+operation)
        finally:
            release.set();thread.join(15)
        checks.check(done.is_set() and not holder_errors,'LOCK_TIMEOUT','holder cleanup and unlock '+operation)
        for name,action in (
            ('B_after_release',lambda:b.perform(row,transport)),
            ('C_after_release',lambda:c.perform(row,transport)),
            ('restart_after_release',lambda:Run(package,directory,b.run_id,resume=True))):
            error = checks.reject(action,'LOCK_TIMEOUT','post-release terminal '+name,'PROVENANCE_MISMATCH')
            results[name] = {'rejected':True,'event':error.event}
        checks.check(not calls and a.journal.read()==baseline and len(sealed_records(b))==1,
                     'LOCK_TIMEOUT','no open/new START or fake receipt after release '+operation)
        report = {'operation':operation,'actual_contention':True,'default_timeout':default,'elapsed_seconds':elapsed,
            'event':caught.event,'category':'INVALID','original_exception_propagated':True,
            'incident_persisted':True,'record':records[0],'held_lock_retention':True,'transport_invocations':len(calls),
            'START_count':0,'open_START_count':0,'continuations':results,'state_B':b.state(),'state_C':c.state(),
            'provider_model_calls':0,'clock_injection':not default}
        write_once(directory/'TIMEOUT_REPORT.json',report)
        if default:
            write_once(root/'ACTUAL_TIMEOUT_REPORT.json',report)
    process_retention(package,checks,root/'process_retention')
    uncontended = Run(package,root/'uncontended','G-CAL1-SYNTHETIC-UNCONTENDED')
    uncontended.perform(package.schedule[0],synthetic(lambda request,row:success(package,request,row)))
    checks.check(len(uncontended.evidence)==1 and not uncontended.events and not sealed_records(uncontended),
                 'LOCK_TIMEOUT_NORMAL','clean synthetic call, no spurious incident')
    checks.check(not (uncontended.directory/'lock_boundary_incidents').exists(),
                 'LOCK_TIMEOUT_NORMAL','normal authority tree layout unchanged')


def process_retention(package,checks,directory):
    a = Run(package,directory,'G-CAL1-SYNTHETIC-PROCESS-TIMEOUT')
    cp = a.checkpoint()
    indices = []
    for index,row in enumerate(package.schedule):
        if row['cell_id'] not in [package.schedule[i]['cell_id'] for i in indices]:
            indices.append(index)
        if len(indices)==2:
            break
    children = []
    for index in indices:
        child = subprocess.Popen([sys.executable,'-B',__file__,'--child-timeout',str(directory),a.run_id,str(cp),str(index)],
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        children.append(child)
        checks.check(child.stdout.readline().strip()=='READY','LOCK_TIMEOUT_PROCESS','independent object verified before contention')
    held,release = threading.Event(),threading.Event()
    def holder():
        with locks.run_lock(directory):
            held.set();release.wait(30)
    thread = threading.Thread(target=holder)
    thread.start()
    checks.check(held.wait(10),'LOCK_TIMEOUT_PROCESS','same run OS lock held')
    try:
        for child in children:
            child.stdin.write('GO\n');child.stdin.flush()
        reports = []
        for child in children:
            output = child.stdout.readline()
            child.wait(timeout=15)
            checks.check(child.returncode==0,'LOCK_TIMEOUT_PROCESS','process retained incident:'+child.stderr.read())
            report = json.loads(output);reports.append(report)
            checks.check(report['event']=='PROVENANCE_MISMATCH' and report['transport_calls']==0 and
                         report['state']['verdict']=='INVALID','LOCK_TIMEOUT_PROCESS','child terminal before lock release')
        records = sealed_records(a)
        checks.check(len(records)==2 and {r['payload']['cell'] for r in records}=={package.schedule[i]['cell_id'] for i in indices},
                     'LOCK_TIMEOUT_PROCESS','two complete independent records, no collision/overwrite')
        checks.check(all(r['sha256']==digest(canonical(r['payload'])) for r in records),
                     'LOCK_TIMEOUT_PROCESS','sealed complete bytes from both processes')
    finally:
        release.set();thread.join(10)
        for child in children:
            if child.poll() is None:
                child.kill();child.wait()
    checks.reject(lambda:a.final_report(),'LOCK_TIMEOUT_PROCESS','stale parent terminal after unlock','PROVENANCE_MISMATCH')
    checks.check(not a.incidents.read() and all(r['payload']['kind']!='START' for r in a.journal.read()),
                 'LOCK_TIMEOUT_PROCESS','only independent incidents, no journal/receipt fabrication')
    write_once(directory/'PROCESS_REPORT.json',{'reports':reports,'incident_count':2,'provider_model_calls':0})


def child_timeout():
    package = Package()
    directory,run_id,cp,index = Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4]),int(sys.argv[5])
    run = Run(package,directory,run_id,resume=True);run.verify_resume(cp)
    print('READY',flush=True)
    if sys.stdin.readline().strip()!='GO':
        raise RuntimeError('missing contention barrier')
    calls = []
    @synthetic
    def transport(request,row):
        calls.append(1);return success(package,request,row)
    reads = []
    def clock():
        reads.append(1)
        return 0.0 if len(reads)==1 else 121.0
    with patch.object(locks.time,'monotonic',clock):
        try:
            run.perform(package.schedule[index],transport)
        except IntegrityError as exc:
            event = exc.event
        else:
            raise AssertionError('contention was not enforced')
    print(json.dumps({'event':event,'transport_calls':len(calls),'state':run.state()}),flush=True)


if __name__=='__main__':
    sys.addaudithook(deny_network)
    if sys.argv[1:2]==['--child-timeout']:
        child_timeout()
    else:
        raise SystemExit('Invoked only by offline producer certification')
