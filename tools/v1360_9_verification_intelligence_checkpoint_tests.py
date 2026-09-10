import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from verification_intelligence_checkpoint import *
from v1360_test_support import *
P=0
r=build_verification_intelligence_scorecard(source_manifest_digest=S,evidence_surfaces=SURF,benchmark_cases=CASES);v=r['verification_intelligence'];req(r['ok'],'checkpoint');P+=1;req(v['verification_strategy_passed'],'strategy');P+=1;req(v['misclassification_count']==0,'classification');P+=1;req(v['content_free'] and v['read_only'],'privacy');P+=1;req(not r['verification_authority_granted'] and not r['release_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1360.9-verification-intelligence-checkpoint'})
