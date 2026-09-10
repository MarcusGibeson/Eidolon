from pathlib import Path
import json,tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.cognitive_recovery_lifecycle import CognitiveRecoveryLifecycleStore
from conscious_agent.sustainable_cognitive_windows import SustainableCognitiveWindowStore
passed=0
def check(n,v):
 global passed
 if not v:raise AssertionError(n)
 passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td);life=CognitiveRecoveryLifecycleStore(root);rid=life.propose("e1",review_id="r1",recommendation="recovery_window_recommended")["result"]["recovery_id"];s=SustainableCognitiveWindowStore(root);r=s.record("o1",recovery_id=rid,before_pressure=.9,after_pressure=.5,before_margin=.1,after_margin=.5,observation_count=2);check("effective",r["result"]["outcome"]=="effective");check("duplicate",s.record("o1",recovery_id=rid)["idempotent"]);u=s.record("o2",recovery_id=rid,observation_count=0);check("unknown",u["result"]["outcome"]=="unknown");check("not_positive",not s.inspection_summary()["missing_feedback_is_positive"]);check("correction",s.record("o3",recovery_id=rid,corrects_outcome_id=r["result"]["outcome_id"])["result"]["outcome"]=="corrected");check("retract",s.record("o4",recovery_id=rid,retracted=True)["result"]["outcome"]=="retracted");row=s.snapshot()["outcomes"][0];check("no_mutation",not row["schedule_changed"] and not row["adaptation_applied"]);check("privacy",not s.inspection_summary()["private_content_exposed"])
print(json.dumps({"passed":passed,"total":8,"suite":"v1116.4"}))
