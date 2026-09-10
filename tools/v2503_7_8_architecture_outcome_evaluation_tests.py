from __future__ import annotations
import json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n): checks.append(n); assert v,n
def make_repo(base, giant_name="giant.py"):
 repo=base/'repo';rt=base/'rt';(repo/'pkg').mkdir(parents=True);(repo/'tools').mkdir();(repo/'tests').mkdir();(repo/'pkg/__init__.py').write_text('')
 lines=[]
 for i in range(220): lines += [f'def maintenance_memory_verify_release_{i}(x):','    return x','','']
 (repo/f'pkg/{giant_name}').write_text('\n'.join(lines))
 return repo,rt
from architecture_project_goal import discover_architecture_goal_candidates,prepare_architecture_project_goal
from architecture_outcome_evaluation import evaluate_architecture_project_outcome
from repository_inventory import build_repository_inventory
with tempfile.TemporaryDirectory(prefix='eidolon-v2503-7-8-') as td:
 repo,rt=make_repo(Path(td));d=discover_architecture_goal_candidates(repo,runtime_root=rt);g=prepare_architecture_project_goal(repo,d['candidates'][0]['candidate_id'],runtime_root=rt)['goal'];incomplete=evaluate_architecture_project_outcome(repo,g['goal_id'],runtime_root=rt);req(not incomplete['ok'],'unchanged_not_success');req('verification_evidence_passed' in incomplete['failed_checks'],'verification_required');old=(repo/'pkg/giant.py').read_text();keep='\n'.join(old.splitlines()[:120])+'\n';(repo/'pkg/giant.py').write_text(keep);(repo/'pkg/extracted.py').write_text('\n'.join(old.splitlines()[120:])+'\n');manifest=build_repository_inventory(repo,runtime_root=rt)['inventory']['source_manifest_digest'];verification={'verification_digest':hashlib.sha256(b'focused+regression evidence').hexdigest(),'passed':True,'source_manifest_digest':manifest,'unexplained_regression_count':0};result=evaluate_architecture_project_outcome(repo,g['goal_id'],verification_evidence=verification,runtime_root=rt);req(result['ok'],'outcome_satisfied');req(result['status']=='architecture_goal_outcome_satisfied','satisfied_status');req(result['checks']['target_line_count_reduced'],'lines_reduced');req(result['checks']['target_symbol_count_reduced'],'symbols_reduced');req(result['checks']['no_new_dependency_cycles'],'cycles_not_increased');req(result['checks']['verification_evidence_passed'],'verification_bound');req(not result['tests_executed'],'evaluator_did_not_run_tests');req(not result['goal_completed_automatically'],'no_auto_completion');req(not result['action_executed'] and not result['standing_authority_granted'],'no_authority');bad=dict(verification);bad['unexplained_regression_count']=1;fail=evaluate_architecture_project_outcome(repo,g['goal_id'],verification_evidence=bad,runtime_root=rt);req(not fail['ok'],'regression_blocks_success');print(json.dumps({'suite':'v2503.7.8-architecture-outcome-evaluation','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
