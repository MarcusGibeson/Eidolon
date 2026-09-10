from __future__ import annotations

"""v1500 Autonomous Developer benchmark evidence and decision boundary.

The benchmark measures whether the reviewed development pipeline can discover,
compare, plan, edit an isolated workspace, diagnose failures, verify, coordinate
campaign state, and prepare governed review evidence.  It does not install,
promote, certify, contact a provider, or grant independent authority.
"""

import hashlib, json
from typing import Any, Iterable, Mapping

from development_authority import is_hex64, validate_operator_authorization

CONTRACT_VERSION='v1500.0.1'
REQUIRED_CAPABILITIES=(
 'dynamic_discovery_integrity','candidate_quality','durable_backlog','evidence_bound_planning',
 'generalized_isolated_coding','bounded_failure_diagnosis','verification_intelligence',
 'governed_review','continuous_campaign_recovery','windows_protocol_ready',
 'privacy_authority_preserved','exactly_once_preserved',
)


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def capability_receipt(name:str,*,passed:bool,evidence_digest:str,evidence_source:str,executed:bool,notes_class:str='')->dict[str,Any]:
 if name not in REQUIRED_CAPABILITIES:raise ValueError('unknown_v1500_capability')
 if not executed or not is_hex64(evidence_digest) or evidence_source not in {'focused_suite','integrated_benchmark','authority_regression','native_protocol'}:raise ValueError('unsealed_v1500_capability_evidence')
 row={'contract_version':CONTRACT_VERSION,'capability':name,'passed':bool(passed),'executed':True,'evidence_digest':str(evidence_digest).casefold(),'evidence_source':str(evidence_source),'notes_class':str(notes_class or '')[:80],'content_free':True}
 row['receipt_digest']=_digest(row);return row

def build_autonomous_developer_benchmark(receipts:Iterable[Mapping[str,Any]],*,windows_evidence:Mapping[str,Any]|None=None,operator_review_receipt:Mapping[str,Any]|None=None)->dict[str,Any]:
 rows=[dict(r or {}) for r in receipts]
 valid=[]
 for row in rows:
  supplied=str(row.get('receipt_digest') or '');core={k:v for k,v in row.items() if k!='receipt_digest'}
  if is_hex64(supplied) and supplied==_digest(core) and row.get('contract_version')==CONTRACT_VERSION and row.get('executed') is True and is_hex64(row.get('evidence_digest')):valid.append(row)
 names=[str(r.get('capability') or '') for r in valid];duplicates=sorted({name for name in names if names.count(name)>1})
 by={str(r.get('capability') or ''):r for r in valid}
 missing=[name for name in REQUIRED_CAPABILITIES if name not in by]
 failed=[name for name in REQUIRED_CAPABILITIES if name in by and not bool(by[name].get('passed'))]
 passed=len(REQUIRED_CAPABILITIES)-len(missing)-len(failed)
 deterministic_complete=not missing and not failed and not duplicates and len(valid)==len(rows)
 score=round(100.0*passed/len(REQUIRED_CAPABILITIES),1)
 review_ready=deterministic_complete
 deterministic_evidence_digest=_digest({'rows':[(name,str(by.get(name,{}).get('receipt_digest') or '')) for name in REQUIRED_CAPABILITIES],'duplicates':duplicates})
 windows=dict(windows_evidence or {});windows_complete=bool(windows.get('evidence_complete') and is_hex64(windows.get('certification_evidence_digest')) and int(windows.get('invalid_receipt_count') or 0)==0 and not windows.get('duplicate_checks'))
 operator_validation=validate_operator_authorization(operator_review_receipt,stage='operator_review',subject_id='v1500',subject_digest=deterministic_evidence_digest)
 operator_complete=operator_validation['ok']
 result={'contract_version':CONTRACT_VERSION,'required_capability_count':len(REQUIRED_CAPABILITIES),'valid_capability_receipt_count':len(valid),'invalid_capability_receipt_count':len(rows)-len(valid),'duplicate_capabilities':duplicates,'passed_capability_count':passed,'missing_capabilities':missing,'failed_capabilities':failed,'score_percent':score,'deterministic_evidence_digest':deterministic_evidence_digest,'deterministic_benchmark_passed':deterministic_complete,'browser_review_candidate_ready':review_ready,'windows_evidence_complete':windows_complete,'operator_review_complete':operator_complete,'operator_review_authorization_id':operator_validation['authorization_id'] if operator_complete else '','promotion_decision_ready':bool(deterministic_complete and windows_complete and operator_complete),'installation_executed':False,'promotion_executed':False,'certification_granted':False,'independent_authority_granted':False,'model_management_authorized':False,'provider_contacted':False,'content_free':True}
 result['benchmark_digest']=_digest({'deterministic_evidence_digest':deterministic_evidence_digest,'windows_evidence_digest':str(windows.get('certification_evidence_digest') or ''),'operator_review_receipt_digest':operator_validation['receipt_digest'] if operator_complete else ''});return result

def final_candidate_boundary(benchmark:Mapping[str,Any])->dict[str,Any]:
 return {'contract_version':CONTRACT_VERSION,'candidate_may_be_packaged':bool(benchmark.get('browser_review_candidate_ready')),'candidate_may_be_reviewed':True,'candidate_may_be_installed_automatically':False,'candidate_may_be_promoted_automatically':False,'operator_installation_decision_required':True,'operator_promotion_decision_required':True,'windows_review_required':not bool(benchmark.get('windows_evidence_complete')),'independent_autonomy_granted':False,'benchmark_digest':str(benchmark.get('benchmark_digest') or ''),'content_free':True}

__all__=['CONTRACT_VERSION','REQUIRED_CAPABILITIES','capability_receipt','build_autonomous_developer_benchmark','final_candidate_boundary']
