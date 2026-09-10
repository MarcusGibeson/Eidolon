import hashlib,json,shutil
from pathlib import Path
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();SM=D('sm');BC=D('bc');CID='selfc_138613861386'
def req(c,m):
 if not c:raise AssertionError(m)
def roots(r:Path,candidate='same'):
 b=r/'base';(b/'shadow').mkdir(parents=True);(b/'app.py').write_text('X=1\n');(b/'shadow'/'scenario.py').write_text("print('base')\n")
 s=r/'src';shutil.copytree(b,s)
 if candidate=='changed':(s/'shadow'/'scenario.py').write_text("print('candidate')\n")
 if candidate=='fail':(s/'shadow'/'scenario.py').write_text("raise SystemExit(2)\n")
 return b,s
