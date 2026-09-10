from __future__ import annotations
"""Integrated v1489 completion-benchmark state for Bundle 20.

The browser may prepare and verify a review candidate, but Windows workflow
review and operator-scored unscripted conversation remain external gates.
"""
from typing import Any,Iterable,Mapping
import hashlib,json

FROZEN_FEATURE_DOMAINS=(
 'truthful_memory','natural_conversation','mixed_command_routing','action_receipts',
 'exactly_once_recovery','response_time','provider_reliability','desktop_chat',
 'accessibility','governed_initiative','reasoning_planning','practical_coding',
 'supervised_self_development','security_privacy_authority','verification_evidence',
 'installation_upgrade_rollback',
)

def feature_freeze(requested_domain:str)->dict[str,Any]:
    token=str(requested_domain or '').strip().lower().replace(' ','_')
    allowed=token in FROZEN_FEATURE_DOMAINS
    return {'requested_domain':token[:80],'within_frozen_v1489_scope':allowed,'unrelated_addition_rejected':not allowed,'content_free':True}

def external_review_gates(*,windows_workflow_review:bool=False,operator_unscripted_trial:bool=False)->dict[str,Any]:
    return {
      'windows_workflow_review':bool(windows_workflow_review),'operator_unscripted_trial':bool(operator_unscripted_trial),
      'browser_completion_candidate_allowed':True,'promotion_allowed':bool(windows_workflow_review and operator_unscripted_trial),
      'certification_allowed':False,'installation_allowed':False,'operator_review_required':True,'content_free':True,
    }

def integrated_evidence_ledger(receipts:Iterable[Mapping[str,Any]],*,external_gates:Mapping[str,Any])->dict[str,Any]:
    rows=list(receipts);passed=sum(int(r.get('passed') or 0) for r in rows);failed=sum(int(r.get('failed') or 0) for r in rows)
    payload={'suite_count':len(rows),'checks_passed':passed,'checks_failed':failed,'windows_review_complete':bool(external_gates.get('windows_workflow_review')),'operator_trial_complete':bool(external_gates.get('operator_unscripted_trial')),'promotion_allowed':False,'content_free':True}
    payload['ledger_digest']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest();return payload

def coding_benchmark_result(*,inspected:bool,implemented:bool,tested:bool,unrelated_preserved:bool,auto_applied:bool=False)->dict[str,Any]:
    ok=bool(inspected and implemented and tested and unrelated_preserved and not auto_applied)
    return {'ok':ok,'inspected_first':bool(inspected),'implemented':bool(implemented),'tested':bool(tested),'unrelated_changes_preserved':bool(unrelated_preserved),'auto_applied':bool(auto_applied),'content_free':True}

def repair_decision(*,concrete_defects:Iterable[str])->dict[str,Any]:
    defects=[str(x)[:100] for x in concrete_defects if str(x).strip()]
    return {'concrete_defect_count':len(defects),'repair_only_if_concrete':True,'unrelated_feature_work_allowed':False,'rerun_affected_verification':bool(defects),'content_free':True}
