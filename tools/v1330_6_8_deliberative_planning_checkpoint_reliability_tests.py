from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from deliberative_planning_integration import *
from goal_representation import create_goal
from project_evidence_store import atomic_json,evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
pu={'workspace_digest':'a'*64,'source_manifest_digest':'b'*64,'manifest_consistent':True};g=create_goal(outcome='feature',acceptance_criteria=['pass'])
with tempfile.TemporaryDirectory() as td:
 tie=build_deliberative_planning_checkpoint(g,pu,decision_context={'risk_level':'medium','tradeoffs_matter':True},runtime_root=td);req(not tie['ok'] and tie['status']=='tradeoff_tie_requires_explicit_planning_choice','tie_not_forced')
 r=build_deliberative_planning_checkpoint(g,pu,decision_context={'risk_level':'low','reversible':True},boundary_conflict=True,runtime_root=td)['deliberative_planning'];req(r['stop_required'] and not r['planning_chain_ready'],'faithful_stop');req('boundary_conflict' in r['stop_escalation']['reason_codes'],'stop_reason')
 raw=load_deliberative_planning_checkpoint(r['checkpoint_id'],runtime_root=td,include_private=True);raw['planning_chain_ready']=True;atomic_json(evidence_root('deliberative_planning_checkpoint',td)/'records'/f"{r['checkpoint_id']}.json",raw);req(load_deliberative_planning_checkpoint(r['checkpoint_id'],runtime_root=td)=={},'tamper_rejected')
 print(json.dumps({'suite':'v1330.6-8-deliberative-planning-checkpoint','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
