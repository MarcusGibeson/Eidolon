from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from candidate_approaches import *
from goal_representation import create_goal
from release_authority import WORKING_SOURCE_VERSION,PREVIOUS_WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT,CHECKPOINT_HISTORY
checks=[]
def req(v,n): checks.append(n); assert v,n
PU={'workspace_digest':'2'*64,'source_manifest_digest':'3'*64,'manifest_consistent':True};g=create_goal(outcome='bounded change')
with tempfile.TemporaryDirectory() as td:
    p=build_candidate_approaches(g,PU,decision_context={'tradeoffs_matter':True},runtime_root=td)['candidate_approaches']
    req(p['approach_count']>=2 and p['selection_deferred'],'checkpoint_behavior')
    req(not p['action_executed'] and not p['project_mutation_authorized'] and not p['standing_authority_granted'],'governance')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.'))>=(1321,9),'metadata_version')
req(any(v=='1321.9' and title=='Candidate Approaches' for v,title in CHECKPOINT_HISTORY),'history')
req(bool(NEXT_BOUNDED_UNIT),'next_named')
print(json.dumps({'suite':'v1321.9-candidate-approaches-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
