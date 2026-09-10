from __future__ import annotations
"""v1367 structural data diagnosis without reading private content into public evidence."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1367.8'
DENIED={'source_mutation_authorized':False,'data_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'application_authorized':False}
CODES=('schema_drift','partial_write','index_corruption','migration_gap','content_metadata_boundary_failure')
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def diagnose_data_state(*,expected:Mapping[str,Any],observed:Mapping[str,Any],repair_observed:Mapping[str,Any]|None=None)->dict[str,Any]:
    if not isinstance(expected,Mapping) or not isinstance(observed,Mapping):return {'ok':False,'status':'data_evidence_invalid','action_executed':False,**DENIED}
    findings=[]
    def add(code:str,evidence:Any): findings.append({'code':code,'evidence_digest':_d(evidence)})
    if str(expected.get('schema_digest') or '')!=str(observed.get('schema_digest') or ''):add('schema_drift',{'e':expected.get('schema_digest'),'o':observed.get('schema_digest')})
    tx=str(observed.get('transaction_state') or 'committed'); exp_rows=int(expected.get('row_count') or 0); obs_rows=int(observed.get('row_count') or 0)
    if tx not in {'committed','clean'} or exp_rows!=obs_rows:add('partial_write',{'tx':tx,'expected_rows':exp_rows,'observed_rows':obs_rows})
    if int(expected.get('index_entry_count') or 0)!=int(observed.get('index_entry_count') or 0) or (expected.get('index_digest') and expected.get('index_digest')!=observed.get('index_digest')):add('index_corruption',{'ec':expected.get('index_entry_count'),'oc':observed.get('index_entry_count'),'ed':expected.get('index_digest'),'od':observed.get('index_digest')})
    ev=int(expected.get('schema_version') or 0); ov=int(observed.get('schema_version') or 0); applied={int(x) for x in observed.get('applied_migrations',[]) if str(x).isdigit()}
    if ov!=ev or (ev and any(v not in applied for v in range(1,ev+1))):add('migration_gap',{'expected_version':ev,'observed_version':ov,'applied':sorted(applied)})
    if observed.get('public_evidence_contains_content') is True or observed.get('content_digest')!=observed.get('metadata_content_digest'):add('content_metadata_boundary_failure',{'content_leak':bool(observed.get('public_evidence_contains_content')),'digest_match':observed.get('content_digest')==observed.get('metadata_content_digest')})
    repaired=None
    if repair_observed is not None:
        rr=diagnose_data_state(expected=expected,observed=repair_observed)
        repaired=bool(rr.get('ok') and not rr['data_diagnosis']['finding_codes'])
    rec={'contract_version':CONTRACT_VERSION,'status':'data_defects_detected' if findings else 'data_state_coherent','finding_codes':[f['code'] for f in findings],'finding_count':len(findings),'findings':findings,'expected_digest':_d(dict(expected)),'observed_digest':_d(dict(observed)),'repair_snapshot_verified':repaired,'content_free':True,'read_only':True,'selected_source_modified':False,'runtime_data_modified':False,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
    return {'ok':True,'status':rec['status'],'data_diagnosis':rec,'action_executed':False,**DENIED}
def process_data_diagnosis_control(text:str,*,project_state=None,**_):
    if str(text or '').strip().lower() not in {'show data diagnosis','inspect data diagnosis','show storage diagnosis'}:return {'active':False}
    rec=dict((project_state or {}).get('data_diagnosis') or {});return {'active':True,'ok':bool(rec),'status':'data_diagnosis_found' if rec else 'data_diagnosis_missing','data_diagnosis':rec,'action_executed':False,**DENIED}
