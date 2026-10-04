import audit
import ast
import copy
import json
import shutil
import subprocess
import traceback
from collections import Counter
from pathlib import Path
from g_extract1_contract import Package, IntegrityError, canonical, digest, load
from g_extract1_runner import Run
from g_extract1_journal import Journal, SCHEMA, seal_checkpoint
from g_extract1_scoring import evaluate, event_category
from g_extract1_pilot import SyntheticTransport, integrity_tests
from g_extract1_lifecycle_tests import lifecycle_tests, reseal
from g_extract1_final_lifecycle_tests import final_lifecycle_tests, completed_state_regressions
from g_extract1_control_flow_tests import control_flow_tests, control_flow_b_regressions

ROOT, OUT = audit.ROOT, audit.OUT
E = ROOT/'experiments/G-EXTRACT1-candidate/preexecution/control_flow_closure'
records = [json.loads(line) for line in (OUT/'suite_assertions.jsonl').read_bytes().splitlines()]
summary = load(OUT/'REPORT.json')
summary['audit_harness_setup_notes'] = ['Initial producer integrity helper invocation lacked its pre-created temp parent. FileNotFoundError occurred before that test; no product assertion failed. Corrected only auditor temp harness prerequisites and continued the same review.']
summary.pop('error',None)
summary.pop('traceback',None)
class Checks:
    def check(self, group, name, condition):
        row = dict(group=group,test=name,result='PASS' if condition else 'FAIL')
        records.append(row)
        with (OUT/'suite_assertions.jsonl').open('ab') as f: f.write(canonical(row)+b'\n')
        if not condition: raise AssertionError(group+':'+name)
    def rejects(self, group, name, event, action):
        try: action()
        except IntegrityError as exc:
            self.check(group,name,exc.event == event)
            return
        self.check(group,name,False)
t = Checks()
def git(*args):
    r = subprocess.run(['git','-c','safe.directory=C:/Users/marcu/Eidolon-g4adj',*args],cwd=ROOT,capture_output=True)
    assert r.returncode == 0, r.stderr
    return r.stdout
def tree(directory):
    return {p.relative_to(directory).as_posix():digest(p.read_bytes()) for p in directory.rglob('*') if p.is_file()}
def stage(label):
    (OUT/'progress.json').write_bytes(canonical(dict(stage=label,executed_suite_assertions=len(records),groups=dict(Counter(x['group'] for x in records)))))
    print(label,len(records),flush=True)

def independent_additional(p):
    good = SyntheticTransport(p)
    for label,field,value,event in [('prompt','request_sha256','0'*64,'UNAUTHORIZED_PROMPT_MUTATION'),
        ('schedule','schedule_position',3,'SCHEDULE_POSITION_MISMATCH')]:
        r = Run(p,OUT/('own_'+label),label)
        r.perform(r.a[0],good,p.receipts())
        bad = copy.deepcopy(r.a[1]); bad[field] = value
        counter = audit.Counting()
        t.rejects('independent_integrated',label+':original',event,lambda:r.perform(bad,counter,p.receipts()))
        t.rejects('independent_integrated',label+':healthy postcatch',event,lambda:r.perform(r.a[1],counter,p.receipts()))
        incident = Journal(r.directory/'integrity').read()[0]['payload']
        t.check('independent_integrated',label+':persisted scope',incident['event'] == event and incident['phase'] == 'A' and incident['cell'] == bad['cell_id'])
        rebuilt = Run(p,r.directory,r.run_id,resume=True)
        t.rejects('independent_integrated',label+':restart',event,lambda:rebuilt.perform(rebuilt.a[1],counter,p.receipts()))
        t.check('independent_integrated',label+':no new START or contact',counter.calls == 0 and len(r.journal.read()) == 2)
    r = Run(p,OUT/'own_duplicate','duplicate')
    r.perform(r.a[0],good,p.receipts())
    payloads = [copy.deepcopy(x['payload']) for x in r.journal.read()]
    payloads += copy.deepcopy(payloads)
    reseal(r.directory/'journal',payloads)
    t.rejects('independent_integrated','resealed duplicate replay','DUPLICATE_CALL',lambda:Run(p,r.directory,r.run_id,resume=True))
    t.check('independent_integrated','duplicate incident persisted',Journal(r.directory/'integrity').read()[0]['payload']['event'] == 'DUPLICATE_CALL')
    seed = Run(p,OUT/'own_lrseed','own_lrseed')
    seed.perform(seed.a[0],good,p.receipts()); cp = seed.checkpoint('valid')
    for label,payload in [('list',[]),('null',None),('numeric',4),('string','x'),('boolean',False),('object',{})]:
        dest = OUT/('own_cp_'+label)
        shutil.copytree(seed.directory,dest)
        seal_checkpoint(dest/'OWN_ATTACK.json',payload)
        r = Run(p,dest,seed.run_id,resume=True)
        t.rejects('independent_LR1',label+':own sealed malformed','CORRUPTED_CHECKPOINT',lambda:r.resume(dest/'OWN_ATTACK.json'))
        t.check('independent_LR1',label+':immediate persistence',r.events == ['CORRUPTED_CHECKPOINT'] and Journal(dest/'integrity').read()[0]['payload']['event'] == 'CORRUPTED_CHECKPOINT')
        t.rejects('independent_LR1',label+':valid resume terminal','CORRUPTED_CHECKPOINT',lambda:r.resume(dest/'CHECKPOINT_valid.json'))
        rebuilt = Run(p,dest,seed.run_id,resume=True)
        counter = audit.Counting()
        t.rejects('independent_LR1',label+':restart perform terminal','CORRUPTED_CHECKPOINT',lambda:rebuilt.perform(rebuilt.a[1],counter,p.receipts()))
        t.check('independent_LR1',label+':zero transport',counter.calls == 0)
    source = (ROOT/'tools/g_extract1_runner.py').read_text(encoding='utf8')
    module = ast.parse(source)
    guard = next(x for x in module.body if isinstance(x,ast.FunctionDef) and x.name == 'guarded')
    handlers = [ast.unparse(x.type) for x in ast.walk(guard) if isinstance(x,ast.ExceptHandler)]
    t.check('independent_source','guard never catches BaseException',handlers == ['IntegrityError','Exception'])
    base_handlers = [x for x in ast.walk(module) if isinstance(x,ast.ExceptHandler) and ast.unparse(x.type) == 'BaseException']
    t.check('independent_source','one specific BaseException boundary',len(base_handlers) == 1 and 'transport-control-flow:' in ast.unparse(base_handlers[0]) and any(isinstance(x,ast.Raise) and x.exc is None for x in base_handlers[0].body))
    imports = []
    for rel in summary['source_sha256']:
        mod = ast.parse((ROOT/rel).read_text(encoding='utf8'))
        imports += [x.module or '' for x in ast.walk(mod) if isinstance(x,ast.ImportFrom)]
        imports += [y.name for x in ast.walk(mod) if isinstance(x,ast.Import) for y in x.names]
    t.check('independent_source','no provider adapter imports',not any(any(k in n.lower() for k in ('ollama','openai','anthropic','requests','httpx')) for n in imports))
    summary['imported_module_names'] = sorted(audit.sys.modules)
    candidate = load(E/'EXECUTION_FREEZE_CANDIDATE.json')
    for key in ('comparator_sha256','scorer_sha256','qualification_logic_sha256'):
        t.check('independent_bindings',key,candidate[key] == summary['source_sha256']['tools/g_extract1_scoring.py'])
    t.check('independent_bindings','schedule algorithm',candidate['schedule_algorithm_sha256'] == summary['source_sha256']['tools/g_extract1_contract.py'])
    t.check('independent_bindings','response validator',candidate['response_validator_sha256'] == digest((ROOT/'tools/g_route3_operational.py').read_bytes()))
    t.check('independent_LR3','exact ten PRE catalog',len(p.design['integrity_event_contract']['precontact_blocking_events']) == 10)

try:
    p = Package(ROOT)
    independent_additional(p)
    stage('INDEPENDENT_ADDITIONAL_PASS')
    (OUT/'integrity_helpers').mkdir()
    integrity_tests(p,p.schedule('A'),t,OUT/'integrity_helpers')
    summary['helper_summaries']['CF'] = control_flow_tests(p,t,OUT/'control_helpers',SyntheticTransport)
    stage('CONTROL_HELPERS_PASS')
    summary['helper_summaries']['LR'] = final_lifecycle_tests(p,t,OUT/'final_helpers',SyntheticTransport)
    stage('LR1_LR3_HELPERS_PASS')
    summary['helper_summaries']['I'] = lifecycle_tests(p,t,OUT/'lifecycle_helpers',SyntheticTransport)
    stage('I1_I6_ACTUAL_480A_PASS')
    h1,h2 = tree(E/'mechanical_pilot'),tree(E/'mechanical_pilot_replay')
    t.check('producer_trees','all authority files identical',h1 == h2)
    t.check('producer_trees','exact file counts',len(h1) == len(h2) == 1447)
    producer_report = load(E/'MECHANICAL_PILOT_REPORT.json')
    t.check('producer_trees','full file map exact',h1 == producer_report['replay_files_sha256'])
    summary['producer_trees'] = dict(file_count_each=len(h1),files_sha256=h1)
    a,b = p.schedule('A'),p.schedule('B',sorted(p.blueprint['schedule_plan']['phase_b_cell_order']))
    for label in ('mechanical_pilot','mechanical_pilot_replay'):
        source,dest = E/label,OUT/label
        shutil.copytree(source,dest)
        header = load(dest/'RUN.json')
        r = Run(p,dest,header['run_id'],resume=True)
        t.check('producer_replay',label+':480A240B',len(r.attempted) == 720 and sum(x.startswith('A:') for x in r.attempted) == 480 and len(r.evidence) == 720 and r.current_phase == 'B')
        t.check('producer_replay',label+':schedule files',load(source/'PHASE_A_SCHEDULE.json') == a and load(source/'PHASE_B_SCHEDULE.json') == b)
        t.check('producer_replay',label+':checkpoint state',r._last_checkpoint['row']['payload']['state'] == r.state())
        fr = load(source/'FINAL_REPORT.json')
        t.check('producer_replay',label+':report state binding',fr['state'] == r.state() and fr['binding'] == r.binding and fr['synthetic_observations'] == 720 and fr['phase_a_schedule_sha256'] == digest(canonical(a)) and fr['phase_b_schedule_sha256'] == digest(canonical(b)))
        journal = Journal(dest/'journal').read()
        pending = None
        for rec in journal:
            item = rec['payload']
            if item['type'] == 'START':
                pending = item['call']
                t.check('producer_lineage',label+':wire:'+pending['call_id'],digest(p.wire(pending)) == item['wire_sha256'] == pending['request_sha256'])
            elif item['type'] == 'COMPLETE':
                t.check('producer_lineage',label+':evaluation:'+pending['call_id'],item['call_id'] == pending['call_id'] and item['receipt']['call_id'] == pending['call_id'] and item['receipt']['request_sha256'] == pending['request_sha256'] and item['evaluation'] == evaluate(p.variants[pending['rendered_variant_id']],item['raw_output'],truncated=item['provider_truncated']))
                pending = None
        t.check('producer_lineage',label+':all720closed',pending is None and len(journal) == 1442)
        r.resume(dest/'CHECKPOINT_final.json')
        t.check('producer_replay',label+':resume retained incomplete',r.final_report()['synthetic_primary_verdict'] == 'INCOMPLETE')
    # Completed-state helpers need a clean, unresumed pilot, not the copies just resumed.
    pristine = OUT/'pristine_pilot_for_completed_helpers'
    shutil.copytree(E/'mechanical_pilot',pristine)
    summary['helper_summaries']['completed'] = completed_state_regressions(p,t,OUT/'completed_helpers',pristine,SyntheticTransport)
    summary['helper_summaries']['B_control'] = control_flow_b_regressions(p,t,OUT/'b_control_helpers',pristine,SyntheticTransport)
    stage('PRODUCER_FULL_REPLAY_COMPLETED_B_CONTROL_PASS')
    baseline = load(OUT/'repository_before.json')
    now = {name:digest((ROOT/name).read_bytes()) for name in baseline['files']}
    t.check('preservation','all snapshotted evidence/protected/historical bytes unchanged',now == baseline['files'])
    t.check('preservation','status unchanged',git('status','--porcelain=v1','--branch').decode() == baseline['status'])
    t.check('preservation','historical GRoute4 committed unchanged since start',not git('diff','--name-only','694742a7cc3723f2c562121d5fc666cc777992ca','HEAD','--','experiments/G-ROUTE4-candidate'))
    untracked = [line[3:] for line in baseline['status'].splitlines() if line.startswith('?? ')]
    t.check('preservation','exact seven preserved untracked corpus files',len(untracked) == 7 and all(now[x] == p.pins[x] for x in untracked))
    summary['preservation_file_count'] = len(now)
    summary['preserved_untracked'] = {name:now[name] for name in untracked}
    t.check('safety','zero socket attempts',not audit.network_attempts)
    summary.update(verdict='PASS',readiness='READY_FOR_EXECUTION_FREEZE_REVIEW_ONLY',gaps=[],provider_calls=0,execution_freeze_active=False,findings=[])
except BaseException as exc:
    summary.update(verdict='BLOCKED',error=repr(exc),traceback=traceback.format_exc(),gaps=['Remaining scope stopped at first product failure or test infrastructure failure. No repository repair.'])
    print(summary['traceback'],flush=True)
summary['group_counts'] = dict(Counter(x['group'] for x in records))
summary['executed_assertions'] = len(records)+len(summary['independent_first'])
summary['socket_attempts'] = audit.network_attempts
(OUT/'FINAL_AUDIT.json').write_bytes(canonical(summary))
print('AUDIT_RESULT',summary['verdict'],summary['executed_assertions'],summary['group_counts'],flush=True)
