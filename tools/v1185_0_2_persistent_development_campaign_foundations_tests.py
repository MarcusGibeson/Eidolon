from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.persistent_development_campaign import *
from conscious_agent.persistent_development_campaign_foundations_checkpoint import build_persistent_development_campaign_foundations_checkpoint
h=lambda s:hashlib.sha256(s.encode()).hexdigest(); checks=[]
def req(x): checks.append(bool(x))
c=create_campaign_charter(campaign_id='c1',source_baseline_digest=h('b'),scope_digest=h('s'),goal_digests=[h('g1'),h('g2')],limits={'max_work_items':3,'max_sessions':2,'max_elapsed_seconds':60,'max_disk_bytes':1024,'max_token_budget':500})
req(c['status']=='ready_for_review');req(c['content_free']);req(not c['work_started']);req(not c['authority_granted'])
for d,st in [('approve','approved_not_started'),('reject','rejected'),('defer','deferred')]:
 r=create_campaign_review(charter=c,decision=d,operator_decision_digest=h(d));req(r['status']==st);req(not r['execution_invoked']);req(not r['authority_granted'])
r=create_campaign_review(charter=c,decision='approve',operator_decision_digest=h('a'));l=create_campaign_ledger(charter=c,review=r);req(l['status']=='approved_empty_ledger');req(not l['work_started'])
item={'work_item_id':'w1','status':'queued','work_item_digest':h('w1'),'content_free':True};l2=create_campaign_ledger(charter=c,review=r,work_items=[item]);req(l2['status']=='approved_bounded_ledger');req(l2['work_item_count']==1)
mut=dict(c);mut['scope_digest']='0'*64;req('tampered_charter' in create_campaign_review(charter=mut,decision='approve',operator_decision_digest=h('a'))['errors'])
for bad in [
 create_campaign_charter(campaign_id='',source_baseline_digest=h('b'),scope_digest=h('s'),goal_digests=[h('g')],limits={'max_sessions':1}),
 create_campaign_charter(campaign_id='x',source_baseline_digest='x',scope_digest=h('s'),goal_digests=[h('g')],limits={'max_sessions':1}),
 create_campaign_charter(campaign_id='x',source_baseline_digest=h('b'),scope_digest=h('s'),goal_digests=[],limits={'max_sessions':1}),
 create_campaign_charter(campaign_id='x',source_baseline_digest=h('b'),scope_digest=h('s'),goal_digests=[h('g'),h('g')],limits={'max_sessions':1}),
 create_campaign_charter(campaign_id='x',source_baseline_digest=h('b'),scope_digest=h('s'),goal_digests=[h('g')],limits={'max_sessions':0}),
]: req(bad['status']=='blocked')
req(create_campaign_review(charter=c,decision='launch',operator_decision_digest=h('x'))['status']=='blocked')
req(create_campaign_ledger(charter=c,review=create_campaign_review(charter=c,decision='reject',operator_decision_digest=h('r')))['status']=='blocked')
req(create_campaign_ledger(charter=c,review=r,work_items=[item,item])['status']=='blocked')
s=campaign_public_summary(c,r,l);req(set(s).isdisjoint({'prompt','source','patch','stdout','stderr','memory','conversation'}));req(s['operator_review_required_for_work_selection'])
report=build_persistent_development_campaign_foundations_checkpoint(source_root=ROOT,runtime_root=Path(tempfile.gettempdir()));req(report['ok']);req(report['read_only']);req(not report['campaign_work_started'])
print(json.dumps({'suite':'v1185.0-v1185.2-persistent-development-campaign-foundations','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
