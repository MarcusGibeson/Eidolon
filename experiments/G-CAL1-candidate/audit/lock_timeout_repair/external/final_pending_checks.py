"""Finish pending read-only checks in the SAME independent audit; no Run tests."""
import sys
sys.dont_write_bytecode = True
import json
import traceback
import subprocess
from collections import Counter
from pathlib import Path
import audit as a

OUT, REPO = a.OUT, a.REPO
def load(path):
    return json.loads(Path(path).read_bytes())
def file_sha(path):
    return a.sha(Path(path).read_bytes())
def assertion(ok,name,path='tools/g_cal1_lab.py',line=1):
    a.check(ok,name,file=path,line=line)

def complete():
    previous = load(OUT/'completion_assertions.json')
    assertion(len(previous)==35 and all(x['passed'] for x in previous[:-1]) and previous[-1]['name']=='source exact Git implementation bytes:tools/g_route1_operational.py',
              'same audit pending closure resumes only after recorded inherited EOL harness expectation')
    preserved = load(OUT/'COMPLETION_INPUT_PRESERVATION.json')
    before = load(OUT/'REPOSITORY_BEFORE.json')
    data = REPO/'experiments/G-CAL1-candidate'
    directory = data/'preexecution/lock_timeout_repair'
    candidate = load(directory/'EXECUTION_FREEZE_CANDIDATE.json')
    package = a.contract.Package()
    head = a.git('rev-parse','HEAD').decode().strip()
    branch = a.git('branch','--show-current').decode().strip()
    implementation = 'c01706ca04f14e88819b26bdd148a3d61b5688ec'
    completed = {r['name'] for r in previous if r['passed']}
    sources = {}
    for relative in [x for x in package.pins if x.startswith('tools/')]:
        blob = a.git('show',implementation+':'+relative)
        actual = (REPO/relative).read_bytes()
        name = 'source exact Git implementation bytes:' + relative
        eol = a.git('ls-files','--eol','--',relative).decode().strip()
        identical = blob==actual
        inherited_conversion = (not relative.startswith('tools/g_cal1') and 'w/crlf' in eol and 'i/lf' in eol and
                                'attr/-text' not in eol and actual.replace(b'\r\n',b'\n')==blob)
        if name not in completed:
            assertion(identical or inherited_conversion,'source commit lineage:exact or explicit inherited Git EOL conversion:' + relative,relative)
        sources[relative] = {'checkout_sha256':a.sha(actual),'Git_blob_sha256':a.sha(blob),'Git_eol':eol,'raw_equal':identical,
                             'inherited_EOL_only':inherited_conversion,'protected_checkout_hash_exact':a.sha(actual)==package.pins[relative]}
        assertion(a.sha(actual)==package.pins[relative],'source protected checkout bytes exact:' + relative,relative)
    assertion(subprocess.run(['git','-c','safe.directory='+REPO.as_posix(),'merge-base','--is-ancestor',implementation,'HEAD'],cwd=REPO).returncode==0,'implementation commit preserved in local ancestry')
    evidence = load(directory/'EVIDENCE_MANIFEST.json')
    for relative,expected in evidence['files'].items():
        assertion(file_sha(directory/relative)==expected,'actual producer evidence bytes:' + relative,str((directory/relative).relative_to(REPO)))
    producer = load(directory/'PILOT_REPORT.json')
    categories = Counter(r['category'] for r in producer['assertions'])
    assertion(all(r['passed'] is True for r in producer['assertions']) and producer['verdict']=='PASS' and len(producer['assertions'])==producer['checks'],'producer actual assertion rows/check count/verdict internally consistent')
    assertion(dict(categories)==producer['categories'],'producer actual category counts independently recomputed')
    lock_related = sum(v for k,v in categories.items() if k.startswith('LOCK_TIMEOUT'))
    baseline = load(directory/'PRESERVATION_BEFORE.json')
    assertion({k:len(v) for k,v in baseline.items()}=={'science':91,'prior_evidence':33513,'closed_history':2961},'preservation baseline exact scopes/counts')
    actual_groups = {}
    for group,pins in baseline.items():
        for relative,expected in pins.items():
            assertion(file_sha(REPO/relative)==expected,'preserved actual bytes:' + group + '/' + relative,relative)
        actual_groups[group] = {'files':len(pins),'mismatches':0}
    prior = load(directory/'PRIOR_LAB_MANIFEST.json')
    current = load(data/'LAB_MANIFEST.json')
    old_pins,new_pins = prior['protected_artifacts'],current['protected_artifacts']
    changed = {k for k in set(old_pins)|set(new_pins) if old_pins.get(k)!=new_pins.get(k)}
    assertion(changed=={'tools/g_cal1_lab.py','tools/g_cal1_timeout_tests.py','tools/g_cal1_timeout_repair.py'},'manifest rebind limited to repaired implementation and two source additions')
    assertion({k:v for k,v in prior.items() if k!='protected_artifacts'}=={k:v for k,v in current.items() if k!='protected_artifacts'},'manifest non-pin science/governance fields unchanged')
    supersession = load(directory/'CANDIDATE_SUPERSESSION.json')
    assertion(supersession['blocked_predecessor']['status']=='BLOCKED_UNACTIVATED_SUPERSEDED' and supersession['superseding_candidate']['sha256']==file_sha(directory/'EXECUTION_FREEZE_CANDIDATE.json'), 'old f458 candidate remains BLOCKED unactivated superseded')
    old_review = load(data/'audit/lifecycle_repair/LOCK_TIMEOUT_REVIEW_COMPLETION.json')
    assertion(old_review['overall_review_verdict']=='BLOCKED' and old_review['retained_incident_count']==0 and old_review['state_B_after_external_catch']=='RUNNING','old failed timeout review remains failed evidence')
    assertion(load(data/'audit/INDEPENDENT_PREREGISTRATION_AUDIT.json')['verdict']=='BLOCKED','previous preregistration audit remains BLOCKED')
    stop = load(directory/'PREPARATION_STOP_01.json')
    assertion(stop['status']=='PREPARATION_STOP' and stop['test_operations']==0 and stop['provider_model_calls']==0 and stop['independent_audit_started'] is False,'initial encoding-guard preparation stop preserved without tests')
    closure_commit = '1757155387af122d126f6db9fd03477e2823c2bb'
    for path in (REPO/'experiments/G-EXTRACT1-candidate/closure').glob('*'):
        if path.is_file():
            relative = path.relative_to(REPO).as_posix()
            blob = a.git('show',closure_commit+':'+relative)
            actual = path.read_bytes()
            eol = a.git('ls-files','--eol','--',relative).decode()
            accepted = actual==blob or ('i/lf' in eol and 'w/crlf' in eol and 'attr/-text' not in eol and actual.replace(b'\r\n',b'\n')==blob)
            assertion(accepted,'G-EXTRACT1 accepted closure commit content and declared checkout EOL:' + path.name,relative)
    route = load(REPO/'experiments/G-ROUTE4-candidate/closure/G_ROUTE4_CLOSURE.json')
    assertion(route['closure_verdict']=='FAILED' and route['primary_status']=='FAIL','G-ROUTE4 actual closure remains CLOSED FAILED')
    status = load(data/'STAGE_STATUS.json')
    assertion(status['G_EXTRACT1']=='CLOSED VALID NEGATIVE; NO_PHASE_A_CELL_QUALIFIED unchanged' and status['G_ROUTE4']=='CLOSED FAILED unchanged','metadata retains correct closed-history states')
    actual_status = a.git('status','--porcelain=v1','--untracked-files=all').decode()
    untracked = [line[3:] for line in actual_status.splitlines() if line.startswith('?? ')]
    assertion(len(untracked)==7 and all(x.startswith('experiments/G-EXTRACT1-candidate/corpus/') for x in untracked),'exact seven unrelated untracked artifacts remain')
    assertion(all(before[x]==file_sha(REPO/x) for x in untracked),'seven unrelated untracked files byte-preserved')
    after = a.repository_snapshot()
    assertion(before==after,'entire checkout exact initial/final file-byte identity')
    assertion(actual_status==load(OUT/'initial_git.json')['status'],'Git status unchanged from before first timeout')
    for name,expected in preserved.items():
        assertion(file_sha(OUT/name)==expected,'historical external audit input/source/stop unchanged:' + name,str(OUT/name))
    assertion(not a.NETWORK_ATTEMPTS,'completion zero socket/network/provider/metadata attempts')
    trees = [a.tree(OUT/'raw'/name) for name in ('independent_pilot_one','independent_pilot_two')]
    assertion(trees[0]==trees[1] and len(trees[0])==327,'completed pilot evidence unchanged byte-identical 327 files each')
    a.save('raw/independent_pilot_tree.json',trees[0])
    a.save('raw/preservation_verification.json',{'groups':actual_groups,'whole_checkout_files':len(before),
             'whole_checkout_tree_sha256':a.sha(a.canon(before)),'baseline_sha256':file_sha(directory/'PRESERVATION_BEFORE.json'),
             'untracked':{x:before[x] for x in untracked},'whole_checkout_unchanged':True})
    a.save('raw/source_bindings_verification.json',sources)
    return {'implementation':implementation,'HEAD':head,'branch':branch,'candidate_sha256':file_sha(directory/'EXECUTION_FREEZE_CANDIDATE.json'),
            'protected_pins':len(package.pins),'producer_actual_assertions':len(producer['assertions']),'producer_actual_lock_assertions':lock_related,
            'producer_count_is_not_authority':True,'producer_manifest_members':len(evidence['files']),
            'preservation_groups':actual_groups,'whole_checkout_files':len(before),'untracked_preserved':7,
            'pilot_files_each':327,'pilot_tree_sha256':a.sha(a.canon(trees[0])),
            'historical_source_versions':{name:preserved[name] for name in ('FIRST_TIMEOUT_EXECUTED_SOURCE.py','FULL_EXECUTED_SOURCE.py','REMAINING_EXECUTED_SOURCE.py')},
            'scope':'same new independent audit; no attacks/pilots rerun; pending read-only closure checks only'}

if __name__=='__main__':
    try:
        details = complete()
        verdict,error = 'PASS',None
    except BaseException:
        details = {}
        verdict,error = 'BLOCKED',traceback.format_exc()
    a.save('completion_assertions.json',a.ROWS)
    a.save('final_pending_result.json',{'verdict':verdict,'assertions':len(a.ROWS),'passed':sum(r['passed'] for r in a.ROWS),
                                   'details':details,'error':error,'network_attempts':a.NETWORK_ATTEMPTS,'provider_model_calls':0,
                                   'repository_writes':0,'activation':False,'execution_authorized':False})
    print(json.dumps({'verdict':verdict,'assertions':len(a.ROWS),'details':details,'error':error}),flush=True)
    if verdict!='PASS':sys.exit(2)
