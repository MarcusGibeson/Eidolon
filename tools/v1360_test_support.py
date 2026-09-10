from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
S='a'*64;E='b'*64
SURF={k:{'evidence_digest':E,'passed':True} for k in ('acceptance_traceability','test_selection','unit_contract_tests','integration_tests','property_fuzz_tests','ui_accessibility_tests','performance_verification','security_verification','evidence_quality')}
CASES=[
 {'case_id':'defect.parser','case_kind':'seeded_product_defect','observed_classification':'product_failure','detected':True},
 {'case_id':'defect.lifecycle','case_kind':'seeded_product_defect','observed_classification':'product_failure','detected':True},
 {'case_id':'fixture.drift','case_kind':'fixture_drift','observed_classification':'fixture_or_environment','detected':True},
 {'case_id':'provider.down','case_kind':'provider_unavailable','observed_classification':'fixture_or_environment','detected':True},
 {'case_id':'evidence.bad','case_kind':'invalid_evidence','observed_classification':'evidence_problem','detected':True},
 {'case_id':'healthy.base','case_kind':'healthy','observed_classification':'pass','detected':False},
]
def req(v,m):
 if not v:raise AssertionError(m)
