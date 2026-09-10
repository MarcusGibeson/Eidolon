from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import multi_tool_orchestration as orch
from v1237_orchestration_fixture import build_orchestration_fixture, clone_runtime
checks=[]
def check(v): checks.append(bool(v))
def signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(ROOT).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),len(rows)
before=signature(); f=build_orchestration_fixture('v1237-foundations'); base=f['runtime']
def prepare(rt,tools=None,steps=None,quality=True,initial=None):
    return orch.prepare_multi_tool_orchestration_plan(
        f['alignment_assessment']['assessment_id'],expected_alignment_assessment_digest=f['alignment_assessment']['assessment_digest'],
        alignment_review_id=f['alignment_review']['review_id'],expected_alignment_review_digest=f['alignment_review']['review_digest'],
        quality_assessment_id=f['quality_assessment']['assessment_id'] if quality else '',
        expected_quality_assessment_digest=f['quality_assessment']['assessment_digest'] if quality else '',
        quality_review_id=f['quality_review']['review_id'] if quality else '',
        expected_quality_review_digest=f['quality_review']['review_digest'] if quality else '',
        tools=f['tools'] if tools is None else tools,steps=f['steps'] if steps is None else steps,
        initial_artifact_types=f['initial_artifact_types'] if initial is None else initial,runtime_root=rt)
contract=orch.build_multi_tool_orchestration_contract()
for v in (
    contract.get('ok'),contract.get('contract_version')=='v1237.8',contract.get('milestone_name')=='Multi-Tool Orchestration',
    contract.get('roadmap_path')=='Balanced Mind-and-Action Path 3',contract.get('exact_accepted_v1236_alignment_binding') is True,
    contract.get('optional_exact_v1234_quality_binding') is True,contract.get('sealed_content_free_tool_registry') is True,
    contract.get('ordered_contract_checked_step_graph') is True,contract.get('deterministic_tool_compatibility_evaluation') is True,
    contract.get('bounded_external_step_result_recording') is True,contract.get('operator_reviewed_handoff_proposals') is True,
    contract.get('failure_routes_stop_for_operator_review') is True,contract.get('accepted_plan_does_not_authorize_tools') is True,
    contract.get('completed_step_does_not_authorize_next_tool') is True,contract.get('accepted_handoff_does_not_authorize_next_tool') is True,
    set(contract.get('plan_dispositions') or [])==orch.PLAN_DISPOSITIONS,set(contract.get('handoff_dispositions') or [])==orch.HANDOFF_DISPOSITIONS,
    set(contract.get('step_outcomes') or [])==orch.STEP_OUTCOMES,
): check(v)
for k,e in orch.AUTHORITY_FLAGS.items(): check(contract.get(k) is e)
rt=clone_runtime(base,'v1237-valid'); p=prepare(rt)
for v in (
    p.get('ok'),p.get('status')=='multi_tool_orchestration_ready_for_operator_review',p.get('orchestration_state')=='ready',
    p.get('plan_acceptable') is True,p.get('step_count')==5,p.get('tool_count')==5,p.get('provider_tool_count')==1,
    p.get('mutation_capable_step_count')==1,p.get('quality_evidence_bound') is True,p.get('project_reference')==f['project_reference'],
    len(p.get('plan_digest',''))==64,len(p.get('tool_registry_digest',''))==64,len(p.get('basis_digest',''))==64,
    all(len(s.get('step_contract_digest',''))==64 for s in p.get('steps') or []),
    all(len(s.get('step_input_binding_digest',''))==64 for s in p.get('steps') or []),
    p.get('tool_invoked') is False,p.get('next_tool_authorized') is False,p.get('automatic_continuation_created') is False,
): check(v)
for k,e in orch.AUTHORITY_FLAGS.items(): check(p.get(k) is e)
replay=prepare(rt); check(replay.get('ok')); check(replay.get('operation_status')=='replayed'); check(replay.get('plan_digest')==p.get('plan_digest'))
rt2=clone_runtime(base,'v1237-no-quality'); noquality=prepare(rt2,quality=False)
check(noquality.get('ok')); check(noquality.get('quality_evidence_bound') is False); check(noquality.get('orchestration_state')=='ready')
# Missing tool is recorded as non-acceptable evidence, not silently substituted.
tools=f['tools'][:-1]; rt3=clone_runtime(base,'v1237-missing-tool'); missing=prepare(rt3,tools=tools)
check(missing.get('ok')); check(missing.get('orchestration_state')=='missing_tool'); check(missing.get('plan_acceptable') is False)
check(any(x.startswith('missing_tool:') for x in missing.get('issue_codes') or []))
# Contract mismatch and incompatible handoff remain visible.
steps=[dict(x) for x in f['steps']]; steps[1]=dict(steps[1]); steps[1]['input_contract_digest']='f'*64
bad=prepare(clone_runtime(base,'v1237-contract'),steps=steps)
check(bad.get('ok')); check(bad.get('orchestration_state')=='incompatible'); check(any('input_contract_mismatch' in x for x in bad.get('issue_codes') or []))
steps=[dict(x) for x in f['steps']]; steps[2]=dict(steps[2]); steps[2]['depends_on']=[]
incompatible=prepare(clone_runtime(base,'v1237-handoff'),steps=steps)
check(incompatible.get('ok')); check(any('incompatible_handoff' in x for x in incompatible.get('issue_codes') or []))
# Forward/cyclic dependency is rejected by evaluation and cannot be accepted.
steps=[dict(x) for x in f['steps']]; steps[0]=dict(steps[0]); steps[0]['depends_on']=['step_edit']
cyclic=prepare(clone_runtime(base,'v1237-cycle'),steps=steps)
check(cyclic.get('ok')); check(cyclic.get('orchestration_state')=='cyclic'); check(cyclic.get('plan_acceptable') is False)
blocked=orch.review_multi_tool_orchestration_plan(cyclic['plan_id'],expected_plan_digest=cyclic['plan_digest'],disposition='accept_plan',runtime_root=clone_runtime(base,'v1237-cycle-review'))
check(blocked.get('ok') is False)
# Invalid exact lineage fails closed.
stale=orch.prepare_multi_tool_orchestration_plan(f['alignment_assessment']['assessment_id'],expected_alignment_assessment_digest='0'*64,alignment_review_id=f['alignment_review']['review_id'],expected_alignment_review_digest=f['alignment_review']['review_digest'],tools=f['tools'],steps=f['steps'],initial_artifact_types=f['initial_artifact_types'],runtime_root=clone_runtime(base,'v1237-stale'))
check(stale.get('ok') is False); check('stale_or_invalid_alignment_assessment' in stale.get('reason',''))
check(before==signature())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
