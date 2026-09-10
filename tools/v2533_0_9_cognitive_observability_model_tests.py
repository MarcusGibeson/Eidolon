from __future__ import annotations
import tempfile
from pathlib import Path

from conscious_agent.cognitive_observability_v2533 import build_cognitive_observability_snapshot
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline


def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        timeline=MentalActivityTimeline(root)
        digest="a"*64
        timeline.append("e1", event_kind="cognitive", transition="cycle_started", source_digest=digest, subject_ref="subject-1")
        timeline.append("e2", event_kind="planning", transition="plan_review", source_digest=digest, outcome_code="REVIEW")
        snap=build_cognitive_observability_snapshot(root, limit=10)
        checks += [
            snap["ok"] is True,
            snap["contract_version"]=="v2533.0",
            snap["recent_count"]==2,
            snap["recent"][0]["summary"],
            snap["trends"]["event_kind_counts"]["cognitive"]==1,
            snap["trends"]["event_kind_counts"]["planning"]==1,
            snap["authority_boundary"]["read_only"] is True,
            snap["authority_boundary"]["hidden_reasoning_exposed"] is False,
            snap["authority_boundary"]["raw_prompt_stored"] is False,
            len(snap["snapshot_digest"])==64,
        ]
        filtered=build_cognitive_observability_snapshot(root, kind="planning")
        checks += [filtered["recent_count"]==1, filtered["recent"][0]["event_kind"]=="planning"]
        try:
            build_cognitive_observability_snapshot(root, kind="secret_thought")
            checks.append(False)
        except ValueError:
            checks.append(True)
    passed=sum(bool(x) for x in checks)
    print({"passed":passed,"total":len(checks),"checks":[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)

if __name__=="__main__": main()
