from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.persistent_development_campaign import *
from conscious_agent.persistent_development_campaign_continuation import *
from conscious_agent.persistent_development_campaign_continuation_checkpoint import build_persistent_development_campaign_continuation_checkpoint
h=lambda s:hashlib.sha256(s.encode()).hexdigest(); checks=[]
def req(x):checks.append(bool(x))
c=create_campaign_charter(campaign_id='c1',source_baseline_digest=h('b'),scope_digest=h('s'),goal_digests=[h('g')],limits={'max_work_items':2,'max_sessions':3,'max_elapsed_seconds':100})
r=create_campaign_review(charter=c,decision='approve',operator_decision_digest=h('approve'))
items=[{'work_item_id':f'w{i}','status':'queued','work_item_digest':h(f'w{i}'),'content_free':True} for i in (1,2)]
l=create_campaign_ledger(charter=c,review=r,work_items=items)
s=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id='session-1',session_index=1,state='ready',consumed={'sessions':1,'work_items':0})
req(s['status']=='session_snapshot_ready');req(not s['durable_write_performed']);req(not s['work_executed'])
for d,st in [('approve','selection_approved'),('reject','selection_rejected'),('defer','selection_deferred')]:
 q=create_work_selection_review(snapshot=s,ledger=l,candidate_work_item_ids=['w1'],decision=d,operator_decision_digest=h(d));req(q['status']==st);req(not q['implementation_authorized'])
q=create_work_selection_review(snapshot=s,ledger=l,candidate_work_item_ids=['w1','w2'],decision='approve',operator_decision_digest=h('q'))
sel=create_bounded_work_selection(charter=c,snapshot=s,ledger=l,selection_review=q,max_items=1);req(sel['status']=='bounded_selection_ready');req(sel['selected_work_item_ids']==['w1']);req(not sel['work_executed']);req(sel['operator_review_required_before_execution'])
for target,ok in [('active',True),('abandoned',True),('completed',False),('paused',False)]: req((create_session_transition(snapshot=s,requested_state=target,operator_transition_digest=h(target))['status']=='transition_recorded')==ok)
paused=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id='session-2',session_index=2,state='paused',prior_snapshot_digest=s['snapshot_digest'],consumed={'sessions':2})
req(create_session_transition(snapshot=paused,requested_state='active',operator_transition_digest=h('resume'))['status']=='transition_recorded')
req(create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id='x',session_index=4,state='ready',consumed={'sessions':4})['status']=='blocked')
req(create_work_selection_review(snapshot=s,ledger=l,candidate_work_item_ids=['missing'],decision='approve',operator_decision_digest=h('x'))['status']=='blocked')
req(create_work_selection_review(snapshot=s,ledger=l,candidate_work_item_ids=['w1','w1'],decision='approve',operator_decision_digest=h('x'))['status']=='blocked')
req(create_bounded_work_selection(charter=c,snapshot=s,ledger=l,selection_review=q,max_items=3)['status']=='blocked')
mut=dict(s);mut['session_index']=9;req('tampered_snapshot' in create_work_selection_review(snapshot=mut,ledger=l,candidate_work_item_ids=['w1'],decision='approve',operator_decision_digest=h('x'))['errors'])
summary=continuation_public_summary(s,sel);req(set(summary).isdisjoint({'prompt','source','patch','stdout','stderr','memory','conversation'}));req(not summary['automatic_resume']);req(not summary['authority_granted'])
report=build_persistent_development_campaign_continuation_checkpoint(source_root=ROOT,runtime_root=Path(tempfile.gettempdir()));req(report['ok']);req(report['read_only']);req(not report['campaign_work_started'])
print(json.dumps({'suite':'v1185.3-v1185.5-persistent-development-campaign-continuation','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
