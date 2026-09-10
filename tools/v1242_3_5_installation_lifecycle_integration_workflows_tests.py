from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from installation_upgrade_backup_rollback_integration import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest()
c=[];ck=lambda v:c.append(bool(v))
with tempfile.TemporaryDirectory() as rt:
    p=prepare_installation_lifecycle_preflight('desktop-main',operation='upgrade',current_version='1241.9',target_version='1242.9',installation_state='healthy',compatibility_state='migration_required',backup_requirement='required',current_installation_digest=h('cur'),current_inventory_digest=h('inv'),target_artifact_digest=h('art'),target_manifest_digest=h('manifest'),compatibility_evidence_digest=h('compat'),runtime_schema_digest=h('schema'),lifecycle_policy_digest=h('policy'),runtime_root=rt)
    q=prepare_installation_lifecycle_proposal(p['preflight_id'],expected_preflight_digest=p['preflight_record_digest'],current_target_digest=h('cur'),backup_evidence_digest=h('backup'),backup_manifest_digest=h('backup-manifest'),backup_restore_verification_digest=h('restore-check'),migration_preview_digest=h('migration'),verification_plan_digest=h('verification'),rollback_plan_digest=h('rollback-plan'),rollback_target_digest=h('cur'),disk_space_evidence_digest=h('disk'),backup_verified=True,rollback_feasible=True,migration_reversible=True,estimated_change_count=42,runtime_root=rt)
    for v in (q['ok'],q['proposal_acceptable'],q['backup_verified'],q['rollback_feasible'],q['migration_reversible'],q['estimated_change_count']==42,len(q['stages'])==6,q['stages'][1]['stage']=='backup',q['stages'][1]['required'],q['stages'][2]['required'],q['verification_required_before_completion'],q['rollback_bound_to_exact_backup_and_target'],bool(q['proposal_record_digest'])):ck(v)
    phrase=f"Review lifecycle proposal accept_proposal for proposal {q['proposal_id']} digest {q['proposal_record_digest']}."
    review=review_installation_lifecycle_proposal(q['proposal_id'],expected_proposal_digest=q['proposal_record_digest'],disposition='accept_proposal',exact_phrase=phrase,runtime_root=rt)
    for v in (review['ok'],review['proposal_interpretation_accepted'],not review['operator_follow_up_required'],review['fresh_installation_authority_still_required'],not review['installation_authorized_by_review'],not review['upgrade_authorized_by_review'],not review['restore_authorized_by_review'],not review['rollback_authorized_by_review'],bool(review['review_record_digest'])):ck(v)
    replay=review_installation_lifecycle_proposal(q['proposal_id'],expected_proposal_digest=q['proposal_record_digest'],disposition='accept_proposal',exact_phrase=phrase,runtime_root=rt);ck(replay['review_id']==review['review_id']);ck(replay['review_record_digest']==review['review_record_digest'])
    recovery=prepare_installation_lifecycle_recovery_assessment(q['proposal_id'],expected_proposal_digest=q['proposal_record_digest'],proposal_review_id=review['review_id'],expected_review_digest=review['review_record_digest'],observed_state='apply_partial',transaction_evidence_digest=h('transaction'),observed_target_digest=h('partial-target'),observed_backup_digest=h('backup'),completed_stage_count=4,evidence_complete=True,runtime_root=rt)
    for v in (recovery['ok'],recovery['recommended_action']=='prepare_rollback_proposal',recovery['rollback_proposal_only'],not recovery['resume_proposal_only'],not recovery['automatic_resume_permitted'],not recovery['automatic_rollback_permitted'],bool(recovery['assessment_record_digest'])):ck(v)
    rphrase=f"Review lifecycle recovery acknowledge for assessment {recovery['assessment_id']} digest {recovery['assessment_record_digest']}."
    rr=review_installation_lifecycle_recovery(recovery['assessment_id'],expected_assessment_digest=recovery['assessment_record_digest'],disposition='acknowledge',exact_phrase=rphrase,runtime_root=rt)
    for v in (rr['ok'],rr['recovery_interpretation_acknowledged'],not rr['resume_authority_created'],not rr['rollback_authority_created'],rr['fresh_exact_recovery_authority_still_required']):ck(v)
    for factory,key,count in ((public_installation_lifecycle_preflights,'preflight_count',1),(public_installation_lifecycle_proposals,'proposal_count',1),(public_installation_lifecycle_reviews,'review_count',1),(public_installation_lifecycle_recovery_assessments,'recovery_assessment_count',1),(public_installation_lifecycle_recovery_reviews,'recovery_review_count',1)):
        row=factory(runtime_root=rt);ck(row['ok']);ck(row[key]==count);ck(row['content_free'])
    for text in ('show installation lifecycle registry','show installation lifecycle preflights','show installation lifecycle proposals','show installation lifecycle reviews','show installation lifecycle recovery assessments','show installation lifecycle recovery reviews'):
        turn=process_ordinary_chat_development_turn(text,runtime_root=rt);ck(turn.get('active'));ck('installation_lifecycle' in turn);ck('No installation' in turn['response'] or 'read-only inspection' in turn['response'])
    turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt);ck(turn.get('active'));ck(turn['installation_lifecycle']['review_id']==review['review_id']);ck('No installation' in turn['response'])
    turn=process_ordinary_chat_development_turn(rphrase,runtime_root=rt);ck(turn.get('active'));ck(turn['installation_lifecycle']['review_id']==rr['review_id']);ck('No installation' in turn['response'])
    dash=installation_lifecycle_dashboard_record(runtime_root=rt);ck(dash['panel_id']=='lifecycle');ck(dash['read_only']);ck(not dash['installation_authorized']);ck(bool(dash['record_digest']))
    page=render_installation_lifecycle_dashboard_html(runtime_root=rt)
    for token in ('Installation Lifecycle Integration','GET-only inspection','Fresh exact authority required','/api/cognition/installation-lifecycle-registry'):ck(token in page)
for k,e in AUTHORITY_FLAGS.items():ck(q.get(k) is e and review.get(k) is e and recovery.get(k) is e and rr.get(k) is e)
source={name:(R/name).read_text(encoding='utf-8') for name in ('conscious_agent/api_server.py','eidolon.py','conscious_agent/dashboard.py','conscious_agent/ordinary_chat_development_campaign.py')}
for token in ('installation-lifecycle-registry','installation-lifecycle-preflights','installation-lifecycle-proposals','installation-lifecycle-recovery-assessments','installation-lifecycle-integration-checkpoint'):ck(token in source['conscious_agent/api_server.py'] and token in source['eidolon.py'])
ck('/installation-lifecycle' in source['conscious_agent/dashboard.py']);ck('/api/installation-lifecycle' in source['conscious_agent/dashboard.py']);ck('process_installation_lifecycle_control' in source['conscious_agent/ordinary_chat_development_campaign.py'])
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
