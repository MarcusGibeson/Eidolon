from pathlib import Path
import tempfile
from conscious_agent.revisable_world_model_signals import RevisableWorldModelSignalStore
from conscious_agent.revisable_world_model_candidates import RevisableWorldModelCandidateStore
from conscious_agent.revisable_world_model_intake_checkpoint import build_revisable_world_model_intake_checkpoint
ROOT=Path(__file__).resolve().parents[1]
def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td)/"cognition"; s=RevisableWorldModelSignalStore(r); sid=s.register("s1",origin_ids=["o1"],subject_id="person:p",subject_category="person",object_id="project:x",object_category="project",relation_category="associated_with",evidence_ids=["ev1"])["result"]["signal_id"]; RevisableWorldModelCandidateStore(r).register("c1",signal_ids=[sid])
  out=build_revisable_world_model_intake_checkpoint(r,source_root=ROOT); assert out["ok"] and len(out["checks"])==17
  assert not out["runtime_mutated"] and not out["source_modified"]
  assert not out["raw_content_exposed"] and not out["external_action_executed"]
 print("v1132.2 revisable world-model intake checkpoint: 3/3 passed")
if __name__=="__main__": main()
