from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1252-3-5-')
import memory
from append_memory_journal import append_memory_journal,recover_append_journal
from indexed_memory_retrieval import indexed_memory_window,indexed_memory_operation_exists
from memory_compaction_recovery import memory_compaction,memory_index_rebuild,memory_append_recovery
from persistent_state_index import INDEX_FILENAME,persistent_state_index_status
checks=[]
def req(v): checks.append(bool(v)); assert v
mf=memory.MEMORY_FILE; mf.parent.mkdir(parents=True,exist_ok=True)
seed=[{'id':f'm{i}','type':'fact','created_at':'2026-01-01T00:00:00','content':f'topic {i%41} value {i}','conversation_operation_id':f'op{i}'} for i in range(5000)]
mf.write_text(json.dumps(seed,separators=(',',':')),encoding='utf-8')
# Read-only legacy access must not create derivative index files. Explicit migration owns the first index write.
recent=memory.load_memories(limit=80); req(len(recent)==80); req(recent[-1]['id']=='m4999'); req(not (mf.parent/INDEX_FILENAME).exists())
initial_rebuild=memory_index_rebuild(mf); req(initial_rebuild['ok']); req(initial_rebuild['indexed']==5000); req((mf.parent/INDEX_FILENAME).is_file())
window=indexed_memory_window(mf,limit=12); req(window['ok']); req(len(window['memories'])==12); req(window['full_legacy_json_parse'] is False)
req(indexed_memory_operation_exists(mf,'op4999','fact'))
before=mf.stat().st_size; memory.store_memory({'id':'m5000','type':'fact','content':'new value','conversation_operation_id':'op5000'},vectorize=False); after=mf.stat().st_size
rows=json.loads(mf.read_text()); req(len(rows)==5001); req(rows[-1]['id']=='m5000'); req(after>before); req(indexed_memory_operation_exists(mf,'op5000','fact'))
report=append_memory_journal(mf,[{'id':'m5001','type':'fact','content':'journal value'}]); req(report['ok']); req(report['full_history_rewrite'] is False); req(len(json.loads(mf.read_text()))==5002)
comp=memory_compaction(mf); req(comp['compacted']); req(comp['count']==5002); req(len(json.loads(mf.read_text()))==5002)
# Direct legacy rewrite must be noticed without allowing a read-only call to mutate the derivative index.
mf.write_text(json.dumps([{'id':'external','type':'fact','content':'external rewrite'}]),encoding='utf-8'); index_before=(mf.parent/INDEX_FILENAME).read_bytes(); req(memory.load_memories()==[{'id':'external','type':'fact','content':'external rewrite'}]); req((mf.parent/INDEX_FILENAME).read_bytes()==index_before)
reb=memory_index_rebuild(mf); req(reb['ok']); req(reb['indexed']==1)
# Simulate an interrupted append and verify bounded rollback of the tail.
base=mf.read_bytes(); insertion=base.rfind(b']'); tail=base[insertion:]; payload={'id':'partial','type':'fact','content':'partial'}; canonical=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False)
journal=mf.with_name(mf.name+'.append-journal.json'); journal.write_text(json.dumps({'schema_version':1,'insertion_offset':insertion,'tail_hex':tail.hex(),'record_count':1,'last_record_digest':hashlib.sha256(canonical.encode()).hexdigest()}),encoding='utf-8')
with mf.open('r+b') as h: h.seek(insertion); h.write(b',{"id":"partial"'); h.truncate()
rec=memory_append_recovery(mf); req(rec['recovered']); req(rec['action']=='rolled_back_incomplete_append'); req(json.loads(mf.read_text())[0]['id']=='external')
status=persistent_state_index_status(mf.parent); req(status['counts']['memories']==1)
source=(ROOT/'conscious_agent/memory.py').read_text(); req('append_memory_records' in source); req('mutate_memories(append)' not in source)
r={'suite':'v1252.3-v1252.5-memory-storage-indexing','ok':all(checks),'passed':sum(checks),'total':len(checks)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
