from __future__ import annotations
import os,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from conversation_operations import *
from conversation_sessions import create_conversation_session,append_conversation_turn,load_conversation_session
from operation_identity_contract import *
C=[]
def req(n,c,d=''): C.append((n,bool(c),d)); (_ for _ in ()).throw(AssertionError(f'{n}: {d}')) if not c else None

def main():
 s=create_conversation_session('exactly once fixture',source='fixture'); sid=s['id']; key=new_client_acceptance_key(); proposed=[new_conversation_operation_id() for _ in range(50)]
 results=[]; lock=threading.Lock()
 def worker(op):
  r=claim_operation_acceptance(sid,key,op)
  with lock: results.append(r)
 th=[threading.Thread(target=worker,args=(op,)) for op in proposed]
 for x in th:x.start()
 for x in th:x.join()
 winners=[r for r in results if r['claimed']]
 req('0072-rapid-acceptance-one-winner',len(winners)==1,len(winners)); op=winners[0]['operation_id']
 req('0078-race-converges',all(r['operation_id']==op for r in results),{r['operation_id'] for r in results})
 marker=create_operation_marker(op,sid,acceptance_key=key)
 projections=[public_operation_identity(marker,surface=x) for x in ('browser','desktop','api','runtime')]
 req('0071-cross-surface-identity',all(operation_identity_equivalent(projections[0],p) for p in projections[1:]))
 req('0071-no-raw-acceptance-key',all(key not in str(p.public_summary()) for p in projections))
 turn1=append_conversation_turn(sid,turn_id=op,user_message='fixture user',assistant_response='fixture reply',completion_state='completed',success=True)
 turn2=append_conversation_turn(sid,turn_id=op,user_message='different should not append',assistant_response='different',completion_state='completed',success=True)
 loaded=load_conversation_session(sid,include_turns=True)
 req('0073-turn-dedup',turn1==turn2 and len([t for t in loaded['turns'] if t['id']==op])==1)
 done=finalize_operation_marker(op,completion_state='completed',success=True,final_session_turn_recorded=True)
 late=finalize_operation_marker(op,completion_state='failed',success=False,failure_category='late_fixture')
 req('0074-late-result-no-detached-state',late['public_state']=='completed' and late['late_result_ignored_count']==1,late)
 # cancellation persists across disconnect/reload and never implies automatic retry
 key2=new_client_acceptance_key(); op2=new_conversation_operation_id(); claim_operation_acceptance(sid,key2,op2); create_operation_marker(op2,sid,acceptance_key=key2)
 request_operation_cancellation(op2); mark_operation_client_disconnected(op2); re=load_operation_marker(op2)
 req('0075-cancel-persists',re['cancellation_requested'] and re['client_disconnected'],re)
 rp=public_operation_identity(re,surface='desktop')
 req('0076-stale-owner-reconcile-only',rp.recovery_mode=='reconcile_only' and not rp.automatic_reexecution_allowed,rp)
 uncertain=finalize_operation_marker(op2,completion_state='uncertain',success=False)
 req('0077-uncertain-no-auto-reexecute',recovery_mode_for_marker(uncertain)=='explicit_retry_required')
 # 100 repeated accepts after restart/reconnect still map to the first operation.
 ids={operation_id_for_acceptance_key(sid,key)}
 for _ in range(100): ids.add(claim_operation_acceptance(sid,key,new_conversation_operation_id())['operation_id'])
 req('0079-repeated-send-stress',ids=={op},ids)
 pub=projections[0].public_summary(); req('0079-content-free-counts',pub['content_free'] and not pub['automatic_reexecution_allowed'],pub)
 print(f'v1489.0071-.0080 exactly-once/recovery: {len(C)}/{len(C)} checks passed')
 for n,_,__ in C: print('  PASS',n)
if __name__=='__main__': main()
