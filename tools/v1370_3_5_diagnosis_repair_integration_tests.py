import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from diagnosis_repair_integration import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1370_test_support import *
P=0
r=build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=SURFACES,benchmark_cases=CASES);v=r["diagnosis_repair"];req(r["ok"],"score");P+=1
c=process_ordinary_chat_development_turn("show diagnosis and repair",project_state={"diagnosis_repair":v});req(c.get("active") and c.get("ok"),"chat");P+=1
req(c["diagnosis_repair"]["record_digest"]==v["record_digest"],"projection");P+=1
req(not c["action_executed"] and not c["application_authorized"],"readonly");P+=1
req(v["benchmark_case_count"]==1 and v["symptom_only_fix_count"]==0,"benchmark");P+=1
req(v["seeded_cross_subsystem_defect_count"]==1,"seeded");P+=1
print({"ok":P==6,"passed":P,"total":6,"suite":"v1370-integration"})
