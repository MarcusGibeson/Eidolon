from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_lifecycle_reconciliation_v2519 import reconcile_capability_lifecycle
c=[]
def req(v,n):c.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
e={'envelope_digest':d('env'),'invocation_id':'i'}
r={'receipt_digest':d('r'),'envelope_digest':e['envelope_digest'],'status':'succeeded','result_digest':d('out'),'side_effect_performed':False,'exactly_once_consumed':True}
x=reconcile_capability_lifecycle(envelope=e,result_receipts=[r,r]);req(x['status']=='succeeded' and x['unique_result_receipt_count']==1,'duplicate_receipt_replay_safe');req(x['replay_safe'] and x['exactly_once_consumed'],'exactly_once_preserved')
r2=dict(r,receipt_digest=d('r2'),status='failed');y=reconcile_capability_lifecycle(envelope=e,result_receipts=[r,r2]);req(y['conflicting_results'] and y['manual_review_required'],'conflict_requires_review')
ctrl={'control_request_digest':d('c'),'envelope_digest':e['envelope_digest'],'request_ready':True,'control_performed':False,'control':'rollback'};z=reconcile_capability_lifecycle(envelope=e,result_receipts=[r],control_requests=[ctrl]);req(z['pending_controls']==['rollback'] and not z['control_performed_by_reconciliation'],'control_visible_not_executed')
print({'ok':True,'checkpoint_version':'2519.9','passed':len(c),'total':len(c),'checks':c})
