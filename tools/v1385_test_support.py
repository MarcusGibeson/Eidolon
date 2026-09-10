import hashlib,json
from pathlib import Path
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
SM=D('sm');BC=D('bc');CID='selfc_138513851385'
def req(c,m):
 if not c:raise AssertionError(m)
def src(root:Path,fail=False):
 s=root/'src';(s/'tools').mkdir(parents=True);(s/'app.py').write_text('X=1\n');(s/'tools'/'self_test.py').write_text('raise SystemExit(%d)\n'%(1 if fail else 0));return s
