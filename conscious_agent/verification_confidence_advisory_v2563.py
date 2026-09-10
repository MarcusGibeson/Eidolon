from __future__ import annotations
"""v2563 advisory confidence routing from coverage/blind-spot evidence."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2563.0'
AUTHORITY={'required_test_waiver_authorized':False,'test_suppression_authorized':False,'release_authorized':False,'certification_authorized':False,'automatic_test_creation_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_verification_confidence_advisory(coverage:Mapping[str,Any], blind_spots:Mapping[str,Any])->dict[str,Any]:
    if str(coverage.get('contract_version') or '')!='v2561.0' or str(blind_spots.get('contract_version') or '')!='v2562.0': raise ValueError('coverage_and_blind_spot_contracts_required')
    high=sum(r.get('severity')=='high' for r in blind_spots.get('blind_spots') or [])
    medium=sum(r.get('severity')=='medium' for r in blind_spots.get('blind_spots') or [])
    if high: recommendation='focused_coverage_required_before_fast_confidence'
    elif medium: recommendation='tier2_integration_required_and_direct_coverage_recommended'
    else: recommendation='fast_verification_plan_has_structural_coverage_support'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'confidence':coverage.get('confidence'),'high_blind_spot_count':high,'medium_blind_spot_count':medium,'recommendation':recommendation,'tier1_tests_preserved':True,'tier2_not_waived':True,'release_certification_still_required':True,**AUTHORITY};out['advisory_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_verification_confidence_advisory']
