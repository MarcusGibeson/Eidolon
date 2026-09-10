from __future__ import annotations
"""v1368 evidence-driven provider failure classification without provider contact."""
import hashlib,json
from typing import Any,Mapping
CONTRACT_VERSION='v1368.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'model_management_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'application_authorized':False}
ORDER=('configuration','endpoint','model','transport','streaming','embedding','timeout','model_quality')
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def diagnose_provider(observation:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(observation,Mapping):return {'ok':False,'status':'provider_evidence_invalid','action_executed':False,**DENIED}
 c=[]
 if observation.get('configured') is False or observation.get('configuration_valid') is False:c.append('configuration')
 if observation.get('endpoint_resolved') is False or observation.get('endpoint_expected') is False:c.append('endpoint')
 if observation.get('model_present') is False or observation.get('model_compatible') is False:c.append('model')
 if observation.get('transport_connected') is False or observation.get('protocol_valid') is False:c.append('transport')
 if observation.get('streaming_expected') and observation.get('streaming_valid') is False:c.append('streaming')
 if observation.get('embedding_expected') and observation.get('embedding_valid') is False:c.append('embedding')
 if observation.get('timed_out') is True or (observation.get('elapsed_ms') is not None and observation.get('timeout_ms') is not None and float(observation['elapsed_ms'])>float(observation['timeout_ms'])):c.append('timeout')
 if observation.get('transport_connected') is True and observation.get('response_schema_valid') is True and observation.get('quality_acceptable') is False:c.append('model_quality')
 c=[x for x in ORDER if x in c]
 primary=c[0] if c else None
 rec={'contract_version':CONTRACT_VERSION,'status':'provider_failure_classified' if c else 'provider_evidence_healthy','failure_classes':c,'failure_count':len(c),'primary_failure_class':primary,'observation_digest':_d(dict(observation)),'provider_contact_performed':False,'model_management_performed':False,'raw_provider_content_persisted':False,'content_free':True,'read_only':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':True,'status':rec['status'],'provider_diagnosis':rec,'action_executed':False,**DENIED}
def process_provider_diagnosis_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show provider diagnosis','inspect provider diagnosis','show provider failure'}:return {'active':False}
 rec=dict((project_state or {}).get('provider_diagnosis') or {});return {'active':True,'ok':bool(rec),'status':'provider_diagnosis_found' if rec else 'provider_diagnosis_missing','provider_diagnosis':rec,'action_executed':False,**DENIED}
