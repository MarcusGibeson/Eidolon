import hashlib,json,shutil
from pathlib import Path
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();TX='selftx_138813881388'
def req(c,m):
 if not c:raise AssertionError(m)
def trees(r:Path,health_exit=0):
 old=r/'installed';(old/'health').mkdir(parents=True);(old/'app.py').write_text('VERSION="old"\n');(old/'health'/'post.py').write_text('raise SystemExit(0)\n')
 cand=r/'candidate';(cand/'health').mkdir(parents=True);(cand/'app.py').write_text('VERSION="new"\n');(cand/'health'/'post.py').write_text(f'raise SystemExit({health_exit})\n');return old,cand
def canary():
 x={'contract_version':'x','candidate_id':'selfc_x','canary_passed':True,'eligible_for_install_review':True};x['canary_digest']=D(x);return x
