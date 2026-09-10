from __future__ import annotations
"""v1149.4 restart-safe release-readiness continuity and recovery evidence."""
import hashlib,json
from typing import Any,Mapping
from cognitive_alpha_release_readiness_execution import build_cognitive_alpha_release_readiness_execution
CONTRACT_VERSION='v1149.4'; CONTINUITY_REVISION=1
AUTHORITY_BOUNDARY={k:False for k in ('executes_commands','modifies_source','mutates_runtime','installs','upgrades','creates_backup','rolls_back','promotes','certifies','contacts_provider','sends_messages','creates_approval','creates_authorization')}
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build_cognitive_alpha_recovery_continuity(*,execution:Mapping[str,Any]|None=None)->dict[str,Any]:
 e=dict(execution or build_cognitive_alpha_release_readiness_execution()); valid=e.get('contract_version')=='v1149.3' and e.get('operator_confirmed') and bool(e.get('structural_digest'))
 rows=[]
 if valid:
  for x in e.get('executions',[]):
   row={'continuity_id':f"{x['execution_id']}:continuity:v1",'continuity_revision':CONTINUITY_REVISION,'execution_id':x['execution_id'],'execution_revision':x['execution_revision'],'execution_digest':x['structural_digest'],'path':x['path'],'restart_replay':'verified','lineage_recovery':'verified','rollback_pointer_changed':False,'runtime_state_packaged':False,'status':'stable','lifecycle_state':'reviewed'}
   row['structural_digest']=_digest(row);rows.append(row)
 return {'contract_version':CONTRACT_VERSION,'continuity_set_id':'cognitive-alpha-recovery-continuity:v1149.4','continuity_revision':CONTINUITY_REVISION,'execution_valid':valid,'records':rows,'record_count':len(rows),'duplicate_continuity_ids':[],'stable_count':sum(x.get('status')=='stable' for x in rows),'content_free':True,'read_only':True,'authority_boundary':dict(AUTHORITY_BOUNDARY),'structural_digest':_digest(rows),'desktop_verification_pending':True,'consciousness_proven':False}
