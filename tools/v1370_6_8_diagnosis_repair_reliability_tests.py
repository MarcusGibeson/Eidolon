import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from diagnosis_repair_integration import *
from v1370_test_support import *
P=0
bad={k:dict(v) for k,v in SURFACES.items()};bad["ui_diagnosis"]["passed"]=False;req(not build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=bad,benchmark_cases=CASES)["ok"],"surface");P+=1
bad={k:dict(v) for k,v in SURFACES.items()};bad["provider_diagnosis"]["evidence_digest"]="bad";req(not build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=bad,benchmark_cases=CASES)["ok"],"digest");P+=1
c=[dict(CASES[0])];c[0]["root_trigger_absent_after_repair"]=False;r=build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=SURFACES,benchmark_cases=c);req(not r["ok"] and r["diagnosis_repair"]["symptom_only_fix_count"]==1,"symptom only");P+=1
c=[dict(CASES[0])];c[0]["root_cause_confirmed"]=False;req(not build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=SURFACES,benchmark_cases=c)["ok"],"root cause");P+=1
c=[dict(CASES[0])];c[0]["focused_regression_passed"]=False;req(not build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=SURFACES,benchmark_cases=c)["ok"],"regression");P+=1
req(not build_diagnosis_repair_scorecard(source_manifest_digest="bad",evidence_surfaces=SURFACES,benchmark_cases=CASES)["ok"],"lineage");P+=1
req(not build_diagnosis_repair_scorecard(source_manifest_digest=S,evidence_surfaces=SURFACES,benchmark_cases=[])["ok"],"empty");P+=1
print({"ok":P==7,"passed":P,"total":7,"suite":"v1370-reliability"})
