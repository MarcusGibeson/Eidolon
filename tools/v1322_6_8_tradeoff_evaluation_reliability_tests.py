from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from tradeoff_evaluation import *
from project_evidence_store import evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
C={'approach_set_id':'a','goal_digest':'g','workspace_digest':'w','source_manifest_digest':'m','approaches':[{'approach_id':'1','approach_code':'x'},{'approach_id':'2','approach_code':'y'}]}
with tempfile.TemporaryDirectory() as td:
 r=evaluate_tradeoffs(C,evidence_by_approach={'1':{'correctness':50},'2':{'correctness':50}},runtime_root=td)['tradeoff_evaluation'];req(r['tie'] and not r['recommended_approach_id'],'tie_preserved')
 req(r['all_criteria_unverified'] is False,'asserted_signal_not_all_unknown')
 eid=r['evaluation_id'];p=evidence_root('tradeoff_evaluation',td)/'records'/f'{eid}.json';o=json.loads(p.read_text());o['tie']=False;p.write_text(json.dumps(o));req(load_tradeoff_evaluation(eid,runtime_root=td)=={},'tamper_rejected')
 try:evaluate_tradeoffs({'approaches':[]},runtime_root=td);ok=False
 except ValueError:ok=True
 req(ok,'empty_rejected')
print(json.dumps({'suite':'v1322.6-8-tradeoff-evaluation','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
