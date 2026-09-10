import hashlib
def d(x='x'):return hashlib.sha256(x.encode()).hexdigest()
def req(v,m):
 if not v:raise AssertionError(m)
