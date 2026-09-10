from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from assumption_ledger import *
from project_evidence_store import evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 try:create_assumption_ledger(goal_digest='g',workspace_digest='w',source_manifest_digest='m',assumptions=[{'code':'x','statement':'a'},{'code':'x','statement':'b'}],runtime_root=td);ok=False
 except ValueError:ok=True
 req(ok,'duplicate_rejected');r=create_assumption_ledger(goal_digest='g',workspace_digest='w',source_manifest_digest='m',assumptions=[{'code':'x','statement':'a'}],runtime_root=td)['assumption_ledger'];p=evidence_root('assumption_ledger',td)/'records'/f"{r['ledger_id']}.json";o=json.loads(p.read_text());o['assumption_count']=9;p.write_text(json.dumps(o));req(load_assumption_ledger(r['ledger_id'],runtime_root=td)=={},'tamper_rejected')
 try:revise_assumption({'assumptions':[]},assumption_code='x',outcome='validated');ok=False
 except ValueError:ok=True
 req(ok,'unknown_revision_rejected')
print(json.dumps({'suite':'v1323.6-8-assumption-ledger','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
