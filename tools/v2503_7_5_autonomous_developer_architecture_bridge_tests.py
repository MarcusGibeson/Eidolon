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
from development_authority import issue_operator_authorization
with tempfile.TemporaryDirectory(prefix="eidolon-v2503-7-5-") as td:
 repo,rt=make_repo(Path(td));d=discover_architecture_goal_candidates(repo,runtime_root=rt);g=prepare_architecture_project_goal(repo,d['candidates'][0]['candidate_id'],runtime_root=rt)['goal'];none=prepare_architecture_autonomous_developer_bridge(g['goal_id'],operator_selection_receipt=None,runtime_root=rt);req(not none['ok'],'selection_required');text='select architecture project goal';receipt=issue_operator_authorization(stage='candidate_selection',subject_id=g['goal_id'],subject_digest=g['goal_evidence_digest'],explicit_operator_text=text,expected_operator_text=text);b=prepare_architecture_autonomous_developer_bridge(g['goal_id'],operator_selection_receipt=receipt,runtime_root=rt);req(b['ok'],'bridge_ok');req(b['developer_contract']['ok'],'developer_contract');req(b['architecture_stage_evidence']['ok'],'stage_evidence');req(b['architecture_stage_evidence'].get('owner')=='deep_project_understanding','retained_owner');req(b['architecture_stage_evidence'].get('stage')=='architecture','architecture_stage');req(not b['campaign_started'],'not_started');req(not b['action_executed'] and not b['implementation_executed'],'no_execution');req(not b['candidate_installed'] and not b['candidate_promoted'],'no_install_promotion');req(not b['standing_authority_granted'],'no_standing_authority');wrong=issue_operator_authorization(stage='candidate_selection',subject_id=g['goal_id'],subject_digest='0'*64,explicit_operator_text=text,expected_operator_text=text);bad=prepare_architecture_autonomous_developer_bridge(g['goal_id'],operator_selection_receipt=wrong,runtime_root=rt);req(not bad['ok'],'wrong_digest_rejected');print(json.dumps({'suite':'v2503.7.5-autonomous-developer-architecture-bridge','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
