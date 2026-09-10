from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from problem_framing_intelligence import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n): checks.append(n); assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v1725-9-') as td:
    rt=Path(td)/'runtime'
    frame=build_problem_frame(
        'Build a parser that must preserve existing behavior. I prefer concise output. Assuming the input is UTF-8, verify all focused tests pass and no regressions occur.',
        project_evidence={'workspace_digest':'a'*64},runtime_root=rt)
    req(frame['ok'],'frame_ok'); req(frame['status']=='problem_frame_ready','frame_status')
    req(frame['counts']['goals']>=1,'goal'); req(frame['counts']['hard_constraints']>=1,'hard')
    req(frame['counts']['soft_preferences']>=1,'soft'); req(frame['counts']['assumptions']>=1,'assumption')
    req(frame['counts']['acceptance_criteria']>=1,'acceptance'); req(not frame['private_request_exposed'],'privacy')
    req('preserve existing behavior' not in json.dumps(frame),'private_text_absent')
    req(all(not row.get('text_exposed') and row.get('text_digest') for field in ('goals','hard_constraints','soft_preferences','assumptions','acceptance_criteria') for row in frame[field]),'public_items_digest_only')
    digest=frame['problem_frame_digest'];fid=frame['problem_frame_id']
    judged=judge_clarification(fid,digest,runtime_root=rt)
    req(judged['judgment']=='proceed_bounded','clear_proceeds'); req(not judged['automatic_execution'],'no_execute')
    same=build_problem_frame('Build a parser that must preserve existing behavior. I prefer concise output. Assuming the input is UTF-8, verify all focused tests pass and no regressions occur.',project_evidence={'workspace_digest':'a'*64},runtime_root=rt)
    req(same['status']=='problem_frame_current','idempotent')
    corrected=correct_problem_frame(fid,digest,'soft_preference',1,'Prefer very concise output.',runtime_root=rt)
    req(corrected['status']=='problem_frame_corrected','corrected')
    req(corrected['revision']==2,'revision')
    stale=correct_problem_frame(fid,digest,'soft_preference',1,'stale edit',runtime_root=rt)
    req(not stale['ok'] and stale['status']=='stale_problem_frame_digest','stale_rejected')
    # Contradictions are explicit and force clarification.
    conflict=build_problem_frame('Build the cache. It must use disk caching. It must not use disk caching. Verify tests pass.',runtime_root=rt)
    req(conflict['counts']['contradictions']>=1,'contradiction_found')
    cj=judge_clarification(conflict['problem_frame_id'],conflict['problem_frame_digest'],runtime_root=rt)
    req(cj['judgment']=='ask' and cj['reason_code']=='contradictory_requirements','conflict_asks')
    # Reversible incomplete work can prototype rather than pestering the operator.
    proto=build_problem_frame('Prototype an isolated parser and inspect the result.',runtime_root=rt)
    pj=judge_clarification(proto['problem_frame_id'],proto['problem_frame_digest'],runtime_root=rt)
    req(pj['judgment']=='prototype','prototype_judgment')
    # Consequential ambiguity cannot be silently inferred.
    consequential=build_problem_frame('Install the production migration.',runtime_root=rt)
    qj=judge_clarification(consequential['problem_frame_id'],consequential['problem_frame_digest'],runtime_root=rt)
    req(qj['judgment']=='ask' and qj['consequential_request'],'consequential_asks')
    # External unknowns point to research, but research is not executed.
    research=build_problem_frame('Investigate the latest API version? Verify the current specification.',runtime_root=rt)
    rj=judge_clarification(research['problem_frame_id'],research['problem_frame_digest'],runtime_root=rt)
    req(rj['judgment']=='research' and not rj['external_research_authorized'],'research_judgment_only')
    cancelled=cancel_problem_frame(fid,corrected['problem_frame_digest'],runtime_root=rt)
    req(cancelled['status']=='problem_frame_cancelled','cancelled')
    replay=cancel_problem_frame(fid,cancelled['problem_frame_digest'],runtime_root=rt)
    req(replay['status']=='problem_frame_already_cancelled','cancel_replay')
    # Ordinary-chat exact controls route through the established boundary.
    ctl=process_ordinary_chat_development_turn('frame problem: Build a CLI. It must not modify source. Verify tests pass.',runtime_root=rt)
    req(ctl.get('active') and ctl.get('problem_frame_id'),'chat_frame_control')
    compound=process_ordinary_chat_development_turn('frame problem: inspect this and install it',runtime_root=rt)
    req(compound.get('active') and compound.get('status')=='read_only_scope_expansion_rejected','compound_rejected')
    # A normal development proposal now carries problem framing without changing approval semantics.
    proposal=process_ordinary_chat_development_turn('Build a small calculator tool that must preserve existing files and verify tests pass.',runtime_root=rt,session_id='era3-test')
    req(proposal.get('active') and proposal.get('event') in {'proposal_created','proposal_resumed'},'proposal_active')
    pf=proposal.get('problem_framing') or {}
    req(bool(pf.get('problem_frame_id')) and pf.get('clarification_judgment') in {'proceed_bounded','ask','prototype','infer_reversibly','research'},'proposal_framed')
    req(pf.get('automatic_execution') is False and pf.get('authority_granted') is False,'proposal_no_authority')
print(json.dumps({'suite':'v1725.9-requirements-problem-framing-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
