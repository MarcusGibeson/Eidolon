import hashlib,json,shutil
from pathlib import Path
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def req(c,m):
 if not c:raise AssertionError(m)
def seal(x,f):
 y=dict(x);y[f]=D(y);return y
def synthetic(rollback=False):
 sm=seal({'working_source_version':'1390.9','content_free':True},'self_model_digest');bd=seal({'self_model_digest':sm['self_model_digest'],'candidates':[]},'backlog_digest');cid='selfc_139013901390';ws={'candidate_id':cid,'self_model_digest':sm['self_model_digest'],'lineage_digest':D('ws')};scope=seal({'automatic_apply_allowed':False,'protected_core_touched':False},'scope_digest');dog=seal({'candidate_id':cid,'failed':0,'candidate_installable':True},'verification_digest');shadow=seal({'candidate_id':cid,'regression_count':0,'shadow_only':True},'shadow_digest');can=seal({'candidate_id':cid,'canary_passed':True},'canary_digest');tx=seal({'health_passed':not rollback,'rollback_verified':rollback},'transaction_digest');lin=seal({'candidate_id':cid,'transaction_digest':tx['transaction_digest'],'canary_digest':can['canary_digest']},'lineage_digest');return sm,bd,ws,scope,dog,shadow,can,tx,lin
def fixture(r:Path):
 s=r/'source';(s/'tools').mkdir(parents=True);(s/'shadow').mkdir();(s/'canary').mkdir();(s/'health').mkdir();(s/'app.py').write_text('VERSION="old"\n');(s/'tools'/'self_test.py').write_text('raise SystemExit(0)\n');(s/'shadow'/'scenario.py').write_text("print('stable')\n");(s/'canary'/'health.py').write_text('raise SystemExit(0)\n');(s/'health'/'post.py').write_text('raise SystemExit(0)\n');return s
