import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from diagnosis_repair_integration import *
from v1370_test_support import *
P=0
r=build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=SURFACES,benchmark_cases=CASES);v=r["diagnosis_repair"];req(r["ok"],"checkpoint");P+=1
req(v["diagnosis_repair_strategy_passed"],"strategy");P+=1
req(v["root_cause_not_symptom_verified"] and v["symptom_only_fix_count"]==0,"cause");P+=1
req(v["content_free"] and v["read_only"],"privacy");P+=1
req(not r["release_authorized"] and not r["independent_authority_granted"],"authority");P+=1
print({"ok":P==5,"passed":P,"total":5,"suite":"v1370-checkpoint"})
