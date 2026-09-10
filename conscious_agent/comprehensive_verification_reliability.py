from __future__ import annotations
"""v1295.6-v1295.8 false-pass and evidence-integrity hardening."""
from typing import Any,Iterable,Mapping
from comprehensive_verification_foundations import DENIED_AUTHORITY,EVIDENCE_DOMAINS,valid_digest
CONTRACT_VERSION='v1295.8'
def assess_comprehensive_verification_reliability(results:Iterable[Mapping[str,Any]])->dict[str,Any]:
 violations=[];count=0
 for r in results:
  count+=1;tag=f'verification-{count}';states=dict(r.get('domain_states') or {})
  if any(bool(r.get(k)) for k in DENIED_AUTHORITY):violations.append(f'{tag}:authority_expansion')
  if r.get('ok') and r.get('status')!='comprehensive_verification_passed':violations.append(f'{tag}:ok_status_mismatch')
  if r.get('ok') and not r.get('native_windows_passed'):violations.append(f'{tag}:false_pass_without_native_windows')
  if r.get('ok') and any(states.get(d)!='passed' for d in EVIDENCE_DOMAINS):violations.append(f'{tag}:false_pass_missing_or_nonpassing_domain')
  if r.get('missing_native_is_pass') or r.get('missing_evidence_is_pass'):violations.append(f'{tag}:missing_evidence_promoted_to_pass')
  if r.get('verification_is_release_authority'):violations.append(f'{tag}:verification_conflated_with_release_authority')
  if r.get('verification_digest') and not valid_digest(r.get('verification_digest')):violations.append(f'{tag}:invalid_verification_digest')
  if r.get('integrity_violations') and r.get('ok'):violations.append(f'{tag}:integrity_violation_ignored')
 return {'contract_version':CONTRACT_VERSION,'ok':not violations,'status':'comprehensive_verification_reliability_clear' if not violations else 'comprehensive_verification_reliability_blocked','result_count':count,'violations':violations,'native_windows_execution_still_external_to_this_read_only_model':True,'content_free':True,'read_only':True,**DENIED_AUTHORITY}
