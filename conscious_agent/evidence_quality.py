from __future__ import annotations
"""v1359 evidence-quality validation for reproducible content-minimized receipts."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1359.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'evidence_authority_granted':False}
FORBIDDEN_KEYS={'raw_prompt','raw_content','secret','secret_value','credential','token_value','absolute_path','private_path','payload'}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _has_forbidden(v):
 if isinstance(v,Mapping):return any(str(k).lower() in FORBIDDEN_KEYS or _has_forbidden(x) for k,x in v.items())
 if isinstance(v,(list,tuple)):return any(_has_forbidden(x) for x in v)
 return False
def _cycle(graph):
 visiting=set();done=set()
 def visit(n):
  if n in visiting:return True
  if n in done:return False
  visiting.add(n)
  for m in graph.get(n,()):
   if m in graph and visit(m):return True
  visiting.remove(n);done.add(n);return False
 return any(visit(n) for n in graph)
def evaluate_evidence_quality(*,source_manifest_digest:str,evidence_records:Sequence[Mapping[str,Any]])->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')):return {'ok':False,'status':'evidence_quality_source_lineage_required','action_executed':False,**DENIED}
 if not evidence_records or len(evidence_records)>512:return {'ok':False,'status':'evidence_quality_record_count_invalid','action_executed':False,**DENIED}
 ids=[];graph={};raw_by_id={}
 for raw in evidence_records:
  eid=str(raw.get('evidence_id') or '')
  if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',eid) or eid in raw_by_id:return {'ok':False,'status':'evidence_quality_identity_invalid','action_executed':False,**DENIED}
  ids.append(eid);raw_by_id[eid]=raw;graph[eid]=tuple(str(x) for x in (raw.get('provenance_ids') or ()))
 cyclic=_cycle(graph);rows=[];accepted=0
 for eid in ids:
  raw=raw_by_id[eid];reasons=[]
  if str(raw.get('source_manifest_digest') or '')!=source_manifest_digest:reasons.append('stale_source_lineage')
  if eid in graph[eid] or cyclic and any(x in graph for x in graph[eid]):
   # Mark records participating in/feeding the cyclic local graph conservatively.
   reasons.append('circular_provenance')
  if raw.get('self_asserted') is True:reasons.append('self_asserted_claim')
  if raw.get('complete') is not True:reasons.append('incomplete_evidence')
  if raw.get('reproducible') is not True:reasons.append('not_reproducible')
  if raw.get('content_free') is not True or _has_forbidden(raw):reasons.append('content_leak')
  if not re.fullmatch(r'[a-f0-9]{64}',str(raw.get('claim_digest') or '')):reasons.append('claim_digest_invalid')
  if not re.fullmatch(r'[a-f0-9]{64}',str(raw.get('verification_method_digest') or '')):reasons.append('verification_method_missing')
  ok=not reasons;accepted+=int(ok)
  rows.append({'evidence_id_digest':_d(eid),'accepted':ok,'reason_codes':sorted(set(reasons)),'provenance_count':len(graph[eid]),'source_current':str(raw.get('source_manifest_digest') or '')==source_manifest_digest})
 passed=accepted==len(rows)
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'record_count':len(rows),'accepted_count':accepted,'rejected_count':len(rows)-accepted,'records':rows,'all_evidence_acceptable':passed,'raw_content_persisted':False,'content_free':True,'read_only':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':passed,'status':'evidence_quality_passed' if passed else 'evidence_quality_rejected','evidence_quality':rec,'action_executed':False,**DENIED}
def process_evidence_quality_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show evidence quality','inspect evidence quality','show evidence checks'}:return {'active':False}
 rec=dict((project_state or {}).get('evidence_quality') or {});return {'active':True,'ok':bool(rec),'status':'evidence_quality_found' if rec else 'evidence_quality_missing','evidence_quality':rec,'action_executed':False,**DENIED}
