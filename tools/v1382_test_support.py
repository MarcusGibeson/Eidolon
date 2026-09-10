import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
SM=D('self-model')
def req(c,m):
 if not c:raise AssertionError(m)
def obs(cat='failure',issue='bug',scope='scope',impact=8,confidence=90,effort=2,risk='medium',protected=False):return {'category':cat,'evidence_digest':D(cat+issue),'scope_digest':D(scope),'issue_class':issue,'impact':impact,'confidence':confidence,'effort':effort,'risk':risk,'protected_boundary':protected}
