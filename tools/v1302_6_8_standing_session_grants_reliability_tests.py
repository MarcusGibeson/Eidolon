from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import create_authority_profile
from standing_session_grants import *
p=create_authority_profile(name='bounded_autonomous',workspace_digest='c'*64,max_minutes=2);x=prepare_standing_session(p,now_unix=100);g=activate_standing_session(x['grant'],x['exact_authorization_phrase'],now_unix=101)['grant'];pa=transition_standing_session(g,'pause',now_unix=110)['grant'];req(not standing_session_allows(pa,'file_write',now_unix=111),'paused');re=transition_standing_session(pa,'resume',now_unix=112)['grant'];req(standing_session_allows(re,'file_write',now_unix=113),'resumed');rv=transition_standing_session(re,'revoke',now_unix=114)['grant'];req(not standing_session_allows(rv,'file_write',now_unix=115),'revoked');req(not standing_session_allows(g,'file_write',now_unix=999),'expired')
print(json.dumps({'suite':'v1302.6-8-standing-session-grants','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
