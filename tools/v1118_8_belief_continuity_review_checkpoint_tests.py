from pathlib import Path
import tempfile, os, json, subprocess, sys
from conscious_agent.belief_continuity_review_checkpoint import build_belief_continuity_review_checkpoint
from conscious_agent.api_server import dispatch_api
ROOT=Path(__file__).resolve().parents[1];p=f=0
def req(x):
 global p,f;p+=bool(x);f+=not bool(x)
with tempfile.TemporaryDirectory() as td:
 root=Path(td); before=list(root.rglob('*'));r=build_belief_continuity_review_checkpoint(root,source_root=ROOT);req(r['ok']);req(r['contract_version']=='v1118.8');req(len(r['checks'])==16);req(all(x['status']=='pass' for x in r['checks']));req(before==list(root.rglob('*')));req(not r['belief_mutated']);req(not any(r[k] for k in ('proposal_applied','approval_granted','authorization_granted','external_action_executed')));os.environ['EIDOLON_DATA_DIR']=str(root/'api');status,payload=dispatch_api('GET','/api/cognition/belief-continuity-review-checkpoint');req(status==200 and payload['data']['contract_version']=='v1118.8');post,_=dispatch_api('POST','/api/cognition/belief-continuity-review-checkpoint',body={});req(post in (404,405));dash=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text();req('belief-continuity-review-checkpoint-panel' in dash)
print(f'v1118.8 belief continuity checkpoint: {p}/10 passed');raise SystemExit(0 if f==0 and p==10 else 1)
