from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from long_running_multi_day_session_continuity import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
def evidence(seed='x'): return {scope:h(seed+scope) for scope in FRESHNESS_SCOPES}
def fixture(rt,*,day=1,state='paused',windows=None,changed=()):
    p=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('session'),checkpoint_index=1,logical_day=day,progress_state='paused',stage_code='end_of_day',completed_evidence_digests=[h('done')],incomplete_work_codes=['step_two'],runtime_root=rt)
    m=prepare_session_continuity_manifest('project_alpha','session_alpha',session_digest=h('session'),session_state=state,stop_reason='end_of_day',logical_day=day,continuity_generation=1,latest_progress_id=p['progress_id'],expected_progress_digest=p['progress_record_digest'],evidence_digests=evidence(),freshness_windows_days=windows,completed_work_codes=['step_one'],remaining_work_codes=['step_two'],changed_assumption_codes=changed,runtime_root=rt)
    return p,m
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt)
    a=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=2,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt)
    for v in (a['ok'],a['assessment_state']=='eligible_for_resume_proposal',a['resume_proposal_eligible'],a['stale_scopes']==['authorization'],not a['changed_scopes'],not a['missing_scopes'],a['fresh_resume_authorization_required'],a['old_authorization_explicitly_nonreusable'],not a['resume_authorized'],bool(a['continuity_assessment_record_digest'])):ck(v)
    phrase=f"Review session continuity accept_resume_proposal for assessment {a['assessment_id']} digest {a['continuity_assessment_record_digest']}."
    r=review_session_continuity_assessment(a['assessment_id'],expected_assessment_digest=a['continuity_assessment_record_digest'],disposition='accept_resume_proposal',exact_phrase=phrase,runtime_root=rt)
    for v in (r['ok'],r['resume_proposal_interpretation_accepted'],r['fresh_resume_authority_still_required'],not r['resume_authority_created'],not r['provider_authority_created'],not r['tool_authority_created'],not r['resource_claim_created'],not r['resume_authorized'],bool(r['continuity_review_record_digest'])):ck(v)
    replay=review_session_continuity_assessment(a['assessment_id'],expected_assessment_digest=a['continuity_assessment_record_digest'],disposition='accept_resume_proposal',exact_phrase=phrase,runtime_root=rt);ck(replay['review_id']==r['review_id']);ck(replay['continuity_review_record_digest']==r['continuity_review_record_digest'])
    turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt);ck(turn.get('active'));ck(turn['session_continuity']['review_id']==r['review_id']);ck('No session resumed' in turn['response'])
    for text,key,count in [('Show long running session continuity registry.','session_continuity',None),('Show session continuity progress checkpoints.','session_continuity',1),('Show session continuity manifests.','session_continuity',1),('Show session continuity assessments.','session_continuity',1),('Show session continuity reviews.','session_continuity',1)]:
        t=process_ordinary_chat_development_turn(text,runtime_root=rt);ck(t.get('active'));ck(key in t);ck(t.get('action_taken') is False)
        if count is not None:ck(t[key].get('count')==count)
    dash=session_continuity_dashboard_record(runtime_root=rt);page=render_session_continuity_dashboard_html(runtime_root=rt)
    for v in (dash['assessment_count']==1,dash['review_count']==1,dash['manifest_count']==1,dash['progress_checkpoint_count']==1,not dash['resume_authorized'],'GET-only inspection' in page):ck(v)
    for decision in ('hold','reject','request_changes'):
        xphrase=f"Review session continuity {decision} for assessment {a['assessment_id']} digest {a['continuity_assessment_record_digest']}."
        x=review_session_continuity_assessment(a['assessment_id'],expected_assessment_digest=a['continuity_assessment_record_digest'],disposition=decision,exact_phrase=xphrase,runtime_root=rt)
        ck(x['ok']);ck(x['disposition']==decision);ck(not x['resume_proposal_interpretation_accepted']);ck(not x['resume_authorized'])
    for k,e in AUTHORITY_FLAGS.items():ck(a.get(k) is e and r.get(k) is e and dash.get(k) is e)
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt,windows={'provider':0})
    a=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=2,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt)
    ck(a['assessment_state']=='revalidation_required');ck('provider' in a['stale_scopes']);ck(not a['resume_proposal_eligible']);ck(a['provider_revalidation_required'])
    phrase=f"Review session continuity accept_resume_proposal for assessment {a['assessment_id']} digest {a['continuity_assessment_record_digest']}."
    blocked=review_session_continuity_assessment(a['assessment_id'],expected_assessment_digest=a['continuity_assessment_record_digest'],disposition='accept_resume_proposal',exact_phrase=phrase,runtime_root=rt);ck(not blocked['ok']);ck(blocked['reason']=='assessment_not_eligible_for_resume_proposal')
source={n:(R/n).read_text(encoding='utf-8') for n in ('conscious_agent/api_server.py','eidolon.py','conscious_agent/dashboard.py','conscious_agent/ordinary_chat_development_campaign.py','conscious_agent/unified_operator_dashboard.py')}
for token in ('long-running-session-continuity-registry','session-continuity-progress','session-continuity-manifests','session-continuity-assessments','session-continuity-reviews','long-running-multi-day-session-continuity-checkpoint'):
    ck(token in source['conscious_agent/api_server.py']);ck(token in source['eidolon.py'])
ck('/session-continuity' in source['conscious_agent/dashboard.py']);ck('/api/session-continuity' in source['conscious_agent/dashboard.py']);ck('process_session_continuity_control' in source['conscious_agent/ordinary_chat_development_campaign.py']);ck('session-continuity-assessments' in source['conscious_agent/unified_operator_dashboard.py'])
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
