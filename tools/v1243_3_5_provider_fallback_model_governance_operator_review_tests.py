from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from provider_fallback_model_governance import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))

def fixture(rt):
 providers=[{'provider_id':'provider_local_primary','provider_class':'local','health_state':'unavailable','privacy_tier':'local_only','capability_codes':['generation','code'],'tool_support':True,'streaming_support':True,'health_evidence_digest':h('lh'),'configuration_digest':h('lc'),'governance_policy_digest':h('lp'),'models':[{'model_id':'model_local_code','capability_codes':['generation','code'],'context_window':8192,'tool_support':True,'streaming_support':True,'quality_tier':'high','latency_tier':'low','cost_tier':'none','model_evidence_digest':h('lm'),'enabled':True}]},{'provider_id':'provider_remote_backup','provider_class':'remote','health_state':'ready','privacy_tier':'redacted_remote','capability_codes':['generation','code'],'tool_support':True,'streaming_support':True,'health_evidence_digest':h('rh'),'configuration_digest':h('rc'),'governance_policy_digest':h('rp'),'models':[{'model_id':'model_remote_code','capability_codes':['generation','code'],'context_window':32768,'tool_support':True,'streaming_support':True,'quality_tier':'high','latency_tier':'medium','cost_tier':'medium','model_evidence_digest':h('rm'),'enabled':True}]}]
 s=prepare_provider_model_registry_snapshot(providers,registry_policy_digest=h('policy'),snapshot_evidence_digest=h('evidence'),registry_generation=1,runtime_root=rt)
 p=prepare_provider_model_selection('project_alpha',task_digest=h('task'),registry_snapshot_id=s['snapshot_id'],expected_registry_digest=s['registry_record_digest'],preferred_provider_id='provider_local_primary',preferred_model_id='model_local_code',privacy_requirement='redacted_remote_allowed',required_capabilities=['generation','code'],minimum_context_window=4096,tools_required=True,streaming_required=True,fallback_reason='provider_unavailable',restricted_data_codes=['digest_only'],runtime_root=rt)
 phrase=f"Review provider model selection accept_selection for proposal {p['proposal_id']} digest {p['proposal_record_digest']}."
 r=review_provider_model_selection(p['proposal_id'],expected_proposal_digest=p['proposal_record_digest'],disposition='accept_selection',exact_phrase=phrase,runtime_root=rt)
 return s,p,r,phrase
with tempfile.TemporaryDirectory() as rt:
 s,p,r,phrase=fixture(rt)
 for v in (r['ok'],r['selection_interpretation_accepted'],not r['operator_follow_up_required'],r['fresh_provider_contact_authority_still_required'],not r['provider_contact_authority_created'],not r['prompt_transmission_authority_created'],not r['provider_switch_authority_created'],not r['default_model_change_authority_created'],not r['execution_resume_authority_created'],bool(r['review_record_digest'])):ck(v)
 replay=review_provider_model_selection(p['proposal_id'],expected_proposal_digest=p['proposal_record_digest'],disposition='accept_selection',exact_phrase=phrase,runtime_root=rt);ck(replay['review_id']==r['review_id']);ck(replay['review_record_digest']==r['review_record_digest'])
 a=prepare_provider_fallback_assessment(p['proposal_id'],expected_proposal_digest=p['proposal_record_digest'],proposal_review_id=r['review_id'],expected_review_digest=r['review_record_digest'],current_registry_digest=s['registry_record_digest'],observed_provider_id=p['selected_provider_id'],observed_model_id=p['selected_model_id'],observed_health_state='unavailable',health_evidence_digest=h('outage'),failure_code='provider_outage',attempt_count=1,prompt_was_transmitted=False,response_was_received=False,evidence_complete=True,runtime_root=rt)
 for v in (a['ok'],a['recommended_action']=='prepare_new_selection_proposal',a['new_selection_proposal_only'],not a['automatic_fallback_permitted'],not a['automatic_retry_permitted'],not a['automatic_resume_permitted'],not a['provider_contact_authorized'],bool(a['assessment_record_digest'])):ck(v)
 aphrase=f"Review provider fallback acknowledge for assessment {a['assessment_id']} digest {a['assessment_record_digest']}."
 ar=review_provider_fallback(a['assessment_id'],expected_assessment_digest=a['assessment_record_digest'],disposition='acknowledge',exact_phrase=aphrase,runtime_root=rt)
 for v in (ar['ok'],ar['fallback_interpretation_acknowledged'],not ar['new_selection_authority_created'],not ar['provider_contact_authority_created'],not ar['retry_authority_created'],not ar['resume_authority_created'],ar['fresh_exact_selection_and_contact_authority_still_required']):ck(v)
 for factory,key in ((public_provider_model_registry_snapshots,'snapshot_count'),(public_provider_model_selection_proposals,'proposal_count'),(public_provider_model_selection_reviews,'review_count'),(public_provider_fallback_assessments,'fallback_assessment_count'),(public_provider_fallback_reviews,'fallback_review_count')):
  row=factory(runtime_root=rt);ck(row['ok']);ck(row[key]==1);ck(row['content_free'])
 for text in ('show provider model governance registry','show provider model registry snapshots','show provider model selection proposals','show provider model selection reviews','show provider fallback assessments','show provider fallback reviews'):
  turn=process_ordinary_chat_development_turn(text,runtime_root=rt);ck(turn.get('active'));ck('provider_model_governance' in turn);ck('read-only inspection' in turn['response'] or 'ready for read-only inspection' in turn['response'])
 turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt);ck(turn.get('active'));ck(turn['provider_model_governance']['review_id']==r['review_id']);ck('No provider contact' in turn['response'])
 turn=process_ordinary_chat_development_turn(aphrase,runtime_root=rt);ck(turn.get('active'));ck(turn['provider_model_governance']['review_id']==ar['review_id']);ck('No provider contact' in turn['response'])
 d=provider_model_governance_dashboard_record(runtime_root=rt);page=render_provider_model_governance_dashboard_html(runtime_root=rt)
 for v in (d['read_only'],d['proposal_count']==1,d['review_count']==1,d['fallback_assessment_count']==1,not d['provider_contact_authorized'],'Provider Fallback and Model Governance' in page,'GET-only inspection' in page):ck(v)
for k,e in AUTHORITY_FLAGS.items():ck(r.get(k) is e and a.get(k) is e and ar.get(k) is e)
source={n:(R/n).read_text(encoding='utf-8') for n in ('conscious_agent/api_server.py','eidolon.py','conscious_agent/dashboard.py','conscious_agent/ordinary_chat_development_campaign.py')}
for token in ('provider-model-governance-registry','provider-model-registry-snapshots','provider-model-selection-proposals','provider-fallback-assessments','provider-fallback-model-governance-checkpoint'):ck(token in source['conscious_agent/api_server.py'] and token in source['eidolon.py'])
ck('/provider-model-governance' in source['conscious_agent/dashboard.py']);ck('/api/provider-model-governance' in source['conscious_agent/dashboard.py']);ck('process_provider_model_governance_control' in source['conscious_agent/ordinary_chat_development_campaign.py'])
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
