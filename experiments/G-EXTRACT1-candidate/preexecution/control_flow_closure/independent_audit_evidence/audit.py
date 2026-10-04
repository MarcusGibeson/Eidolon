import sys
import socket
import json
from pathlib import Path

ROOT = Path('C:/Users/marcu/Eidolon-g4adj')
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
network_attempts = []
def no_network(*args, **kwargs):
    network_attempts.append(repr(args))
    raise AssertionError('socket tripwire')
socket.socket = no_network
socket.create_connection = no_network
socket.getaddrinfo = no_network
from g_extract1_contract import Package, IntegrityError, canonical, digest
from g_extract1_runner import Run
from g_extract1_scoring import event_category

rows = []
def check(name, condition, **facts):
    record = dict(group='independent_control', name=name, passed=bool(condition), **facts)
    rows.append(record)
    (OUT / 'independent_raw.json').write_bytes(canonical(rows))
    if not condition:
        raise AssertionError(name)

class Counting:
    synthetic_only = True
    def __init__(self): self.calls = 0
    def __call__(self, wire, row):
        self.calls += 1
        raise AssertionError('continuation reached transport')

class Control(BaseException): pass

def signal_case(package, signal):
    label = type(signal).__name__
    directory = OUT / ('first_' + label)
    run = Run(package, directory, label)
    first, second = run.a[:2]
    class Raising:
        synthetic_only = True
        def __call__(self, wire, row):
            assert len(run.journal.read()) == 1
            assert run.journal.read()[0]['payload']['type'] == 'START'
            raise signal
    try:
        run.perform(first, Raising(), package.receipts())
    except BaseException as caught:
        # Inspection occurs immediately, before another run method is called.
        incidents = [json.loads(p.read_bytes()) for p in sorted((directory/'integrity').glob('*.json'))]
        events = list(run.events)
        scopes = list(run.event_scopes)
        journal = run.journal.read()
        check(label+':original', caught is signal and caught.args == signal.args, args=list(caught.args))
        check(label+':immediate_retention', events == ['SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT'] and
              scopes == [dict(event=events[0], phase='A', cell=first['cell_id'])] and
              len(incidents) == 1 and incidents[0]['payload']['event'] == events[0] and
              incidents[0]['payload']['phase'] == 'A' and incidents[0]['payload']['cell'] == first['cell_id'] and
              event_category(package.design, events[0]) == 'INVALID', events=events, scopes=scopes, persisted=incidents)
        check(label+':no_fabrication', len(journal) == 1 and journal[0]['payload']['type'] == 'START')
    else:
        check(label+':propagation', False)
    counter = Counting()
    try: run.perform(second, counter, package.receipts())
    except IntegrityError as exc: check(label+':postcatch_rejected', exc.event == events[0])
    else: check(label+':postcatch_rejected', False)
    check(label+':no_second_start', counter.calls == 0 and len(run.journal.read()) == 1)
    del run
    try: Run(package, directory, label, resume=True)
    except IntegrityError as exc: check(label+':restart_frozen', exc.event == events[0], event=exc.event)
    else: check(label+':restart_frozen', False)

def main():
    package = Package(ROOT)
    # First behavioral actions: the requested old blocker, through real perform.
    signal_case(package, KeyboardInterrupt('independent_keyboard', 7))
    signal_case(package, SystemExit('independent_system', 9))
    signal_case(package, GeneratorExit('independent_generator'))
    signal_case(package, Control('independent_custom', 11))
    check('socket_unused', not network_attempts)
    print('FIRST_BLOCKER_PASS', len(rows), flush=True)

def suite():
    import copy
    import shutil
    import subprocess
    import traceback
    from collections import Counter
    from g_extract1_contract import source_pins, load
    from g_extract1_journal import Journal, SCHEMA
    from g_extract1_pilot import (SyntheticTransport, schedule_tests, response_tests,
        gates_tests, integrity_tests, reserve_tests)
    from g_extract1_lifecycle_tests import lifecycle_tests
    from g_extract1_final_lifecycle_tests import final_lifecycle_tests, completed_state_regressions
    from g_extract1_control_flow_tests import control_flow_tests, control_flow_b_regressions
    evidence = ROOT / 'experiments/G-EXTRACT1-candidate/preexecution/control_flow_closure'
    records = []
    class AuditChecks:
        def check(self, group, name, condition):
            record = dict(group=group, test=name, result='PASS' if condition else 'FAIL')
            records.append(record)
            with (OUT/'suite_assertions.jsonl').open('ab') as f:
                f.write(canonical(record)+b'\n')
            if not condition: raise AssertionError(group+':'+name)
        def rejects(self, group, name, event, action):
            try: action()
            except IntegrityError as exc:
                self.check(group,name,exc.event == event)
                return
            self.check(group,name,False)
    t = AuditChecks()
    def git(*args):
        result = subprocess.run(['git','-c','safe.directory=C:/Users/marcu/Eidolon-g4adj',*args],cwd=ROOT,capture_output=True)
        if result.returncode: raise AssertionError(result.stderr.decode('utf8','replace'))
        return result.stdout
    def hashes(paths):
        return {str(p.relative_to(ROOT)).replace('\\','/'):digest(p.read_bytes()) for p in paths if p.is_file()}
    def tree(directory):
        return {p.relative_to(directory).as_posix():digest(p.read_bytes()) for p in directory.rglob('*') if p.is_file()}
    p = Package(ROOT)
    baseline_paths = set(ROOT/name for name in p.pins)
    baseline_paths.update((ROOT/'experiments/G-ROUTE4-candidate').rglob('*'))
    baseline_paths.update((p.data/'corpus').rglob('*'))
    # Preserve all prior/new evidence bytes, including blocked candidate trees.
    baseline_paths.update((p.data/'preexecution').rglob('*'))
    baseline = hashes(sorted(baseline_paths))
    status = git('status','--porcelain=v1','--branch')
    (OUT/'repository_before.json').write_bytes(canonical(dict(head=git('rev-parse','HEAD').decode().strip(),status=status.decode(),files=baseline)))
    summary = dict(independent_first=json.loads((OUT/'independent_raw.json').read_bytes()), helper_summaries={})
    try:
        t.check('bindings','current HEAD',git('rev-parse','HEAD').decode().strip() == '10cc8a978237fa6a403c1bfd72184845200b192e')
        t.check('bindings','branch',git('branch','--show-current').decode().strip() == 'g-extract1/design')
        candidate = load(evidence/'EXECUTION_FREEZE_CANDIDATE.json')
        t.check('bindings','candidate SHA',digest((evidence/'EXECUTION_FREEZE_CANDIDATE.json').read_bytes()) == '4819d754192df7c49055a825353b9387d2cf51efe9652ef9f64bda8736be62c1')
        t.check('bindings','all 50 protected files',len(p.pins) == 50 and all(digest((ROOT/name).read_bytes()) == sha for name,sha in p.pins.items()))
        t.check('bindings','candidate protected pins',candidate['complete_manifest_verification']['protected_files'] == p.pins and candidate['accepted_binding']['protected_artifacts'] == p.pins)
        sources = source_pins()
        summary['source_sha256'] = sources
        t.check('bindings','source map equals candidate',sources == candidate['source_sha256'] == candidate['accepted_binding']['implementation_sha256'])
        for name,sha in sources.items():
            t.check('bindings','working source equals implementation commit:'+name,digest(git('show','17af89c9c4f279d55d48aac46125c2844d3b4ad5:'+name)) == sha)
            t.check('bindings','working source equals current commit:'+name,digest(git('show','HEAD:'+name)) == sha)
        t.check('bindings','accepted package and science closure',candidate['accepted_science_closure_commit'] == '6c85b10930cefe410a1965c0924e4fd9f47eb4ef' and candidate['accepted_binding']['package_commit'] == '81dc9d05f49e9c1310bb38676bfd7cf6a8620cf7')
        t.check('bindings','science/checker/historical tracked unchanged since starting HEAD',not git('diff','--name-only','694742a7cc3723f2c562121d5fc666cc777992ca','HEAD','--',*[n for n in p.pins]))
        t.check('bindings','candidate unactivated',candidate['status'] == 'EXECUTION_FREEZE_CANDIDATE_ONLY' and not any(candidate[k] for k in ('activated','phase_a_authorized','phase_b_authorized','provider_model_calls')))
        old = ['14fb601c3a58777942ccd0361c2a303b5bfcf10d4c05536a32d265c0babe537f','6e7295b3c79ee95930fee7231265e342905b7848d261ae716d1ef1546ca785ab','687a9a50d9bbbe480f3e74e103f5b75c621a46a9ffdcc8e80dab65f6b2915a35']
        t.check('bindings','all three blocked candidates preserved',candidate['supersedes_blocked_candidate_sha256'] == old and all(x in baseline.values() for x in old))
        for key,name in [('pilot_report_sha256','MECHANICAL_PILOT_REPORT.json'),('e5_wire_report_sha256','E5_HARNESS_WIRE_AUDIT.json'),('lifecycle_repair_report_sha256','LIFECYCLE_REPAIR_REPORT.json'),('final_lifecycle_repair_report_sha256','FINAL_LIFECYCLE_REPAIR_REPORT.json'),('control_flow_closure_report_sha256','CONTROL_FLOW_CLOSURE_REPORT.json')]:
            t.check('bindings',name,digest((evidence/name).read_bytes()) == candidate[key])
        t.check('bindings','schema exact',candidate['journal_checkpoint_schema'] == SCHEMA and candidate['journal_checkpoint_schema_sha256'] == digest(canonical(SCHEMA)))
        t.check('bindings','event catalog exact',candidate['integrity_event_contract_sha256'] == digest(canonical(p.design['integrity_event_contract'])))
        t.check('bindings','expected identities only',candidate['model_provider'] == p.receipts())
        a,b,audits = schedule_tests(p,t)
        t.check('bindings','both schedules exact',candidate['phase_a_schedule_sha256'] == digest(canonical(a)) and candidate['phase_b_maximum_schedule_sha256'] == digest(canonical(b)))
        t.check('bindings','E5 report exact',load(evidence/'E5_HARNESS_WIRE_AUDIT.json')['audits'] == audits)
        response_tests(p,t)
        gates_tests(p,a,b,t)
        reserve_tests(p,t)
        print('SCHEDULE_SCORER_GATES_BINDINGS_PASS',len(records),flush=True)
        integrity_tests(p,a,t,OUT/'integrity_helpers')
        summary['helper_summaries']['CF'] = control_flow_tests(p,t,OUT/'control_helpers',SyntheticTransport)
        print('CONTROL_HELPERS_PASS',len(records),flush=True)
        summary['helper_summaries']['LR'] = final_lifecycle_tests(p,t,OUT/'final_helpers',SyntheticTransport)
        print('LR_HELPERS_PASS',len(records),flush=True)
        summary['helper_summaries']['I'] = lifecycle_tests(p,t,OUT/'lifecycle_helpers',SyntheticTransport)
        print('I1_I6_HELPERS_PASS',len(records),flush=True)
        # Never construct a Run against producer directories: copy before replay.
        h1,h2 = tree(evidence/'mechanical_pilot'),tree(evidence/'mechanical_pilot_replay')
        t.check('producer_trees','all authority files identical',h1 == h2)
        t.check('producer_trees','exact file counts',len(h1) == len(h2) == 1447)
        report = load(evidence/'MECHANICAL_PILOT_REPORT.json')
        t.check('producer_trees','full file map exact',h1 == report['replay_files_sha256'])
        summary['producer_trees'] = dict(file_count_each=len(h1),files_sha256=h1)
        for label in ('mechanical_pilot','mechanical_pilot_replay'):
            source = evidence/label
            destination = OUT/label
            shutil.copytree(source,destination)
            header = load(destination/'RUN.json')
            r = Run(p,destination,header['run_id'],resume=True)
            t.check('producer_replay',label+':480A240B',len(r.attempted) == 720 and sum(x.startswith('A:') for x in r.attempted) == 480 and len(r.evidence) == 720 and r.current_phase == 'B')
            t.check('producer_replay',label+':schedule files',load(source/'PHASE_A_SCHEDULE.json') == a and load(source/'PHASE_B_SCHEDULE.json') == b)
            t.check('producer_replay',label+':checkpoint state',r._last_checkpoint['row']['payload']['state'] == r.state())
            frozen_report = load(source/'FINAL_REPORT.json')
            t.check('producer_replay',label+':report state binding',frozen_report['state'] == r.state() and frozen_report['binding'] == r.binding and frozen_report['synthetic_observations'] == 720)
            journal = Journal(destination/'journal').read()
            pending = None
            for rec in journal:
                item = rec['payload']
                if item['type'] == 'START':
                    pending = item['call']
                    t.check('producer_lineage',label+':wire:'+pending['call_id'],digest(p.wire(pending)) == item['wire_sha256'] == pending['request_sha256'])
                elif item['type'] == 'COMPLETE':
                    from g_extract1_scoring import evaluate
                    t.check('producer_lineage',label+':evaluation:'+pending['call_id'],item['call_id'] == pending['call_id'] and item['receipt']['call_id'] == pending['call_id'] and item['receipt']['request_sha256'] == pending['request_sha256'] and item['evaluation'] == evaluate(p.variants[pending['rendered_variant_id']],item['raw_output'],truncated=item['provider_truncated']))
                    pending = None
            t.check('producer_lineage',label+':all720closed',pending is None and len(journal) == 1442)
            # Incomplete is retained, even after an otherwise valid full resume.
            r.resume(destination/'CHECKPOINT_final.json')
            t.check('producer_replay',label+':resume retained incomplete',r.final_report()['synthetic_primary_verdict'] == 'INCOMPLETE')
        summary['helper_summaries']['completed'] = completed_state_regressions(p,t,OUT/'completed_helpers',OUT/'mechanical_pilot',SyntheticTransport)
        summary['helper_summaries']['B_control'] = control_flow_b_regressions(p,t,OUT/'b_control_helpers',OUT/'mechanical_pilot',SyntheticTransport)
        print('PRODUCER_REPLAY_COMPLETED_B_CONTROL_PASS',len(records),flush=True)
        t.check('preservation','all repository evidence/protected/historical bytes unchanged',baseline == hashes(sorted(baseline_paths)))
        t.check('preservation','repository status unchanged',git('status','--porcelain=v1','--branch') == status)
        t.check('safety','zero socket attempts',not network_attempts)
        summary.update(verdict='PASS',readiness='READY_FOR_EXECUTION_FREEZE_REVIEW_ONLY',gaps=[],provider_calls=0,execution_freeze_active=False)
    except BaseException as exc:
        summary.update(verdict='BLOCKED',error=repr(exc),traceback=traceback.format_exc(),gaps=['Scope following first failure was intentionally stopped; no repairs.'])
        print(summary['traceback'],flush=True)
    summary['executed_assertions'] = len(records)+len(summary['independent_first'])
    summary['group_counts'] = dict(Counter(x['group'] for x in records))
    summary['socket_attempts'] = network_attempts
    (OUT/'REPORT.json').write_bytes(canonical(summary))
    print('AUDIT_RESULT',summary['verdict'],summary['executed_assertions'],summary['group_counts'],flush=True)

if __name__ == '__main__':
    suite() if '--suite' in sys.argv else main()
