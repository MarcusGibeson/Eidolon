from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1300-test-'))
from v1269_fixture import approved_chain
from governed_self_update_foundations import prepare_governed_self_update
from governed_self_update import authorize_and_apply_governed_self_update
from isolated_self_modification_foundations import source_only_manifest
from automated_recovery_foundations import prepare_recovery_contract,recovery_trigger
from automated_recovery import perform_automatic_recovery
from supervised_self_development_beta import evaluate_supervised_self_development_beta
from v1300_test_support import identity,steps,d
checks=[]
def req(v,n):checks.append(n);assert v,n
# Actual exact-authorized update on a disposable source tree, never the Eidolon source under development.
with tempfile.TemporaryDirectory(prefix='eidolon-v1300-exact-update-') as td:
 base=Path(td);chain=approved_chain(base);rt=base/'update';u=prepare_governed_self_update(chain['packet']['review_id'],chain['source'],self_modification_runtime_root=chain['sm'],review_runtime_root=chain['review_rt'],runtime_root=rt);before=source_only_manifest(chain['source'])['source_manifest_digest']
 bad=authorize_and_apply_governed_self_update(u['update_id'],chain['source'],runtime_root=rt,authorization_phrase='go ahead',restart_health_verifier=lambda root,digest:{'ok':True});req(not bad['ok'] and bad['status']=='governed_self_update_exact_authorization_required','generic_rejected');req(source_only_manifest(chain['source'])['source_manifest_digest']==before,'generic_no_write')
 exact=authorize_and_apply_governed_self_update(u['update_id'],chain['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=lambda root,digest:{'ok':True});req(exact['ok'] and exact['status']=='governed_self_update_applied_and_verified','exact_update');req(source_only_manifest(chain['source'])['source_manifest_digest']==u['candidate_manifest_digest'],'candidate_installed');req(exact['release_authorized'] is False,'update_not_release')
 # Then simulate a defined post-update regression and use v1297 exact-baseline recovery.
 rc=prepare_recovery_contract(u['update_id'],chain['source'],runtime_root=rt,health_policy_digest=d('health-policy'),prepared_unix=1000,observation_window_seconds=300);tr=recovery_trigger(rc,trigger_code='defined_behavior_regression',evidence_digest=d('post-update-regression'),observed_unix=1050);rec=perform_automatic_recovery(rc,tr,chain['source'],runtime_root=rt);req(rec['ok'] and rec['status']=='automatic_recovery_complete','automatic_recovery');req(rec['source_restored_to_baseline'] and source_only_manifest(chain['source'])['source_manifest_digest']==before,'baseline_restored');req(rec['new_update_authorization_consumed'] is False,'recovery_no_new_auth')
 ue={'disposable_source_fixture':True,'generic_authorization_rejected':True,'exact_authorization_consumed':True,'governed_update_verified':True,'candidate_installed_before_recovery':True,'release_authorized':False,'standing_authority_granted':False,'update_result_digest':hashlib.sha256(json.dumps(exact,sort_keys=True,default=str).encode()).hexdigest()}
 re={'defined_failure_triggered':True,'automatic_recovery_completed':True,'baseline_restored':True,'new_update_authorization_consumed':False,'general_rollback_authorized':False,'release_authorized':False,'recovery_result_digest':hashlib.sha256(json.dumps(rec,sort_keys=True,default=str).encode()).hexdigest()}
 i=identity();result=evaluate_supervised_self_development_beta(i,steps(i),update_evidence=ue,recovery_evidence=re,native_windows_status='pending');req(result['ok'],'beta_ready');req(result['status']=='supervised_self_development_beta_portable_ready_native_pending','beta_status');req(result['roadmap_complete_through_v1300'],'roadmap_complete');req(result['native_windows_certified'] is False,'native_truth');req(result['active_installed_eidolon_modified'] is False,'active_install_untouched');req(result['generic_authorization_phrase_is_sufficient'] is False,'generic_boundary');req(result['rollback_remains_separately_governed_for_successful_operator_rollback'],'rollback_boundary');req(not result['integrity_violations'],'integrity_clear')
print(json.dumps({'suite':'v1300.3-v1300.5-supervised-self-development-beta-integration','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
