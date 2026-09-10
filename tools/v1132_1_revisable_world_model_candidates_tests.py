from pathlib import Path
import tempfile
from conscious_agent.revisable_world_model_signals import RevisableWorldModelSignalStore
from conscious_agent.revisable_world_model_candidates import RevisableWorldModelCandidateStore

def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); s=RevisableWorldModelSignalStore(r); a=s.register("s1",origin_ids=["o1"],subject_id="project:p",subject_category="project",object_id="event:e",object_category="event",relation_category="involves",evidence_ids=["ev1"])["result"]["signal_id"]
  c=RevisableWorldModelCandidateStore(r); x=c.register("c1",signal_ids=[a],scope_digest="scope1",semantic_overlap_key="overlap1"); assert x["result"]["state"]=="active"
  y=c.register("c1",signal_ids=[a]); assert y["idempotent"]
  z=c.inspection_summary(); assert z["candidate_count"]==1 and z["recent_candidates"][0]["evidence_ids"]==["ev1"]
  assert not z["raw_content_exposed"] and not any(z["authority_boundary"].values())
 print("v1132.1 revisable world-model candidates: 4/4 passed")
if __name__=="__main__": main()
