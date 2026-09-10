from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from long_running_multi_day_session_continuity import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest(); c=[]; ck=lambda v:c.append(bool(v))
def evidence(seed='x'):
    return {scope:h(seed+scope) for scope in FRESHNESS_SCOPES}
reg=long_running_session_continuity_registry(); contract=build_long_running_session_continuity_contract()
for v in (reg['ok'],reg['inspection_only'],len(reg['session_states'])==6,len(reg['stop_reasons'])==11,len(reg['freshness_scopes'])==10,reg['default_freshness_windows_days']['authorization']==0,bool(reg['registry_digest']),contract['ok'],contract['durable_session_epochs'],contract['progress_checkpoint_lineage'],contract['sequential_manifest_generations_required'],contract['freshness_windows_enforced'],contract['old_authority_never_reused'],contract['resume_requires_fresh_exact_separate_authority']): ck(v)
for k,e in AUTHORITY_FLAGS.items(): ck(reg.get(k) is e and contract.get(k) is e)
with tempfile.TemporaryDirectory() as rt:
    p1=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('s'),checkpoint_index=1,logical_day=3,progress_state='in_progress',stage_code='tool_step_one',completed_evidence_digests=[h('a'),h('b')],incomplete_work_codes=['step_two'],pending_review_codes=['operator_review'],runtime_root=rt)
    for v in (p1['ok'],p1['checkpoint_index']==1,p1['completed_evidence_count']==2,p1['incomplete_work_count']==1,p1['pending_review_count']==1,bool(p1['progress_record_digest']),not p1['resume_authorized']):ck(v)
    same=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('s'),checkpoint_index=1,logical_day=3,progress_state='in_progress',stage_code='tool_step_one',completed_evidence_digests=[h('b'),h('a')],incomplete_work_codes=['step_two'],pending_review_codes=['operator_review'],runtime_root=rt)
    ck(same['progress_id']==p1['progress_id']); ck(same['progress_record_digest']==p1['progress_record_digest'])
    p2=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('s'),checkpoint_index=2,logical_day=3,progress_state='paused',stage_code='safe_boundary',completed_evidence_digests=[h('c')],incomplete_work_codes=['step_three'],previous_progress_id=p1['progress_id'],previous_progress_digest=p1['progress_record_digest'],runtime_root=rt)
    ck(p2['ok']);ck(p2['checkpoint_index']==2);ck(p2['previous_progress_id']==p1['progress_id'])
    m=prepare_session_continuity_manifest('project_alpha','session_alpha',session_digest=h('s'),session_state='paused',stop_reason='end_of_day',logical_day=3,continuity_generation=1,latest_progress_id=p2['progress_id'],expected_progress_digest=p2['progress_record_digest'],evidence_digests=evidence(),freshness_windows_days={'plan':14,'provider':2},completed_work_codes=['step_one','step_two'],remaining_work_codes=['step_three'],changed_assumption_codes=[],uncertainty_codes=['provider_health_tomorrow'],runtime_root=rt)
    for v in (m['ok'],m['session_state']=='paused',m['stop_reason']=='end_of_day',m['completed_work_count']==2,m['remaining_work_count']==1,m['uncertainty_count']==1,m['freshness_windows_days']['plan']==14,m['freshness_windows_days']['authorization']==0,m['resume_eligibility_not_evaluated'],bool(m['continuity_manifest_record_digest'])):ck(v)
    same_m=prepare_session_continuity_manifest('project_alpha','session_alpha',session_digest=h('s'),session_state='paused',stop_reason='end_of_day',logical_day=3,continuity_generation=1,latest_progress_id=p2['progress_id'],expected_progress_digest=p2['progress_record_digest'],evidence_digests=evidence(),freshness_windows_days={'provider':2,'plan':14},completed_work_codes=['step_two','step_one'],remaining_work_codes=['step_three'],uncertainty_codes=['provider_health_tomorrow'],runtime_root=rt)
    ck(same_m['manifest_id']==m['manifest_id']);ck(same_m['continuity_manifest_record_digest']==m['continuity_manifest_record_digest'])
    p3=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('s'),checkpoint_index=3,logical_day=4,progress_state='paused',stage_code='next_day_boundary',previous_progress_id=p2['progress_id'],previous_progress_digest=p2['progress_record_digest'],runtime_root=rt)
    m2=prepare_session_continuity_manifest('project_alpha','session_alpha',session_digest=h('s'),session_state='paused',stop_reason='operator_absence',logical_day=4,continuity_generation=2,latest_progress_id=p3['progress_id'],expected_progress_digest=p3['progress_record_digest'],evidence_digests=evidence('next'),previous_manifest_id=m['manifest_id'],previous_manifest_digest=m['continuity_manifest_record_digest'],runtime_root=rt)
    ck(p3['ok']);ck(m2['ok']);ck(m2['continuity_generation']==2);ck(m2['previous_manifest_id']==m['manifest_id'])
    missing_prev=prepare_session_continuity_manifest('project_alpha','session_alpha',session_digest=h('s'),session_state='paused',stop_reason='operator_absence',logical_day=4,continuity_generation=2,latest_progress_id=p3['progress_id'],expected_progress_digest=p3['progress_record_digest'],evidence_digests=evidence('next'),runtime_root=rt)
    ck(not missing_prev['ok']);ck(missing_prev['reason']=='previous_manifest_required')
    pubp=public_session_continuity_progress(runtime_root=rt); pubm=public_session_continuity_manifests(runtime_root=rt); dash=session_continuity_dashboard_record(runtime_root=rt); page=render_session_continuity_dashboard_html(runtime_root=rt)
    for v in (pubp['count']==3,pubm['count']==2,dash['read_only'],dash['get_only'],dash['progress_checkpoint_count']==3,dash['manifest_count']==2,'Long-Running and Multi-Day Session Continuity' in page,'GET-only inspection' in page):ck(v)
    for k,e in AUTHORITY_FLAGS.items():ck(p1.get(k) is e and p2.get(k) is e and m.get(k) is e and dash.get(k) is e)
for state in sorted(SESSION_STATES):
    with tempfile.TemporaryDirectory() as rt:
        p=record_session_progress_checkpoint('project_beta','session_beta',session_digest=h(state),checkpoint_index=1,logical_day=1,progress_state='paused' if state!='completed' else 'completed',stage_code='checkpoint',runtime_root=rt)
        m=prepare_session_continuity_manifest('project_beta','session_beta',session_digest=h(state),session_state=state,stop_reason='manual_handoff',logical_day=1,continuity_generation=1,latest_progress_id=p['progress_id'],expected_progress_digest=p['progress_record_digest'],evidence_digests=evidence(state),runtime_root=rt)
        ck(m['ok']);ck(m['session_state']==state)
for reason in sorted(STOP_REASONS):
    with tempfile.TemporaryDirectory() as rt:
        p=record_session_progress_checkpoint('project_gamma','session_gamma',session_digest=h(reason),checkpoint_index=1,logical_day=2,progress_state='paused',stage_code='safe_boundary',runtime_root=rt)
        m=prepare_session_continuity_manifest('project_gamma','session_gamma',session_digest=h(reason),session_state='paused',stop_reason=reason,logical_day=2,continuity_generation=1,latest_progress_id=p['progress_id'],expected_progress_digest=p['progress_record_digest'],evidence_digests=evidence(reason),runtime_root=rt)
        ck(m['ok']);ck(m['stop_reason']==reason)
invalid=[
    lambda rt:record_session_progress_checkpoint('project_secret_token','session_a',session_digest=h('s'),checkpoint_index=1,logical_day=0,progress_state='paused',stage_code='x',runtime_root=rt),
    lambda rt:record_session_progress_checkpoint('project_a','session_a',session_digest='bad',checkpoint_index=1,logical_day=0,progress_state='paused',stage_code='x',runtime_root=rt),
    lambda rt:record_session_progress_checkpoint('project_a','session_a',session_digest=h('s'),checkpoint_index=2,logical_day=0,progress_state='paused',stage_code='x',runtime_root=rt),
    lambda rt:record_session_progress_checkpoint('project_a','session_a',session_digest=h('s'),checkpoint_index=1,logical_day=-1,progress_state='paused',stage_code='x',runtime_root=rt),
]
for fn in invalid:
    with tempfile.TemporaryDirectory() as rt:
        row=fn(rt);ck(not row['ok']);ck(row['status'].endswith('blocked'))
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
