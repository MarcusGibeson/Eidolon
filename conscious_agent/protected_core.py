from __future__ import annotations
"""v1384 protected-core classification and stronger-review receipts."""
import hashlib,json,re
from pathlib import PurePosixPath
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1384.8';DIGEST=re.compile(r'^[a-f0-9]{64}$')
DENIED={'work_execution_authorized':False,'source_mutation_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False}
# Exact files are intentionally visible source architecture, not private runtime state.
PROTECTED={
 'authority':{'conscious_agent/release_authority.py','conscious_agent/release_certification_authority.py','conscious_agent/authority_profiles.py'},
 'release':{'conscious_agent/release_installation.py','conscious_agent/release_installation_transaction.py','conscious_agent/release_promotion_transaction.py','conscious_agent/release_metadata_consolidation.py'},
 'secrets':{'conscious_agent/privacy_security_secret_management_audit.py'},
 'rollback':{'conscious_agent/campaign_rollback.py','conscious_agent/controlled_application_rollback.py','conscious_agent/rollback_recovery.py'},
 'evidence_verification':{'conscious_agent/checkpoint_registry.py','conscious_agent/verification_evidence.py','conscious_agent/comprehensive_verification.py','conscious_agent/segmented_release_verifier.py'},
}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _path(v:Any)->str:
 raw=str(v or '').replace('\\','/').strip();p0=PurePosixPath(raw)
 if not raw or p0.is_absolute() or '..' in p0.parts or raw.startswith(('/', './', '../')):return ''
 x=raw.lstrip('./');p=PurePosixPath(x)
 if not x or p.is_absolute() or '..' in p.parts or '\x00' in x:return ''
 return p.as_posix()
def protected_core_map()->dict[str,Any]:
 rows=[{'category':c,'paths':sorted(paths),'review_level':'stronger_review'} for c,paths in sorted(PROTECTED.items())]
 out={'contract_version':CONTRACT_VERSION,'categories':rows,'category_count':len(rows),'protected_path_count':sum(len(x['paths']) for x in rows),'source_architecture_only':True,'read_only':True,'action_executed':False,**DENIED};out['protected_core_digest']=_d(out);return out
def classify_self_change_scope(*,changed_paths:Sequence[str],expected_protected_core_digest:str='')->dict[str,Any]:
 m=protected_core_map()
 if expected_protected_core_digest and expected_protected_core_digest!=m['protected_core_digest']:return {'ok':False,'status':'protected_core_map_stale','action_executed':False,**DENIED}
 if not changed_paths or len(changed_paths)>2048:return {'ok':False,'status':'protected_scope_invalid','action_executed':False,**DENIED}
 cleaned=[]
 for raw in changed_paths:
  p=_path(raw)
  if not p:return {'ok':False,'status':'protected_scope_path_invalid','action_executed':False,**DENIED}
  cleaned.append(p)
 cleaned=sorted(set(cleaned));hits=[]
 for p in cleaned:
  cats=sorted(c for c,paths in PROTECTED.items() if p in paths)
  if cats:hits.append({'path':p,'categories':cats})
 core={'contract_version':CONTRACT_VERSION,'changed_paths':cleaned,'changed_path_count':len(cleaned),'protected_hits':hits,'protected_path_count':len(hits),'protected_core_touched':bool(hits),'required_review_level':'stronger_review' if hits else 'standard_review','automatic_apply_allowed':False,'action_executed':False,**DENIED}
 core['change_set_digest']=_d(cleaned);core['scope_digest']=_d(core)
 return {'ok':True,'status':'protected_scope_classified','scope':core,'action_executed':False,**DENIED}
def review_protected_scope(*,scope:Mapping[str,Any],expected_scope_digest:str,operator_reviewed:bool,protected_review_acknowledged:bool=False)->dict[str,Any]:
 row=dict(scope or {});sup=str(row.pop('scope_digest',''))
 if sup!=expected_scope_digest or sup!=_d(row):return {'ok':False,'status':'protected_scope_stale_or_tampered','action_executed':False,**DENIED}
 if not operator_reviewed:return {'ok':False,'status':'protected_scope_operator_review_required','action_executed':False,**DENIED}
 protected=bool(scope.get('protected_core_touched'))
 if protected and not protected_review_acknowledged:return {'ok':False,'status':'protected_core_stronger_review_required','action_executed':False,**DENIED}
 receipt={'contract_version':CONTRACT_VERSION,'scope_digest':sup,'change_set_digest':scope.get('change_set_digest'),'protected_core_touched':protected,'review_level':'stronger_review' if protected else 'standard_review','operator_reviewed':True,'protected_review_acknowledged':bool(protected_review_acknowledged),'execution_authorized':False,'install_authorized':False,'release_authorized':False,'action_executed':False,**DENIED};receipt['review_digest']=_d(receipt)
 return {'ok':True,'status':'protected_scope_reviewed','review':receipt,'action_executed':False,**DENIED}
def process_protected_core_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show protected core','inspect protected core','show protected boundaries'}:return {'active':False}
 state=project_state or {};scope=dict(state.get('protected_scope') or {})
 return {'active':True,'ok':True,'status':'protected_core_ready','protected_core':protected_core_map(),'protected_scope':scope,'action_executed':False,**DENIED}
