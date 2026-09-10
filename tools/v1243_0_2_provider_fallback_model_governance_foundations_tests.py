from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from provider_fallback_model_governance import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest()
c=[];ck=lambda v:c.append(bool(v))

def providers(local_health='ready',remote_health='ready'):
 return [
  {'provider_id':'provider_local_primary','provider_class':'local','health_state':local_health,'privacy_tier':'local_only','capability_codes':['generation','code','analysis'],'tool_support':True,'streaming_support':True,'health_evidence_digest':h('lh'+local_health),'configuration_digest':h('lc'),'governance_policy_digest':h('lp'),'models':[{'model_id':'model_local_code','capability_codes':['generation','code','analysis'],'context_window':8192,'tool_support':True,'streaming_support':True,'quality_tier':'high','latency_tier':'low','cost_tier':'none','model_evidence_digest':h('lm'),'enabled':True},{'model_id':'model_local_small','capability_codes':['generation'],'context_window':2048,'tool_support':False,'streaming_support':True,'quality_tier':'medium','latency_tier':'low','cost_tier':'none','model_evidence_digest':h('ls'),'enabled':True}]},
  {'provider_id':'provider_remote_backup','provider_class':'remote','health_state':remote_health,'privacy_tier':'redacted_remote','capability_codes':['generation','code','analysis'],'tool_support':True,'streaming_support':True,'health_evidence_digest':h('rh'+remote_health),'configuration_digest':h('rc'),'governance_policy_digest':h('rp'),'models':[{'model_id':'model_remote_code','capability_codes':['generation','code','analysis'],'context_window':32768,'tool_support':True,'streaming_support':True,'quality_tier':'high','latency_tier':'medium','cost_tier':'medium','model_evidence_digest':h('rm'),'enabled':True}]}
 ]
reg=provider_model_governance_registry();contract=build_provider_model_governance_contract()
for v in (reg['ok'],reg['inspection_only'],len(reg['provider_classes'])==2,len(reg['health_states'])==5,bool(reg['registry_digest']),contract['ok'],contract['retained_provider_model_module_count']==7,contract['local_remote_privacy_classification_required'],contract['context_tool_streaming_compatibility_checked'],contract['provider_outage_never_triggers_automatic_fallback']):ck(v)
for k,e in AUTHORITY_FLAGS.items():ck(reg.get(k) is e and contract.get(k) is e)
with tempfile.TemporaryDirectory() as rt:
 s=prepare_provider_model_registry_snapshot(providers(),registry_policy_digest=h('policy'),snapshot_evidence_digest=h('evidence'),registry_generation=1,runtime_root=rt)
 for v in (s['ok'],s['provider_count']==2,s['model_count']==3,s['local_provider_count']==1,s['remote_provider_count']==1,s['health_evidence_digest_bound'],s['configuration_digest_bound'],bool(s['registry_record_digest'])):ck(v)
 same=prepare_provider_model_registry_snapshot(providers(),registry_policy_digest=h('policy'),snapshot_evidence_digest=h('evidence'),registry_generation=1,runtime_root=rt);ck(same['snapshot_id']==s['snapshot_id']);ck(same['registry_record_digest']==s['registry_record_digest'])
 p=prepare_provider_model_selection('project_alpha',task_digest=h('task'),registry_snapshot_id=s['snapshot_id'],expected_registry_digest=s['registry_record_digest'],preferred_provider_id='provider_local_primary',preferred_model_id='model_local_code',privacy_requirement='local_only',required_capabilities=['generation','code'],minimum_context_window=4096,tools_required=True,streaming_required=True,fallback_reason='none',restricted_data_codes=['project_digest'],orchestration_plan_id='orchestration_plan_'+('a'*24),orchestration_plan_digest=h('orch'),execution_session_id='session_alpha',execution_session_digest=h('sess'),runtime_root=rt)
 for v in (p['ok'],p['selection_state']=='preferred_ready',p['selected_provider_id']=='provider_local_primary',p['selected_model_id']=='model_local_code',p['preferred_compatible'],p['compatible_candidate_count']>=1,p['selection_acceptable'],not p['issue_codes'],bool(p['proposal_record_digest']),p['privacy_implication_codes'][0] in {'no_external_data_route','no_restricted_data_codes_declared'}):ck(v)
 for k,e in AUTHORITY_FLAGS.items():ck(p.get(k) is e)
with tempfile.TemporaryDirectory() as rt:
 s=prepare_provider_model_registry_snapshot(providers(local_health='unavailable'),registry_policy_digest=h('policy'),snapshot_evidence_digest=h('evidence2'),registry_generation=2,runtime_root=rt)
 p=prepare_provider_model_selection('project_alpha',task_digest=h('task2'),registry_snapshot_id=s['snapshot_id'],expected_registry_digest=s['registry_record_digest'],preferred_provider_id='provider_local_primary',preferred_model_id='model_local_code',privacy_requirement='redacted_remote_allowed',required_capabilities=['generation','code'],minimum_context_window=4096,tools_required=True,streaming_required=True,fallback_reason='provider_unavailable',restricted_data_codes=['digest_only'],runtime_root=rt)
 for v in (p['ok'],p['selection_state']=='fallback_proposed',p['selected_provider_id']=='provider_remote_backup',p['selected_model_id']=='model_remote_code','provider_unavailable' in p['why_fallback_needed_codes'],bool(p['tradeoff_codes'])):ck(v)
 local=prepare_provider_model_selection('project_alpha',task_digest=h('task3'),registry_snapshot_id=s['snapshot_id'],expected_registry_digest=s['registry_record_digest'],preferred_provider_id='provider_local_primary',preferred_model_id='model_local_code',privacy_requirement='local_only',required_capabilities=['generation','code'],minimum_context_window=4096,tools_required=True,streaming_required=True,fallback_reason='provider_unavailable',runtime_root=rt)
 ck(not local['ok']);ck(local['reason']=='') if 'reason' in local and local['status'].endswith('blocked') else ck(local['selection_state']=='blocked');ck(not local.get('provider_contact_authorized'))
for raw,reason in [([], 'provider_registry_required'),([{'provider_id':'provider_secret_token'}],'invalid_provider_id')]:
 with tempfile.TemporaryDirectory() as rt:
  row=prepare_provider_model_registry_snapshot(raw,registry_policy_digest=h('p'),snapshot_evidence_digest=h('e'),registry_generation=1,runtime_root=rt);ck(not row['ok']);ck(reason in row['reason'])
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
