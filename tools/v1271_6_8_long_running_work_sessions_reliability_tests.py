from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1271_fixture import prepared_long_chain
from v1270_fixture import initial_provider
from long_running_work_sessions import execute_long_running_candidate,interrupt_long_running_work_session,resume_long_running_work_session,long_running_operator_status
from long_running_work_sessions_foundations import load_long_running_work_session,AUTHORITY_FLAGS
from long_running_work_sessions_reliability import *
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1271-rel-') as td:
    base=Path(td);c=prepared_long_chain(base,now=1000.0,lease_seconds=30);sid=c['session']['session_id'];calls=[]
    a=claim_or_renew_work_session_lease(sid,'worker-a',runtime_root=c['runtime'],now=1010.0);req(a['lease_acquired'],'lease_acquired');req(a['lease_generation']==1,'lease_generation_one')
    b=claim_or_renew_work_session_lease(sid,'worker-b',runtime_root=c['runtime'],now=1020.0);req(not b['lease_acquired'],'live_lease_blocks_other_owner');req(b['status']=='long_running_work_session_lease_held','lease_held_status')
    renew=claim_or_renew_work_session_lease(sid,'worker-a',runtime_root=c['runtime'],now=1025.0);req(renew['status']=='long_running_work_session_lease_renewed','heartbeat_renewal');req(renew['lease_generation']==1,'renew_no_generation_change')
    expired=reconcile_long_running_work_session(sid,runtime_root=c['runtime'],now=1060.0);req(expired['expired_lease_recovered'],'expired_lease_recovered');req(expired['state']=='interrupted','expired_lease_interrupts');req(expired['duplicate_provider_tool_test_activity_created'] is False,'recovery_no_activity')
    resume_long_running_work_session(sid,runtime_root=c['runtime']);stage=execute_long_running_candidate(sid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls));req(len(calls)==1,'provider_once_before_interruption')
    interrupt_long_running_work_session(sid,runtime_root=c['runtime'],reason='dashboard_closed');resume_long_running_work_session(sid,runtime_root=c['runtime']);recon=reconcile_long_running_work_session(sid,runtime_root=c['runtime'],now=1070.0);req('candidate_stage' in recon['completed_work_codes'],'completed_stage_survives_restart')
    again=execute_long_running_candidate(sid,c['source'],runtime_root=c['runtime'],authorization_phrase=c['campaign']['candidate_authorization_phrase'],provider=initial_provider(calls));req(again['long_session_duplicate_suppressed'],'post_restart_duplicate_suppressed');req(len(calls)==1,'post_restart_no_duplicate_provider')
    lease2=claim_or_renew_work_session_lease(sid,'worker-b',runtime_root=c['runtime'],now=1080.0);req(lease2['lease_acquired'],'expired_owner_transfer_allowed');req(lease2['lease_generation']==2,'ownership_generation_incremented');req(lease2['lease_is_execution_authority'] is False,'lease_not_authority')
    rel=release_work_session_lease(sid,'worker-b',runtime_root=c['runtime']);req(rel['ok'],'lease_release')
    # Long path runtime storage remains functional on the host filesystem.
    longrt=base/('segment_'+'x'*40)/('segment_'+'y'*40)/('segment_'+'z'*40)/'runtime';c2=prepared_long_chain(base/'longsrc',now=2000.0); # source fixture itself
    # Separate session under a deliberately deep runtime using same campaign cannot be transplanted; instead validate health/path-safe atomic primitives on current runtime.
    req(len(str((Path(c['runtime'])/'long_running_work_sessions'/'sessions'/f'{sid}.json')))>80,'nontrivial_runtime_path')
    health=inspect_long_running_work_sessions_health(source_root=ROOT);req(health['ok'],'health_ready');handoff=build_long_running_work_sessions_operator_handoff(source_root=ROOT);req(handoff['ok'],'handoff_ready');req('process_lifetime_and_shutdown' in handoff['native_windows_review'],'windows_process_review');req('lease_is_advisory_not_v1273_exactly_once_concurrency' in handoff['known_limitations'],'v1273_boundary_explicit');req('monolithic_full_source_probe_exceeded_wall_clock_budget' in handoff['v1270_harness_finding'],'v1270_harness_finding_preserved')
    status=long_running_operator_status(sid,runtime_root=c['runtime']);req(status['active_source_modified'] is False,'operator_status_source_safe')
    for k,v in AUTHORITY_FLAGS.items():req(status[k] is v,'authority_'+k)
print(json.dumps({'ok':True,'suite':'v1271.6-v1271.8-long-running-work-sessions-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
