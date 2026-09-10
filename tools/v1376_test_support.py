import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
C='d'*64;T=D('task');E=D('producer')
def req(c,m):
 if not c:raise AssertionError(m)
