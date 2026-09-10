import hashlib,json
from pathlib import Path
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
SM=D('self-model');BC=D('backlog-candidate');CID='selfc_123456789abc'
def req(c,m):
 if not c: raise AssertionError(m)
def source(root:Path):
 s=root/'source';s.mkdir();(s/'app.py').write_text('VALUE = 1\n');(s/'pkg').mkdir();(s/'pkg'/'x.py').write_text('def x(): return 1\n');return s
