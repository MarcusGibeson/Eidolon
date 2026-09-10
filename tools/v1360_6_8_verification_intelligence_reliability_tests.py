import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from verification_intelligence_checkpoint import *
from v1360_test_support import *
P=0
bad={k:dict(v) for k,v in SURF.items()};bad['security_verification']['passed']=False;req(not build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=bad,benchmark_cases=CASES)['ok'],'surface');P+=1
bad={k:dict(v) for k,v in SURF.items()};bad['evidence_quality']['evidence_digest']='bad';req(not build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=bad,benchmark_cases=CASES)['ok'],'digest');P+=1
c=[dict(x) for x in CASES];c[0]['detected']=False;req(not build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=SURF,benchmark_cases=c)['ok'],'missed defect');P+=1
c=[dict(x) for x in CASES];c[2]['observed_classification']='product_failure';r=build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=SURF,benchmark_cases=c);req(not r['ok'] and r['verification_intelligence']['misclassification_count']>0,'fixture');P+=1
c=[dict(x) for x in CASES];c[3]['observed_classification']='product_failure';req(not build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=SURF,benchmark_cases=c)['ok'],'provider');P+=1
req(not build_verification_intelligence_scorecard(source_manifest_digest='bad',evidence_surfaces=SURF,benchmark_cases=CASES)['ok'],'lineage');P+=1
print({'ok':P==6,'passed':P,'total':6,'suite':'v1360.6-8-verification-intelligence-reliability'})
