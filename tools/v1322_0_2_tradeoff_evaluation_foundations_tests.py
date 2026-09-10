from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from tradeoff_evaluation import *
checks=[]
def req(v,n):checks.append(n);assert v,n
C={'approach_set_id':'a','goal_digest':'g','workspace_digest':'w','source_manifest_digest':'m','approaches':[{'approach_id':'1','approach_code':'minimal_targeted_change'},{'approach_id':'2','approach_code':'boundary_refactor'}]}
with tempfile.TemporaryDirectory() as td:
 e={'1':{'correctness':{'score':90,'confidence':1,'evidence_digests':['a'*64]}},'2':{'correctness':{'score':55,'confidence':1,'evidence_digests':['b'*64]}}}
 r=evaluate_tradeoffs(C,evidence_by_approach=e,runtime_root=td)['tradeoff_evaluation']
 req(CONTRACT_VERSION=='v1322.8','contract');req(tuple(CRITERIA)==('correctness','complexity','compatibility','reversibility','performance','privacy','maintenance'),'criteria')
 req(r['recommended_approach_id']=='1' and not r['tie'],'unique_recommendation');req(not r['recommendation_is_authority'],'recommendation_not_authority')
 req(not r['planning_execution_authorized'],'no_execution')
print(json.dumps({'suite':'v1322.0-2-tradeoff-evaluation','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
