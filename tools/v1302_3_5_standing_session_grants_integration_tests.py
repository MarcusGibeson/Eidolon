from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from authority_profiles import create_authority_profile
from standing_session_grants import *
p=create_authority_profile(name='bounded_autonomous',workspace_digest='b'*64,max_minutes=10);x=prepare_standing_session(p,now_unix=100);bad=activate_standing_session(x['grant'],'go ahead',now_unix=101);req(not bad['ok'],'generic_rejected');ok=activate_standing_session(x['grant'],x['exact_authorization_phrase'],now_unix=101);g=ok['grant'];req(ok['ok'] and g['activation_consumed'],'exact');req(standing_session_allows(g,'file_write',now_unix=102),'standing');req(not standing_session_allows(g,'external_publish',now_unix=102),'protected')
print(json.dumps({'suite':'v1302.3-5-standing-session-grants','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
