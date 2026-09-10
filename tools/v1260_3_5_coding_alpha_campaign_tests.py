from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from natural_language_action_routing import build_natural_language_action_projection
from isolated_coding_execution import load_isolated_coding_review
from complete_application_construction import load_complete_application_quality
from diagnostic_repair_reasoning_foundations import load_diagnostic_result
from controlled_application_rollback import load_controlled_application_execution
from persistent_development_sessions_foundations import load_persistent_development_session
from coding_alpha_campaign import build_coding_alpha_lineage
from v1260_test_support import CodingAlphaProvider,make_project,tree_signature
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def turn(text,session,runtime,project=None,provider=None):
    kw={'session_id':session,'runtime_root':runtime,'node_executable':'node'}
    if project is not None: kw['project_state']={'id':'calculator','name':'Calculator','path':str(project)}
    if provider is not None: kw['provider_generate']=provider
    return process_ordinary_chat_development_turn(text,action_projection=build_natural_language_action_projection(text),**kw)
with tempfile.TemporaryDirectory(prefix='eid-v1260-3-5-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_project(base); original=tree_signature(project); session='coding-alpha-chat'
    created=turn('Build me a complete responsive accessible calculator webpage.',session,runtime,project)
    req(created['event']=='proposal_created','ordinary_request_creates_proposal'); p=created['proposal']
    req(p['approval_consumed'] is False,'proposal_waits_for_exact_approval')
    vague=turn('Go ahead.',session,runtime); req(vague['event']=='generic_authorization_blocked','generic_go_ahead_blocked')
    approved=turn(f"Approve development proposal {p['proposal_id']} revision {p['revision']}.",session,runtime)
    req(approved['event']=='approval_consumed','exact_proposal_approval_consumed'); rid=approved['isolated_coding_request_id']; ex=approved['isolated_coding_execution']
    req(ex['status']=='isolated_coding_execution_authorization_required','isolated_execution_separate_authority_required')
    req(tree_signature(project)==original,'selected_project_unchanged_after_proposal_approval')
    provider=CodingAlphaProvider()
    executed=turn(ex['authorization_phrase'],session,runtime,provider=provider)
    req(executed['event']=='isolated_coding_execution_completed','isolated_execution_completes')
    req(provider.calls==2,'intentional_failure_then_one_repair_provider_calls')
    req(tree_signature(project)==original,'selected_project_unchanged_after_isolated_execution')
    review=load_isolated_coding_review(rid,runtime_root=runtime); req(review['reviewable_diff_available'],'reviewable_diff_ready')
    req(len(review.get('changed_paths') or [])>=6,'complete_application_diff_has_six_files')
    q1=load_complete_application_quality(rid,1,runtime_root=runtime); q2=load_complete_application_quality(rid,2,runtime_root=runtime)
    req(q1['passed'] is False and q2['passed'] is True,'failed_then_passing_quality_evidence')
    diag=load_diagnostic_result(rid,1,runtime_root=runtime); req(diag['repair_supported'] and diag['preferred_hypothesis_code'],'diagnostic_reasoning_guided_repair')
    ps=(executed.get('persistent_development_session') or {}); sid=ps.get('session_id'); req(bool(sid),'persistent_session_attached')
    resumed=turn(f'Resume development session {sid}.',session,runtime)
    req(resumed['active'] and resumed['event'].startswith('persistent_development_session'),'restart_resume_is_observational')
    req(provider.calls==2,'resume_does_not_recontact_provider')
    prep=turn(f'Prepare controlled application for request {rid}.',session,runtime)
    req(prep['event']=='controlled_application_authorization_required','application_packet_prepared')
    app=prep['controlled_application']; req(app['application_execution_authorized'] is False,'application_preparation_grants_no_authority')
    req(tree_signature(project)==original,'project_unchanged_before_exact_apply')
    applied=turn(app['authorization_phrase'],session,runtime)
    req(applied['event']=='controlled_application_completed','exact_application_completes')
    ar=applied['controlled_application_result']; req(ar['verification_passed'] and ar['rollback_available'],'post_apply_verification_passes_and_rollback_available')
    applied_sig=tree_signature(project); req(applied_sig!=original,'project_changed_only_after_exact_apply')
    req((project/'app.js').is_file() and (project/'tests/app.test.js').is_file(),'complete_application_installed')
    replay=turn(app['authorization_phrase'],session,runtime); req(replay['event']=='controlled_application_completed','duplicate_apply_idempotent')
    req(tree_signature(project)==applied_sig,'duplicate_apply_changes_nothing')
    rbprep=turn(f'Prepare controlled rollback for request {rid}.',session,runtime)
    req(rbprep['event']=='controlled_rollback_authorization_required','rollback_packet_prepared')
    rb=rbprep['controlled_rollback']; req(rb['rollback_execution_authorized'] is False,'rollback_preparation_grants_no_authority')
    rolled=turn(rb['authorization_phrase'],session,runtime)
    req(rolled['event']=='controlled_rollback_completed','exact_rollback_completes')
    req(rolled['controlled_rollback_result']['rollback_verified'],'rollback_verified')
    req(tree_signature(project)==original,'rollback_restores_exact_pre_apply_tree')
    lineage=build_coding_alpha_lineage(rid,runtime_root=runtime)
    req(lineage['ok'] and lineage['attempt_count']==2 and lineage['repair_attempt_count']==1,'lineage_records_attempt_and_repair_counts')
    req(lineage['application_completed'] and lineage['rollback_completed'],'lineage_records_apply_and_rollback')
    req(lineage['release_authorized'] is False and lineage['independent_authority_granted'] is False,'lineage_grants_no_release_or_independent_authority')
print(json.dumps({'ok':True,'suite':'v1260.3-v1260.5-coding-alpha-campaign','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_calls':2,'repair_attempts':1,'application_completed':True,'rollback_completed':True,'release_authorized':False},indent=2,sort_keys=True))
