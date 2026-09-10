import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
C='b'*64
TASKS=[
 {"task_id":"read-a","kind":"read","reads":["a"],"cpu_units":1,"memory_mb":32,"execution_authorized":True},
 {"task_id":"test-b","kind":"test","reads":["b"],"cpu_units":1,"memory_mb":32,"execution_authorized":True},
 {"task_id":"write-a","kind":"mutation","reads":["a"],"writes":["a"],"cpu_units":1,"memory_mb":32,"execution_authorized":True},
]
def req(c,m):
 if not c:raise AssertionError(m)
