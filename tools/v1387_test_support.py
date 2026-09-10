import hashlib,json
from pathlib import Path
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();SM=D('sm');BC=D('bc');CID='selfc_138713871387'
def req(c,m):
 if not c:raise AssertionError(m)
def src(r:Path,fail=False):
 s=r/'src';(s/'canary').mkdir(parents=True);(s/'tools').mkdir();(s/'app.py').write_text('X=1\n');(s/'canary'/'health.py').write_text('raise SystemExit(%d)\n'%(1 if fail else 0));(s/'tools'/'self_test.py').write_text('raise SystemExit(0)\n');return s
def seal(v,field):
 z=dict(v);z[field]=D(z);return z
def evidence(cid=CID):
 d=seal({'contract_version':'x','candidate_id':cid,'failed':0,'candidate_installable':True},'verification_digest');sh=seal({'contract_version':'x','candidate_id':cid,'regression_count':0,'shadow_only':True},'shadow_digest');return d,sh
