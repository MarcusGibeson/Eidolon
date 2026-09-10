from __future__ import annotations
import json,sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from temporal_identity_coherence import build_temporal_identity_projection,resolve_identity_alias,temporal_relation
checks=[]
def req(v,n): checks.append(n); assert v,n
now=datetime(2026,8,22,tzinfo=timezone.utc)
rows=[
 {'id':'1','entity_id':'person:alex','name':'Alex','aliases':['A'],'role':'coworker','occurred_at':'2024-01-01T00:00:00Z'},
 {'id':'2','entity_id':'person:alex','name':'Alex','aliases':['A'],'role':'friend','occurred_at':'2025-01-01T00:00:00Z'},
 {'id':'3','entity_id':'person:other','name':'Alex','aliases':['Other Alex'],'role':'neighbor','occurred_at':'2025-02-01T00:00:00Z'},
 {'id':'4','entity_id':'project:eidolon','name':'Eidolon','role':'version_1800','start_at':'2026-08-20T00:00:00Z','end_at':'2026-08-22T00:00:00Z'},
 {'id':'5','entity_id':'person:alex','event_type':'anniversary','anniversary':True,'occurred_at':'about 2026-08-22T12:00:00Z'},
 {'id':'6','entity_id':'person:alex','recurrence':'yearly','start_at':'2020-08-22T00:00:00Z','end_at':'2020-08-22T23:59:00Z'},
]
out=build_temporal_identity_projection(rows,now=now)
req(out['ok'],'projection_ok')
req(out['evidence']['entity_count']==3,'explicit_identity_count')
req(out['evidence']['role_change_count']>=1,'role_change_tracked')
req(out['evidence']['uncertain_date_count']>=1,'uncertain_date_tracked')
req(out['evidence']['recurring_event_count']==1,'recurrence_tracked')
req(out['evidence']['anniversary_count']==1,'anniversary_tracked')
req(out['evidence']['identity_mutated'] is False,'identity_not_mutated')
req(resolve_identity_alias('Other Alex',rows)['resolved'] is True,'unique_alias_resolves')
req(resolve_identity_alias('Alex',rows)['ambiguous'] is True,'ambiguous_name_fails_closed')
req(temporal_relation({'start_at':'2024-01-01T00:00:00Z','end_at':'2024-01-02T00:00:00Z'},{'start_at':'2024-02-01T00:00:00Z','end_at':'2024-02-02T00:00:00Z'})=='before','before_relation')
req(temporal_relation({'start_at':'about 2024-01-01T00:00:00Z'},{'start_at':'2024-02-01T00:00:00Z'})=='uncertain','uncertain_relation')
print(json.dumps({'suite':'v1850.9-temporal-identity','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
