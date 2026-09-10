import hashlib
def d(x):return hashlib.sha256(x.encode()).hexdigest()
def req(v,m):
 if not v:raise AssertionError(m)
def sample_contracts():return [
 {'contract_id':'inv.counter_nonnegative','kind':'invariant','evidence_digest':d('inv')},
 {'contract_id':'schema.goal','kind':'schema','evidence_digest':d('schema')},
 {'contract_id':'life.goal','kind':'lifecycle','evidence_digest':d('life')},
 {'contract_id':'api.goal.create','kind':'api','evidence_digest':d('api')},]
