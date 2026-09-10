from __future__ import annotations
"""v2583 bind explicit follow-up corrections to prior minimized retrieval evidence."""
from typing import Any, Mapping
try:
    from memory_retrieval_outcome_v2579 import build_memory_retrieval_outcome
    from memory_retrieval_outcome_history_v2580 import append_memory_retrieval_outcome
except ImportError:
    from memory_retrieval_outcome_v2579 import build_memory_retrieval_outcome
    from memory_retrieval_outcome_history_v2580 import append_memory_retrieval_outcome
CONTRACT_VERSION='v2583.0'

def learn_from_followup_correction(prior_observability:Mapping[str,Any], current_learning:Mapping[str,Any], *, runtime_root=None)->dict[str,Any]:
    prior_present=bool(prior_observability.get('present'))
    prior_feedback=prior_observability.get('feedback') if isinstance(prior_observability.get('feedback'),Mapping) else {}
    op_ref=str(prior_observability.get('operation_ref_digest') or '')
    candidate=current_learning.get('candidate') if isinstance(current_learning.get('candidate'),Mapping) else {}
    candidate_type=str(candidate.get('candidate_type') or 'none')
    explicit_negative=candidate_type in {'correction','retraction'}
    if not prior_present or len(op_ref)!=64 or not explicit_negative:
        return {'ok':True,'contract_version':CONTRACT_VERSION,'evidence_recorded':False,'reason':'no_explicit_followup_correction' if not explicit_negative else 'no_prior_retrieval_evidence','memory_mutated':False,'retrieval_policy_mutated':False,'authority_granted':False}
    outcome=build_memory_retrieval_outcome(prior_feedback,turn_completed=True,correction_detected=candidate_type=='correction',contradiction_detected=candidate_type=='retraction')
    receipt=append_memory_retrieval_outcome(outcome,operation_ref_digest=op_ref,runtime_root=runtime_root)
    return {'ok':True,'contract_version':CONTRACT_VERSION,'evidence_recorded':True,'outcome_disposition':outcome['outcome_disposition'],'history_digest':receipt['history_digest'],'raw_memory_text_stored':False,'raw_correction_text_stored':False,'memory_mutated':False,'retrieval_policy_mutated':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','learn_from_followup_correction']
