from __future__ import annotations
"""v1149.1 content-free install, upgrade, backup, and rollback readiness intake."""
import hashlib,json
from typing import Any,Mapping
from cognitive_alpha_feature_freeze import build_cognitive_alpha_feature_freeze
CONTRACT_VERSION='v1149.1'; READINESS_REVISION=1
PATHS=('fresh_install','upgrade','backup','rollback','source_only_package')
AUTHORITY_BOUNDARY={k:False for k in ('executes_commands','modifies_source','mutates_runtime','installs','rolls_back','promotes','certifies','contacts_provider','sends_messages','creates_approval','creates_authorization')}
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build_cognitive_alpha_install_readiness(*,freeze:Mapping[str,Any]|None=None)->dict[str,Any]:
 f=dict(freeze or build_cognitive_alpha_feature_freeze()); valid=f.get('contract_version')=='v1149.0' and not f.get('new_feature_intake_open') and bool(f.get('structural_digest'))
 rows=[]
 if valid:
  for name in PATHS:
   row={'readiness_id':f'cognitive-alpha-readiness:{name}:v1','readiness_revision':READINESS_REVISION,'path':name,'freeze_id':f['freeze_id'],'freeze_revision':f['freeze_revision'],'freeze_digest':f['structural_digest'],'required_evidence': ['exact_source_lineage','deterministic_replay','runtime_separation','operator_review'],'execution_eligible':False,'operator_confirmation_required':True,'status':'intake_defined','lifecycle_state':'defined'}
   row['structural_digest']=_digest(row);rows.append(row)
 return {'contract_version':CONTRACT_VERSION,'readiness_set_id':'cognitive-alpha-install-readiness:v1149.1','readiness_revision':READINESS_REVISION,'freeze_valid':valid,'paths':rows,'path_count':len(rows),'duplicate_readiness_ids':[],'content_free':True,'read_only':True,'authority_boundary':dict(AUTHORITY_BOUNDARY),'structural_digest':_digest(rows),'desktop_verification_pending':True,'consciousness_proven':False}
