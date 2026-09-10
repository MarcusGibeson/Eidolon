from __future__ import annotations
"""v1291.0-v1291.2 evidence-backed independent improvement proposal foundations."""
from hashlib import sha256
import json
from typing import Any,Iterable,Mapping
CONTRACT_VERSION='v1291.2';MAX_PROPOSALS=8
DENIED_AUTHORITY={'provider_contact_authorized':False,'command_execution_authorized':False,'test_execution_authorized':False,'repair_authorized':False,'project_mutation_authorized':False,'backlog_mutation_authorized':False,'priority_change_authorized':False,'source_application_authorized':False,'self_update_authorized':False,'rollback_authorized':False,'release_authorized':False,'standing_authority_granted':False}
ACTIONABLE_KINDS={'defect','security','privacy','reliability','performance','usability','accessibility','maintainability','completeness','operator_readiness','documentation'}
SUPPRESSED_KINDS={'todo','uncertainty','aesthetic_preference','style_preference','observation_only'}
def digest(v:Any)->str:return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def normalize_observations(rows:Iterable[Mapping[str,Any]])->list[dict[str,Any]]:
 out=[];seen=set()
 for raw in rows:
  kind=str(raw.get('kind') or 'observation_only').lower().strip();e=str(raw.get('evidence_digest') or '').lower();issue=str(raw.get('issue_digest') or e).lower()
  if len(e)!=64 or any(c not in '0123456789abcdef' for c in e):raise ValueError('proposal_evidence_digest_required')
  if len(issue)!=64 or any(c not in '0123456789abcdef' for c in issue):raise ValueError('proposal_issue_digest_required')
  if issue in seen:continue
  seen.add(issue);out.append({'kind':kind,'issue_digest':issue,'evidence_digest':e,'relevance':max(0,min(100,int(raw.get('relevance',0)))),'impact':max(0,min(100,int(raw.get('impact',0)))),'confidence':max(0,min(100,int(raw.get('confidence',0)))),'actionability':max(0,min(100,int(raw.get('actionability',0)))),'novel':bool(raw.get('novel',True)),'fresh':bool(raw.get('fresh',True)),'private':bool(raw.get('private',False)),'content_free':True})
 return sorted(out,key=lambda r:r['issue_digest'])
def proposal_eligibility(row:Mapping[str,Any])->dict[str,Any]:
 reasons=[];kind=str(row.get('kind') or '')
 if kind not in ACTIONABLE_KINDS:reasons.append('non_actionable_observation_kind')
 if not row.get('fresh'):reasons.append('stale')
 if row.get('private'):reasons.append('private_evidence_suppressed')
 if not row.get('novel'):reasons.append('duplicate_or_already_addressed')
 if int(row.get('relevance') or 0)<50:reasons.append('weak_current_relevance')
 if int(row.get('impact') or 0)<35:reasons.append('low_expected_value')
 if int(row.get('confidence') or 0)<40:reasons.append('insufficient_evidence')
 if int(row.get('actionability') or 0)<45:reasons.append('insufficient_actionability')
 return {'eligible':not reasons,'suppression_reasons':reasons,'proposal_is_work':False,'content_free':True,**DENIED_AUTHORITY}
