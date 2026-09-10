from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1277_fixture import prepared_observability_chain
from development_observability_foundations import *
from development_observability_reliability import *
from restart_crash_recovery_foundations import note_recovery_interruption
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory() as td:
 c=prepared_observability_chain(Path(td),now=100);oid=c['observability']['observability_id']
 for i,(phase,secs,budget) in enumerate([('candidate_execution',4,30),('candidate_execution',2,30),('verification_and_repair',31,90),('verification_and_repair',95,90)]):record_observability_event(oid,runtime_root=c['runtime'],event_code='phase_completed',phase=phase,outcome='completed',work_code='sample',elapsed_seconds=secs,phase_budget_seconds=budget,lineage_marker=f'{900+i:064x}',now=110+i)
 record_observability_event(oid,runtime_root=c['runtime'],event_code='retry_observed',phase='verification_and_repair',outcome='observed',work_code='verification_stage',lineage_marker='b'*64);record_observability_event(oid,runtime_root=c['runtime'],event_code='failure_observed',phase='verification_and_repair',outcome='blocked',work_code='verification_stage',lineage_marker='c'*64)
 d=diagnose_development_performance(oid,runtime_root=c['runtime']);req(d['ok'],'diag');req(d['phase_timing_rows'][0]['phase']=='verification_and_repair','slow_first');req('verification_and_repair' in d['over_budget_phases'],'over_budget');req(d['retry_count_total']==1,'retry');req(d['failure_count_total']>=1,'failure');req(d['global_timeout_increase_recommended'] is False,'no_timeout');req(d['raw_prompts_or_responses_required'] is False,'no_private')
 note_recovery_interruption(c['recovery']['recovery_id'],runtime_root=c['runtime'],interruption_code='process_restart',now=200);r=reconcile_observability_after_restart(oid,runtime_root=c['runtime'],now=201);req(r['restart_generation']>=1,'restart_gen');req(r['duplicate_provider_activity_triggered'] is False,'no_provider_replay');req(r['duplicate_test_activity_triggered'] is False,'no_test_replay');req(r['authorization_reused'] is False,'no_auth_reuse');before=r['event_count_total'];req(reconcile_observability_after_restart(oid,runtime_root=c['runtime'],now=202)['event_count_total']==before,'restart_idempotent')
 h=inspect_development_observability_health(source_root=ROOT);req(h['ok'],'health');req(h['native_windows_validation']=='desktop_review_required','windows');hand=build_development_observability_operator_handoff(source_root=ROOT);req(hand['ok'],'handoff');req(hand['next_bounded_unit']=='v1278 Security and Privacy Hardening','next');req('multi_hour_phase_timing' in hand['native_windows_review'],'multi_hour')
 from development_observability_foundations import _path
 p=_path(oid,c['runtime']);raw=json.loads(p.read_text());raw['raw_prompt_persisted']=True;p.write_text(json.dumps(raw));q=quarantine_invalid_development_observability(oid,runtime_root=c['runtime'],now=300);req(q['quarantined'],'quarantine');req(q['external_action_replayed'] is False,'q_no_replay');req(q['authorization_recreated'] is False,'q_no_auth')
with tempfile.TemporaryDirectory() as td:
 base=Path(td)
 while len(str(base))<285:base=base/('segment_'+'x'*28)
 base.mkdir(parents=True);c=prepared_observability_chain(base,now=400);oid=c['observability']['observability_id'];record_observability_event(oid,runtime_root=c['runtime'],event_code='progress_observed',phase='prepared',outcome='observed',work_code='long_path',lineage_marker='d'*64);req(validate_development_observability(load_development_observability(oid,runtime_root=c['runtime']))['ok'],'long_valid');req(diagnose_development_performance(oid,runtime_root=c['runtime'])['ok'],'long_diag')
print(json.dumps({'ok':True,'suite':'v1277.6-8-development-observability-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
