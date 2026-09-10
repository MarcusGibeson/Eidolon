from __future__ import annotations
"""v1277.6-v1277.8 restart/reliability and performance diagnostics."""
import os,shutil,time
from pathlib import Path
from typing import Any
from self_development_alpha_foundations import _runtime_root
from development_observability_foundations import *
from development_observability import sync_development_observability
CONTRACT_VERSION='v1277.8'
def diagnose_development_performance(observability_id,*,runtime_root):
    row=load_development_observability(observability_id,runtime_root=runtime_root)
    if not validate_development_observability(row).get('ok'):return {'ok':False,'status':'development_observability_invalid',**AUTHORITY_FLAGS}
    totals={};mx={};samples={};over=[]
    for e in row.get('events') or []:
        p=str(e.get('phase') or 'unknown');el=int(e.get('elapsed_ms') or 0);b=int(e.get('phase_budget_ms') or 0)
        if el:totals[p]=totals.get(p,0)+el;mx[p]=max(mx.get(p,0),el);samples[p]=samples.get(p,0)+1
        if b and el>b and p not in over:over.append(p)
    rows=[{'phase':p,'retained_sample_count':samples.get(p,0),'retained_total_elapsed_ms':totals[p],'retained_max_elapsed_ms':mx.get(p,0)} for p in sorted(totals,key=lambda x:(-totals[x],x))[:12]]
    return {'ok':True,'status':'development_performance_diagnostics_ready','phase_timing_rows':rows,'over_budget_phases':sorted(over),'failure_count_total':int(row.get('failure_count_total') or 0),'retry_count_total':int(row.get('retry_count_total') or 0),'recovery_count_total':int(row.get('recovery_count_total') or 0),'budget_split_count_total':int(row.get('budget_split_count_total') or 0),'retention_is_bounded':True,'older_event_counts_preserved_in_aggregate':int(row.get('event_count_total') or 0)>=len(row.get('events') or []),'raw_prompts_or_responses_required':False,'global_timeout_increase_recommended':False,'active_source_modified':False,**AUTHORITY_FLAGS}
def reconcile_observability_after_restart(observability_id,*,runtime_root,now=None):
    runtime=_runtime_root(runtime_root);before=load_development_observability(observability_id,runtime_root=runtime);sync=sync_development_observability(observability_id,runtime_root=runtime,now=now);from development_observability import _lineage,_marker;lin=_lineage(sync,runtime);r=lin['recovery'];gen=int(r.get('restart_generation') or 0) if r else 0
    if gen:record_observability_event(observability_id,runtime_root=runtime,event_code='restart_observed',phase=str(sync.get('current_phase') or 'blocked'),outcome='observed',work_code='recovery',detail_codes=['restart_generation_observed'],lineage_marker=_marker('restart_generation',str(gen)),now=now)
    row=load_development_observability(observability_id,runtime_root=runtime);return {**row,'operation_status':'observability_restart_reconciled','previous_record_digest':before.get('record_digest'),'restart_generation':gen,'duplicate_provider_activity_triggered':False,'duplicate_test_activity_triggered':False,'authorization_reused':False}
def quarantine_invalid_development_observability(observability_id,*,runtime_root,now=None):
    from development_observability_foundations import _path,_root,_read
    p=_path(observability_id,runtime_root)
    if not p.exists():return {'ok':False,'status':'development_observability_missing',**AUTHORITY_FLAGS}
    try:
        if validate_development_observability(_read(p)).get('ok'):return {'ok':True,'status':'development_observability_valid_no_quarantine','quarantined':False,**AUTHORITY_FLAGS}
    except Exception:pass
    q=_root(runtime_root)/'quarantine';q.mkdir(parents=True,exist_ok=True);t=q/f'{observability_id}-{int(time.time() if now is None else now)}.json'
    try:os.replace(p,t)
    except OSError:
        try:shutil.copy2(p,t);p.unlink(missing_ok=True)
        except OSError:return {'ok':False,'status':'development_observability_quarantine_failed',**AUTHORITY_FLAGS}
    return {'ok':True,'status':'development_observability_quarantined_rebuild_from_durable_lineage_required','quarantined':True,'private_content_recovered':False,'external_action_replayed':False,'authorization_recreated':False,**AUTHORITY_FLAGS}
def inspect_development_observability_health(*,source_root=None):
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();names=['development_observability_foundations.py','development_observability.py','development_observability_reliability.py','long_running_work_sessions.py','restart_crash_recovery.py','ownership_concurrency.py','environment_awareness.py'];checks={x.replace('.py','_present'):(root/'conscious_agent'/x).is_file() for x in names};return {'ok':all(checks.values()),'status':'development_observability_health_ready' if all(checks.values()) else 'development_observability_health_blocked','checks':checks,'native_windows_validation':'desktop_review_required','active_source_modified':False,**AUTHORITY_FLAGS}
def build_development_observability_operator_handoff(*,source_root=None):
    h=inspect_development_observability_health(source_root=source_root);return {'ok':h.get('ok') is True,'contract_version':CONTRACT_VERSION,'status':'development_observability_operator_handoff_ready' if h.get('ok') else 'development_observability_operator_handoff_blocked','capabilities':['bounded_content_free_progress_events','phase_and_elapsed_timing','failure_retry_recovery_counts','authorization_requirement_visibility','v1272_recovery_correlation','v1273_ownership_correlation','v1274_environment_evidence_correlation','harness_budget_split_signal','restart_observability_reconciliation','aggregate_counts_survive_event_compaction'],'known_limitations':['retained_event_window_is_bounded_and_is_not_a_complete_forensic_log','timing_is_wall_clock_observation_not_cpu_profiler_attribution','provider_payloads_prompts_responses_and_raw_test_output_are_intentionally_not_retained','native_windows_process_lifetime_and_shutdown_timing_require_desktop_validation','observability_never_grants_retry_execution_update_or_release_authority'],'native_windows_review':['multi_hour_phase_timing','dashboard_close_and_reopen_status','process_restart_reconciliation','filesystem_lock_wait_visibility','long_path_validation_timing','provider_outage_and_return_signals','split_verification_harness_timing','bounded_log_growth_over_long_campaign','shutdown_during_receipt_write'],'next_bounded_unit':'v1278 Security and Privacy Hardening','active_source_modified':False,**AUTHORITY_FLAGS}
__all__=['CONTRACT_VERSION','diagnose_development_performance','reconcile_observability_after_restart','quarantine_invalid_development_observability','inspect_development_observability_health','build_development_observability_operator_handoff']
