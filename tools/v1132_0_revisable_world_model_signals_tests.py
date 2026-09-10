from pathlib import Path
import tempfile
from conscious_agent.revisable_world_model_signals import RevisableWorldModelSignalStore

def main():
 with tempfile.TemporaryDirectory() as td:
  s=RevisableWorldModelSignalStore(Path(td)); a=s.register("e1",origin_ids=["reflection:o1"],subject_id="person:p1",subject_category="person",object_id="project:x",object_category="project",relation_category="involves",evidence_ids=["evidence:d1"],temporal_context_id="time:t1",confidence=.8,uncertainty=.2); assert a["result"]["state"]=="active"
  b=s.register("e1",origin_ids=["reflection:o1"],subject_id="person:p1",subject_category="person",object_id="project:x",object_category="project",relation_category="involves",evidence_ids=["evidence:d1"]); assert b["idempotent"]
  c=s.register("e2",origin_ids=["revision:o2"],subject_id="belief:b1",subject_category="belief",object_id="event:e1",object_category="event",relation_category="corrects",evidence_ids=["evidence:d2"],predecessor_signal_ids=[a["result"]["signal_id"]],correction=True); assert c["result"]["state"]=="active"
  i=s.inspection_summary(); assert i["signal_count"]==2 and not i["raw_content_exposed"] and not any(i["authority_boundary"].values())
 print("v1132.0 revisable world-model signals: 4/4 passed")
if __name__=="__main__": main()
