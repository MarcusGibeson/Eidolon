from __future__ import annotations
"""v1298.3-v1298.5 resumable multi-cycle maintenance evidence reducer."""
from typing import Any,Mapping
from repeated_self_maintenance_foundations import DENIED_AUTHORITY,digest,valid_digest
CONTRACT_VERSION='v1298.5'
def apply_maintenance_event(state:Mapping[str,Any],event:Mapping[str,Any])->dict[str,Any]:
 s=dict(state);cycle=dict(s.get('active_cycle') or {});e=dict(event)
 def blocked(reason):return {**s,'status':'maintenance_blocked','block_reason':reason,**DENIED_AUTHORITY}
 if not cycle:return blocked('no_active_cycle')
 if int(e.get('cycle_index') or 0)!=int(cycle.get('cycle_index') or 0):return blocked('cycle_identity_mismatch')
 if int(e.get('sequence') or 0)!=int(cycle.get('next_sequence') or 0):return blocked('stale_or_replayed_sequence')
 if str(e.get('prior_event_digest') or '')!=str(cycle.get('prior_event_digest') or ''):return blocked('event_chain_mismatch')
 sealed_payload={k:v for k,v in e.items() if k!='event_digest' and k not in DENIED_AUTHORITY}
 if not valid_digest(e.get('event_digest')) or e.get('event_digest')!=digest(sealed_payload):return blocked('event_digest_mismatch')
 if e.get('source_digest')!=cycle.get('source_digest_at_start'):return blocked('source_changed_mid_cycle_stale_plan')
 if any(bool(e.get(k)) for k in DENIED_AUTHORITY):return blocked('authority_expansion')
 stage=str(cycle.get('stage'));etype=str(e.get('event_type') or '')
 allowed={'inspect':'inspection_complete','backlog':'backlog_complete','prioritize':'priority_selected','plan':'plan_complete','build':'build_complete','test':'test_result','repair':'repair_complete','review':'review_complete'}
 if etype!=allowed.get(stage):return blocked('invalid_stage_transition')
 if stage=='backlog':
  new=int(e.get('new_proposal_count') or 0);opened=e.get('open_proposal_count');opened=int(opened if opened is not None else cycle.get('open_proposal_count') or 0)
  if new>int(s.get('max_new_proposals_per_cycle') or 0) or opened>int(s.get('max_open_proposals') or 0):return blocked('proposal_growth_budget_exceeded')
  cycle['new_proposal_count']=new;cycle['open_proposal_count']=opened;s['open_proposal_count']=opened
 if stage=='plan':cycle['planned_source_digest']=str(e.get('source_digest') or '')
 if stage in {'build','test','repair','review'} and cycle.get('planned_source_digest')!=cycle.get('source_digest_at_start'):return blocked('stale_plan_detected')
 next_stage={'inspect':'backlog','backlog':'prioritize','prioritize':'plan','plan':'build','build':'test'}
 if stage=='test':
  if e.get('test_passed') is True:next_name='review'
  else:cycle['test_failures']=int(cycle.get('test_failures') or 0)+1;next_name='repair'
 elif stage=='repair':cycle['repair_count']=int(cycle.get('repair_count') or 0)+1;next_name='test'
 elif stage=='review':
  final=str(e.get('final_source_digest') or '')
  if not valid_digest(final):return blocked('final_source_digest_required')
  next_name='complete';cycle['final_source_digest']=final
 else:next_name=next_stage.get(stage,'')
 events=list(cycle.get('events') or []);events.append({k:v for k,v in e.items() if k not in DENIED_AUTHORITY});cycle['events']=events;cycle['prior_event_digest']=e.get('event_digest');cycle['next_sequence']=int(cycle['next_sequence'])+1;cycle['stage']=next_name
 if next_name=='complete':
  cycle['status']='complete';cycles=list(s.get('cycles') or []);cycles.append({k:v for k,v in cycle.items() if k!='events'}|{'event_count':len(events),'completion_digest':digest(cycle)});s['cycles']=cycles;s['seen_work_item_digests']=list(s.get('seen_work_item_digests') or [])+[cycle['work_item_digest']];s['current_source_digest']=cycle['final_source_digest'];s['open_proposal_count']=max(0,int(cycle.get('open_proposal_count') or 0)-1);s['active_cycle']=None;s['status']='cycle_complete'
 else:s['active_cycle']=cycle;s['status']='cycle_active'
 s['session_digest']=digest({k:v for k,v in s.items() if k!='session_digest'});return s|DENIED_AUTHORITY

def maintenance_summary(state:Mapping[str,Any])->dict[str,Any]:
 s=dict(state);cycles=list(s.get('cycles') or []);return {'contract_version':CONTRACT_VERSION,'status':s.get('status'),'completed_cycle_count':len(cycles),'cycle_budget':s.get('max_cycles'),'seen_work_item_count':len(set(s.get('seen_work_item_digests') or [])),'open_proposal_count':s.get('open_proposal_count'),'current_source_digest':s.get('current_source_digest'),'test_failure_count':sum(int(c.get('test_failures') or 0) for c in cycles),'repair_count':sum(int(c.get('repair_count') or 0) for c in cycles),'duplicate_work_detected':len(s.get('seen_work_item_digests') or [])!=len(set(s.get('seen_work_item_digests') or [])),'read_only_projection':True,'content_free':True,**DENIED_AUTHORITY}
