import sys, os, json, hashlib, socket, shutil, copy, itertools, subprocess, traceback
from pathlib import Path
from collections import Counter

REPO = Path(r'C:\Users\marcu\Eidolon-g4adj')
OUT = Path(__file__).resolve().parent
assert OUT.is_relative_to(Path(os.environ['TEMP'])) and not OUT.is_relative_to(REPO)
sys.dont_write_bytecode = True
net_attempts = []
def tripwire(*args, **kwargs):
    net_attempts.append('socket_attempt')
    raise AssertionError('INDEPENDENT_AUDIT_NETWORK_FORBIDDEN')
socket.socket = socket.create_connection = socket.getaddrinfo = tripwire
sys.path.insert(0, str(REPO / 'tools'))
from g_extract1_contract import Package, IntegrityError
from g_extract1_runner import Run
from g_extract1_journal import Journal, SCHEMA
from g_extract1_scoring import primary_verdict, evaluate

def enc(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
def sha(b):
    return hashlib.sha256(b).hexdigest()
def fh(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()
def read(p):
    return json.loads(Path(p).read_bytes())
def save(p, x):
    p = Path(p)
    assert p.is_relative_to(OUT)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(enc(x))
def git(*args):
    r = subprocess.run(['git', '-c', 'safe.directory=' + REPO.as_posix(), *args], cwd=REPO, capture_output=True)
    assert r.returncode == 0, r.stderr
    return r.stdout
continuing = '--continue-lr2' in sys.argv
rows = [json.loads(x) for x in (OUT/'assertions.jsonl').read_bytes().splitlines()] if continuing else []
cases = [json.loads(x) for x in (OUT/'cases.jsonl').read_bytes().splitlines()] if continuing else []
summary = {}
def check(group, name, condition, detail=None):
    if not condition:
        raise AssertionError(group + ':' + name + ':' + str(detail))
    row = dict(group=group, assertion=name, result='PASS')
    rows.append(row)
    with (OUT/'assertions.jsonl').open('ab') as f:
        f.write(enc(row) + b'\n')
def case(group, name, **details):
    row = dict(group=group, case=name, **details)
    cases.append(row)
    with (OUT/'cases.jsonl').open('ab') as f:
        f.write(enc(row) + b'\n')
def reject(group, name, event, fn):
    try:
        fn()
    except IntegrityError as e:
        check(group, name, e.event == event, dict(expected=event, actual=e.event, detail=e.detail))
        return e
    except Exception as e:
        raise AssertionError(group + ':' + name + ':RAW_ESCAPE:' + type(e).__name__) from e
    raise AssertionError(group + ':' + name + ':ATTACK_ACCEPTED')

class Probe:
    synthetic_only = True
    def __init__(self, result=None, raises=False):
        self.result, self.raises, self.calls = result, raises, 0
    def __call__(self, wire, row):
        self.calls += 1
        if self.raises:
            raise RuntimeError('independent_synthetic_exception')
        if self.result:
            return self.result(row)
        return dict(raw_output=gold_text(p.variants[row['rendered_variant_id']]), provider_truncated=False,
                    receipt=dict(call_id=row['call_id'], request_sha256=sha(wire), synthetic_only=True))

def gold_text(member):
    parts = []
    for k, schema in sorted(member['request']['input']['schema'].items()):
        value = member['gold'][k]
        token = str(value) if schema in ('integer', 'number') else json.dumps(value, ensure_ascii=False)
        parts.append(json.dumps(k) + ':' + token)
    return '{' + ','.join(parts) + '}'
def fresh(label, package=None):
    return Run(package or p, OUT/label, label)
def clone(seed, label):
    dest = OUT/label
    shutil.copytree(seed.directory, dest)
    return Run(p, dest, seed.run_id, resume=True)
def restart(run):
    return Run(p, run.directory, run.run_id, resume=True)
def terminal(group, name, run, event, row_index=1):
    q = Probe()
    reject(group, name + ':catch_next', event, lambda:run.perform(run.a[row_index], q, p.receipts()))
    recovered = restart(run)
    reject(group, name + ':disk_next', event, lambda:recovered.perform(recovered.a[row_index], q, p.receipts()))
    check(group, name + ':zero_later_transport', q.calls == 0)
    retained = any(x['payload']['event'] == event for x in Journal(run.directory/'integrity').read())
    retained |= any(x['payload'].get('type') == 'FAILURE' and x['payload'].get('event') == event for x in run.journal.read())
    check(group, name + ':durable_incident_or_failure', retained)
    check(group, name + ':INVALID', primary_verdict(p.design, dict(events=recovered.events)) == 'INVALID')

def reseal(folder, payloads):
    directory = folder/'journal'
    assert directory.is_relative_to(OUT)
    directory.mkdir(exist_ok=True)
    for x in directory.glob('*.json'):
        x.unlink()
    previous = '0'*64
    for i, payload in enumerate(payloads, 1):
        record = dict(sequence=i, previous_sha256=previous, payload=payload)
        record['sha256'] = sha(enc(record))
        save(directory/f'{i:06d}.json', record)
        previous = record['sha256']

before = {}
status_before = git('status', '--porcelain=v1', '--untracked-files=all').decode()
try:
    check('binding', 'HEAD', git('rev-parse', 'HEAD').decode().strip() == '2a3bda951e7ae48802834712c38c9d6be1e27169')
    check('binding', 'branch', git('branch', '--show-current').decode().strip() == 'g-extract1/design')
    candidate_path = REPO/'experiments/G-EXTRACT1-candidate/preexecution/final_lifecycle_repair/EXECUTION_FREEZE_CANDIDATE.json'
    candidate = read(candidate_path)
    check('binding', 'candidate_hash', fh(candidate_path) == '687a9a50d9bbbe480f3e74e103f5b75c621a46a9ffdcc8e80dab65f6b2915a35')
    p = Package()
    monitored = set(p.pins) | set(candidate['source_sha256'])
    monitored |= {x.relative_to(REPO).as_posix() for x in (p.data/'corpus').glob('*.json')}
    monitored |= {candidate_path.relative_to(REPO).as_posix(),
        'experiments/G-EXTRACT1-candidate/preexecution/EXECUTION_FREEZE_CANDIDATE.json',
        'experiments/G-EXTRACT1-candidate/preexecution/lifecycle_repair/EXECUTION_FREEZE_CANDIDATE.json'}
    current = {n:fh(REPO/n) for n in sorted(monitored)}
    before = read(OUT/'before_hashes.json') if continuing else current
    check('preservation','initial_snapshot_retained',before == current)
    if not continuing:
        save(OUT/'before_hashes.json', before)
        save(OUT/'status_before.json', status_before)
        seed = fresh('seed')
        seed.perform(seed.a[0], Probe(), p.receipts())
        cp = seed.checkpoint('original')
    else:
        seed = Run(p,OUT/'seed','seed',resume=True)
        cp = read(seed.directory/'CHECKPOINT_original.json')
        save(OUT/'PROBE_CORRECTION.json',dict(reason='LR2 failure event is retained in main journal, not required in integrity sidecar',
            repository_unchanged=True,continued_same_audit=True,LR1_not_reexecuted=True))

    malformed = [('list', []), ('null', None), ('zero', 0), ('one', 1), ('string', 'x'),
                 ('true', True), ('false', False), ('empty_object', {})]
    for key in cp['payload']:
        v = copy.deepcopy(cp['payload']); del v[key]
        malformed.append(('missing_' + key, v))
    for key, wrong in [('schema_version', []), ('run_id', 1), ('frozen_binding', None),
                       ('schedule_sha256', False), ('journal_prefix', []), ('next_schedule_position', '2'),
                       ('next_schedule_position', True), ('state', []), ('state', None)]:
        v = copy.deepcopy(cp['payload']); v[key] = wrong
        malformed.append(('type_' + key + '_' + type(wrong).__name__, v))
    nested = [('journal_prefix', 'record_count', True), ('journal_prefix', 'last_sha256', 1),
              ('state', 'qualified', [0]), ('state', 'integrity_events', [None]),
              ('state', 'event_scopes', [None]), ('state', 'event_scopes', [{}]),
              ('state', 'event_scopes', [dict(event='CORRUPTED_CHECKPOINT', phase=1, cell=None)]),
              ('state', 'cell_states', []), ('state', 'reports', []), ('state', 'b_entered', 1)]
    for i, (parent, key, wrong) in enumerate(nested):
        v = copy.deepcopy(cp['payload']); v[parent][key] = wrong
        malformed.append((f'nested_{i}_{key}', v))
    for label, value in malformed:
        if continuing:
            break
        run = clone(seed, 'LR1_' + label)
        attack = run.directory/'ATTACK.json'
        save(attack, dict(payload=value, sha256=sha(enc(value))))
        reject('LR1', label + ':malformed', 'CORRUPTED_CHECKPOINT', lambda:run.resume(attack))
        reject('LR1', label + ':original_after_catch', 'CORRUPTED_CHECKPOINT', lambda:run.resume(run.directory/'CHECKPOINT_original.json'))
        terminal('LR1', label, run, 'CORRUPTED_CHECKPOINT')
        recovered = restart(run)
        reject('LR1', label + ':original_after_disk', 'CORRUPTED_CHECKPOINT', lambda:recovered.resume(recovered.directory/'CHECKPOINT_original.json'))
        check('LR1', label + ':authority_lock_retained', not recovered._checkpoint_verified)
        case('LR1', label, event='CORRUPTED_CHECKPOINT', verdict='INVALID', later_transport_calls=0, path=str(attack))
    envelopes = [('envelope_list', []), ('envelope_null', None), ('envelope_scalar', 1),
                 ('envelope_missing', {'sha256': '0'*64}), ('envelope_extra', dict(cp, extra=1)),
                 ('envelope_wrongseal', dict(cp, sha256=1))]
    for label, value in envelopes:
        if continuing:
            break
        run = clone(seed, 'LR1_' + label)
        attack = run.directory/'ATTACK.json'; save(attack, value)
        reject('LR1', label, 'CORRUPTED_CHECKPOINT', lambda:run.resume(attack))
        terminal('LR1', label, run, 'CORRUPTED_CHECKPOINT')
        case('LR1', label, event='CORRUPTED_CHECKPOINT', later_transport_calls=0)
    summary['LR1'] = dict(sealed_payload_cases=len(malformed), envelope_cases=len(envelopes))
    print('LR1 PASS ' + str(summary['LR1']), flush=True)

    bad = [('none', None), ('list', []), ('empty_string', ''), ('zero', 0), ('false', False),
           ('object', object()), ('empty_dict', {}), ('failure_null', {'failure': None, 'receipt': None}),
           ('raw_null', {'raw_output': None, 'provider_truncated': False, 'receipt': {}}),
           ('missing_truncated', {'raw_output':'{}', 'receipt':{}}),
           ('missing_raw', {'provider_truncated':False, 'receipt':{}}),
           ('missing_receipt', {'raw_output':'{}', 'provider_truncated':False}),
           ('raw_number', {'raw_output':3, 'provider_truncated':False, 'receipt':{}}),
           ('truncated_number', {'raw_output':'{}', 'provider_truncated':0, 'receipt':{}}),
           ('receipt_list', {'raw_output':'{}', 'provider_truncated':False, 'receipt':[]}),
           ('receipt_null', {'raw_output':'{}', 'provider_truncated':False, 'receipt':None}),
           ('receipt_object', {'raw_output':'{}', 'provider_truncated':False, 'receipt':object()}),
           ('failure_number', {'failure':1, 'receipt':None}), ('failure_empty', {'failure':'', 'receipt':None}),
           ('failure_unknown', {'failure':'bogus', 'receipt':None}),
           ('failure_receipt_number', {'failure':'timeout', 'receipt':1}),
           ('failure_missing_receipt', {'failure':'timeout'}), ('nonstring_key', {1:2}),
           ('exception', None)]
    def success(r):
        return dict(raw_output=gold_text(p.variants[r['rendered_variant_id']]), provider_truncated=False,
                    receipt=dict(call_id=r['call_id'], request_sha256=r['request_sha256'], synthetic_only=True))
    factories = [
        ('wrong_call', lambda r:dict(success(r), receipt=dict(call_id='wrong', request_sha256=r['request_sha256']))),
        ('wrong_hash', lambda r:dict(success(r), receipt=dict(call_id=r['call_id'], request_sha256='0'*64))),
        ('call_type', lambda r:dict(success(r), receipt=dict(call_id=[], request_sha256=r['request_sha256']))),
        ('hash_type', lambda r:dict(success(r), receipt=dict(call_id=r['call_id'], request_sha256=1))),
        ('unserializable_receipt', lambda r:dict(success(r), receipt=dict(call_id=r['call_id'], request_sha256=r['request_sha256'], extra=object()))),
        ('wrong_failure_kind', lambda r:dict(failure='timeout', receipt=dict(call_id=r['call_id'],request_sha256=r['request_sha256'],failure_kind='error'))),
        ('wrong_failure_binding', lambda r:dict(failure='timeout', receipt=dict(call_id='wrong',request_sha256=r['request_sha256'],failure_kind='timeout'))),
        ('hybrid', lambda r:dict(success(r), failure='timeout')),
        ('surrogate_raw', lambda r:dict(success(r), raw_output='\ud800')),
    ]
    outcomes = [(name, lambda r,v=v:v, name == 'exception') for name,v in bad]
    outcomes += [(name,fn,False) for name,fn in factories]
    for name, fn, raises in outcomes:
        label = 'LR2_' + name
        if (OUT/label).exists():
            label += '_probe_corrected'
        run = fresh(label)
        q = Probe(fn, raises)
        run.perform(run.a[0], q, p.receipts())
        journal = run.journal.read()
        check('LR2', name + ':START_FAILURE', [x['payload']['type'] for x in journal] == ['START','FAILURE'])
        check('LR2', name + ':event', journal[-1]['payload']['event'] == 'PROVIDER_FAILURE_WITHOUT_RECEIPT')
        check('LR2', name + ':INVALID', run.final_report()['synthetic_primary_verdict'] == 'INVALID')
        terminal('LR2', name, run, 'PROVIDER_FAILURE_WITHOUT_RECEIPT')
        recovered = restart(run)
        check('LR2', name + ':closed_replay', len(recovered.attempted) == 1 and not recovered.evidence and
              set(recovered.events) == {'PROVIDER_FAILURE_WITHOUT_RECEIPT'})
        check('LR2', name + ':one_initial_call', q.calls == 1)
        case('LR2', name, event='PROVIDER_FAILURE_WITHOUT_RECEIPT', later_transport_calls=0, start_closed=True)
    for kind in ('success', 'timeout', 'error', 'missing', 'unreceipted'):
        run = fresh('LR2_valid_' + kind)
        expected = dict(timeout='PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', error='PROVIDER_ERROR_WITH_FAILURE_RECEIPT',
                        missing='MISSING_RESPONSE_WITH_FAILURE_RECEIPT', unreceipted='PROVIDER_FAILURE_WITHOUT_RECEIPT').get(kind)
        def result(r, k=kind):
            if k == 'success':
                return success(r)
            receipt = None if k == 'unreceipted' else dict(call_id=r['call_id'], request_sha256=r['request_sha256'], failure_kind=k, synthetic_only=True)
            return dict(failure=k, receipt=receipt)
        run.perform(run.a[0], Probe(result), p.receipts())
        recovered = restart(run)
        check('LR2', kind + ':valid_replay', recovered.events == ([] if expected is None else [expected]) and len(recovered.evidence) == int(kind == 'success'))
        if expected:
            q = Probe()
            reject('LR2', kind + ':terminal_restart', expected, lambda:recovered.perform(recovered.a[1],q,p.receipts()))
            check('LR2', kind + ':zero_later', q.calls == 0)
        case('LR2_regression', kind, event=expected)
    summary['LR2'] = dict(malformed_cases=len(outcomes), valid_regressions=5)
    print('LR2 PASS ' + str(summary['LR2']), flush=True)

    # Paired control-flow exception probe, explicitly requested within this audit.
    exception_evidence = []
    for exception_type in (KeyboardInterrupt, SystemExit):
        name = exception_type.__name__
        run = fresh('LR2_control_' + name)
        def raise_control(r, cls=exception_type):
            raise cls('independent_transport_control_exception')
        first = Probe(raise_control)
        escaped = None
        try:
            run.perform(run.a[0],first,p.receipts())
        except BaseException as e:
            escaped = type(e).__name__
        initial_report = run.final_report()
        initial_payloads = [x['payload'] for x in run.journal.read()]
        save(run.directory/'AFTER_EXTERNAL_CATCH.json',dict(escaped=escaped,report=initial_report,journal=initial_payloads))
        before_next_folder = OUT/('LR2_control_' + name + '_before_next_reconstruction')
        shutil.copytree(run.directory,before_next_folder)
        restart_event = None
        try:
            Run(p,before_next_folder,run.run_id,resume=True)
        except IntegrityError as e:
            restart_event = e.event
        next_probe = Probe()
        next_error = None
        try:
            run.perform(run.a[1],next_probe,p.receipts())
        except BaseException as e:
            next_error = type(e).__name__ + ':' + str(e)
        next_report = run.final_report()
        after_restart_event = None
        try:
            Run(p,run.directory,run.run_id,resume=True)
        except IntegrityError as e:
            after_restart_event = e.event
        evidence = dict(exception=name,escaped=escaped,initial_transport_calls=first.calls,
            initial_events=initial_report['state']['integrity_events'],
            initial_verdict=initial_report['synthetic_primary_verdict'],
            initial_journal_types=[x['type'] for x in initial_payloads],
            externally_caught_next_transport_calls=next_probe.calls,next_error=next_error,
            post_next_journal_types=[x['payload']['type'] for x in run.journal.read()],
            post_next_report_events=next_report['state']['integrity_events'],
            post_next_verdict=next_report['synthetic_primary_verdict'],
            restart_before_next_event=restart_event,restart_after_next_event=after_restart_event,
            run_path=str(run.directory),before_next_reconstruction_path=str(before_next_folder))
        save(run.directory/'CONTROL_EXCEPTION_EVIDENCE.json',evidence)
        exception_evidence.append(evidence)
        case('LR2_control_exception',name,**{k:v for k,v in evidence.items() if k!='exception'})
        print('CONTROL_EXCEPTION '+json.dumps(evidence),flush=True)
    summary['LR2_control_exceptions']=exception_evidence
    if any(x['externally_caught_next_transport_calls'] > 0 for x in exception_evidence):
        raise AssertionError('P2: transport BaseException leaves open START and permits transport after external catch; reconstruction detects INVALID only later')

    catalog = p.design['integrity_event_contract']['precontact_blocking_events']
    receipt_keys = {'PRE_MODEL_IDENTITY_MISMATCH':'models', 'PRE_PROVIDER_VERSION_MISMATCH':'provider_version',
                    'PRE_GENERATION_CONFIG_MISMATCH':'generation_configuration'}
    for event in catalog:
        run = fresh('LR3_' + event)
        receipts = copy.deepcopy(p.receipts())
        if event in receipt_keys:
            receipts[receipt_keys[event]] = None
        else:
            isolated = copy.copy(p)
            def blocked(*a, _event=event, **kw):
                raise IntegrityError(_event, 'independent frozen catalog synthesis')
            isolated.verify = blocked
            run.package = isolated
        q = Probe()
        reject('LR3', event + ':perform', event, lambda:run.perform(run.a[0],q,receipts))
        run.package = p
        report = run.final_report(); state = report['state']
        check('LR3', event + ':six_blocked', len(state['cell_states']) == 6 and set(state['cell_states'].values()) == {'A_BLOCKED'})
        check('LR3', event + ':no_B', state['qualified'] == [] and not state['b_entered'] and run.b == [])
        check('LR3', event + ':verdict', report['synthetic_primary_verdict'] == 'PRE_CONTACT_BLOCKED')
        recovered = restart(run)
        check('LR3', event + ':disk_state', set(recovered.state()['cell_states'].values()) == {'A_BLOCKED'})
        reject('LR3', event + ':disk_perform', event, lambda:recovered.perform(recovered.a[0],q,p.receipts()))
        reject('LR3', event + ':disk_enter_b', event, recovered.enter_b)
        check('LR3', event + ':zero_transport', q.calls == 0 and not recovered.attempted)
        case('LR3', event, actual_receipt_mutation=event in receipt_keys, later_transport_calls=0)
    run = fresh('LR3_provider_name')
    receipts = copy.deepcopy(p.receipts()); receipts['provider'] = 'changed'
    q = Probe()
    reject('LR3','actual_provider_name','PRE_PROVIDER_VERSION_MISMATCH',lambda:run.perform(run.a[0],q,receipts))
    check('LR3','provider_name_state', set(run.state()['cell_states'].values()) == {'A_BLOCKED'} and q.calls == 0)
    case('LR3','provider_name_extra', actual_receipt_mutation=True)
    for kind, expected in [('timeout','INCOMPLETE'), ('unreceipted','INVALID')]:
        run = fresh('LR3_post_' + kind)
        def failure(r, k=kind):
            receipt = None if k == 'unreceipted' else dict(call_id=r['call_id'],request_sha256=r['request_sha256'],failure_kind=k)
            return dict(failure=k,receipt=receipt)
        run.perform(run.a[0], Probe(failure), p.receipts())
        report = run.final_report()
        check('LR3',kind + ':postcontact_not_blocked', report['synthetic_primary_verdict'] == expected and 'A_BLOCKED' not in report['state']['cell_states'].values())
        case('LR3_postcontact',kind, verdict=expected)
    summary['LR3'] = dict(catalog_cases=len(catalog), actual_receipt_cases=4, synthetic_catalog_cases=len(catalog)-3, postcontact_cases=2)
    print('LR3 PASS ' + str(summary['LR3']), flush=True)

    for operation in ('perform','enter_b','checkpoint','final_report'):
        run = clone(seed, 'I1_' + operation)
        q = Probe()
        methods = dict(perform=lambda:run.perform(run.a[1],q,p.receipts()),enter_b=run.enter_b,
                       checkpoint=lambda:run.checkpoint('bypass'),final_report=run.final_report)
        reject('I1', operation + ':unverified', 'PROVENANCE_MISMATCH', methods[operation])
        reject('I1', operation + ':resume_after_catch', 'PROVENANCE_MISMATCH', lambda:run.resume(run.directory/'CHECKPOINT_original.json'))
        recovered = restart(run)
        reject('I1', operation + ':resume_after_disk', 'PROVENANCE_MISMATCH', lambda:recovered.resume(recovered.directory/'CHECKPOINT_original.json'))
        check('I1', operation + ':zero_transport', q.calls == 0)
        case('I1',operation, retained_after_disk=True)
    for name, event in [('skip','SCHEDULE_POSITION_MISMATCH'),('retry','UNAUTHORIZED_RETRY'),('duplicate_copy','UNAUTHORIZED_RETRY'),
                        ('prompt','UNAUTHORIZED_PROMPT_MUTATION'),('manifest','PROTECTED_ARTIFACT_DIGEST_MISMATCH')]:
        run = fresh('I2_' + name); run.perform(run.a[0],Probe(),p.receipts())
        row = copy.deepcopy(run.a[2 if name == 'skip' else 0 if name in ('retry','duplicate_copy') else 1])
        if name == 'prompt':
            altered = copy.copy(p); altered.wire = lambda r:p.wire(r) + b' '
            run.package = altered
        elif name == 'manifest':
            altered = copy.copy(p); altered.root = OUT/'I2_manifest_bytes'; altered.pins = dict(p.pins)
            relative = 'experiments/G-EXTRACT1-candidate/corpus/CORPUS_MANIFEST.json'
            for n in p.pins:
                dest = altered.root/n; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(REPO/n,dest)
            target = altered.root/relative; b = target.read_bytes(); target.write_bytes(bytes([b[0]^1])+b[1:])
            run.package = altered
        q = Probe()
        reject('I2',name + ':attack',event,lambda:run.perform(row,q,p.receipts()))
        run.package = p
        terminal('I2',name,run,event)
        check('I2',name + ':zero_initial_attack_transport',q.calls == 0)
        case('I2',name,event=event)

    for name, fn, event in [
        ('prefix',lambda x:x['journal_prefix'].update(last_sha256='a'*64),'UNVERIFIABLE_JOURNAL_PREFIX'),
        ('position',lambda x:x.update(next_schedule_position=3),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT'),
        ('schedule',lambda x:x.update(schedule_sha256='a'*64),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT'),
        ('binding',lambda x:x['frozen_binding'].update(package_commit='a'*40),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT'),
        ('state',lambda x:x['state'].update(current_phase='B'),'UNVERIFIABLE_INTERRUPTION_CHECKPOINT')]:
        run = clone(seed,'I4_cp_' + name); value=copy.deepcopy(cp['payload']);fn(value)
        path = run.directory/'ATTACK.json';save(path,dict(payload=value,sha256=sha(enc(value))))
        reject('I4',name,event,lambda:run.resume(path));terminal('I4',name,run,event)
        case('I4','checkpoint_' + name,event=event)
    fail = fresh('I4_failure_seed')
    def timeout(r):
        return dict(failure='timeout',receipt=dict(call_id=r['call_id'],request_sha256=r['request_sha256'],failure_kind='timeout'))
    fail.perform(fail.a[0],Probe(timeout),p.receipts())
    mutations = [('receipt_none',lambda x:x.update(receipt=None)),
                 ('call_binding',lambda x:x['receipt'].update(call_id='wrong')),
                 ('request_binding',lambda x:x['receipt'].update(request_sha256='a'*64)),
                 ('kind',lambda x:x['receipt'].update(failure_kind='error')),
                 ('event',lambda x:x.update(event='PROVIDER_ERROR_WITH_FAILURE_RECEIPT')),
                 ('completion_state',lambda x:x.update(completion_state='INVALID'))]
    for name, fn in mutations:
        folder=OUT/('I4_receipt_' + name);shutil.copytree(fail.directory,folder)
        payloads=[copy.deepcopy(x['payload']) for x in fail.journal.read()];fn(payloads[-1]);reseal(folder,payloads)
        reject('I4',name,'PROVENANCE_MISMATCH',lambda:Run(p,folder,fail.run_id,resume=True))
        case('I4','receipt_' + name,event='PROVENANCE_MISMATCH')
    for name in ('initial_lineage','post_checkpoint_lineage','missing_marker','fabricated_marker'):
        folder=OUT/('I4_' + name);shutil.copytree(seed.directory,folder)
        payloads=[copy.deepcopy(x['payload']) for x in seed.journal.read()]
        if name == 'initial_lineage':
            payloads[0]['checkpoint_lineage']='a'*64
        elif name == 'post_checkpoint_lineage':
            r=Run(p,folder,seed.run_id,resume=True);r.resume(folder/'CHECKPOINT_original.json');r.perform(r.a[1],Probe(),p.receipts())
            payloads=[copy.deepcopy(x['payload']) for x in r.journal.read()]
            next(x for x in reversed(payloads) if x['type']=='START')['checkpoint_lineage']='a'*64
        elif name == 'missing_marker':
            payloads.pop()
        else:
            payloads[-1]['checkpoint_sha256']='a'*64
        reseal(folder,payloads)
        if name == 'missing_marker':
            r=Run(p,folder,seed.run_id,resume=True)
            reject('I4',name,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT',lambda:r.resume(folder/'CHECKPOINT_original.json'))
        else:
            reject('I4',name,'UNVERIFIABLE_INTERRUPTION_CHECKPOINT',lambda:Run(p,folder,seed.run_id,resume=True))
        case('I4',name,event='UNVERIFIABLE_INTERRUPTION_CHECKPOINT')
    print('I1/I2/I4 PASS',flush=True)

    # All protected originals are verified independently, then integrated file-byte attacks use a complete isolated copy.
    check('I6','fifty_files',len(p.pins)==50)
    for n,h in p.pins.items():
        check('I6','actual_file:' + n,fh(REPO/n)==h)
    authoring=read(p.data/'corpus/AUTHORING_CANDIDATES.json')
    projection=[[x['logical_base_id'],x['fixture']['gold_values']] for x in authoring['accepted']]
    projection_sha=sha(json.dumps(projection,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode())
    check('I6','separate_gold_projection',projection_sha==p.manifest['gold_projection_sha256']=='803e8e4c57b63c7edb22f02194cbefdbf6be3fc964a0d77f65faa658f8904aec')
    isolated=copy.copy(p);isolated.root=OUT/'I6_full_protected_copy';isolated.data=isolated.root/'experiments/G-EXTRACT1-candidate'
    isolated.manifest_path=isolated.data/'corpus/CORPUS_MANIFEST.json'
    for n in p.pins:
        dest=isolated.root/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REPO/n,dest)
    for filename in ('AUTHORING_CANDIDATES.json','validate_corpus.py','independent_contamination.py','validate_finalization.py'):
        relative=next(n for n in p.pins if n.endswith('/'+filename));path=isolated.root/relative
        for contacted in (False,True):
            label=filename+('_post' if contacted else '_pre');run=fresh('I6_'+label,isolated)
            if contacted:
                run.perform(run.a[0],Probe(),p.receipts())
            with path.open('r+b') as f:
                b=f.read(1);f.seek(0);f.write(bytes([b[0]^1]))
            event='PROTECTED_ARTIFACT_DIGEST_MISMATCH' if contacted else 'PRE_ARTIFACT_DIGEST_MISMATCH'
            q=Probe();row=run.a[int(contacted)]
            reject('I6',label+':perform',event,lambda:run.perform(row,q,p.receipts()))
            with path.open('r+b') as f:
                f.write(b)
            reject('I6',label+':restored_catch',event,lambda:run.perform(row,q,p.receipts()))
            recovered=Run(isolated,run.directory,run.run_id,resume=True)
            reject('I6',label+':restored_disk',event,lambda:recovered.perform(row,q,p.receipts()))
            check('I6',label+':zero_transport',q.calls==0)
            category='INVALID' if contacted else 'PRE_CONTACT_BLOCKED'
            check('I6',label+':terminal_verdict',primary_verdict(p.design,dict(events=recovered.events,provider_generation_calls=0))==category)
            check('I6',label+':original_intact',fh(REPO/relative)==p.pins[relative])
            case('I6',label,path=relative,event=event,full_pin_copy=True)
    summary['I6']=dict(protected_actual_files=50,integrated_byte_mutations=8,gold_projection_sha256=projection_sha)
    print('I6 PASS',flush=True)
    save(OUT/'stage1_summary.json',summary)
except BaseException as e:
    summary['blocked']=dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc())
    print('BLOCKED '+str(e),flush=True)
    save(OUT/'BLOCKED.json',summary)
    raise
finally:
    after={n:fh(REPO/n) for n in before}
    save(OUT/'after_stage1_hashes.json',after)
    save(OUT/'stage1_counts.json',dict(assertions=Counter(x['group'] for x in rows),cases=Counter(x['group'] for x in cases),network_attempts=net_attempts))
    assert before==after,'AUDIT_PRESERVATION_CHANGED'
    assert status_before==git('status','--porcelain=v1','--untracked-files=all').decode(),'AUDIT_STATUS_CHANGED'
    assert not net_attempts,'AUDIT_NETWORK_ATTEMPT'
