from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from assumption_ledger import *
from goal_representation import create_goal
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n):checks.append(n);assert v,n
PU={'workspace_digest':'a'*64,'source_manifest_digest':'b'*64,'manifest_consistent':True};g=create_goal(outcome='plan change')
with tempfile.TemporaryDirectory() as td:
 r=process_ordinary_chat_development_turn('show assumption ledger',project_state={'planning_goal':g,'project_understanding':PU,'planning_assumptions':[{'code':'tests_cover','statement':'tests cover seam','confidence':.4}]},runtime_root=td);req(r.get('active') and r.get('ok'),'ordinary_route');l=r['assumption_ledger'];private=load_assumption_ledger(l['ledger_id'],runtime_root=td,include_private=True);r2=revise_assumption(private,assumption_code='tests_cover',outcome='validated',evidence_digests=['c'*64],confidence=.9,runtime_root=td)['assumption_ledger'];req(r2['revision_count']==1 and r2['assumptions'][0]['status']=='validated','revision');req(bool(r2['previous_ledger_digest']),'lineage');req(assess_assumption_freshness(r2,source_manifest_digest='d'*64)['status']=='stale','stale')
print(json.dumps({'suite':'v1323.3-5-assumption-ledger','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
