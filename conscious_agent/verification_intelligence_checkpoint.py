from __future__ import annotations
"""v1360 integrated Verification Intelligence checkpoint scorecard."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1360.8'
SURFACES=('acceptance_traceability','test_selection','unit_contract_tests','integration_tests','property_fuzz_tests','ui_accessibility_tests','performance_verification','security_verification','evidence_quality')
EXPECTED_CLASSES={'seeded_product_defect':'product_failure','fixture_drift':'fixture_or_environment','provider_unavailable':'fixture_or_environment','invalid_evidence':'evidence_problem','healthy':'pass'}
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'verification_authority_granted':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_verification_intelligence_scorecard(*,source_manifest_digest:str,evidence_surfaces:Mapping[str,Mapping[str,Any]],benchmark_cases:Sequence[Mapping[str,Any]])->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')):return {'ok':False,'status':'verification_intelligence_source_lineage_required','action_executed':False,**DENIED}
 rows=[];surface_ok=True
 for name in SURFACES:
  raw=evidence_surfaces.get(name) or {};dg=str(raw.get('evidence_digest') or '');passed=raw.get('passed') is True
  valid=bool(re.fullmatch(r'[a-f0-9]{64}',dg)) and passed;surface_ok=surface_ok and valid
  rows.append({'surface':name,'evidence_digest':dg if re.fullmatch(r'[a-f0-9]{64}',dg) else '','passed':passed,'valid':valid})
 if not benchmark_cases or len(benchmark_cases)>128:return {'ok':False,'status':'verification_intelligence_benchmark_count_invalid','action_executed':False,**DENIED}
 cases=[];seeded=seeded_caught=misclassified=0
 for raw in benchmark_cases:
  cid=str(raw.get('case_id') or '');kind=str(raw.get('case_kind') or '');observed=str(raw.get('observed_classification') or '');detected=raw.get('detected') is True
  if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',cid) or kind not in EXPECTED_CLASSES:return {'ok':False,'status':'verification_intelligence_benchmark_invalid','action_executed':False,**DENIED}
  expected=EXPECTED_CLASSES[kind];correct=observed==expected
  if kind=='seeded_product_defect':seeded+=1;seeded_caught+=int(detected and correct)
  if kind in {'fixture_drift','provider_unavailable'} and observed=='product_failure':misclassified+=1
  if not correct:misclassified+=1 if not (kind in {'fixture_drift','provider_unavailable'} and observed=='product_failure') else 0
  cases.append({'case_id_digest':_d(cid),'case_kind':kind,'expected_classification':expected,'observed_classification':observed,'detected':detected,'classification_correct':correct})
 benchmark_ok=seeded>0 and seeded==seeded_caught and misclassified==0 and all(x['classification_correct'] for x in cases)
 passed=surface_ok and benchmark_ok
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'surface_count':len(rows),'surfaces':rows,'all_surfaces_valid':surface_ok,'benchmark_case_count':len(cases),'benchmark_cases':cases,'seeded_product_defect_count':seeded,'seeded_product_defects_caught':seeded_caught,'misclassification_count':misclassified,'fixture_drift_is_not_product_failure':all(x['observed_classification']!='product_failure' for x in cases if x['case_kind']=='fixture_drift'),'provider_unavailable_is_not_product_failure':all(x['observed_classification']!='product_failure' for x in cases if x['case_kind']=='provider_unavailable'),'verification_strategy_passed':passed,'raw_test_payloads_persisted':False,'content_free':True,'read_only':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':passed,'status':'verification_intelligence_checkpoint_ready' if passed else 'verification_intelligence_checkpoint_blocked','verification_intelligence':rec,'action_executed':False,**DENIED}
def process_verification_intelligence_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show verification intelligence','inspect verification intelligence','show verification checkpoint'}:return {'active':False}
 rec=dict((project_state or {}).get('verification_intelligence') or {});return {'active':True,'ok':bool(rec),'status':'verification_intelligence_found' if rec else 'verification_intelligence_missing','verification_intelligence':rec,'action_executed':False,**DENIED}
