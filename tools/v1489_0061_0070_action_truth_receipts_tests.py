from __future__ import annotations
import sys,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from execution_claim_guard import *
C=[]
def req(n,c,d=''): C.append((n,bool(c),d)); (_ for _ in ()).throw(AssertionError(f'{n}: {d}')) if not c else None

def action(status='proposed', aid='act_1', ok=True, attempt=1):
 return {'id':aid,'intent':'run_diagnostics','capability_id':'diagnostics','execution_mode':'read_only','risk_level':'low','status':status,'execution_attempt':attempt,'events':[],'result':({'ok':ok} if status in {'completed','executed','failed'} else {})}

def t():
 missing=action(aid=''); req('0061-no-start-without-id',build_execution_truth_receipt(missing)=={})
 states=['proposed','blocked','running','failed','cancelled','timed_out','completed']
 rendered={}
 for st in states:
  a=action(st,ok=(st=='completed')); r=build_execution_truth_receipt(a); rendered[st]=(r.get('completion_state'),render_receipt_bound_action_response(a,r))
 req('0063-distinct-states',len(set(v[0] for v in rendered.values()))==7,rendered)
 a=action('completed',ok=True,attempt=2); r=build_execution_truth_receipt(a)
 req('0062-success-needs-authoritative-receipt',receipt_allows_success_claim(r,a),r)
 req('0065-summary-bound-digests',bool(public_action_truth_projection(a,r)['action_state_digest']) and bool(public_action_truth_projection(a,r)['receipt_digest']))
 req('0066-attempt-count',public_action_truth_projection(a,r)['execution_attempt']==2)
 req('0067-reconnect-rebuild-stable',build_execution_truth_receipt(a)==r)
 fake='I ran diagnostics and everything is optimal.'
 guarded=enforce_execution_claim_truth(fake,a,None)
 req('0064-no-invented-system-status','do not have a valid execution receipt' in guarded.lower(),guarded)
 req('0068-model-cannot-impersonate',guarded!=fake,guarded)
 tam=copy.deepcopy(r); tam['receipt_digest']='0'*64
 req('0069-tamper-fails',not validate_execution_truth_receipt(tam,a)[0],tam)
 stale=copy.deepcopy(a); stale['execution_attempt']=3
 req('0069-stale-receipt-fails',not validate_execution_truth_receipt(r,stale)[0])
 req('0069-missing-fails',not validate_execution_truth_receipt(None,a)[0])
 req('0069-replay-content-free',public_action_truth_projection(a,r)['content_free'] and not public_action_truth_projection(a,r)['generated_prose_authoritative'])
for _ in range(2): t()
print(f'v1489.0061-.0070 action truth/receipts: {len(C)}/{len(C)} checks passed')
for n,_,__ in C: print('  PASS',n)
