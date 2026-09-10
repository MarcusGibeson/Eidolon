from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for x in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(x) not in sys.path: sys.path.insert(0,str(x))
sys.dont_write_bytecode=True
from architecture_change_reasoning import build_architecture_change_assessment,load_architecture_change_assessment,build_refactor_migration_plan,load_refactor_migration_plan
from architecture_project_goal import discover_architecture_goal_candidates,prepare_architecture_project_goal,prepare_architecture_autonomous_developer_bridge
from architecture_outcome_evaluation import evaluate_architecture_project_outcome
from development_authority import issue_operator_authorization
from repository_inventory import build_repository_inventory
from release_authority import WORKING_SOURCE_VERSION,PREVIOUS_WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT,validate_release_authority

checks=[]
def req(v,n): checks.append(n); assert v,n

def make_repo(base: Path):
    repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'helpers').mkdir();(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('');(repo/'helpers/__init__.py').write_text('')
    lines=[]
    for i in range(230): lines += [f'def maintenance_memory_verify_release_{i}(x):','    return x','','']
    (repo/'pkg/giant.py').write_text('\n'.join(lines))
    (repo/'pkg/use.py').write_text('from pkg.giant import maintenance_memory_verify_release_1\n')
    (repo/'tests/test_use.py').write_text('from pkg.use import maintenance_memory_verify_release_1\n')
    (repo/'helpers/source_shape.py').write_text("from pathlib import Path\ndef inspect(): return Path('pkg/giant.py').read_text()\n")
    (repo/'tests/test_shape.py').write_text('from helpers.source_shape import inspect\n')
    return repo,rt

with tempfile.TemporaryDirectory(prefix='eidolon-v2503-7-9-') as td:
    repo,rt=make_repo(Path(td))
    assessment=build_architecture_change_assessment(repo,['pkg/giant.py'],runtime_root=rt)
    req(assessment['ok'],'assessment_ok')
    req(assessment['assessment']['complete'],'assessment_complete')
    private=load_architecture_change_assessment(assessment['assessment']['analysis_id'],runtime_root=rt,include_private=True);finding=private['findings'][0]
    req('pkg/use.py' in finding['direct_importers'],'direct_importer')
    req('tests/test_use.py' in finding['transitive_importers'],'transitive_importer')
    req('helpers/source_shape.py' in finding['filename_bound_consumers'],'structural_consumer')
    req('tests/test_shape.py' in finding['candidate_tests'],'consumer_test')
    req(finding['responsibilities'],'responsibility_inference')
    req(finding['risk'] in {'high','very_high'},'risk_classification')
    req(not assessment['action_executed'],'assessment_nonexecuting')

    plan_result=build_refactor_migration_plan(repo,['pkg/giant.py'],runtime_root=rt)
    req(plan_result['ok'],'plan_ok');plan=load_refactor_migration_plan(plan_result['plan']['plan_id'],runtime_root=rt,include_private=True)
    req(plan['review_only'],'plan_review_only')
    req(plan['requires_operator_authorization_before_mutation'],'plan_approval_boundary')
    req(any(x['kind']=='establish_compatibility_facade' for x in plan['steps']),'plan_facade')
    req(any(x['kind']=='verify_slice' for x in plan['steps']),'plan_verification')
    req(not plan['action_executed'],'plan_nonexecuting')

    discovery=discover_architecture_goal_candidates(repo,runtime_root=rt)
    req(discovery['ok'] and discovery['candidate_count']>=1,'hotspot_discovery')
    candidate=discovery['candidates'][0]
    req(candidate['candidate_only'] and not candidate['auto_selected'],'candidate_inert')
    req(candidate['architecture_reasons'],'candidate_evidence')
    goal_result=prepare_architecture_project_goal(repo,candidate['candidate_id'],runtime_root=rt);req(goal_result['ok'],'goal_ready');goal=goal_result['goal']
    req(not goal['goal_activated'],'goal_inert')
    req(goal['operator_selection_required'],'goal_selection_boundary')
    req(goal['acceptance_criteria']['new_dependency_cycles_allowed']==0,'goal_cycle_gate')
    req(goal['acceptance_criteria']['unexplained_regressions_allowed']==0,'goal_regression_gate')

    denied=prepare_architecture_autonomous_developer_bridge(goal['goal_id'],operator_selection_receipt=None,runtime_root=rt)
    req(not denied['ok'],'bridge_requires_selection')
    text='select architecture project goal'
    receipt=issue_operator_authorization(stage='candidate_selection',subject_id=goal['goal_id'],subject_digest=goal['goal_evidence_digest'],explicit_operator_text=text,expected_operator_text=text)
    bridge=prepare_architecture_autonomous_developer_bridge(goal['goal_id'],operator_selection_receipt=receipt,runtime_root=rt)
    req(bridge['ok'],'bridge_ready')
    req(not bridge['campaign_started'],'bridge_does_not_start')
    req(not bridge['action_executed'],'bridge_nonexecuting')

    incomplete=evaluate_architecture_project_outcome(repo,goal['goal_id'],runtime_root=rt)
    req(not incomplete['ok'],'outcome_requires_change_and_verification')
    old=(repo/'pkg/giant.py').read_text();(repo/'pkg/giant.py').write_text('\n'.join(old.splitlines()[:100])+'\n');(repo/'pkg/extracted.py').write_text('\n'.join(old.splitlines()[100:])+'\n')
    manifest=build_repository_inventory(repo,runtime_root=rt)['inventory']['source_manifest_digest']
    evidence={'verification_digest':hashlib.sha256(b'checkpoint-verification').hexdigest(),'passed':True,'source_manifest_digest':manifest,'unexplained_regression_count':0}
    outcome=evaluate_architecture_project_outcome(repo,goal['goal_id'],verification_evidence=evidence,runtime_root=rt)
    req(outcome['ok'],'outcome_satisfied')
    req(outcome['checks']['target_line_count_reduced'],'outcome_lines')
    req(outcome['checks']['target_symbol_count_reduced'],'outcome_symbols')
    req(outcome['checks']['no_new_dependency_cycles'],'outcome_cycles')
    req(outcome['verification_evidence_valid'],'outcome_verification_bound')
    req(not outcome['goal_completed_automatically'],'outcome_no_auto_completion')
    req(not outcome['action_executed'],'outcome_nonexecuting')

req(WORKING_SOURCE_VERSION=='2503.7.9','version_current')
req(PREVIOUS_WORKING_SOURCE_VERSION=='2503.5.5','lineage_parent')
req(NEXT_BOUNDED_UNIT=='v2503.8.0 - Operator-Selected Architecture Project Trial','next_unit')
auth=validate_release_authority(source_root=ROOT)
req(auth['ok'] and auth['passed']==auth['total']==17,'release_authority')
print(json.dumps({'suite':'v2503.7.9-architecture-reasoning-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
