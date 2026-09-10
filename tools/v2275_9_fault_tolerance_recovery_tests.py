from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2275-data-')
from transactional_recovery_v2200 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2275-runtime-'))
root=Path(tempfile.mkdtemp(prefix='eidolon-v2275-source-')); (root/'a.txt').write_text('alpha',encoding='utf-8'); (root/'nested').mkdir(); (root/'nested'/'b.json').write_text('{"ok":true}',encoding='utf-8')
cp=build_recovery_checkpoint(checkpoint_id='c1',source_manifest_digest='a'*64,runtime_state_digest='b'*64,priority=90,health_codes=['healthy'])
req(cp['checkpoint_is_installation_authority'] is False and cp['raw_private_content_recorded'] is False,'checkpoint_is_evidence_not_authority')
crash=classify_recovery_signal({'class':'process_crash','certainty':'observed'})
req(crash['recognized'] and crash['recommended_action']=='prepare_recovery','observed_crash_prepares_recovery')
j=append_recovery_journal(operation_id='op1',checkpoint_digest=cp['checkpoint_digest'],signal_digest=crash['signal_digest'],state_code='prepared',runtime_root=runtime)
req(j['ok'] and j['status']=='recovery_journal_appended','recovery_journal_persists')
j2=append_recovery_journal(operation_id='op1',checkpoint_digest=cp['checkpoint_digest'],signal_digest=crash['signal_digest'],state_code='prepared',runtime_root=runtime)
req(j2['idempotent'] and j2['status']=='recovery_journal_replayed','recovery_journal_exactly_once')
journal=inspect_recovery_journal(runtime_root=runtime)
req(journal['entry_count']==1 and journal['state_counts']['prepared']==1,'recovery_journal_restart_inspectable')
unknown=classify_recovery_signal({'class':'alien_failure','certainty':'unknown'})
req(not unknown['recognized'] and unknown['recommended_action']=='collect_evidence','unknown_failure_preserves_uncertainty')
drift=classify_recovery_signal({'class':'source_drift','certainty':'observed'})
req(drift['recommended_action']=='freeze_and_escalate','source_drift_fails_closed')
res=simulate_transactional_recovery(root,signal={'class':'process_crash','certainty':'observed'})
req(res['ok'] and res['rollback_verified'] and res['backup_verified'],'disposable_transactional_recovery_exact')
req(res['source_unchanged'] and not (root/'.era8_failure_marker').exists(),'authoritative_source_unchanged')
req(res['failure_marker_persisted_to_source'] is False,'failure_injection_disposable_only')
blocked=simulate_transactional_recovery(root,signal={'class':'source_drift','certainty':'observed'})
req(not blocked['ok'] and blocked['status']=='recovery_simulation_blocked_for_escalation','unsafe_recovery_blocked')
wrong=simulate_transactional_recovery(root,signal={'class':'process_crash','certainty':'observed'},expected_manifest={'wrong':'x'})
req(not wrong['ok'] and wrong['status']=='recovery_baseline_manifest_mismatch','baseline_drift_detected')
req(all(not bool(res[k]) for k in ('authoritative_source_modified','private_runtime_modified','installation_authorized','promotion_authorized','authority_expanded')),'recovery_simulation_preserves_authority')
print(json.dumps({'suite':'v2275.9-fault-tolerance-recovery','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
