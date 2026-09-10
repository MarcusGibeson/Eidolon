from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1252-6-8-')
from indexed_chat_action_ledger import action_ledger_index_report,action_ledger_lookup
from persistent_state_index import INDEX_FILENAME,rebuild_action_index,update_action_index,validate_persistent_index_consistency
from persistent_state_projection_cache import cached_projection,clear_persistent_projection_cache,persistent_projection_cache_status
from persistent_state_scaling_migration import rebuild_persistent_indexes,recover_corrupt_persistent_index
checks=[]
def req(v): checks.append(bool(v)); assert v
root=Path(os.environ['EIDOLON_DATA_DIR']); ad=root/'chat_actions'; ad.mkdir(parents=True)
for i in range(700):
    row={'id':f'chat_action_{i:05d}','status':'executed' if i%4==0 else 'proposed','created_at':f'2026-07-01T00:{i%60:02d}:00','updated_at':f'2026-07-01T00:{i%60:02d}:00','deduplication_key':f'op-{i}','intent':f'action topic {i%19}'}
    (ad/f"{row['id']}.json").write_text(json.dumps(row,separators=(',',':')),encoding='utf-8')
reb=rebuild_action_index(ad); req(reb['indexed']==700)
report=action_ledger_index_report(ad); req(report['ok']); req(report['count']==700); req(report['full_receipt_parse'] is False)
ids=action_ledger_lookup(ad,deduplication_keys=('op-699',)); req(ids==['chat_action_00699'])
clear_persistent_projection_cache(); calls={'n':0}
def build(): calls['n']+=1; return {'value':calls['n']}
a=cached_projection(ad,'action',('probe',),build,ttl_seconds=60); b=cached_projection(ad,'action',('probe',),build,ttl_seconds=60); req(a==b=={'value':1}); req(calls['n']==1)
new={'id':'chat_action_00700','status':'proposed','created_at':'2026-07-02T00:00:00','updated_at':'2026-07-02T00:00:00','deduplication_key':'op-700','intent':'new'}; (ad/'chat_action_00700.json').write_text(json.dumps(new),encoding='utf-8'); update_action_index(ad,new)
c=cached_projection(ad,'action',('probe',),build,ttl_seconds=60); req(c=={'value':2}); req(calls['n']==2); req(persistent_projection_cache_status()['invalidations']>=1)
# Seed canonical memory/session sources so a complete rebuild can prove migration ownership.
(root/'memories.json').write_text('[{"id":"m1","type":"fact","content":"x"}]',encoding='utf-8'); sd=root/'conversation_sessions'; sd.mkdir(); sid='conversation_session_20260807T120000_0000000001'; (sd/f'{sid}.json').write_text(json.dumps({'id':sid,'type':'conversation_session','project_id':'eidolon','title':'x','created_at':'2026-08-07T12:00:00Z','updated_at':'2026-08-07T12:00:00Z','last_turn_at':'','turn_count':0,'completed_turn_count':0,'status':'active','turns':[]}),encoding='utf-8')
mig=rebuild_persistent_indexes(root); req(mig['ok']); req(mig['canonical_data_mutated'] is False); req(mig['consistency']['counts']=={'sessions':1,'memories':1,'actions':701})
index=root/INDEX_FILENAME; req(index.is_file()); rec=recover_corrupt_persistent_index(root); req(rec['ok']); req(rec['recovered']); req(Path(rec['quarantined_index']).is_file()); req(rec['consistency']['counts']['actions']==701)
cons=validate_persistent_index_consistency(root); req(cons['ok'])
r={'suite':'v1252.6-v1252.8-action-cache-migration','ok':all(checks),'passed':sum(checks),'total':len(checks)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
