from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from planning_stop_escalation import evaluate_stop_escalation
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=evaluate_stop_escalation(uncertainty={'confidence':20,'epistemic_state':'unverified'},boundary_conflict=True,runtime_root=td)['stop_escalation'];req(set(['material_uncertainty','boundary_conflict']).issubset(r['reason_codes']),'compound');req('request_separate_authority' in r['actionable_choice_codes'],'boundary_choice')
 chat=process_ordinary_chat_development_turn('should planning stop',project_state={'planning_resource_exhausted':True},runtime_root=td);req(chat.get('active') and chat['stop_escalation']['stop_required'],'ordinary_route');req(not chat['stop_escalation']['choice_execution_authorized'],'choice_not_execution')
print(json.dumps({'suite':'v1328.3-5-stop-escalation','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
