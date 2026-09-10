from __future__ import annotations

"""v2544 minimized verification feedback projection.

Consumes content-free tiered-verification receipts and emits bounded structural
feedback suitable for cognition, UI activity, and developer evidence. It does
not execute tests, expose stdout/stderr, certify a release, or grant authority.
"""

import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION='v2544.0'
AUTHORITY={
 'source_mutation_authorized':False,'project_mutation_authorized':False,
 'provider_contact_authorized':False,'network_authorized':False,
 'release_authorized':False,'certification_authorized':False,
 'approval_granted':False,'independent_authority_granted':False,
}

def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()

def build_verification_feedback(receipt: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(receipt,Mapping): raise ValueError('receipt_mapping_required')
    status=str(receipt.get('status') or '').strip()
    if not status.startswith('tiered_verification_'): raise ValueError('tiered_receipt_required')
    rows=list(receipt.get('receipts') or [])
    if not rows: raise ValueError('tier_receipts_required')
    compact=[]; failures=[]; elapsed=0.0
    for row in rows[:3]:
        if not isinstance(row,Mapping): continue
        tier=int(row.get('tier',-1)); ok=bool(row.get('ok'))
        tests=[]
        for t in list(row.get('tests') or [])[:8]:
            if not isinstance(t,Mapping): continue
            rel=str(t.get('test') or '')[:200]
            tr={'test':rel,'ok':bool(t.get('ok')),'status':str(t.get('status') or '')[:48],'timed_out':bool(t.get('timed_out'))}
            if len(str(t.get('stdout_sha256') or ''))==64: tr['stdout_sha256']=str(t.get('stdout_sha256'))
            if len(str(t.get('stderr_sha256') or ''))==64: tr['stderr_sha256']=str(t.get('stderr_sha256'))
            tests.append(tr)
            if not tr['ok']: failures.append({'tier':tier,**tr})
            try: elapsed += float(t.get('elapsed_seconds') or 0.0)
            except Exception: pass
        compact.append({'tier':tier,'ok':ok,'status':str(row.get('status') or '')[:64],'test_count':int(row.get('test_count') or 0),'tests':tests})
    ok=bool(receipt.get('ok')) and not failures
    stopped=int(receipt.get('stopped_after_tier', rows[-1].get('tier',0)))
    if not ok: recommendation='repair_before_further_verification'
    elif stopped < 2: recommendation=f'eligible_for_tier_{stopped+1}_confidence_check'
    else: recommendation='fast_confidence_complete_release_certification_still_required'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'verification_ok':ok,'stopped_after_tier':stopped,
         'recommendation':recommendation,'failure_count':len(failures),'failures':failures[:8],
         'tier_summaries':compact,'measured_test_seconds':round(elapsed,3),'raw_output_stored':False,
         'hidden_reasoning_exposed':False,'release_certified':False,**AUTHORITY}
    out['feedback_digest']=_digest(out); return out

def project_verification_activity(feedback: Mapping[str,Any]) -> dict[str,Any]:
    if str(feedback.get('contract_version') or '') != CONTRACT_VERSION: raise ValueError('feedback_contract_required')
    ok=bool(feedback.get('verification_ok')); tier=int(feedback.get('stopped_after_tier') or 0)
    summary=(f'Fast verification through Tier {tier} passed.' if ok else f'Fast verification stopped at Tier {tier} with a failing check.')
    return {'kind':'verification','status':'passed' if ok else 'failed','tier':tier,'summary':summary,
            'feedback_digest':str(feedback.get('feedback_digest') or ''),'hidden_reasoning_exposed':False,'raw_content_stored':False,
            'authority_granted':False,'release_certified':False,**AUTHORITY}

__all__=['CONTRACT_VERSION','build_verification_feedback','project_verification_activity']
