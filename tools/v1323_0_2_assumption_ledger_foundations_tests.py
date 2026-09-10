from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from assumption_ledger import *
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 r=create_assumption_ledger(goal_digest='g'*64,workspace_digest='w'*64,source_manifest_digest='m'*64,assumptions=[{'code':'api_stable','statement':'API remains compatible','confidence':.6,'evidence_digests':['e'*64],'validation_method':'contract_test','invalidation_conditions':['schema changes']}],runtime_root=td)['assumption_ledger']
 req(CONTRACT_VERSION=='v1323.8','contract');req(r['assumption_count']==1 and r['assumptions'][0]['evidence_count']==1,'recorded');req(r['assumptions'][0]['invalidation_condition_count']==1,'invalidation');req(not r['raw_statement_persisted'],'privacy');req(not r['action_executed'],'nonexecuting')
print(json.dumps({'suite':'v1323.0-2-assumption-ledger','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
