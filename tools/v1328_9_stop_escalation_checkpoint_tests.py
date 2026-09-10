from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from planning_stop_escalation import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:r=evaluate_stop_escalation(failure_count=3,runtime_root=td)['stop_escalation'];req(r['stop_required'],'checkpoint');req(not r['automatic_retry_allowed'] and not r['automatic_resume_allowed'] and not r['planning_execution_authorized'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1328,9),'metadata');req(any(v=='1328.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1328.9') or ('v1329' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1328.9-stop-escalation-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
