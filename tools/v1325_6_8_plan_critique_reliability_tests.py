from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from plan_critique import *
from project_evidence_store import evidence_root
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory() as td:
 try:critique_plan({},runtime_root=td);ok=False
 except ValueError:ok=True
 req(ok,'missing_plan_rejected');plan={'plan_id':'p','goal_digest':'g','source_manifest_digest':'m','steps':[{'step_code':'x'}],'checkpoint_count':1,'verification_step_count':1,'rollback_step_count':1,'execution_authorized':True};r=critique_plan(plan,runtime_root=td)['plan_critique'];req(any(x['finding_code']=='plan_contains_authority_escalation' and x['blocking'] for x in r['findings']),'authority_escalation_caught');p=evidence_root('plan_critique',td)/'records'/f"{r['critique_id']}.json";o=json.loads(p.read_text());o['blocking_count']=0;p.write_text(json.dumps(o));req(load_plan_critique(r['critique_id'],runtime_root=td)=={},'tamper_rejected')
print(json.dumps({'suite':'v1325.6-8-plan-critique','ok':True,'passed':len(checks),'checks':checks},sort_keys=True))
