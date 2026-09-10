from __future__ import annotations
import json,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from structured_action_clarification import build_structured_clarification_request, apply_structured_clarification_answer, build_clarified_proposal_binding
from clarification_continuity import register_clarification,resume_clarification,transition_clarification,inspect_clarification_continuity
checks=[]
def req(v): checks.append(bool(v)); assert v
with tempfile.TemporaryDirectory() as td:
 pth=Path(td)/'clarifications.json'; p=build_natural_language_action_projection('Review a file'); r=build_structured_clarification_request(p)
 reg=register_clarification(pth,r,now=1000); req(reg['ok'] and reg['state']=='pending' and reg['persisted'])
 dup=register_clarification(pth,r,now=1001); req(dup['state']=='duplicate_pending' and not dup['persisted'])
 resumed=resume_clarification(pth,request_digest=r['request_digest'],source_projection_digest=r['source_projection_digest'],source_binding_digest=r['source_binding_digest'],now=1002)
 req(resumed['resumable'] and resumed['requested_fields']==['target_ref']); req(not resumed['answer_stored'] and not resumed['authority_granted'])
 mismatch=resume_clarification(pth,request_digest=r['request_digest'],source_projection_digest='0'*64,source_binding_digest=r['source_binding_digest'],now=1002); req(not mismatch['resumable'] and not mismatch['exact_digest_binding'])
 a=apply_structured_clarification_answer(p,r,{'target_ref':'conscious_agent/memory.py'}); req(a['exact_clarified_binding'])
 b=build_clarified_proposal_binding(p,a,operation_id='review-memory'); req(b['proposal_binding']['proposal_candidate_created'] and not b['proposal_binding']['proposal_persisted'])
 done=transition_clarification(pth,request_digest=r['request_digest'],transition='consumed',now=1003); req(done['ok'] and done['state']=='consumed')
 replay=transition_clarification(pth,request_digest=r['request_digest'],transition='consumed',now=1004); req(not replay['ok'] and replay['duplicate_terminal_transition'])
 noresume=resume_clarification(pth,request_digest=r['request_digest'],source_projection_digest=r['source_projection_digest'],source_binding_digest=r['source_binding_digest'],now=1005); req(not noresume['resumable'] and noresume['state']=='consumed')
 pth2=Path(td)/'clarifications_cancel.json'; register_clarification(pth2,r,now=2000)
 cancel=transition_clarification(pth2,request_digest=r['request_digest'],transition='cancelled',now=2001); req(cancel['ok'] and cancel['state']=='cancelled')
 p3=build_natural_language_action_projection('Inspect your project'); r3=build_structured_clarification_request(p3)
 # may be bound already or unsupported; invalid registration must fail closed
 bad=register_clarification(pth,{'state':'awaiting_structured_answer','request_digest':'bad'},now=3000); req(not bad['ok'])
 pth3=Path(td)/'clarifications_expire.json'; p4=build_natural_language_action_projection('Review a file'); r4=build_structured_clarification_request(p4); register_clarification(pth3,r4,now=0)
 exp=resume_clarification(pth3,request_digest=r4['request_digest'],source_projection_digest=r4['source_projection_digest'],source_binding_digest=r4['source_binding_digest'],now=90000); req(not exp['resumable'] and exp['state']=='expired')
 ins=inspect_clarification_continuity(pth,now=90001); req(ins['record_count']>=1 and not ins['raw_content_exposed'] and not ins['answers_exposed'])
 raw=pth.read_text(); req('conscious_agent/memory.py' not in raw and 'Review a file' not in raw)
 req('approval' not in raw.lower() or 'approval_created' in raw)
 req(len(raw.encode())<16384)
 # malformed recovery
 pth.write_text('{bad'); ins2=inspect_clarification_continuity(pth); req(ins2['record_count']==0)
 # ordinary conversation remains non-action
 q=build_natural_language_action_projection('Do you like the name Eidolon?'); req(q['intent']['category']=='question' and q['clarification_request']['state']=='not_required')
 c=build_natural_language_action_projection('Stop calling me Daddy.'); req(c['intent']['category']=='correction' and c['clarification_request']['state']=='not_required')
 h=build_natural_language_action_projection('What if I said "run diagnostics"?'); req(h['intent']['category']=='question' and not h['intent']['action_intent_present'])
start=time.perf_counter()
with tempfile.TemporaryDirectory() as td:
 pth=Path(td)/'c.json'; p=build_natural_language_action_projection('Review a file'); r=build_structured_clarification_request(p)
 for i in range(100): register_clarification(pth,r,now=i)
req(time.perf_counter()-start<1.5)
print(json.dumps({'ok':True,'suite':'v1176.6-v1176.8-clarification-reliability-conversation-continuity','passed':sum(checks),'total':len(checks)},sort_keys=True))
