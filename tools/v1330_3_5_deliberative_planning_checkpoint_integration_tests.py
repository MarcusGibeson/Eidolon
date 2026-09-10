from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from deliberative_planning_integration import build_deliberative_planning_checkpoint
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from goal_representation import create_goal
checks=[]
def req(v,n):checks.append(n);assert v,n
pu={'workspace_digest':'a'*64,'source_manifest_digest':'b'*64,'manifest_consistent':True};g=create_goal(outcome='medium feature',acceptance_criteria=['contract passes','integration passes'])
options=[{'code':'targeted','strategy':'targeted'},{'code':'refactor','strategy':'refactor'}];ev={'targeted':{c:{'score':90,'confidence':.9,'evidence_digests':['e']} for c in ('correctness','complexity','compatibility','reversibility','performance','privacy','maintenance')},'refactor':{c:{'score':60,'confidence':.9,'evidence_digests':['e']} for c in ('correctness','complexity','compatibility','reversibility','performance','privacy','maintenance')}}
out={'outcome_observed':True,'verification_evidence_digests':['verify'],'prediction_total':2,'prediction_hits':2,'acceptance_criteria_total':2,'acceptance_criteria_met_count':2}
with tempfile.TemporaryDirectory() as td:
 r=build_deliberative_planning_checkpoint(g,pu,decision_context={'risk_level':'medium','tradeoffs_matter':True},explicit_options=options,evidence_by_approach=ev,assumptions=[{'code':'existing_contract','statement_digest':'s','confidence':.8,'evidence_digests':['e'],'validation_method':'retained_test'}],outcome_evidence=out,runtime_root=td)['deliberative_planning'];req(r['candidate_count']==2 and not r['tradeoff_tie'],'medium_compared');req(r['stage_ids']['assumption_ledger'],'assumption_lineage');req(r['plan_quality']['evaluable'],'outcome_scored');req(r['grounded_rationale_available'],'rationale')
 chat=process_ordinary_chat_development_turn('show deliberative planning',project_state={'planning_goal':g,'project_understanding':pu,'planning_decision_context':{'risk_level':'low','reversible':True}},runtime_root=td);req(chat.get('active') and chat.get('deliberative_planning',{}).get('checkpoint_id'),'ordinary_route')
print(json.dumps({'suite':'v1330.3-5-deliberative-planning-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
