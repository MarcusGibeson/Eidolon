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
from pathlib import Path
from contextlib import contextmanager

REPO = Path('C:/Users/marcu/Eidolon-g4adj')
OUT = Path(__file__).resolve().parent
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
        if phase == 'timeout':
            first_timeout()
        elif phase == 'full':
            full_review()
        else:
            raise ValueError('unknown audit phase')
        finish(phase, 'PASS')
    except BaseException as exc:
        finish(phase, 'BLOCKED', traceback.format_exc())
        sys.exit(2)
