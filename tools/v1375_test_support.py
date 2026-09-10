import hashlib,json,tempfile
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
C='c'*64;T=D('task')
def req(c,m):
 if not c:raise AssertionError(m)
