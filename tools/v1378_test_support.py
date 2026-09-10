import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
B=lambda b:hashlib.sha256(b).hexdigest()
C='c'*64
def req(c,m):
 if not c:raise AssertionError(m)
