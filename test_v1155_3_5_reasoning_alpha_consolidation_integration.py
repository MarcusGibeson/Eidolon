from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from conscious_agent.reasoning_consolidation import build_reasoning_state, prompt_projection
from conscious_agent.reasoning_state_continuity import (
    inspect_reasoning_state_continuity,
    load_prior_reasoning_state,
    record_reasoning_state,
)


def _state(*, missing=False, candidate=True, prior=None):
    return build_reasoning_state(
        reflection_items=[{"confidence": 0.8, "uncertainty_score": 0.2}],
        belief_deliberation={"conflict_count": 1, "quarantined_conflict_count": 0},
        multi_step_deliberation={"cases": [{
            "case_digest": "case-a",
            "options": [{"option_id": "inspect", "proposition": "inspect safely", "confidence": .8, "uncertainty": .2, "evidence_quality": .7}],
            "steps": [{"complete": True}, {"complete": not missing}],
            "comparison": {"outcome": "requires_more_evidence" if missing else "provisional_leader_only", "provisional_leader_option_id": "inspect"},
        }]},
        decision_boundary={"cases": [{
            "boundary_id": "boundary-a",
            "state": "more_evidence_required" if missing else ("candidate_recommendation" if candidate else "no_decision"),
            "candidate_option_id": "inspect" if candidate else "",
            "evidence_sufficient": not missing,
            "prerequisites_complete": not missing,
            "operator_approval_required": True,
        }]},
        continuity={"prior_session_present": bool(prior), "goal_context_count": 1},
        prior_reasoning_state=prior or {},
    )


checks=[]
def ck(name, ok): checks.append((name, bool(ok)))

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    first=_state(missing=True)
    rec=record_reasoning_state(operation_id="op-1", session_id="session-a", state=first, runtime_root=root)
    ck("recorded after commit contract", rec["type"] == "reasoning_alpha_state" and rec["private_chain_of_thought_stored"] is False)
    ck("bounded projection only", "mean_reflection_confidence" not in rec["projection"] and "cases" in rec["projection"])
    ck("authority preserved", rec["decision_created"] is False and rec["action_executed"] is False and rec["authority_broadened"] is False)
    same=record_reasoning_state(operation_id="op-1", session_id="session-a", state=_state(), runtime_root=root)
    ck("operation idempotent", same["record_digest"] == rec["record_digest"])
    prior=load_prior_reasoning_state(session_id="session-a", runtime_root=root)
    ck("same-session continuity", prior["prior_state_present"] is True and prior["projection"]["reasoning_quality"] == "insufficient_evidence")
    other=load_prior_reasoning_state(session_id="session-b", runtime_root=root)
    ck("session isolation", other["prior_state_present"] is False)
    improved=_state(missing=False, prior=prior)
    ck("transition evidence improved", improved["reasoning_transition"] == "evidence_improved")
    ck("candidate remains nonauthorizing", improved["operator_approval_required"] is True and improved["decision_created"] is False and improved["action_executed"] is False)
    projected=prompt_projection(improved)
    ck("prior state admitted boundedly", projected["prior_reasoning_state_present"] is True and projected["reasoning_transition"] == "evidence_improved")
    ck("projection authority none", projected["authority"] == "none" and projected["execution_permitted"] is False)
    # stale record is preserved but not reused
    path=root / "reasoning_alpha_states.json"
    data=json.loads(path.read_text())
    data["records"][0]["created_at"]=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat().replace("+00:00","Z")
    import hashlib
    payload={k:v for k,v in data["records"][0].items() if k!="record_digest"}
    data["records"][0]["record_digest"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    path.write_text(json.dumps(data))
    stale=load_prior_reasoning_state(session_id="session-a", runtime_root=root)
    ck("stale suppressed", stale["prior_state_present"] is False and stale["prior_state_stale"] is True and stale["projection"] == {})
    report=inspect_reasoning_state_continuity(root)
    ck("content-free diagnostics", report["content_free"] is True and "projection" not in report and "operation_id" not in report)
    ck("diagnostic authority", report["authority_preserved"] is True)
    # malformed state is reported, not silently treated as healthy
    path.write_text(json.dumps({"records": {"wrong": "shape"}}))
    malformed=load_prior_reasoning_state(session_id="session-a", runtime_root=root)
    ck("malformed quarantine", malformed["malformed_store"] is True and malformed["prior_state_present"] is False)

src=Path("conscious_agent/conversation_cognitive_backbone.py").read_text()
ck("ordinary postcommit integration", "record_reasoning_state(" in src and 'existing["reasoning_state_recorded"]' in src)
ck("ordinary preturn continuity", "load_prior_reasoning_state(" in src and "prior_reasoning_state=prior_reasoning" in src)
ck("single projection retained", src.count("reasoning_alpha_state data=") == 1 and "multi_step_deliberation data=" not in src)
ck("prompt budget retained", "MAX_PROMPT_CHARS = 1800" in src)
ck("current contract", 'CONTRACT_VERSION = "v1155.8"' in src)

for name, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + name)
print(f"{sum(ok for _,ok in checks)}/{len(checks)} checks passed")
if not all(ok for _,ok in checks):
    raise SystemExit(1)
