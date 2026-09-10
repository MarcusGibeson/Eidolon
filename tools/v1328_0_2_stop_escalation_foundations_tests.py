from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from planning_stop_escalation import *
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=evaluate_stop_escalation(runtime_root=td)['stop_escalation'];req(CONTRACT_VERSION=='v1328.8','contract');req(not r['stop_required'] and r['continue_planning_allowed'],'clean_continue')
 s=evaluate_stop_escalation(failure_count=3,runtime_root=td)['stop_escalation'];req(s['stop_required'] and 'repeated_failure' in s['reason_codes'],'repeat_stop');req('diagnose_root_cause' in s['actionable_choice_codes'],'choices');req(not s['automatic_retry_allowed'] and not s['planning_execution_authorized'],'no_auto_retry')
print(json.dumps({'suite':'v1328.0-2-stop-escalation','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
