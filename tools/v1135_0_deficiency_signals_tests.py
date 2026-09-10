from pathlib import Path
import tempfile
from conscious_agent.deficiency_signals import DeficiencySignalStore, DEFICIENCY_CATEGORIES
with tempfile.TemporaryDirectory() as td:
 s=DeficiencySignalStore(Path(td)); a=s.register("e1",origin_ids=["checkpoint:1"],source_categories=["failed_checkpoint"],deficiency_category="reliability_deficiency",component_ids=["component:alpha"],project_digest="a"*64,scope_digest="b"*64,evidence_ids=["evidence:1"],recurrence_count=3,reproducibility=.9,severity=.8,urgency=.2,confidence=.9,uncertainty=.1)
 assert a["result"]["state"]=="active"
 assert s.register("e1",origin_ids=["checkpoint:1"],source_categories=["failed_checkpoint"],deficiency_category="reliability_deficiency",component_ids=["component:alpha"],project_digest="a"*64,scope_digest="b"*64,evidence_ids=["evidence:1"])["idempotent"]
 q=s.register("e2",origin_ids=["review:1"],source_categories=["architectural_structure"],deficiency_category="architectural_deficiency",component_ids=["component:beta"],project_digest="a"*64,scope_digest="c"*64,evidence_ids=["evidence:2"],recurrence_count=1,reproducibility=.2,severity=.95,confidence=.2,architectural_suspicion=True)
 assert q["result"]["state"]=="suppressed"
 out=s.inspection_summary(); assert len(DEFICIENCY_CATEGORIES)>=8 and not out["raw_content_exposed"] and not any(out["authority_boundary"].values())
print("v1135.0 deficiency signals: 6/6 passed")
