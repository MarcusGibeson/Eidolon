from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from candidate_approaches import *
from goal_representation import create_goal
from project_evidence_store import evidence_root
checks=[]
def req(v,n): checks.append(n); assert v,n
PU={'workspace_digest':'f'*64,'source_manifest_digest':'1'*64,'manifest_consistent':True};g=create_goal(outcome='choose implementation')
with tempfile.TemporaryDirectory() as td:
    r=build_candidate_approaches(g,PU,decision_context={'tradeoffs_matter':True},explicit_options=[{'code':'one'},{'code':'one'},{'code':'two','viable':False}],runtime_root=td)['candidate_approaches']
    req(r['approach_count']>=2,'consequential_singleton_gets_fallback')
    req(len({x['approach_code'] for x in r['approaches']})==r['approach_count'],'duplicates_removed')
    path=evidence_root('candidate_approaches',td)/'records'/f"{r['approach_set_id']}.json"; obj=json.loads(path.read_text());obj['approach_count']=99;path.write_text(json.dumps(obj))
    req(load_candidate_approaches(r['approach_set_id'],runtime_root=td)=={},'tamper_rejected')
    try: build_candidate_approaches(g,{**PU,'manifest_consistent':False},runtime_root=td); ok=False
    except ValueError: ok=True
    req(ok,'conflicted_manifest_rejected')
print(json.dumps({'suite':'v1321.6-8-candidate-approaches','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
