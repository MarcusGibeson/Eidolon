from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from tradeoff_evaluation import *
from release_authority import WORKING_SOURCE_VERSION,CHECKPOINT_HISTORY,NEXT_BOUNDED_UNIT
checks=[]
def req(v,n):checks.append(n);assert v,n
C={'approach_set_id':'a','goal_digest':'g','workspace_digest':'w','source_manifest_digest':'m','approaches':[{'approach_id':'1','approach_code':'minimal_targeted_change'},{'approach_id':'2','approach_code':'boundary_refactor'}]}
with tempfile.TemporaryDirectory() as td:
 r=evaluate_tradeoffs(C,runtime_root=td)['tradeoff_evaluation'];req(len(r['approach_scores'])==2,'checkpoint');req(not r['recommendation_is_authority'] and not r['action_executed'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1322,9),'metadata');req(any(v=='1322.9' for v,_ in CHECKPOINT_HISTORY),'history');req((WORKING_SOURCE_VERSION!='1322.9') or ('v1323' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
print(json.dumps({'suite':'v1322.9-tradeoff-evaluation-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
