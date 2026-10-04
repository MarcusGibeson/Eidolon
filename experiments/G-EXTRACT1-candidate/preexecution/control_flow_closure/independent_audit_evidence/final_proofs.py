import audit
import copy
import json
import shutil
import subprocess
import traceback
from collections import Counter
from g_extract1_contract import Package, canonical, digest, load
from g_extract1_runner import Run
from g_extract1_journal import Journal
from g_extract1_lifecycle_tests import reseal

ROOT, OUT = audit.ROOT, audit.OUT
E = ROOT/'experiments/G-EXTRACT1-candidate/preexecution/control_flow_closure'
summary = load(OUT/'FINAL_AUDIT.json')
records = [json.loads(line) for line in (OUT/'suite_assertions.jsonl').read_bytes().splitlines()]
prior_failures = [x for x in records if x['result'] == 'FAIL']
assert summary['verdict'] == 'PASS' or (
    prior_failures == [dict(group='preservation',test='exact seven preserved untracked corpus files',result='FAIL')]
    and summary['error'] == "AssertionError('preservation:exact seven preserved untracked corpus files')"
), 'Prior product failure: stop without more testing'
summary['audit_harness_setup_notes'].append('The first seven-corpus-artifact accounting assertion incorrectly counted every untracked file, including preexisting MECHANICAL_EVIDENCE_READOUT.md. Raw failed auditor assertion retained. Full snapshot and Git status checks already passed; corrected only the scope filter to corpus files.')
summary.pop('error',None)
summary.pop('traceback',None)
def check(group, name, condition):
    row = dict(group=group,test=name,result='PASS' if condition else 'FAIL')
    records.append(row)
    with (OUT/'suite_assertions.jsonl').open('ab') as f: f.write(canonical(row)+b'\n')
    if not condition: raise AssertionError(group+':'+name)
def git(*args):
    r = subprocess.run(['git','-c','safe.directory=C:/Users/marcu/Eidolon-g4adj',*args],cwd=ROOT,capture_output=True)
    assert r.returncode == 0, r.stderr
    return r.stdout
try:
    p = Package(ROOT)
    candidate = load(E/'EXECUTION_FREEZE_CANDIDATE.json')
    check('independent_bindings','candidate committed exact',git('show','HEAD:experiments/G-EXTRACT1-candidate/preexecution/control_flow_closure/EXECUTION_FREEZE_CANDIDATE.json') == (E/'EXECUTION_FREEZE_CANDIDATE.json').read_bytes())
    check('independent_bindings','manifest categories exact',candidate['complete_manifest_verification']['pin_categories'] == p.pin_categories)
    for label in ('mechanical_pilot','mechanical_pilot_replay'):
        source = E/label
        r = Run(p,OUT/('exact_report_'+label),'mechanical-only')
        shutil.copyfile(source/'CHECKPOINT_final.json',r.directory/'CHECKPOINT_final.json')
        payloads = [copy.deepcopy(x['payload']) for x in Journal(source/'journal').read()]
        reseal(r.directory/'journal',payloads)
        r._replay()
        check('independent_full_reports',label+':entire final report rederived',r.final_report() == load(source/'FINAL_REPORT.json'))
        check('independent_full_reports',label+':full checkpoint lineage rederived',r._last_checkpoint['row'] == load(source/'CHECKPOINT_final.json') and r.checkpoint_lineage == r._last_checkpoint['row']['sha256'])
    # Independently consume all published selector spans rather than trusting a count.
    audits = load(E/'E5_HARNESS_WIRE_AUDIT.json')['audits']
    for number,item in enumerate(audits,1):
        base = item['base']
        members = sorted((v for v in p.variants.values() if v['logical_base_id'] == base),key=lambda v:v['variant_id'])
        seed = p.design['sampling']['candidate_phase_'+base[0].lower()+'_seed_base']+(p.positions[base]['fixture_ordinal']-1)*10+item['repeat']
        wires = [p.wire(dict(rendered_variant_id=v['rendered_variant_id'],model=item['model'],seed=seed)) for v in members]
        masked = [wire[:span[0]]+b'<SELECTOR_REQUEST>'+wire[span[1]:] for wire,span in zip(wires,item['spans'])]
        selectors = [json.dumps(v['fixture']['operation_nodes'][0]['arguments']['selector_value']['value'],ensure_ascii=False) for v in members]
        span_tokens = [wire[span[0]:span[1]].decode('utf8') for wire,span in zip(wires,item['spans'])]
        expected_tokens = [json.dumps(s,ensure_ascii=False)[1:-1] for s in selectors]
        bodies = [json.loads(wire) for wire in wires]
        prompts = [body.pop('prompt') for body in bodies]
        check('independent_E5_spans',str(number)+':'+base, len(wires) == 2 and [digest(w) for w in wires] == item['wire_sha256'] and
              span_tokens == expected_tokens and masked[0] == masked[1] and digest(masked[0]) == item['masked_sha256'] and
              bodies[0] == bodies[1] and prompts[0].replace(selectors[0],'<SELECTOR>',1) == prompts[1].replace(selectors[1],'<SELECTOR>',1))
    check('independent_E5_spans','all108 unique audits',len(audits) == len({(x['base'],x['model'],x['repeat']) for x in audits}) == 108)
    baseline = load(OUT/'repository_before.json')
    untracked = [line[3:] for line in baseline['status'].splitlines() if line.startswith('?? ') and line[3:].startswith('experiments/G-EXTRACT1-candidate/corpus/')]
    check('independent_preservation','exact seven untracked corpus files',len(untracked) == 7 and all(digest((ROOT/name).read_bytes()) == baseline['files'][name] == p.pins[name] for name in untracked))
    summary['preserved_untracked'] = {name:baseline['files'][name] for name in untracked}
    summary['preservation_file_count'] = len(baseline['files'])
    old = candidate['supersedes_blocked_candidate_sha256']
    old_records = []
    for sha in old:
        matches = [name for name,d in baseline['files'].items() if d == sha]
        check('independent_old_authority',sha+':preserved digest',bool(matches))
        for name in matches:
            obj = load(ROOT/name)
            check('independent_old_authority',name+':still unactivated candidate',obj['status'] == 'EXECUTION_FREEZE_CANDIDATE_ONLY' and not any(obj[k] for k in ('activated','phase_a_authorized','phase_b_authorized')))
            old_records.append(dict(path=name,sha256=sha,status=obj['status'],activated=obj['activated']))
    summary['old_candidate_authority'] = old_records
    for name in ('G_ROUTE4_CLOSURE.json','PHASE_B_UNSAFE_STOP_DIAGNOSTIC.json'):
        rel = 'experiments/G-ROUTE4-candidate/closure/'+name
        raw = (ROOT/rel).read_bytes()
        check('independent_historical',name+':current and starting committed blobs unchanged',raw == git('show','HEAD:'+rel) == git('show','694742a7cc3723f2c562121d5fc666cc777992ca:'+rel))
    closure = load(ROOT/'experiments/G-ROUTE4-candidate/closure/G_ROUTE4_CLOSURE.json')
    check('independent_historical','GRoute4 remains CLOSED FAILED',closure['closure_verdict'] == 'FAILED' and closure['governance']['provider_calls_for_closure'] == 0)
    check('safety','no socket attempts in final proofs',not audit.network_attempts)
    summary['scope_completed'] = [
        'First direct Run.perform KeyboardInterrupt/SystemExit/GeneratorExit/custom BaseException attacks and immediate external-catch proof.',
        'Specific post-START transport control handler inspected; ordinary exception and malformed outcome closure; valid success and timeout/error/missing replay.',
        'Own sealed malformed LR1 checkpoints plus all fresh LR1=137, LR2=143, LR3=42 producer-helper assertions; 10 frozen PRE matrix states replayed.',
        'Fresh full I1-I6 behaviors including actual 480 synthetic A calls, integrated eligibility, failed A/B, method locks, retained aftercatch/restart, receipts, lineage, grants and protected mutations.',
        'Schedules 480A/240maxB/720; 720 exact historical wire comparisons; all64 B subsets; independently verified all108 selector-only spans and 12 elapsed clarifications.',
        'Scorer exact/duplicate/truncation/numeric samples, family/repeat/qualification gates, reserve guards.',
        'All 1447 files of each producer full720 tree compared byte-for-byte; both full journals independently replayed, all1440 START wire and COMPLETE evaluation assertions per tree pair, complete final reports and checkpoint lineage rederived.',
        'Current candidate/source working bytes and committed blobs, accepted package/science closure, all50 manifest protected bytes, all report/schema/schedule bindings verified.',
        'All three old blocked candidates preserved unactivated; seven untracked corpus artifacts and historical GRoute4 closure/diagnostic unchanged; full preexecution/historical snapshot preserved.'
    ]
    summary['limitations'] = ['No provider, model or network validation; expected identity receipts are synthetic.','Mechanical exercise_authorization grants are test objects only; no actual activation or authorization.','64 subset and reserve tests exercise frozen mechanical rules, not scientific or cognitive qualification.','Full producer720 journals reused as expressly permitted; actual480A lifecycle executed afresh.']
    summary['audited_implementation_commit'] = '17af89c9c4f279d55d48aac46125c2844d3b4ad5'
    summary['audited_evidence_commit'] = '10cc8a978237fa6a403c1bfd72184845200b192e'
    summary['candidate_sha256'] = digest((E/'EXECUTION_FREEZE_CANDIDATE.json').read_bytes())
    summary['run_commands'] = ['python -B -X utf8 '+str(OUT/'audit.py'),'python -B -X utf8 '+str(OUT/'audit.py')+' --suite','python -B -X utf8 '+str(OUT/'continuation.py'),'python -B -X utf8 '+str(OUT/'final_proofs.py')]
    summary['evidence_root'] = str(OUT)
    summary['independent_first_assertions'] = len(summary['independent_first'])
    summary['repository_edited'] = False
    summary['scientific_qualification_claims'] = False
    summary.update(verdict='PASS',readiness='READY_FOR_EXECUTION_FREEZE_REVIEW_ONLY',gaps=[],provider_calls=0,execution_freeze_active=False,findings=[])
except BaseException as exc:
    summary.update(verdict='BLOCKED',readiness=None,error=repr(exc),traceback=traceback.format_exc(),gaps=['Final proof stopped at first failure; no product repair.'])
    print(summary['traceback'],flush=True)
summary['group_counts'] = dict(Counter(x['group'] for x in records))
summary['executed_assertions'] = len(records)+len(summary['independent_first'])
summary['audit_harness_assertion_failures'] = prior_failures
summary['product_assertion_failures'] = [x for x in records if x['result'] == 'FAIL' and x not in prior_failures]
summary['passed_assertions'] = sum(x['result'] == 'PASS' for x in records)+len(summary['independent_first'])
(OUT/'FINAL_AUDIT.json').write_bytes(canonical(summary))
print('FINAL_PROOFS',summary['verdict'],summary['executed_assertions'],summary['group_counts'],flush=True)
