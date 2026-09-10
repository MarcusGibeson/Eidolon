from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1279_fixture import prepared_operator_experience_chain
from operator_experience import *
from operator_experience_foundations import AUTHORITY_FLAGS,validate_operator_experience_projection
from long_running_work_sessions_foundations import load_long_running_work_session
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
def denied(row,prefix):
    for k,v in AUTHORITY_FLAGS.items():req(row.get(k) is v,f'{prefix}_{k}')
with tempfile.TemporaryDirectory() as td:
    c=prepared_operator_experience_chain(Path(td),now=100);oid=c['observability']['observability_id'];s=c['snapshot'];req(validate_operator_experience_projection(s)['ok'],'snapshot_valid');req(s['campaign_id']==c['campaign']['campaign_id'],'campaign_lineage');req(s['session_id']==c['session']['session_id'],'session_lineage');req(s['authorization']['code']=='v1265_candidate_exact_authorization','next_auth');req(s['current']['active_source_modified'] is False,'source_untouched');denied(s,'snapshot_auth')
    listed=list_operator_experience_snapshots(runtime_root=c['runtime']);req(listed['ok'] and listed['snapshot_count']==1,'listed');req(listed['private_payloads_exposed'] is False,'list_private');denied(listed,'list_auth')
    p=operator_experience_session_control(oid,action='pause',runtime_root=c['runtime']);req(p['ok'] and p['session_state']=='paused','pause');req(not p['provider_contacted'] and not p['tests_executed'] and not p['active_source_modified'],'pause_no_sideeffects');req(load_long_running_work_session(c['session']['session_id'],runtime_root=c['runtime'])['state']=='paused','pause_durable')
    r=operator_experience_session_control(oid,action='resume',runtime_root=c['runtime']);req(r['ok'] and r['session_state']=='active','resume');req(r['snapshot']['authorization']['code']=='v1265_candidate_exact_authorization','resume_no_auth_change')
    bad=operator_experience_session_control(oid,action='authorize',runtime_root=c['runtime']);req(not bad['ok'],'invalid_control');req('authorize' not in bad['allowed_actions'],'no_authorize_control');denied(bad,'bad_auth')
    x=operator_experience_reconcile_recovery(oid,c['source'],runtime_root=c['runtime']);req(x['provider_replayed'] is False and x['tests_replayed'] is False,'reconcile_no_replay');req(x['active_source_modified'] is False,'reconcile_no_source')
    z=operator_experience_session_control(oid,action='cancel',runtime_root=c['runtime']);req(z['ok'] and z['session_state']=='cancelled','cancel');req(z['snapshot']['authorization']['code']=='none_cancelled','cancel_no_auth')
print(json.dumps({'ok':True,'suite':'v1279.3-5-operator-experience-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
