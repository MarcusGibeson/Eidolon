from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from long_running_multi_day_session_continuity import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
def evidence(seed='x'): return {scope:h(seed+scope) for scope in FRESHNESS_SCOPES}
def fixture(rt,*,changed=(),state='paused',windows=None):
    p=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('session'),checkpoint_index=1,logical_day=4,progress_state='paused',stage_code='safe_boundary',runtime_root=rt)
    m=prepare_session_continuity_manifest('project_alpha','session_alpha',session_digest=h('session'),session_state=state,stop_reason='machine_shutdown',logical_day=4,continuity_generation=1,latest_progress_id=p['progress_id'],expected_progress_digest=p['progress_record_digest'],evidence_digests=evidence(),freshness_windows_days=windows,remaining_work_codes=['step_two'],changed_assumption_codes=changed,runtime_root=rt)
    return p,m
# state routing cases
cases=[]
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt)
    cur=evidence();cur['plan']=h('changed-plan')
    cases.append(prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=cur,available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt))
    ck(cases[-1]['assessment_state']=='plan_revision_required');ck('plan' in cases[-1]['changed_scopes']);ck(not cases[-1]['resume_proposal_eligible'])
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt)
    av=[s for s in FRESHNESS_SCOPES if s!='workspace'];cur=evidence();cur['workspace']=''
    a=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=cur,available_scope_codes=av,runtime_root=rt)
    ck(a['assessment_state']=='workspace_recovery_required');ck('workspace' in a['missing_scopes']);ck(not a['resume_proposal_eligible'])
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt)
    a=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,contradiction_codes=['provider_claim_conflict'],runtime_root=rt)
    ck(a['assessment_state']=='manual_reconciliation_required');ck(a['contradiction_codes']==['provider_claim_conflict']);ck(not a['resume_proposal_eligible'])
for state in ('cancelled','completed','failed'):
    with tempfile.TemporaryDirectory() as rt:
        p,m=fixture(rt,state=state)
        a=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state=state,current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt)
        ck(a['assessment_state']=='terminal');ck(not a['resume_proposal_eligible']);ck(not a['resume_authorized'])
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt)
    clock=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=3,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),runtime_root=rt);ck(not clock['ok']);ck(clock['reason']=='clock_moved_before_manifest')
    stale=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=h('stale'),current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),runtime_root=rt);ck(not stale['ok']);ck(stale['reason']=='stale_or_mismatched_manifest_digest')
    changed_session=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('other-session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt);ck('session' in changed_session['changed_scopes']);ck(not changed_session['resume_proposal_eligible'])
    dup=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt)
    dup2=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt);ck(dup['assessment_id']==dup2['assessment_id']);ck(dup['continuity_assessment_record_digest']==dup2['continuity_assessment_record_digest'])
# tamper each family
for family in ('progress','manifest','assessment','review'):
    with tempfile.TemporaryDirectory() as rt:
        p,m=fixture(rt);a=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt)
        phrase=f"Review session continuity accept_resume_proposal for assessment {a['assessment_id']} digest {a['continuity_assessment_record_digest']}.";r=review_session_continuity_assessment(a['assessment_id'],expected_assessment_digest=a['continuity_assessment_record_digest'],disposition='accept_resume_proposal',exact_phrase=phrase,runtime_root=rt)
        obj={'progress':p,'manifest':m,'assessment':a,'review':r}[family]; rid={'progress':'progress_id','manifest':'manifest_id','assessment':'assessment_id','review':'review_id'}[family]; loader={'progress':load_session_progress_checkpoint,'manifest':load_session_continuity_manifest,'assessment':load_session_continuity_assessment,'review':load_session_continuity_review}[family]
        matches=list(Path(rt).rglob(obj[rid]+'.json'));ck(len(matches)==1);raw=json.loads(matches[0].read_text());raw['project_id']='project_tampered';matches[0].write_text(json.dumps(raw));loaded=loader(obj[rid],runtime_root=rt);ck(not loaded['ok']);ck('tampered' in loaded['status'])
# cross-session manifest generations and active-state non-resume
with tempfile.TemporaryDirectory() as rt:
    pa,ma=fixture(rt)
    pb=record_session_progress_checkpoint('project_beta','session_beta',session_digest=h('beta'),checkpoint_index=1,logical_day=5,progress_state='paused',stage_code='safe_boundary',runtime_root=rt)
    cross_manifest=prepare_session_continuity_manifest('project_beta','session_beta',session_digest=h('beta'),session_state='paused',stop_reason='manual_handoff',logical_day=5,continuity_generation=2,latest_progress_id=pb['progress_id'],expected_progress_digest=pb['progress_record_digest'],evidence_digests=evidence('beta'),previous_manifest_id=ma['manifest_id'],previous_manifest_digest=ma['continuity_manifest_record_digest'],runtime_root=rt)
    ck(not cross_manifest['ok']);ck(cross_manifest['reason']=='cross_session_manifest_lineage')
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt,state='active')
    active=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='active',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt)
    ck(active['ok']);ck(not active['resume_proposal_eligible']);ck(not active['resume_authorized'])
# cross-session progression and private inputs
with tempfile.TemporaryDirectory() as rt:
    p=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('s'),checkpoint_index=1,logical_day=1,progress_state='paused',stage_code='step_x',runtime_root=rt)
    cross=record_session_progress_checkpoint('project_alpha','session_beta',session_digest=h('s'),checkpoint_index=2,logical_day=1,progress_state='paused',stage_code='step_x',previous_progress_id=p['progress_id'],previous_progress_digest=p['progress_record_digest'],runtime_root=rt);ck(not cross['ok']);ck(cross['reason']=='cross_session_progress_lineage')
for bad in ('private_path','secret_token','../escape','x'):
    with tempfile.TemporaryDirectory() as rt:
        row=record_session_progress_checkpoint('project_'+bad,'session_alpha',session_digest=h('s'),checkpoint_index=1,logical_day=1,progress_state='paused',stage_code='step_x',runtime_root=rt);ck(not row['ok'])
# wrong phrase and stale review digest
with tempfile.TemporaryDirectory() as rt:
    p,m=fixture(rt);a=prepare_session_continuity_reconciliation(m['manifest_id'],expected_manifest_digest=m['continuity_manifest_record_digest'],current_logical_day=5,current_session_state='paused',current_session_digest=h('session'),current_evidence_digests=evidence(),available_scope_codes=FRESHNESS_SCOPES,runtime_root=rt)
    wrong=review_session_continuity_assessment(a['assessment_id'],expected_assessment_digest=a['continuity_assessment_record_digest'],disposition='hold',exact_phrase='hold it',runtime_root=rt);ck(not wrong['ok']);ck(wrong['reason']=='exact_review_phrase_required')
    stale=review_session_continuity_assessment(a['assessment_id'],expected_assessment_digest=h('stale'),disposition='hold',exact_phrase=f"Review session continuity hold for assessment {a['assessment_id']} digest {h('stale')}.",runtime_root=rt);ck(not stale['ok']);ck(stale['reason']=='stale_or_mismatched_assessment_digest')
    for key in ('private_path_exposed','private_content_exposed','raw_provider_output_exposed','raw_tool_output_exposed','raw_test_output_exposed','automatic_retry_created','automatic_resume_created','session_resumed'):ck(a.get(key) is False)
for row in cases+[long_running_session_continuity_registry(),build_long_running_session_continuity_contract()]:
    for k,e in AUTHORITY_FLAGS.items():ck(row.get(k) is e)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
