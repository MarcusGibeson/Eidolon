from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from causal_counterfactual_intelligence import *
checks=[]
def req(v,n): checks.append(n); assert v,n
H=[
 {'hypothesis_code':'cache_stale','proposition':'stale cache reused','prior_confidence':.5,'predictions':{'bypass_cache':'request_succeeds','restart_only':'still_fails'},'confounders':['network_variance']},
 {'hypothesis_code':'provider_down','proposition':'provider unavailable','prior_confidence':.5,'predictions':{'bypass_cache':'still_fails','restart_only':'still_fails'},'confounders':['network_variance']},
 {'hypothesis_code':'process_state','proposition':'bad process state','prior_confidence':.4,'predictions':{'bypass_cache':'still_fails','restart_only':'request_succeeds'},'confounders':['timing']},
]
with tempfile.TemporaryDirectory(prefix='eidolon-v1750-9-') as td:
 rt=Path(td)/'runtime'
 case=create_causal_case('Requests fail after configuration change',H,evidence_provenance=['operator_observation'],runtime_root=rt)
 req(case['ok'] and case['hypothesis_count']==3,'case_ready')
 req(case['discriminating_probes'][0]['discrimination_score']>0,'discriminating_probe')
 req(case['root_cause_proven'] is False and case['correlation_is_not_causation'],'no_false_proof')
 req(not case['private_hypothesis_text_exposed'] and not case['raw_evidence_exposed'],'privacy')
 cid=case['causal_case_id'];d=case['causal_case_digest']
 stale=record_probe_observation(cid,'0'*64,probe_code='bypass_cache',observed_outcome='request_succeeds',evidence_digest='1'*64,runtime_root=rt)
 req(not stale['ok'] and stale['status']=='stale_causal_case_digest','stale_rejected')
 updated=record_probe_observation(cid,d,probe_code='bypass_cache',observed_outcome='request_succeeds',evidence_digest='1'*64,evidence_quality=.95,independence=.95,runtime_root=rt)
 req(updated['status']=='causal_observation_recorded','observation_recorded')
 rows={h['hypothesis_code']:h for h in updated['hypotheses']}
 req(rows['cache_stale']['posterior_confidence']>.5,'support_raises')
 req(rows['provider_down']['posterior_confidence']<.5,'contradiction_lowers')
 req(rows['cache_stale']['root_cause_proven'] is False,'still_not_proven')
 replay=record_probe_observation(cid,updated['causal_case_digest'],probe_code='bypass_cache',observed_outcome='request_succeeds',evidence_digest='1'*64,evidence_quality=.95,independence=.95,runtime_root=rt)
 req(replay['status']=='causal_observation_replay','replay_exactly_once')
 cf=counterfactual_analysis(cid,updated['causal_case_digest'],intervention_code='restart_only',assumed_outcome='request_succeeds',runtime_root=rt)
 req(cf['ok'] and cf['counterfactual_is_not_observed_evidence'],'counterfactual_not_evidence')
 comp={r['hypothesis_code']:r for r in cf['comparisons']}
 req(comp['process_state']['compatibility']=='compatible','counterfactual_compatible')
 req(comp['cache_stale']['compatibility']=='incompatible','counterfactual_incompatible')
 req(not cf['probe_executed'] and not cf['test_execution_authorized'],'no_probe_execution')
 legacy=legacy_v1281_projection(cid,runtime_root=rt)
 req(legacy.get('ok') and legacy.get('contract_version')=='v1281.2','legacy_owner_composed')
 inspect=inspect_causal_case(cid,runtime_root=rt)
 req(inspect['observation_count']==1,'restart_persistence')
 ctl=process_causal_reasoning_control('show causal reasoning requirements',runtime_root=rt)
 req(ctl['active'] and ctl['ok'] and 'disconfirming_evidence' in ctl['requirements'],'requirements_control')
 cctl=process_causal_reasoning_control(f'show causal case {cid}',runtime_root=rt)
 req(cctl['active'] and cctl['ok'],'case_control')
 compound=process_causal_reasoning_control(f'show causal case {cid} and execute',runtime_root=rt)
 req(compound['active'] and not compound['ok'],'compound_rejected')
 # Missing predictions do not get invented.
 partial=create_causal_case('Partial case',[{'id':'a','predictions':{'p':'x'}},{'id':'b','predictions':{}}],runtime_root=rt)
 req(partial['ok'],'partial_case_valid')
 req(partial['discriminating_probes'][0]['missing_prediction_count']==1,'missing_prediction_explicit')
print(json.dumps({'suite':'v1750.9-causal-counterfactual-reasoning-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
