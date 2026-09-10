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
from architecture_project_goal import *
with tempfile.TemporaryDirectory(prefix="eidolon-v2503-7-4-") as td:
 repo,rt=make_repo(Path(td));d=discover_architecture_goal_candidates(repo,runtime_root=rt);g=prepare_architecture_project_goal(repo,d['candidates'][0]['candidate_id'],runtime_root=rt);req(g['ok'],'goal_ready');req(g['status']=='architecture_project_goal_ready_for_operator_review','review_status');goal=g['goal'];req(goal['contract_version']=='v2503.7.5','contract');req(goal['operator_selection_required'],'operator_boundary');req(not goal['goal_activated'],'not_activated');req(len(goal['goal_evidence_digest'])==64,'evidence_bound');req(goal['acceptance_criteria']['new_dependency_cycles_allowed']==0,'cycle_gate');req(goal['acceptance_criteria']['unexplained_regressions_allowed']==0,'regression_gate');req(goal['acceptance_criteria']['target_line_count_should_decrease']>0,'measurable_line_goal');req(goal['acceptance_criteria']['target_top_level_symbol_count_should_decrease']>0,'measurable_symbol_goal');req(not goal['tests_executed'] and not goal['source_modified'],'no_execution');req(not g['standing_authority_granted'],'no_authority');bad=prepare_architecture_project_goal(repo,'wrong-candidate',runtime_root=rt);req(not bad['ok'],'exact_candidate_required');print(json.dumps({'suite':'v2503.7.4-architecture-project-goal','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
