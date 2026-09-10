from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2299-data-')
from audit_incident_governance_v2200 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2299-runtime-'))
events=[
 {'session_id':'s','event':'intent','intent_digest':'a'*64,'authority_digest':'b'*64,'attempt_digest':'c'*64,'result_digest':'d'*64,'rollback_digest':'','operator_decision_digest':'e'*64,'side_effect_digest':''},
 {'session_id':'s','event':'result','intent_digest':'a'*64,'authority_digest':'b'*64,'attempt_digest':'c'*64,'result_digest':'f'*64,'rollback_digest':'','operator_decision_digest':'e'*64,'side_effect_digest':'f'*64},
]
line=build_audit_lineage(events)
req(line['ok'] and line['tamper_evident'] and line['reconstructable'],'audit_chain_tamper_evident')
req(validate_audit_lineage(line)['ok'],'audit_chain_validates')
req(line['lineage_fields_present'] and line['event_count']==2,'audit_lineage_links_required_dimensions')
req(line['raw_content_exposed'] is False,'audit_content_free')
tampered=json.loads(json.dumps(line)); tampered['chain'][0]['intent_digest']='9'*64
req(not validate_audit_lineage(tampered)['ok'] and 'event_digest_mismatch' in validate_audit_lineage(tampered)['reason_codes'],'audit_tampering_detected')
opened=open_incident(incident_id='i1',signals=[{'code':'approval_forgery','severity':'high'}],affected_capabilities=['file_write','network'],event_id='e1',runtime_root=runtime)
req(opened['ok'] and opened['incident']['triggered'],'high_signal_opens_incident')
req(opened['incident']['logical_capability_freeze'] and opened['incident']['freeze_is_policy_signal_not_os_action'],'incident_freeze_is_bounded_signal')
req(opened['incident']['operator_notification_proposal'] and opened['external_notification_sent'] is False,'notification_is_proposal_only')
replay=open_incident(incident_id='i1',signals=[{'code':'approval_forgery','severity':'high'}],affected_capabilities=['file_write','network'],event_id='e1',runtime_root=runtime)
req(replay['idempotent'] and replay['status']=='incident_open_replayed','incident_open_exactly_once')
low=open_incident(incident_id='i2',signals=[{'code':'flaky_test','severity':'info'}],affected_capabilities=['test'],event_id='e2',runtime_root=runtime)
req(low['status']=='incident_monitoring_started' and not low['incident']['triggered'],'low_signal_monitors_without_freeze')
state=inspect_incidents(runtime_root=runtime)
req(state['incident_count']==2 and state['raw_private_content_exposed'] is False,'incident_state_content_free')
req(all(not bool(opened[k]) for k in ('capability_disabled_in_os','recovery_executed','installation_authorized','promotion_authorized','authority_expanded')),'incident_response_no_unearned_effect')
print(json.dumps({'suite':'v2299.9-audit-incident-response','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
