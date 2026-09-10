from __future__ import annotations
import hashlib,json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1298-'))
from repeated_self_maintenance_foundations import *
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
def d(x):return hashlib.sha256(str(x).encode()).hexdigest()
s=create_maintenance_session(objective_digest=d('objective'),initial_source_digest=d('s0'),max_cycles=4,max_open_proposals=6,max_new_proposals_per_cycle=2);req(s['maintenance_session_id'].startswith('maintenance_'),'id');req(valid_digest(s['session_digest']),'digest');req(s['max_cycles']==4 and s['max_open_proposals']==6,'limits');req(not any(s[k] for k in DENIED_AUTHORITY),'authority');s2=start_cycle(s,work_item_digest=d('work1'),current_source_digest=d('s0'));c=s2['active_cycle'];req(c['cycle_index']==1 and c['stage']=='inspect','cycle');req(c['source_digest_at_start']==d('s0'),'source');e=maintenance_event(c,sequence=1,event_type='inspection_complete',evidence_digest=d('e1'),source_digest=d('s0'));req(valid_digest(e['event_digest']),'event');req(e['prior_event_digest']=='','chain')
for bad in [dict(objective_digest='bad',initial_source_digest=d('s')),dict(objective_digest=d('o'),initial_source_digest=d('s'),max_cycles=1)]:
 try:create_maintenance_session(**bad);ok=False
 except ValueError:ok=True
 req(ok,'bad_session')
try:start_cycle(s,work_item_digest=d('w'),current_source_digest=d('wrong'));ok=False
except ValueError:ok=True
req(ok,'stale_source');req(set(STAGES)>={'inspect','build','test','repair','review','complete'},'stages');req(CONTRACT_VERSION=='v1298.2','version')
print(json.dumps({'suite':'v1298.0-v1298.2-repeated-self-maintenance-foundations','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
