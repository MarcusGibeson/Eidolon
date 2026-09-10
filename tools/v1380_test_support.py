import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def req(c,m):
 if not c:raise AssertionError(m)
def kwargs():
 keys=['campaign','step','schedule','parallel','heartbeat','partial','continuity','resume','conflict','reconcile','final']
 ds=[D(x) for x in keys]
 return dict(campaign_record_digest=ds[0],step_checkpoint_digest=ds[1],dependency_schedule_digest=ds[2],parallel_plan_digest=ds[3],heartbeat_digest=ds[4],partial_result_digest=ds[5],continuity_capsule_digest=ds[6],resume_assessment_digest=ds[7],conflict_assessment_digest=ds[8],reconciliation_disposition_digest=ds[9],final_result_digest=ds[10],started_at_unix=0,interrupted_at_unix=3600,restarted_at_unix=3700,external_change_at_unix=7200,reconciled_at_unix=7300,completed_at_unix=4*3600,interruption_observed=True,restart_observed=True,external_change_detected=True,operator_change_preserved=True,reconciliation_completed=True,campaign_completed=True)
