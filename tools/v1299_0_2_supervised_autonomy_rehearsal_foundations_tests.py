from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1'); os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1299-test-'))
from canary_self_updates_foundations import seal_canary_identity,canary_observation,MANDATORY_SIGNALS,digest as cd
from canary_self_updates import evaluate_canary
from automated_recovery_foundations import prepare_recovery_contract,recovery_trigger
from automated_recovery import evaluate_recovery_trigger
from repeated_self_maintenance_foundations import create_maintenance_session,start_cycle,maintenance_event,digest as md
from repeated_self_maintenance import apply_maintenance_event
from supervised_autonomy_rehearsal_foundations import *
from v1297_test_support import make_applied_fixture,d as rd
from v1299_test_support import identity,d
checks=[]
def req(v,n): checks.append(n); assert v,n
# Canary tamper with an old digest must be detected before health evidence is trusted.
h=lambda s:cd({'x':s})
ident=seal_canary_identity(update_id='selfupdate_v1299test',baseline_source_digest=h('b'),candidate_source_digest=h('c'),update_packet_digest=h('u'),review_decision_digest=h('r'),baseline_workspace_digest=h('bw'),candidate_workspace_digest=h('cw'))
b=[]; c=[]
for sig in MANDATORY_SIGNALS:
    b.append(canary_observation(ident,role='baseline',signal=sig,status='passed',evidence_digest=h('be'+sig),quality_score=1,latency_ms=10))
    c.append(canary_observation(ident,role='candidate',signal=sig,status='passed',evidence_digest=h('ce'+sig),quality_score=1,latency_ms=10))
tam=dict(c[0]); tam['quality_score']=0.0; c[0]=tam
canary=evaluate_canary(ident,b,c); req(any(x.startswith('observation_digest_mismatch:candidate:') for x in canary['integrity_violations']),'canary_digest_tamper_blocked'); req(canary['status']=='canary_integrity_blocked','canary_integrity_status')
# Recovery trigger tamper must block automatic recovery before any restore can occur.
td,source,runtime,uid,*_=make_applied_fixture(); contract=prepare_recovery_contract(uid,source,runtime_root=runtime,health_policy_digest=rd('policy'),prepared_unix=1000,observation_window_seconds=300); trigger=recovery_trigger(contract,trigger_code='startup_failure',evidence_digest=rd('ev'),observed_unix=1050); altered=dict(trigger); altered['trigger_code']='defined_behavior_regression'; gate=evaluate_recovery_trigger(contract,altered); req(not gate['ok'] and 'trigger_digest_mismatch' in gate['violations'],'recovery_digest_tamper_blocked'); td.cleanup()
# Maintenance test-result tamper must not skip the required repair stage.
s=create_maintenance_session(objective_digest=d('obj'),initial_source_digest=d('src')); s=start_cycle(s,work_item_digest=d('work'),current_source_digest=d('src'))
for et in ('inspection_complete','backlog_complete','priority_selected','plan_complete','build_complete'):
    cyc=s['active_cycle']; ev=maintenance_event(cyc,sequence=cyc['next_sequence'],event_type=et,evidence_digest=d(et),source_digest=d('src'),prior_event_digest=cyc['prior_event_digest']); s=apply_maintenance_event(s,ev)
cyc=s['active_cycle']; failed=maintenance_event(cyc,sequence=cyc['next_sequence'],event_type='test_result',evidence_digest=d('test'),source_digest=d('src'),prior_event_digest=cyc['prior_event_digest'],test_passed=False); altered_event=dict(failed); altered_event['test_passed']=True; blocked=apply_maintenance_event(s,altered_event); req(blocked['status']=='maintenance_blocked' and blocked['block_reason']=='event_digest_mismatch','maintenance_digest_tamper_blocked')
# Valid sealed evidence still follows retained behavior.
valid=apply_maintenance_event(s,failed); req(valid['status']=='cycle_active' and valid['active_cycle']['stage']=='repair','valid_failed_test_routes_repair')
ri=identity(); req(ri['defect_id']==REAL_DEFECT_ID,'real_defect_identity'); req(tuple(ri['affected_paths'])==tuple(sorted(REAL_DEFECT_AFFECTED_PATHS)),'exact_multifile_scope'); req(valid_digest(ri['identity_digest']),'identity_sealed'); req(ri['active_installation_modified'] is False,'active_install_untouched'); req(not any(ri[k] for k in DENIED_AUTHORITY),'identity_no_authority')
step=rehearsal_step(ri,sequence=1,stage='inspect',evidence_digest=d('inspect'),source_digest=ri['baseline_source_digest']); req(valid_digest(step['step_digest']),'step_sealed'); req(step['stage']=='inspect' and not step['self_update_authorized'],'step_no_update_authority')
for control in sorted(OPERATOR_CONTROLS):
    row=operator_control_record(ri,control=control,evidence_digest=d('control:'+control)); req(row['control']==control and row['control_is_authorization'] is False and not row['rollback_authorized'],'control_'+control)
try: seal_rehearsal_identity(baseline_source_digest=d('same'),repaired_source_digest=d('same'),defect_evidence_digest=d('x'),proposal_digest=d('p'),deliberation_digest=d('d'),plan_digest=d('pl'),candidate_evaluation_digest=d('c'),verification_digest=d('v'),review_digest=d('r')); bad=False
except ValueError: bad=True
req(bad,'unchanged_source_rejected')
print(json.dumps({'suite':'v1299.0-v1299.2-supervised-autonomy-rehearsal-foundations','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
