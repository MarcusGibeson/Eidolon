from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import create_authority_profile
from standing_session_grants import *
p=create_authority_profile(name='bounded_autonomous',workspace_digest='d'*64);x=prepare_standing_session(p,now_unix=100);g=activate_standing_session(x['grant'],x['exact_authorization_phrase'],now_unix=101)['grant'];req(CONTRACT_VERSION=='v1302.8','contract');req(g['state']=='active','active');req(g['profile_snapshot']['profile_digest']==p['profile_digest'],'snapshot');req(not standing_session_allows(g,'release_promote',now_unix=102),'release_denied')
print(json.dumps({'suite':'v1302.9-standing-session-grants-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
