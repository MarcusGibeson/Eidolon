from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1299-test-'))
from supervised_autonomy_rehearsal import evaluate_supervised_rehearsal
from supervised_autonomy_rehearsal_foundations import operator_control_record
from v1299_test_support import identity,complete_steps,repair_checks,d
checks=[]
def req(v,n):checks.append(n);assert v,n
ident=identity();steps=complete_steps(ident);result=evaluate_supervised_rehearsal(ident,steps,repaired_consumer_checks=repair_checks(),native_windows_status='pending')
req(result['ok'],'complete_rehearsal');req(result['status']=='rehearsal_candidate_ready_for_exact_operator_update_review','review_ready');req(result['stage_count']==10,'ten_stages');req(result['portable_rehearsal_complete'],'portable_complete');req(result['native_windows_status']=='pending','native_pending');req(result['exact_v1269_update_authorization_required'],'exact_update_required');req(result['exact_v1269_update_authorization_consumed'] is False,'update_not_consumed');req(result['generic_authorization_phrase_is_sufficient'] is False,'generic_not_auth');req(result['active_installation_modified'] is False,'active_install_untouched');req(not result['integrity_violations'],'integrity_clear')
for key in ('operator_may_inspect','operator_may_defer','operator_may_reject','operator_may_cancel','operator_may_request_separately_governed_rollback'):req(result[key],key)
# Every operator intervention remains a non-authorizing disposition.
for control in ('inspect','defer','reject','cancel','rollback_request'):
    row=operator_control_record(ident,control=control,evidence_digest=d('op:'+control));req(row['control_is_authorization'] is False and not row['self_update_authorized'] and not row['rollback_authorized'],'control_'+control)
# Incomplete or false repair evidence cannot reach update review.
incomplete=evaluate_supervised_rehearsal(ident,steps[:-1],repaired_consumer_checks=repair_checks());req(not incomplete['ok'] and 'incomplete_rehearsal_stage_set' in incomplete['integrity_violations'],'missing_stage_blocked')
badchecks=repair_checks();badchecks['recovery_trigger_resealed']=False;bad=evaluate_supervised_rehearsal(ident,steps,repaired_consumer_checks=badchecks);req(not bad['ok'] and 'real_integrity_repair_not_verified' in bad['integrity_violations'],'repair_evidence_required')
print(json.dumps({'suite':'v1299.3-v1299.5-supervised-autonomy-rehearsal-integration','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
