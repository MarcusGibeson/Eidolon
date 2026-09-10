from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from risk_sensitive_planning import assess_plan_risk
checks=[]
def req(v,n):checks.append(n);assert v,n
plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':str(i),'mutation_expected':True} for i in range(4)],'execution_authorized':False}
impact={'analysis_id':'i','affected_path_count':10,'candidate_test_count':4,'ui_impact_predicted':True}
with tempfile.TemporaryDirectory() as td:
 r=assess_plan_risk(plan,impact_analysis=impact,runtime_root=td)['risk_sensitive_planning'];req(r['risk_tier'] in {'high','critical'},'scaled');req(r['required_verification_breadth']!='focused_verification','broader_verification')
 chat=process_ordinary_chat_development_turn('show risk-sensitive planning',project_state={'constructed_plan':plan,'impact_analysis':impact},runtime_root=td);req(chat.get('active') and chat.get('risk_sensitive_planning',{}).get('assessment_id'),'ordinary_route');req(not chat.get('planning_execution_authorized'),'ordinary_no_authority')
print(json.dumps({'suite':'v1326.3-5-risk-sensitive-planning','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
