from __future__ import annotations
import hashlib,json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1298-'))
from repeated_self_maintenance_foundations import *
from repeated_self_maintenance import *
from repeated_self_maintenance_reliability import *
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
def d(x):return hashlib.sha256(str(x).encode()).hexdigest()
def finish(s,work,final):
 s=start_cycle(s,work_item_digest=d(work),current_source_digest=s['current_source_digest'])
 for et in ('inspection_complete','backlog_complete','priority_selected','plan_complete','build_complete'):
  c=s['active_cycle'];kw={'new_proposal_count':1,'open_proposal_count':1} if et=='backlog_complete' else {};e=maintenance_event(c,sequence=c['next_sequence'],event_type=et,evidence_digest=d((work,et)),source_digest=c['source_digest_at_start'],prior_event_digest=c['prior_event_digest'],**kw);s=apply_maintenance_event(s,e)
 c=s['active_cycle'];s=apply_maintenance_event(s,maintenance_event(c,sequence=c['next_sequence'],event_type='test_result',evidence_digest=d((work,'test')),source_digest=c['source_digest_at_start'],prior_event_digest=c['prior_event_digest'],test_passed=True));c=s['active_cycle'];s=apply_maintenance_event(s,maintenance_event(c,sequence=c['next_sequence'],event_type='review_complete',evidence_digest=d((work,'review')),source_digest=c['source_digest_at_start'],prior_event_digest=c['prior_event_digest'],final_source_digest=d(final)));return s
s=create_maintenance_session(objective_digest=d('o'),initial_source_digest=d('s0'),max_cycles=3);s=finish(s,'w1','s1');s=finish(s,'w2','s2');a=audit_maintenance_state(s);req(a['ok'],'audit');req(not any(a[k] for k in DENIED_AUTHORITY),'authority')
req(not audit_maintenance_state({**s,'seen_work_item_digests':[d('w1'),d('w1')]} )['ok'],'duplicate');req(not audit_maintenance_state({**s,'open_proposal_count':99})['ok'],'growth');badcycles=list(s['cycles']);badcycles[1]={**badcycles[1],'source_digest_at_start':d('wrong')};req(not audit_maintenance_state({**s,'cycles':badcycles})['ok'],'lineage');req(not audit_maintenance_state({**s,'current_source_digest':d('wrong')})['ok'],'current_contradiction');req(not audit_maintenance_state({**s,'release_authorized':True})['ok'],'authority_tamper')
# stale source mid-cycle
x=create_maintenance_session(objective_digest=d('x'),initial_source_digest=d('x0'),max_cycles=2);x=start_cycle(x,work_item_digest=d('xw'),current_source_digest=d('x0'));c=x['active_cycle'];e=maintenance_event(c,sequence=1,event_type='inspection_complete',evidence_digest=d('e'),source_digest=d('other'));b=apply_maintenance_event(x,e);req(b['block_reason']=='source_changed_mid_cycle_stale_plan','stale_midcycle')
h=inspect_repeated_maintenance_surface_health(source_root=ROOT);req(h['ok'],'surface');req(h['native_windows_validation']=='desktop_review_required','native');req(CONTRACT_VERSION=='v1298.8','version')
print(json.dumps({'suite':'v1298.6-v1298.8-repeated-self-maintenance-reliability','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
