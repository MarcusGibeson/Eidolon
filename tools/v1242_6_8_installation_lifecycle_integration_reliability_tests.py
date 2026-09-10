from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from installation_upgrade_backup_rollback_integration import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest()
c=[];ck=lambda v:c.append(bool(v))
def fixture(rt,compat='migration_required'):
 p=prepare_installation_lifecycle_preflight('desktop-main',operation='upgrade',current_version='1241.9',target_version='1242.9',installation_state='healthy',compatibility_state=compat,backup_requirement='required',current_installation_digest=h('cur'),current_inventory_digest=h('inv'),target_artifact_digest=h('art'),target_manifest_digest=h('manifest'),compatibility_evidence_digest=h('compat'),runtime_schema_digest=h('schema'),lifecycle_policy_digest=h('policy'),runtime_root=rt)
 q=prepare_installation_lifecycle_proposal(p['preflight_id'],expected_preflight_digest=p['preflight_record_digest'],current_target_digest=h('cur'),backup_evidence_digest=h('backup'),backup_manifest_digest=h('backup-manifest'),backup_restore_verification_digest=h('restore-check'),migration_preview_digest=h('migration') if compat=='migration_required' else '',verification_plan_digest=h('verify'),rollback_plan_digest=h('rollback'),rollback_target_digest=h('cur'),disk_space_evidence_digest=h('disk'),backup_verified=True,rollback_feasible=True,migration_reversible=True,estimated_change_count=5,runtime_root=rt)
 phrase=f"Review lifecycle proposal accept_proposal for proposal {q['proposal_id']} digest {q['proposal_record_digest']}."
 r=review_installation_lifecycle_proposal(q['proposal_id'],expected_proposal_digest=q['proposal_record_digest'],disposition='accept_proposal',exact_phrase=phrase,runtime_root=rt)
 return p,q,r
with tempfile.TemporaryDirectory() as rt:
 p,q,r=fixture(rt)
 cases=[
  dict(expected_preflight_digest=h('stale'),current_target_digest=h('cur'),backup_evidence_digest=h('backup'),backup_manifest_digest=h('bm'),backup_restore_verification_digest=h('rv'),migration_preview_digest=h('m'),verification_plan_digest=h('v'),rollback_plan_digest=h('rp'),rollback_target_digest=h('cur'),disk_space_evidence_digest=h('d'),backup_verified=True,rollback_feasible=True,migration_reversible=True,estimated_change_count=1),
  dict(expected_preflight_digest=p['preflight_record_digest'],current_target_digest=h('changed'),backup_evidence_digest=h('backup'),backup_manifest_digest=h('bm'),backup_restore_verification_digest=h('rv'),migration_preview_digest=h('m'),verification_plan_digest=h('v'),rollback_plan_digest=h('rp'),rollback_target_digest=h('cur'),disk_space_evidence_digest=h('d'),backup_verified=True,rollback_feasible=True,migration_reversible=True,estimated_change_count=1),
  dict(expected_preflight_digest=p['preflight_record_digest'],current_target_digest=h('cur'),backup_evidence_digest=h('backup'),backup_manifest_digest=h('bm'),backup_restore_verification_digest=h('rv'),migration_preview_digest=h('m'),verification_plan_digest=h('v'),rollback_plan_digest=h('rp'),rollback_target_digest=h('cur'),disk_space_evidence_digest=h('d'),backup_verified=False,rollback_feasible=True,migration_reversible=True,estimated_change_count=1),
  dict(expected_preflight_digest=p['preflight_record_digest'],current_target_digest=h('cur'),backup_evidence_digest=h('backup'),backup_manifest_digest=h('bm'),backup_restore_verification_digest=h('rv'),migration_preview_digest=h('m'),verification_plan_digest=h('v'),rollback_plan_digest=h('rp'),rollback_target_digest=h('cur'),disk_space_evidence_digest=h('d'),backup_verified=True,rollback_feasible=False,migration_reversible=True,estimated_change_count=1),
  dict(expected_preflight_digest=p['preflight_record_digest'],current_target_digest=h('cur'),backup_evidence_digest=h('backup'),backup_manifest_digest=h('bm'),backup_restore_verification_digest=h('rv'),migration_preview_digest='',verification_plan_digest=h('v'),rollback_plan_digest=h('rp'),rollback_target_digest=h('cur'),disk_space_evidence_digest=h('d'),backup_verified=True,rollback_feasible=True,migration_reversible=False,estimated_change_count=1),
 ]
 for args in cases:
  row=prepare_installation_lifecycle_proposal(p['preflight_id'],runtime_root=rt,**args);ck(not row['ok']);ck(not row.get('installation_authorized'));ck(not row.get('rollback_authorized'))
 badphrase=review_installation_lifecycle_proposal(q['proposal_id'],expected_proposal_digest=q['proposal_record_digest'],disposition='accept_proposal',exact_phrase='accept it',runtime_root=rt);ck(not badphrase['ok']);ck(badphrase['reason']=='exact_review_phrase_required')
 stale=review_installation_lifecycle_proposal(q['proposal_id'],expected_proposal_digest=h('stale'),disposition='hold',exact_phrase=f"Review lifecycle proposal hold for proposal {q['proposal_id']} digest {h('stale')}.",runtime_root=rt);ck(not stale['ok']);ck(stale['reason']=='stale_or_mismatched_proposal_digest')
 path=Path(rt)/'development_campaign'/'installation_lifecycle_proposals'/f"{q['proposal_id']}.json"
 # store root may be runtime root itself depending contract; locate it robustly
 matches=list(Path(rt).rglob(f"{q['proposal_id']}.json"));ck(len(matches)==1)
 raw=json.loads(matches[0].read_text());raw['target_version']='9999.9';matches[0].write_text(json.dumps(raw))
 tampered=load_installation_lifecycle_proposal(q['proposal_id'],runtime_root=rt);ck(not tampered['ok']);ck(tampered['status']=='installation_lifecycle_proposal_tampered')
with tempfile.TemporaryDirectory() as rt:
 p,q,r=fixture(rt)
 for state,complete,backup,action in [('backup_complete',True,'backup','prepare_resume_proposal'),('migration_partial',True,'backup','prepare_resume_proposal'),('interrupted',True,'backup','prepare_resume_proposal'),('apply_partial',True,'backup','prepare_rollback_proposal'),('verification_failed',True,'backup','prepare_rollback_proposal'),('unknown',False,'backup','hold_for_evidence'),('complete',True,'backup','no_action')]:
  a=prepare_installation_lifecycle_recovery_assessment(q['proposal_id'],expected_proposal_digest=q['proposal_record_digest'],proposal_review_id=r['review_id'],expected_review_digest=r['review_record_digest'],observed_state=state,transaction_evidence_digest=h('txn'+state),observed_target_digest=h('target'+state),observed_backup_digest=h(backup),completed_stage_count=2,evidence_complete=complete,runtime_root=rt)
  ck(a['recommended_action']==action);ck(not a['automatic_resume_permitted']);ck(not a['automatic_rollback_permitted']);ck(not a['resume_authorized']);ck(not a['rollback_authorized'])
 mismatch=prepare_installation_lifecycle_recovery_assessment(q['proposal_id'],expected_proposal_digest=q['proposal_record_digest'],proposal_review_id=r['review_id'],expected_review_digest=r['review_record_digest'],observed_state='apply_partial',transaction_evidence_digest=h('txn'),observed_target_digest=h('target'),observed_backup_digest=h('wrong'),completed_stage_count=3,evidence_complete=True,runtime_root=rt);ck(not mismatch['ok']);ck('backup_digest_mismatch' in mismatch['issue_codes']);ck(mismatch['recommended_action']=='manual_reconciliation_required')
 stale=prepare_installation_lifecycle_recovery_assessment(q['proposal_id'],expected_proposal_digest=h('stale'),proposal_review_id=r['review_id'],expected_review_digest=r['review_record_digest'],observed_state='interrupted',transaction_evidence_digest=h('txn'),observed_target_digest=h('target'),observed_backup_digest=h('backup'),completed_stage_count=1,evidence_complete=True,runtime_root=rt);ck(not stale['ok']);ck(stale['reason']=='stale_or_mismatched_recovery_lineage')
for bad in ('private/path','secret-token','../escape','a'):
 with tempfile.TemporaryDirectory() as rt:
  row=prepare_installation_lifecycle_preflight(bad,operation='install',current_version='none',target_version='1242.9',installation_state='absent',compatibility_state='compatible',backup_requirement='not_applicable',current_installation_digest='',current_inventory_digest='',target_artifact_digest=h('a'),target_manifest_digest=h('b'),compatibility_evidence_digest=h('c'),runtime_schema_digest=h('d'),lifecycle_policy_digest=h('e'),runtime_root=rt);ck(not row['ok'])
for k,e in AUTHORITY_FLAGS.items():ck(lifecycle_operation_registry().get(k) is e)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
