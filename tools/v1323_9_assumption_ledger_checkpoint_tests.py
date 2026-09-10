from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from assumption_ledger import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=create_assumption_ledger(goal_digest='g',workspace_digest='w',source_manifest_digest='m',assumptions=[{'code':'x','statement':'a','validation_method':'focused_test'}],runtime_root=td)['assumption_ledger'];req(r['assumption_count']==1,'checkpoint');req(not r['planning_execution_authorized'] and not r['approval_consumed'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1323,9),'metadata');req(any(v=='1323.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1323.9') or ('v1324' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1323.9-assumption-ledger-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
