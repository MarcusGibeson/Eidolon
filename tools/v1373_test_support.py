import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
C='a'*64
TASKS=[
 {"task_id":"a","status":"completed","depends_on":[],"work_units":2,"priority":1},
 {"task_id":"b","status":"pending","depends_on":["a"],"work_units":3,"priority":1},
 {"task_id":"c","status":"pending","depends_on":["a"],"work_units":5,"priority":0},
 {"task_id":"d","status":"pending","depends_on":["b","c"],"work_units":2,"priority":4},
]
def req(c,m):
 if not c: raise AssertionError(m)
