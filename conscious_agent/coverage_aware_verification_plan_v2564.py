from __future__ import annotations
"""v2564 coverage-aware advisory wrapper for tiered verification planning."""
from pathlib import Path
from typing import Any, Sequence
import hashlib,json
from tiered_verification_runtime_v2541 import build_tiered_verification_plan
from verification_coverage_v2561 import assess_verification_coverage
from verification_blind_spots_v2562 import identify_verification_blind_spots
from verification_confidence_advisory_v2563 import build_verification_confidence_advisory
CONTRACT_VERSION='v2564.0'
AUTHORITY={'test_execution_authorized':False,'required_test_waiver_authorized':False,'test_suppression_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_coverage_aware_verification_plan(source_root:str|Path, changed_paths:Sequence[str])->dict[str,Any]:
    plan=build_tiered_verification_plan(source_root,changed_paths)
    coverage=assess_verification_coverage(source_root,changed_paths,plan)
    blind=identify_verification_blind_spots(coverage)
    advisory=build_verification_confidence_advisory(coverage,blind)
    out={'ok':True,'contract_version':CONTRACT_VERSION,'plan':plan,'coverage':coverage,'blind_spots':blind,'advisory':advisory,'selected_tests_modified':False,'tier1_tests':list(plan['tiers']['1']['tests']),'tier2_tests':list(plan['tiers']['2']['tests']),'runs_commands':False,**AUTHORITY};out['record_digest']=_digest({'plan':plan.get('plan_digest'),'coverage':coverage.get('coverage_digest'),'blind':blind.get('blind_spot_digest'),'advisory':advisory.get('advisory_digest')});return out
__all__=['CONTRACT_VERSION','build_coverage_aware_verification_plan']
