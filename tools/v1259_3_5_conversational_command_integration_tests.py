from __future__ import annotations

import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for path in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(path) not in sys.path: sys.path.insert(0,str(path))

from conversational_command_integration import build_conversational_command_integration, process_conversational_development_control
from natural_language_action_routing import build_natural_language_action_projection
from ordinary_chat_development_campaign import (
    list_development_campaign_proposals, load_development_campaign_proposal, process_ordinary_chat_development_turn,
)

CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)

def source_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def development_turn(text, *, session, runtime):
    return process_ordinary_chat_development_turn(
        text,
        action_projection=build_natural_language_action_projection(text),
        session_id=session,
        runtime_root=runtime,
    )

before=source_signature()
with tempfile.TemporaryDirectory(prefix='eid-v1259-3-5-') as d:
    runtime=Path(d)/'runtime'; session='conversation-alpha'
    initial=list_development_campaign_proposals(runtime_root=runtime,public=False)['proposal_count']

    # Non-actions stay out of proposal intake.
    for text in (
        'I wish you could build a calculator app.',
        'I hope you can build a calculator app someday.',
        'Someday you could build a calculator app.',
        'What if you built a calculator app?',
        'Could you explain how to build a calculator app?',
        'Maybe you should build a calculator someday.',
    ):
        result=development_turn(text,session=session,runtime=runtime)
        require(result['active'] is False,f'non_action_inactive:{text}')
    require(list_development_campaign_proposals(runtime_root=runtime,public=False)['proposal_count']==initial,'non_actions_create_no_proposals')

    # One direct request creates exactly one existing supervised proposal.
    created=development_turn('Build me a responsive calculator webpage.',session=session,runtime=runtime)
    require(created['event']=='proposal_created','direct_request_creates_proposal')
    proposal=created['proposal']; pid=proposal['proposal_id']
    require(proposal['revision']==1 and proposal['approval_consumed'] is False,'new_proposal_awaits_exact_approval')
    require(list_development_campaign_proposals(runtime_root=runtime,public=False)['proposal_count']==initial+1,'exactly_one_proposal_created')

    vague=development_turn('Go ahead.',session=session,runtime=runtime)
    require(vague['event']=='generic_authorization_blocked','generic_authorization_blocked')
    stored=load_development_campaign_proposal(pid,runtime_root=runtime)
    require(stored['approval_consumed'] is False and stored['revision']==1,'generic_authorization_consumes_nothing')

    corrected=development_turn('Actually, make it dark mode instead.',session=session,runtime=runtime)
    require(corrected['event']=='conversational_correction_applied','ordinary_correction_revises_pending_proposal')
    require(corrected['proposal_id']==pid and corrected['revision']==2,'correction_preserves_identity_and_increments_revision')
    stored=load_development_campaign_proposal(pid,runtime_root=runtime)
    require(stored['revision']==2 and stored['approval_consumed'] is False,'corrected_revision_requires_fresh_approval')
    require('Operator correction:' in stored['request'],'private_proposal_records_bounded_correction')

    duplicate=development_turn('Actually, make it dark mode instead.',session=session,runtime=runtime)
    require(duplicate['event']=='conversational_correction_applied' and duplicate['deduplicated'] is True,'duplicate_correction_idempotent')
    require(load_development_campaign_proposal(pid,runtime_root=runtime)['revision']==2,'duplicate_correction_does_not_increment_revision')

    stale_approval=process_ordinary_chat_development_turn(
        f'Approve development proposal {pid} revision 1.', session_id=session, runtime_root=runtime
    )
    require(stale_approval['event']=='stale_control_rejected','old_revision_authorization_stays_stale_after_correction')
    require(load_development_campaign_proposal(pid,runtime_root=runtime)['approval_consumed'] is False,'stale_authorization_consumes_nothing')

    exact=process_ordinary_chat_development_turn(
        f'Approve development proposal {pid} revision 2.', session_id=session, runtime_root=runtime
    )
    require(exact['event']=='approval_consumed','exact_current_revision_authorization_retained')
    require(exact['approval_consumption_count']==1,'exact_approval_consumed_once')
    require(load_development_campaign_proposal(pid,runtime_root=runtime)['approval_consumed'] is True,'approved_state_persisted')

    # Corrections after approval do not silently rewrite the approved artifact.
    late=development_turn('Actually, make it blue instead.',session=session,runtime=runtime)
    require(late['event']=='conversational_correction_blocked' or late['event']=='correction_target_ambiguous','post_approval_correction_fails_closed')
    require(load_development_campaign_proposal(pid,runtime_root=runtime)['revision']==2,'post_approval_correction_does_not_mutate_revision')

# Unique conversational cancellation and ambiguous cancellation behavior.
with tempfile.TemporaryDirectory(prefix='eid-v1259-3-5-cancel-') as d:
    runtime=Path(d)/'runtime'; session='conversation-cancel'
    created=development_turn('Build me a calculator webpage.',session=session,runtime=runtime); proposal=created['proposal']; pid=proposal['proposal_id']
    cancelled=development_turn('Cancel that development proposal.',session=session,runtime=runtime)
    require(cancelled['event']=='conversational_cancellation_applied','unique_pending_proposal_cancelled_conversationally')
    require(load_development_campaign_proposal(pid,runtime_root=runtime)['lifecycle_state']=='cancelled','cancellation_persists_terminal_state')
    require(cancelled['authorization_granted'] is False and cancelled['execution_authorized'] is False,'cancellation_grants_no_execution_authority')

with tempfile.TemporaryDirectory(prefix='eid-v1259-3-5-ambiguous-') as d:
    runtime=Path(d)/'runtime'; session='conversation-ambiguous'
    a=development_turn('Build me a calculator webpage.',session=session,runtime=runtime)
    b=development_turn('Build me a notes webpage.',session=session,runtime=runtime)
    require(a['event']=='proposal_created' and b['event']=='proposal_created','two_pending_proposals_created_for_ambiguity_fixture')
    blocked=development_turn('Cancel that development proposal.',session=session,runtime=runtime)
    require(blocked['event']=='cancellation_target_ambiguous','ambiguous_cancellation_fails_closed')
    require(all(load_development_campaign_proposal(x['proposal']['proposal_id'],runtime_root=runtime)['lifecycle_state']=='awaiting_approval' for x in (a,b)),'ambiguous_cancellation_changes_nothing')

# Mixed conversation/action retains exactly one live action route.
with tempfile.TemporaryDirectory(prefix='eid-v1259-3-5-mixed-') as d:
    runtime=Path(d)/'runtime'; session='conversation-mixed'
    text='It would be nice to have a calculator. Build me a responsive calculator webpage.'
    projection=build_conversational_command_integration(text,session_id=session,runtime_root=runtime)
    require(projection['status']=='action_request_routed','mixed_turn_routes_one_action')
    require(projection['classification']['mixed_turn'] is True,'mixed_turn_marked')
    routed=process_ordinary_chat_development_turn(
        projection['routing_text'],action_projection=build_natural_language_action_projection(projection['routing_text']),session_id=session,runtime_root=runtime
    )
    require(routed['event']=='proposal_created','mixed_live_clause_enters_existing_proposal_pipeline')
    require(list_development_campaign_proposals(runtime_root=runtime,public=False)['proposal_count']==1,'mixed_turn_creates_one_proposal')

with tempfile.TemporaryDirectory(prefix='eid-v1259-3-5-mixed-wish-') as d:
    runtime=Path(d)/'runtime'; session='conversation-mixed-wish'
    mixed_wish=development_turn(
        'I wish you could build a calculator app. Build me a responsive notes webpage.',
        session=session,runtime=runtime,
    )
    require(mixed_wish['event']=='proposal_created','wish_plus_direct_request_routes_direct_clause')
    require(mixed_wish['proposal']['revision']==1,'wish_plus_direct_request_creates_one_revision')
    require(list_development_campaign_proposals(runtime_root=runtime,public=False)['proposal_count']==1,'wish_plus_direct_request_creates_one_proposal')

# Full ordinary conversation runtime path, using a deterministic fake provider.
with tempfile.TemporaryDirectory(prefix='eid-v1259-3-5-runtime-') as d:
    runtime=Path(d)/'runtime'
    env=dict(os.environ); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONDONTWRITEBYTECODE']='1'
    proc=subprocess.run([sys.executable,str(ROOT/'tools/v1259_runtime_probe.py')],cwd=ROOT,env=env,text=True,capture_output=True,timeout=60,check=True)
    runtime_result=json.loads(proc.stdout.strip().splitlines()[-1])
    require(runtime_result['info_success'] and runtime_result['info_act']=='information_request','full_runtime_information_request_classified_without_action')
    require(runtime_result['proposal_count_before_mixed']==0,'full_runtime_information_request_created_no_proposal')
    require(runtime_result['mixed_success'] and runtime_result['mixed_act']=='action_request','full_runtime_mixed_action_classified')
    require(runtime_result['mixed_provider_requests']==1 and 'I created supervised development proposal' in runtime_result['mixed_response'],'full_runtime_mixed_turn_retains_governed_conversational_response')
    require('Approve development proposal' in runtime_result['mixed_response'] and runtime_result['proposal_count_after_mixed']==1,'full_runtime_mixed_turn_creates_one_supervised_proposal')
    require(runtime_result['vague_provider_requests']==0 and runtime_result['approval_after_vague'] is False,'full_runtime_generic_authorization_provider_free_and_non_authoritative')
    require(runtime_result['correction_provider_requests']==1 and runtime_result['revision_after_correction']==2,'full_runtime_correction_conversational_and_revision_bound')
    require(runtime_result['fake_provider_calls']==3,'full_runtime_provider_count_matches_conversational_turns')

require(source_signature()==before,'integration_suite_preserves_eidolon_source')
print(json.dumps({'ok':True,'suite':'v1259.3-v1259.5-conversational-command-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'project_modified':False,'generic_authorization_consumed':False,'release_authorized':False},indent=2,sort_keys=True))
