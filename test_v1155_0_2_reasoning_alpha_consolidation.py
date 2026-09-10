from __future__ import annotations
import json, tempfile
from pathlib import Path
from conscious_agent.reasoning_consolidation import build_reasoning_state, prompt_projection


def sample():
    multi={"cases":[{"case_digest":"case1","options":[{"option_id":"a","proposition":"inspect safely","confidence":.8,"uncertainty":.2,"evidence_quality":.7},{"option_id":"b","proposition":"wait","confidence":.5,"uncertainty":.5,"evidence_quality":.4}],"steps":[{"complete":True},{"complete":True}],"comparison":{"outcome":"provisional_leader_only","provisional_leader_option_id":"a"}}]}
    boundary={"cases":[{"boundary_id":"bd1","state":"candidate_recommendation","candidate_option_id":"a","evidence_sufficient":True,"prerequisites_complete":True,"risk_level":"low","reversibility":"high","operator_approval_required":True}]}
    return build_reasoning_state(reflection_items=[{"confidence":.7,"uncertainty_score":.3}], belief_deliberation={"conflict_count":1}, multi_step_deliberation=multi, decision_boundary=boundary, continuity={"prior_session_present":True,"goal_context_count":1})

checks=[]
def ck(name, ok): checks.append((name,bool(ok)))
s=sample(); p=prompt_projection(s)
ck('contract', s['contract_version'] in {'v1155.2','v1155.5','v1155.8'})
ck('quality', s['reasoning_quality']=='bounded_candidate')
ck('bounded cases', len(s['cases'])<=2 and len(s['cases'][0]['options'])<=3)
ck('uncertainty explicit', 'mean_reflection_uncertainty' in s)
ck('candidate approval required', s['operator_approval_required'] is True)
ck('no decision', s['decision_created'] is False)
ck('no intention', s['intention_created'] is False)
ck('no action', s['action_executed'] is False)
ck('no cot', s['private_chain_of_thought_exposed'] is False)
ck('no raw ledger', s['raw_belief_ledger_exposed'] is False)
ck('projection authority', p['authority']=='none' and p['execution_permitted'] is False)
ck('digest stable', s['reasoning_state_digest']==sample()['reasoning_state_digest'])
insufficient=build_reasoning_state(reflection_items=[], belief_deliberation={}, multi_step_deliberation={"cases":[{"options":[],"steps":[],"comparison":{"outcome":"requires_more_evidence"}}]}, decision_boundary={"cases":[{"state":"more_evidence_required"}]}, continuity={})
ck('missing evidence', insufficient['reasoning_quality']=='insufficient_evidence' and insufficient['missing_evidence_explicit'])
# source integration assertions
src=Path('conscious_agent/conversation_cognitive_backbone.py').read_text()
ck('ordinary path integrated', 'build_reasoning_state(' in src and 'reasoning_alpha_state data=' in src)
ck('duplicate projections removed', 'multi_step_deliberation data=' not in src and 'deliberation_decision_boundary data=' not in src and 'deliberation_continuity data=' not in src)
ck('prompt budget retained', 'MAX_PROMPT_CHARS = 1800' in src)
ck('metadata current', 'CONTRACT_VERSION = "v1155.8"' in src)
for name, ok in checks: print(('PASS' if ok else 'FAIL')+': '+name)
print(f'{sum(ok for _,ok in checks)}/{len(checks)} checks passed')
if not all(ok for _,ok in checks): raise SystemExit(1)
