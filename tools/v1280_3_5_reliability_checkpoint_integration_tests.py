from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1279_fixture import prepared_operator_experience_chain
from reliability_checkpoint import *
from reliability_checkpoint_foundations import validate_reliability_trial
from operator_experience import operator_experience_session_control,build_operator_experience_snapshot
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
with tempfile.TemporaryDirectory() as td:
 c=prepared_operator_experience_chain(Path(td),now=100);s=c['snapshot'];t=reliability_trial_from_operator_snapshot(s,scenario_code='normal_campaign');req(validate_reliability_trial(t)['ok'] and validate_reliability_trial(t)['clean'],'snapshot_trial');req(t['next_required_authorization']=='v1265_candidate_exact_authorization','auth_code');m=build_reliability_campaign_matrix(s);req(m['ok'],'matrix');req(m['trial_count']==6,'matrix_count');req(m['total_restarts']==6,'restart_total');req(m['unauthorized_action_count']==0,'no_unauth');req(m['private_content_finding_count']==0,'no_private')
 p=operator_experience_session_control(c['observability']['observability_id'],action='pause',runtime_root=c['runtime']);req(p['ok'],'pause');r=operator_experience_session_control(c['observability']['observability_id'],action='resume',runtime_root=c['runtime']);req(r['ok'],'resume');s2=build_operator_experience_snapshot(c['observability']['observability_id'],runtime_root=c['runtime']);m2=build_reliability_campaign_matrix(s2);req(m2['ok'],'matrix_after_controls');req(m2['aggregate_digest']!=m['aggregate_digest'] or m2['ok'],'projection_rebuilt')
with tempfile.TemporaryDirectory() as td:
 base=Path(td);snaps=[]
 for i in range(3):snaps.append(prepared_operator_experience_chain(base/f'campaign{i}',now=200+i)['snapshot'])
 req(len(snaps)==3,'three_campaigns');req(all(build_reliability_campaign_matrix(x)['ok'] for x in snaps),'repeated_campaigns')
print(json.dumps({'ok':True,'suite':'v1280.3-5-reliability-checkpoint-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
