from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from candidate_approaches import *
from goal_representation import create_goal
checks=[]
def req(v,n): checks.append(n); assert v,n
PU={'workspace_digest':'a'*64,'source_manifest_digest':'b'*64,'manifest_consistent':True}
g=create_goal(outcome='repair bounded defect',acceptance_criteria=['focused test passes'])
with tempfile.TemporaryDirectory() as td:
    r=build_candidate_approaches(g,PU,decision_context={'tradeoffs_matter':True,'risk_level':'medium'},runtime_root=td)['candidate_approaches']
    req(CONTRACT_VERSION=='v1321.8','contract')
    req(r['tradeoffs_matter'] and r['approach_count']>=2 and r['selection_deferred'],'multiple_when_tradeoffs')
    req(not r['raw_goal_content_persisted'],'content_minimized')
    req(all(not a['executed'] for a in r['approaches']),'nonexecuting')
    t=build_candidate_approaches(g,PU,decision_context={'reversible':True,'risk_level':'low','blast_radius':5},runtime_root=td)['candidate_approaches']
    req(t['collapsed_trivial_choice'] and t['approach_count']==1 and not t['selection_deferred'],'trivial_collapsed')
    req(not t['planning_execution_authorized'] and not t['approval_consumed'],'authority_denied')
print(json.dumps({'suite':'v1321.0-2-candidate-approaches','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
