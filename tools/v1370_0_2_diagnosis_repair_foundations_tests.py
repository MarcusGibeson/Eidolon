import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from diagnosis_repair_integration import *
from v1370_test_support import *
P=0
r=build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=SURFACES,benchmark_cases=CASES);req(r["ok"],"ready");P+=1
v=r["diagnosis_repair"];req(v["surface_count"]==9 and v["all_surfaces_valid"],"surfaces");P+=1
req(v["seeded_root_causes_fixed"]==1 and v["root_cause_not_symptom_verified"],"cause");P+=1
req(v["content_free"] and v["read_only"] and not v["raw_reports_persisted"],"privacy");P+=1
req(not r["source_mutation_authorized"] and not r["repair_execution_authorized"],"authority");P+=1
print({"ok":P==5,"passed":P,"total":5,"suite":"v1370-foundations"})
