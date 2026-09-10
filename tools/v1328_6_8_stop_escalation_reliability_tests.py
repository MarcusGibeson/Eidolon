from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from planning_stop_escalation import *
from project_evidence_store import atomic_json,evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=evaluate_stop_escalation(unsafe_side_effect=True,risk_sensitive_planning={'assessment_id':'r','protected_surface':True,'planning_progress_allowed':False},runtime_root=td)['stop_escalation'];req(r['stop_required'] and {'unsafe_side_effect','protected_surface_block'}.issubset(r['reason_codes']),'unsafe_protected');req(not r['automatic_resume_allowed'],'no_auto_resume')
 raw=load_stop_escalation(r['decision_id'],runtime_root=td,include_private=True);raw['stop_required']=False;atomic_json(evidence_root('planning_stop_escalation',td)/'records'/f"{r['decision_id']}.json",raw);req(load_stop_escalation(r['decision_id'],runtime_root=td)=={},'tamper_rejected');req(len(r['actionable_choice_codes'])==len(set(r['actionable_choice_codes'])),'choices_deduped')
print(json.dumps({'suite':'v1328.6-8-stop-escalation','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
