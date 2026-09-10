from pathlib import Path
import tempfile
from conscious_agent.deficiency_signals import DeficiencySignalStore
from conscious_agent.deficiency_candidates import DeficiencyCandidateStore, STATES
with tempfile.TemporaryDirectory() as td:
 root=Path(td); s=DeficiencySignalStore(root); a=s.register("e1",origin_ids=["checkpoint:1"],source_categories=["failed_checkpoint"],deficiency_category="reliability_deficiency",component_ids=["component:alpha"],project_digest="a"*64,scope_digest="b"*64,evidence_ids=["evidence:1"],recurrence_count=3,reproducibility=.9,severity=.8,confidence=.9,uncertainty=.1); sid=a["result"]["signal_id"]
 c=DeficiencyCandidateStore(root); x=c.register("c1",signal_ids=[sid]); assert x["result"]["state"]=="active"
 assert c.register("c1",signal_ids=[sid])["idempotent"]
 y=c.register("c2",signal_ids=[sid]); assert y["result"]["status"]=="semantic_overlap_merged"
 out=c.inspection_summary(); assert len(STATES)==11 and not out["proposal_text_exposed"] and not any(out["authority_boundary"].values())
print("v1135.1 deficiency candidates: 6/6 passed")
