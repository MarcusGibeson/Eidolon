from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import conscious_agent.conversation_cognitive_backbone as backbone
from conscious_agent.deliberation_continuity import (
    build_deliberation_continuity_context,
    inspect_deliberation_continuity,
    record_deliberation_continuity,
)


def _result():
    return {
        "contract_version": "v1153.2",
        "type": "multi_step_deliberation",
        "case_count": 1,
        "cases": [{
            "case_digest": "case-1",
            "options": [
                {"option_id": "b1", "proposition": "provider timeout", "confidence": .7, "uncertainty": .3, "evidence_quality": .6},
                {"option_id": "b2", "proposition": "memory failure", "confidence": .5, "uncertainty": .5, "evidence_quality": .2},
            ],
            "steps": [
                {"step": 1, "kind": "frame_alternatives", "complete": True},
                {"step": 2, "kind": "check_evidence_and_uncertainty", "complete": True},
                {"step": 3, "kind": "compare_without_resolving", "complete": True},
                {"step": 4, "kind": "identify_missing_evidence", "complete": True},
            ],
            "comparison": {"outcome": "requires_more_evidence", "resolution_permitted": False},
        }],
        "quarantined_conflict_count": 0,
        "resolution_permitted": False,
    }


def run():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        cognition=root/'cognition'
        (root/'goals.json').write_text(json.dumps({"goals":[{
            "id":"g1","title":"Diagnose failed replies","description":"Find whether providers or memory commits fail",
            "status":"active","priority":"high","blockers":["need logs"],"next_actions":["inspect evidence"]
        }]}),encoding='utf-8')
        import conscious_agent.deliberation_continuity as continuity
        original=continuity.build_multi_step_deliberation
        continuity.build_multi_step_deliberation=lambda *a,**k:_result()
        try:
            first=record_deliberation_continuity(runtime_root=cognition,operation_id='op1',session_id='s1',user_message='why did the failed reply happen')
            second=record_deliberation_continuity(runtime_root=cognition,operation_id='op1',session_id='s1',user_message='ignored duplicate')
        finally:
            continuity.build_multi_step_deliberation=original
        checks.append(first['continuity_id']==second['continuity_id'])
        checks.append(first['case_count']==1 and first['cases'][0]['completed_step_count']==4)
        checks.append(first['goal_context_count']==1 and first['goal_context'][0]['goal_id']=='g1')
        checks.append(not first['user_content_stored'] and not first['belief_content_stored'])
        checks.append(not first['resolution_permitted'] and not first['decision_created'] and not first['action_executed'])
        inspection=inspect_deliberation_continuity(cognition)
        checks.append(inspection['session_count']==1 and inspection['all_content_free'] and inspection['authority_preserved'])
        before=(cognition/'deliberation_continuity.json').read_bytes()
        ctx=build_deliberation_continuity_context('failed reply evidence',runtime_root=cognition,session_id='s1')
        after=(cognition/'deliberation_continuity.json').read_bytes()
        checks.append(before==after and ctx['read_only'] and not ctx['runtime_mutated'])
        checks.append(ctx['prior_session_present'] and ctx['prior_case_count']==1)
        checks.append(ctx['goal_context_count']==1 and ctx['goal_context'][0]['authority']=='context_only')
        checks.append(not ctx['resolution_permitted'] and not ctx['decision_created'] and not ctx['action_executed'])

        os.environ['EIDOLON_DATA_DIR']=td
        original_multi=backbone.build_multi_step_deliberation
        original_cont=backbone.build_deliberation_continuity_context
        backbone.build_multi_step_deliberation=lambda *a,**k:_result()
        backbone.build_deliberation_continuity_context=lambda *a,**k:ctx
        try:
            prompt=backbone.build_turn_cognitive_context('failed reply evidence',operation_id='op2',session_id='s1',memories=[],self_model={},desires={})
        finally:
            backbone.build_multi_step_deliberation=original_multi
            backbone.build_deliberation_continuity_context=original_cont
        checks.append(prompt['prompt_chars']<=1800)
        checks.append(prompt['deliberation_continuity_present'] is True)
        checks.append(prompt['deliberation_goal_context_count']==1)
        checks.append('reasoning_alpha_state data=' in prompt['prompt_section'] and 'deliberation_continuity data=' not in prompt['prompt_section'])
        checks.append(prompt['multi_step_resolution_permitted'] is False and prompt['authority_broadened'] is False)

        # Post-commit integration records continuity exactly once and remains retry-safe.
        original_record=backbone.record_deliberation_continuity
        calls=[]
        backbone.record_deliberation_continuity=lambda **kw: calls.append(kw) or {"continuity_id":"d1"}
        original_thought=backbone.generate_inner_thought
        original_reflect=backbone.build_evidence_grounded_reflection
        original_store=backbone.store_memory_batch
        original_phases=backbone._phase_memories
        backbone.generate_inner_thought=lambda **kw:{"thought":"consider evidence"}
        backbone.build_evidence_grounded_reflection=lambda **kw:{"reflection_id":"r1","content":"reflection","evidence_refs":[],"use_in_conversation":True}
        phase_state={}
        backbone._phase_memories=lambda marker: dict(phase_state)
        def store(items):
            for item in items: phase_state[item['conversation_side_effect_phase']]=item
        backbone.store_memory_batch=store
        try:
            result=backbone.record_turn_completion(operation_id='post1',session_id='s1',user_message='question',assistant_response='answer',source='test',context_summary={})
        finally:
            backbone.record_deliberation_continuity=original_record
            backbone.generate_inner_thought=original_thought
            backbone.build_evidence_grounded_reflection=original_reflect
            backbone.store_memory_batch=original_store
            backbone._phase_memories=original_phases
        checks.append(result['completion_state']=='completed' and result['deliberation_continuity_recorded'])
        checks.append(len(calls)==1 and calls[0]['operation_id']=='post1')

    passed=sum(bool(x) for x in checks)
    print(f"v1153.3-v1153.5 multi-step deliberation integration: {passed}/{len(checks)}")
    if passed!=len(checks):
        print([i+1 for i,x in enumerate(checks) if not x])
        raise SystemExit(1)

if __name__=='__main__': run()
