from __future__ import annotations

"""v2507.0-v2507.6 longitudinal evidence-based self-trait learning.

Traits are hypotheses over repeated observed outcomes, never persona fiction.
This store retains content-free evidence digests, supporting/counterexample
counts, scope, confidence and revision lineage. It does not rewrite protected
identity claims or grant authority.
"""

from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,re
from pathlib import Path
from typing import Any,Callable,Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION='v2507.6';SCHEMA_VERSION='1'
SOURCE_KINDS=frozenset({'benchmark_receipt','capability_receipt','development_outcome','cognitive_receipt','operator_verified','memory_consolidation_review'})
POLARITIES=frozenset({'support','counterexample'})

def _now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def _digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _code(v,n=120):
 s=re.sub(r'[^a-z0-9_]+','_',str(v or '').strip().lower()).strip('_')[:n]
 return s

def _is_sha(v):
 s=str(v or '').lower();return len(s)==64 and all(c in '0123456789abcdef' for c in s)
def _default():return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'observations':[],'traits':[],'processed_events':[],'revision':0,'updated_at':'','controls':{'max_observations':2048,'max_traits':256,'minimum_support':3,'minimum_independent_evidence':2,'max_confidence_step':0.15},'authority_boundary':{'can_rewrite_identity':False,'can_apply_trait':False,'can_claim_consciousness':False,'can_contact_provider':False,'can_execute_action':False,'can_modify_source':False,'operator_authority_unchanged':True}}

class DevelopmentalSelfModelStore:
 def __init__(self,runtime_root:str|Path,*,clock:Callable[[],str]|None=None):self.root=Path(runtime_root).expanduser().resolve();self.path=self.root/'developmental_self_model_v2507.json';self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get('schema_version')!=SCHEMA_VERSION:s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def observe(self,event_id:str,*,trait_code:str,domain:str,polarity:str,evidence_digest:str,source_kind:str,observation_code:str=''):
  event_id=str(event_id or '').strip()[:180];trait=_code(trait_code);domain=_code(domain,80);polarity=str(polarity or '').strip().lower();source=str(source_kind or '').strip().lower();obs=_code(observation_code or trait_code,120)
  if not event_id or not trait or not domain or polarity not in POLARITIES or source not in SOURCE_KINDS or not _is_sha(evidence_digest):raise ValueError('valid content-free self observation required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior:return {'ok':True,'status':'self_observation_replayed','idempotent':True,'observation_id':prior['observation_id']}
   now=self.clock();oid='self-observation-'+_digest({'event':event_id,'trait':trait,'evidence':evidence_digest})[:24]
   row={'observation_id':oid,'trait_code':trait,'domain':domain,'polarity':polarity,'observation_code':obs,'evidence_digest':str(evidence_digest).lower(),'source_kind':source,'observed_at':now,'content_free':True,'raw_behavior_stored':False,'hidden_reasoning_stored':False}
   s['observations']=(s['observations']+[row])[-int(s['controls']['max_observations']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'observation_id':oid,'occurred_at':now,'content_free':True}])[-4096:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {'ok':True,'status':'self_observation_recorded','observation_id':oid,'idempotent':False,'identity_rewritten':False,'trait_applied':False}
 def evaluate_trait(self,trait_code:str,*,domain:str=''):
  trait=_code(trait_code);scope=_code(domain,80)
  if not trait:raise ValueError('trait_code required')
  s=self._load();rows=[x for x in s['observations'] if x.get('trait_code')==trait and (not scope or x.get('domain')==scope)];supports=[x for x in rows if x.get('polarity')=='support'];counters=[x for x in rows if x.get('polarity')=='counterexample'];independent=len({x.get('evidence_digest') for x in supports});domains=sorted({str(x.get('domain') or '') for x in rows if x.get('domain')})
  minimum=int(s['controls']['minimum_support']);min_ev=int(s['controls']['minimum_independent_evidence']);eligible=len(supports)>=minimum and independent>=min_ev
  net=max(0,len(supports)-len(counters));raw=min(0.95,0.35+0.12*net+0.05*min(independent,4));contest_ratio=len(counters)/max(1,len(rows));confidence=round(max(0.05,raw-0.45*contest_ratio),4)
  if not rows:state='unobserved'
  elif not eligible:state='emerging'
  elif len(counters)>=len(supports):state='contested'
  elif len(counters)>0:state='supported_with_counterexamples'
  else:state='supported'
  result={'ok':True,'contract_version':CONTRACT_VERSION,'trait_code':trait,'scope_domain':scope or ('cross_domain' if len(domains)>1 else (domains[0] if domains else 'unknown')),'observed_domains':domains,'support_count':len(supports),'counterexample_count':len(counters),'independent_support_count':independent,'state':state,'eligible_for_trait_candidate':bool(eligible and state.startswith('supported')),'confidence':confidence,'first_observed_at':rows[0]['observed_at'] if rows else '','last_observed_at':rows[-1]['observed_at'] if rows else '','supporting_evidence_digests':[x['evidence_digest'] for x in supports[-16:]],'counterexample_evidence_digests':[x['evidence_digest'] for x in counters[-16:]],'identity_rewritten':False,'trait_applied':False,'content_free':True,'authority':'none'};result['evaluation_digest']=_digest(result);return result
 def stage_trait_candidate(self,event_id:str,*,trait_code:str,domain:str=''):
  event_id=str(event_id or '').strip()[:180]
  if not event_id:raise ValueError('event_id required')
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s['processed_events'] if x.get('event_id')==event_id),None)
   if prior and prior.get('trait_candidate_id'):return {'ok':True,'status':'trait_candidate_replayed','trait_candidate_id':prior['trait_candidate_id'],'idempotent':True,'trait_applied':False}
   ev=self.evaluate_trait(trait_code,domain=domain)
   if not ev['eligible_for_trait_candidate']:return {'ok':False,'status':'trait_candidate_not_evidence_ready','evaluation':ev,'trait_applied':False,'identity_rewritten':False}
   now=self.clock();cid='developmental-trait-'+_digest({'event':event_id,'evaluation':ev['evaluation_digest']})[:24];prior_trait=next((x for x in reversed(s['traits']) if x.get('trait_code')==ev['trait_code'] and x.get('scope_domain')==ev['scope_domain']),None)
   revision=int(prior_trait.get('revision') or 0)+1 if prior_trait else 1
   row={'trait_candidate_id':cid,'trait_code':ev['trait_code'],'scope_domain':ev['scope_domain'],'state':ev['state'],'confidence':ev['confidence'],'support_count':ev['support_count'],'counterexample_count':ev['counterexample_count'],'evaluation_digest':ev['evaluation_digest'],'revision':revision,'supersedes_candidate_id':prior_trait.get('trait_candidate_id','') if prior_trait else '','status':'candidate_only_unapplied','created_at':now,'trait_applied':False,'identity_rewritten':False,'historical_observations_preserved':True}
   s['traits']=(s['traits']+[row])[-int(s['controls']['max_traits']):];s['processed_events']=(s['processed_events']+[{'event_id':event_id,'event_digest':_digest(event_id),'trait_candidate_id':cid,'occurred_at':now,'content_free':True}])[-4096:];s['revision']+=1;s['updated_at']=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {'ok':True,'status':'developmental_trait_candidate_staged','trait_candidate_id':cid,'trait_code':row['trait_code'],'state':row['state'],'confidence':row['confidence'],'revision':revision,'trait_applied':False,'identity_rewritten':False,'idempotent':False}
 def inspection_summary(self):
  s=self._load();return {'ok':True,'contract_version':CONTRACT_VERSION,'revision':s['revision'],'observation_count':len(s['observations']),'trait_candidate_count':len(s['traits']),'recent_trait_candidates':deepcopy(s['traits'][-32:]),'controls':deepcopy(s['controls']),'authority_boundary':deepcopy(s['authority_boundary']),'identity_rewritten':False,'trait_applied':False,'provider_contacted':False,'external_action_executed':False,'hidden_reasoning_exposed':False}

__all__=['CONTRACT_VERSION','SOURCE_KINDS','DevelopmentalSelfModelStore']
