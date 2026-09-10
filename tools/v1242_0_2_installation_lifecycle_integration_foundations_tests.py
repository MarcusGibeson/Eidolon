from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from installation_upgrade_backup_rollback_integration import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest()
c=[]; ck=lambda v:c.append(bool(v))
reg=lifecycle_operation_registry(); contract=build_installation_lifecycle_integration_contract()
for v in (reg['ok'],reg['operation_count']==4,{x['operation'] for x in reg['operations']}==OPERATIONS,reg['inspection_only'],bool(reg['registry_digest']),contract['ok'],contract['retained_lifecycle_module_count']==7,contract['exact_target_version_artifact_manifest_binding'],contract['backup_before_existing_installation_mutation'],contract['rollback_bound_to_exact_backup_and_target']):ck(v)
for k,e in AUTHORITY_FLAGS.items(): ck(reg.get(k) is e and contract.get(k) is e)

def pre(rt,op='upgrade',state='healthy',compat='migration_required',backup='required',cur='1241.9',target='1242.9',**kw):
    return prepare_installation_lifecycle_preflight('desktop-main',operation=op,current_version=cur,target_version=target,installation_state=state,compatibility_state=compat,backup_requirement=backup,current_installation_digest='' if op=='install' else h('cur'),current_inventory_digest='' if op=='install' else h('inv'),target_artifact_digest=h('art'),target_manifest_digest=h('manifest'),compatibility_evidence_digest=h('compat'),runtime_schema_digest=h('schema'),lifecycle_policy_digest=h('policy'),runtime_root=rt,**kw)
with tempfile.TemporaryDirectory() as rt:
    good=pre(rt)
    for v in (good['ok'],good['preflight_acceptable'],good['backup_must_precede_mutation'],good['migration_preview_required'],good['status'].endswith('ready_for_operator_review'),bool(good['preflight_record_digest']),good['operation']=='upgrade',good['current_version']=='1241.9',good['target_version']=='1242.9',good['issue_count']==0):ck(v)
    for k,e in AUTHORITY_FLAGS.items():ck(good.get(k) is e)
    same=pre(rt); ck(same['preflight_id']==good['preflight_id']);ck(same['preflight_record_digest']==good['preflight_record_digest'])
with tempfile.TemporaryDirectory() as rt:
    install=pre(rt,op='install',state='absent',compat='compatible',backup='not_applicable',cur='none')
    for v in (install['ok'],not install['backup_must_precede_mutation'],not install['migration_preview_required'],install['current_installation_digest']=='',install['current_inventory_digest']==''):ck(v)
for args,issue in [
    (dict(op='install',state='healthy',compat='compatible',backup='not_applicable',cur='none'),'install_requires_absent_target'),
    (dict(op='upgrade',state='healthy',compat='compatible',backup='optional'),'backup_required_for_mutating_existing_installation'),
    (dict(op='upgrade',state='healthy',compat='compatible',backup='required',cur='1242.9',target='1242.9'),'upgrade_version_transition_required'),
    (dict(op='upgrade',state='healthy',compat='incompatible',backup='required'),'target_incompatible'),
    (dict(op='upgrade',state='healthy',compat='unknown',backup='required'),'compatibility_evidence_missing'),
    (dict(op='upgrade',state='partial',compat='compatible',backup='required'),'unhealthy_installation_requires_recovery_review'),
    (dict(op='restore',state='absent',compat='compatible',backup='required',cur='none'),'existing_installation_required'),
]:
    with tempfile.TemporaryDirectory() as rt:
        row=pre(rt,**args);ck(not row['ok']);ck(issue in row['issue_codes']);ck(not row['preflight_acceptable'])
with tempfile.TemporaryDirectory() as rt:
    bad=prepare_installation_lifecycle_preflight('../private/path',operation='upgrade',current_version='1241.9',target_version='1242.9',installation_state='healthy',compatibility_state='compatible',backup_requirement='required',current_installation_digest=h('a'),current_inventory_digest=h('b'),target_artifact_digest=h('c'),target_manifest_digest=h('d'),compatibility_evidence_digest=h('e'),runtime_schema_digest=h('f'),lifecycle_policy_digest=h('g'),runtime_root=rt)
    ck(not bad['ok']);ck(bad['reason']=='invalid_target_reference')
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
