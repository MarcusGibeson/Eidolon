import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from verification_intelligence_checkpoint import *
from v1360_test_support import *
P=0
r=build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=SURF,benchmark_cases=CASES);req(r['ok'],'ready');P+=1;v=r['verification_intelligence'];req(v['surface_count']==9 and v['all_surfaces_valid'],'surfaces');P+=1;req(v['seeded_product_defects_caught']==2,'seeded');P+=1;req(v['fixture_drift_is_not_product_failure'] and v['provider_unavailable_is_not_product_failure'],'classes');P+=1
print({'ok':P==4,'passed':P,'total':4,'suite':'v1360.0-2-verification-intelligence-foundations'})
