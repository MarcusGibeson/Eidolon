import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();CID='selfc_1389candidate'
def req(c,m):
 if not c:raise AssertionError(m)
def args(rt,outcome='installed',ancestor=''):
 return dict(runtime_root=rt,candidate_id=CID,source_digest=D('source'),finding_digest=D('finding'),repair_digest=D('repair'),test_digest=D('test'),canary_digest=D('canary'),transaction_digest=D(outcome),active_version='1389.9',outcome=outcome,rollback_ancestor_digest=ancestor)
