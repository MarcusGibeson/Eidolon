from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from provider_fallback_model_governance import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))

def fixture(rt,privacy='redacted_remote_allowed'):
 providers=[{'provider_id':'provider_local_primary','provider_class':'local','health_state':'unavailable','privacy_tier':'local_only','capability_codes':['generation','code'],'tool_support':True,'streaming_support':True,'health_evidence_digest':h('lh'),'configuration_digest':h('lc'),'governance_policy_digest':h('lp'),'models':[{'model_id':'model_local_code','capability_codes':['generation','code'],'context_window':8192,'tool_support':True,'streaming_support':True,'quality_tier':'high','latency_tier':'low','cost_tier':'none','model_evidence_digest':h('lm'),'enabled':True}]},{'provider_id':'provider_remote_backup','provider_class':'remote','health_state':'ready','privacy_tier':'redacted_remote','capability_codes':['generation','code'],'tool_support':True,'streaming_support':True,'health_evidence_digest':h('rh'),'configuration_digest':h('rc'),'governance_policy_digest':h('rp'),'models':[{'model_id':'model_remote_code','capability_codes':['generation','code'],'context_window':32768,'tool_support':True,'streaming_support':True,'quality_tier':'high','latency_tier':'medium','cost_tier':'medium','model_evidence_digest':h('rm'),'enabled':True}]}]
 s=prepare_provider_model_registry_snapshot(providers,registry_policy_digest=h('policy'),snapshot_evidence_digest=h('evidence'),registry_generation=1,runtime_root=rt)
 p=prepare_provider_model_selection('project_alpha',task_digest=h('task'),registry_snapshot_id=s['snapshot_id'],expected_registry_digest=s['registry_record_digest'],preferred_provider_id='provider_local_primary',preferred_model_id='model_local_code',privacy_requirement=privacy,required_capabilities=['generation','code'],minimum_context_window=4096,tools_required=True,streaming_required=True,fallback_reason='provider_unavailable',restricted_data_codes=['digest_only'],runtime_root=rt)
 if not p.get('ok'): return s,p,{}
 phrase=f"Review provider model selection accept_selection for proposal {p['proposal_id']} digest {p['proposal_record_digest']}."
 r=review_provider_model_selection(p['proposal_id'],expected_proposal_digest=p['proposal_record_digest'],disposition='accept_selection',exact_phrase=phrase,runtime_root=rt)
 return s,p,r
with tempfile.TemporaryDirectory() as rt:
 s,p,r=fixture(rt)
 stale=prepare_provider_model_selection('project_alpha',task_digest=h('task'),registry_snapshot_id=s['snapshot_id'],expected_registry_digest=h('stale'),preferred_provider_id='provider_local_primary',preferred_model_id='model_local_code',privacy_requirement='redacted_remote_allowed',required_capabilities=['generation'],minimum_context_window=128,tools_required=False,streaming_required=False,fallback_reason='provider_unavailable',runtime_root=rt);ck(not stale['ok']);ck(stale['reason']=='stale_or_mismatched_registry_digest')
 badphrase=review_provider_model_selection(p['proposal_id'],expected_proposal_digest=p['proposal_record_digest'],disposition='accept_selection',exact_phrase='accept it',runtime_root=rt);ck(not badphrase['ok']);ck(badphrase['reason']=='exact_review_phrase_required')
 stalereview=review_provider_model_selection(p['proposal_id'],expected_proposal_digest=h('stale'),disposition='hold',exact_phrase=f"Review provider model selection hold for proposal {p['proposal_id']} digest {h('stale')}.",runtime_root=rt);ck(not stalereview['ok']);ck(stalereview['reason']=='stale_or_mismatched_proposal_digest')
 matches=list(Path(rt).rglob(f"{p['proposal_id']}.json"));ck(len(matches)==1);raw=json.loads(matches[0].read_text());raw['selected_model_id']='model_tampered';matches[0].write_text(json.dumps(raw));tampered=load_provider_model_selection(p['proposal_id'],runtime_root=rt);ck(not tampered['ok']);ck(tampered['status']=='provider_model_selection_tampered')
with tempfile.TemporaryDirectory() as rt:
 s,p,r=fixture(rt)
 cases=[
  dict(current_registry_digest=s['registry_record_digest'],observed_provider_id=p['selected_provider_id'],observed_model_id=p['selected_model_id'],observed_health_state='ready',failure_code='none',evidence_complete=True,prompt_was_transmitted=False,response_was_received=False,action='no_action',ok=True),
  dict(current_registry_digest=h('changed'),observed_provider_id=p['selected_provider_id'],observed_model_id=p['selected_model_id'],observed_health_state='unavailable',failure_code='provider_outage',evidence_complete=True,prompt_was_transmitted=False,response_was_received=False,action='refresh_registry_and_reprepare',ok=False),
  dict(current_registry_digest=s['registry_record_digest'],observed_provider_id='provider_local_primary',observed_model_id='model_local_code',observed_health_state='unavailable',failure_code='provider_outage',evidence_complete=True,prompt_was_transmitted=False,response_was_received=False,action='manual_reconciliation_required',ok=False),
  dict(current_registry_digest=s['registry_record_digest'],observed_provider_id=p['selected_provider_id'],observed_model_id=p['selected_model_id'],observed_health_state='unknown',failure_code='unknown_failure',evidence_complete=False,prompt_was_transmitted=False,response_was_received=False,action='hold_for_evidence',ok=False),
  dict(current_registry_digest=s['registry_record_digest'],observed_provider_id=p['selected_provider_id'],observed_model_id=p['selected_model_id'],observed_health_state='degraded',failure_code='read_timeout',evidence_complete=True,prompt_was_transmitted=True,response_was_received=False,action='prepare_new_selection_proposal',ok=True),
  dict(current_registry_digest=s['registry_record_digest'],observed_provider_id=p['selected_provider_id'],observed_model_id=p['selected_model_id'],observed_health_state='ready',failure_code='none',evidence_complete=True,prompt_was_transmitted=False,response_was_received=True,action='manual_reconciliation_required',ok=False),
 ]
 for i,x in enumerate(cases):
  a=prepare_provider_fallback_assessment(p['proposal_id'],expected_proposal_digest=p['proposal_record_digest'],proposal_review_id=r['review_id'],expected_review_digest=r['review_record_digest'],health_evidence_digest=h('health'+str(i)),attempt_count=i, runtime_root=rt,**{k:v for k,v in x.items() if k not in {'action','ok'}})
  ck(a['recommended_action']==x['action']);ck(a['ok'] is x['ok']);ck(not a['automatic_fallback_authorized']);ck(not a['automatic_retry_authorized']);ck(not a['automatic_resume_authorized']);ck(not a['provider_contact_authorized'])
 bad=prepare_provider_fallback_assessment(p['proposal_id'],expected_proposal_digest=h('stale'),proposal_review_id=r['review_id'],expected_review_digest=r['review_record_digest'],current_registry_digest=s['registry_record_digest'],observed_provider_id=p['selected_provider_id'],observed_model_id=p['selected_model_id'],observed_health_state='unavailable',health_evidence_digest=h('x'),failure_code='provider_outage',attempt_count=1,prompt_was_transmitted=False,response_was_received=False,evidence_complete=True,runtime_root=rt);ck(not bad['ok']);ck(bad['reason']=='stale_or_mismatched_selection_lineage')
with tempfile.TemporaryDirectory() as rt:
 s,p,r=fixture(rt,privacy='local_only');ck(not p['ok']);ck(p['selection_state']=='blocked');ck('no_compatible_provider_model' in p['issue_codes'])
for bad in ('private_path','secret_token','../escape','a'):
 with tempfile.TemporaryDirectory() as rt:
  row=prepare_provider_model_registry_snapshot([{'provider_id':bad}],registry_policy_digest=h('p'),snapshot_evidence_digest=h('e'),registry_generation=1,runtime_root=rt);ck(not row['ok'])
for k,e in AUTHORITY_FLAGS.items():ck(provider_model_governance_registry().get(k) is e)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
