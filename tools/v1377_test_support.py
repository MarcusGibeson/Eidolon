import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
C='c'*64;K='k'.encode();A=D('candidate');S0=D('source-0');S1=D('source-1');W0=D('work-0');W1=D('work-1');U0=D('upstream-0');U1=D('upstream-1');OWNER=D('owner');OTHER=D('other')
def req(c,m):
 if not c:raise AssertionError(m)
def change(label,origin='campaign',kind='modified'):
 return {'path_digest':D('path:'+label),'change_digest':D('change:'+label),'origin':origin,'kind':kind}
