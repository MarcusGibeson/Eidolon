from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline
checks=[]
def req(v,n):checks.append(n);assert v,n
def d(s):return hashlib.sha256(s.encode()).hexdigest()
with tempfile.TemporaryDirectory() as td:
 t=MentalActivityTimeline(td)
 rows=[('cognitive','cycle_started','REFLECT'),('cognitive','cycle_completed','NO_DURABLE_CHANGE'),('memory','consolidation_candidate','PROCEDURAL_LESSON_REVIEW'),('self_model','trait_candidate','verification_scope_bias'),('planning','plan_review','attention_required'),('action','proposal_ready','calendar.create')]
 for i,(k,tr,o) in enumerate(rows):t.append(f'e{i}',event_kind=k,transition=tr,source_digest=d(f'e{i}'),outcome_code=o)
 recent=t.recent(limit=10)
 req(recent['event_count']==6,'integrated_timeline')
 req([x['sequence'] for x in recent['events']]==list(range(1,7)),'ordered')
 req(all(x['summary'] and len(x['summary'])<=180 for x in recent['events']),'bounded_summaries')
 req(all(not x['hidden_reasoning_exposed'] for x in recent['events']),'no_hidden_reasoning')
 req(all(not x['raw_content_stored'] for x in recent['events']),'no_raw_content')
 req(all(not x['authority_granted'] and not x['action_executed'] for x in recent['events']),'timeline_not_authority')
 req(recent['read_only_projection'],'read_only_projection')
 req(t.inspection_summary()['counts']['action']==1,'action_accounted')
print({'ok':True,'checkpoint_version':'2511.9','passed':len(checks),'total':len(checks),'checks':checks})
