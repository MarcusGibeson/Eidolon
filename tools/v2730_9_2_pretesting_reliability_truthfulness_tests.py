from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT/'conscious_agent', ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'

checks=[]
def require(v,n):
    if not v: raise AssertionError(n)
    checks.append(n)

from response_grounding_output_audit_v2683 import audit_response_grounding_output
from response_grounding_repair_candidate_v2687 import build_response_grounding_repair_candidate
from response_grounding_repair_review_v2688 import build_response_grounding_repair_review
from response_grounding_repair_execution_v2730_9_2 import authorize_and_execute_response_grounding_repair
from memory_retrieval_policy_review_v2585 import build_memory_retrieval_policy_review_packet
from memory_retrieval_policy_execution_v2730_9_2 import build_memory_retrieval_policy_candidate, authorize_and_apply_memory_retrieval_policy, authorize_and_rollback_memory_retrieval_policy, load_memory_retrieval_policy
from precision_memory_retrieval_v2569 import refine_memory_retrieval
from isolated_coding_execution import _relevant_source_excerpt
from collections import Counter

policy={'personal_memory_reference_permitted':False,'policy_digest':'a'*64}
cal={'must_not_claim_execution_without_receipt':True,'calibration_digest':'b'*64}
for phrase in ['I deleted the file.','I have deleted the file.','I\'ve already updated it.','The file has been removed.','It\'s been sent.']:
    a=audit_response_grounding_output(phrase,policy,cal)
    require('execution_claim_without_authoritative_evidence_shape' in a['concerns'], 'execution_detector_'+str(len(checks)))
for phrase in ['I remember you prefer short answers.','I recall that preference.','You\'ve told me that before.','We\'ve discussed that before.']:
    a=audit_response_grounding_output(phrase,policy,cal)
    require('unsupported_personal_memory_claim_shape' in a['concerns'], 'memory_detector_'+str(len(checks)))

text='I have deleted the file. The valid part of the answer is 42.'
a=audit_response_grounding_output(text,policy,cal)
c=build_response_grounding_repair_candidate(a,policy,cal); r=build_response_grounding_repair_review(c)
blocked=authorize_and_execute_response_grounding_repair(text,audit=a,candidate=c,review=r,policy=policy,calibration=cal,operator_confirmation=False)
require(not blocked['ok'] and blocked['status']=='explicit_operator_confirmation_required','repair_requires_operator_confirmation')
executed=authorize_and_execute_response_grounding_repair(text,audit=a,candidate=c,review=r,policy=policy,calibration=cal,operator_confirmation=True)
require(executed['ok'] and executed['post_audit']['ok'],'repair_executes_and_reaudits')
require('42' in executed['repaired_response'],'repair_preserves_valid_content')
require('authoritative execution evidence' in executed['repaired_response'],'repair_expresses_uncertainty')
require(not executed['receipt']['source_mutation_allowed'] and not executed['receipt']['authority_expanded'],'repair_does_not_expand_authority')
stale=dict(r); stale['candidate_digest']='0'*64
require(not authorize_and_execute_response_grounding_repair(text,audit=a,candidate=c,review=stale,policy=policy,calibration=cal,operator_confirmation=True)['ok'],'repair_rejects_stale_review')

with tempfile.TemporaryDirectory(prefix='eidolon-v2730-9-2-policy-') as td:
    obs={'profiles':[{'history_label':'adverse_history','retrieval_state':'weak_vague_context','count':8,'negative':3,'corrections':2}]}
    review=build_memory_retrieval_policy_review_packet(obs)
    cand=build_memory_retrieval_policy_candidate(review,runtime_root=td)
    before=load_memory_retrieval_policy(td)
    require(before['fallback_selected_limit']==4,'memory_policy_default_loaded')
    require(not authorize_and_apply_memory_retrieval_policy(cand,operator_confirmation=False,runtime_root=td)['ok'],'memory_policy_apply_requires_confirmation')
    applied=authorize_and_apply_memory_retrieval_policy(cand,operator_confirmation=True,runtime_root=td)
    require(applied['ok'] and applied['policy']['fallback_selected_limit']==3,'memory_policy_apply_changes_bounded_policy')
    os.environ['EIDOLON_DATA_DIR']=td
    base={'selected_memory_records':[{'id':str(i),'content':f'memory {i}'} for i in range(6)],'decisions':[{'selected':True,'reason':'bounded_context'} for _ in range(6)]}
    refined=refine_memory_retrieval(base)
    require(len(refined['selected_memory_records'])==3 and refined['precision_diagnostics']['selection_limit']==3,'applied_policy_changes_actual_retrieval')
    rolled=authorize_and_rollback_memory_retrieval_policy(applied['receipt']['receipt_id'],operator_confirmation=True,runtime_root=td)
    require(rolled['ok'] and rolled['restored_policy']['fallback_selected_limit']==4,'memory_policy_rollback_restores_exact_prior')
    require(load_memory_retrieval_policy(td)['fallback_selected_limit']==4,'memory_policy_rollback_persisted')
    os.environ.pop('EIDOLON_DATA_DIR',None)

longline='TARGET_SYMBOL '+('x'*30000)+'\nsecond line\n'
excerpt,start,end=_relevant_source_excerpt(longline,4096,Counter({'TARGET_SYMBOL':10}))
require(len(excerpt.encode('utf-8'))<=4096,'long_line_excerpt_respects_byte_budget')
require('truncated to provider byte budget' in excerpt and start==end==1,'long_line_excerpt_marks_truncation')

sm=(ROOT/'conscious_agent/self_maintenance.py').read_text(encoding='utf-8')
require('.write_text(' not in sm,'self_maintenance_direct_write_text_removed')
require(sm.count('write_text_atomic(')>=130,'self_maintenance_durable_text_uses_atomic_replace')
require('append_text_atomic(' in sm,'self_maintenance_read_modify_write_append_serialized')

print(json.dumps({'suite':'v2730.9.2-pretesting-reliability-truthfulness','ok':True,'passed':len(checks),'failed':0,'checks':checks,'authority_expanded':False,'release_authorized':False},sort_keys=True))
