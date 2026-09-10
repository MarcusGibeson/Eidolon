from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.persistent_development_campaign import *
from conscious_agent.persistent_development_campaign_continuation import *
from conscious_agent.persistent_development_campaign_reliability import *
from conscious_agent.persistent_development_campaign_reliability_checkpoint import build_persistent_development_campaign_reliability_checkpoint
h=lambda s:hashlib.sha256(s.encode()).hexdigest();checks=[]
def req(x):checks.append(bool(x))
c=create_campaign_charter(campaign_id='c',source_baseline_digest=h('source'),scope_digest=h('scope'),goal_digests=[h('g')],limits={'max_work_items':2,'max_sessions':2,'max_elapsed_seconds':100,'max_disk_bytes':1000,'max_token_budget':200})
r=create_campaign_review(charter=c,decision='approve',operator_decision_digest=h('a'));l=create_campaign_ledger(charter=c,review=r,work_items=[{'work_item_id':'w1','status':'queued','work_item_digest':h('w1'),'content_free':True}])
s=create_campaign_session_snapshot(charter=c,review=r,ledger=l,session_id='s',session_index=1,state='active',consumed={'sessions':1});s['source_baseline_digest']=h('source');u=dict(s);u.pop('snapshot_digest');s['snapshot_digest']=hashlib.sha256(json.dumps(u,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
q=create_work_selection_review(snapshot=s,ledger=l,candidate_work_item_ids=['w1'],decision='approve',operator_decision_digest=h('q'));sel=create_bounded_work_selection(charter=c,snapshot=s,ledger=l,selection_review=q,max_items=1)
b=create_campaign_budget_receipt(charter=c,snapshot=s,observed={'work_items':1,'sessions':1,'elapsed_seconds':99,'disk_bytes':999,'token_budget':199});req(b['status']=='budget_within_limits');req(b['budget_enforced']);req(not b['work_executed'])
for key,val in [('work_items',3),('sessions',3),('elapsed_seconds',101),('disk_bytes',1001),('token_budget',201)]:req(create_campaign_budget_receipt(charter=c,snapshot=s,observed={key:val})['status']=='budget_exhausted')
req(create_campaign_budget_receipt(charter=c,snapshot=s,observed={'bad':1})['status']=='blocked');req(create_campaign_budget_receipt(charter=c,snapshot=s,observed={'sessions':-1})['status']=='blocked')
a=create_stale_work_assessment(snapshot=s,selection=sel,current_source_digest=h('source'),work_states={'w1':'current'});req(a['status']=='work_current');req(not a['automatic_reselection'])
for digest,state in [(h('drift'),'current'),(h('source'),'stale')]:req(create_stale_work_assessment(snapshot=s,selection=sel,current_source_digest=digest,work_states={'w1':state})['status']=='reconciliation_required')
req(create_stale_work_assessment(snapshot=s,selection=sel,current_source_digest=h('source'),work_states={})['status']=='blocked');req(create_stale_work_assessment(snapshot=s,selection=sel,current_source_digest='x',work_states={'w1':'current'})['status']=='blocked')
for reason in ['interruption','provider_outage','process_restart','operator_pause']:
 rec=create_campaign_recovery_receipt(snapshot=s,budget_receipt=b,stale_assessment=a,reason=reason,prior_runtime_digest=h('old'),restarted_runtime_digest=h('new'));req(rec['status']=='recovery_review_required');req(not rec['durable_resume_performed']);req(not rec['provider_contacted'])
req(create_campaign_recovery_receipt(snapshot=s,budget_receipt=b,stale_assessment=a,reason='magic',prior_runtime_digest=h('old'),restarted_runtime_digest=h('new'))['status']=='blocked')
ex=create_campaign_budget_receipt(charter=c,snapshot=s,observed={'elapsed_seconds':101});req(create_campaign_recovery_receipt(snapshot=s,budget_receipt=ex,stale_assessment=a,reason='process_restart',prior_runtime_digest=h('old'),restarted_runtime_digest=h('new'))['status']=='blocked')
mut=dict(s);mut['session_index']=9;req('tampered_snapshot' in create_campaign_budget_receipt(charter=c,snapshot=mut,observed={'sessions':1})['errors'])
summary=reliability_public_summary(b,a,create_campaign_recovery_receipt(snapshot=s,budget_receipt=b,stale_assessment=a,reason='process_restart',prior_runtime_digest=h('old'),restarted_runtime_digest=h('new')));req(set(summary).isdisjoint({'prompt','source','patch','stdout','stderr','memory','conversation'}));req(not summary['authority_granted'])
report=build_persistent_development_campaign_reliability_checkpoint(source_root=ROOT,runtime_root=Path(tempfile.gettempdir()));req(report['ok']);req(report['read_only']);req(not report['durable_resume_performed'])
print(json.dumps({'suite':'v1185.6-v1185.8-persistent-development-campaign-reliability','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True));raise SystemExit(0 if all(checks) else 1)
