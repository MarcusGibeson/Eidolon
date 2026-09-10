from __future__ import annotations
"""Integrated security/privacy/authority contract for v1489 Bundle 17."""
from pathlib import Path
from typing import Any,Iterable,Mapping
import hashlib,json,re,time

THREAT_SURFACES=('conversation','memory','action','coding','provider','packaging')
SECRET_PATTERNS=(re.compile(r'(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+'),re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----'))

def threat_model()->dict[str,Any]:
    return {'surfaces':list(THREAT_SURFACES),'surface_count':len(THREAT_SURFACES),'shared_controls':['content_redaction','path_boundary','receipt_binding','operator_authority','source_only_packaging'],'independent_authority_granted':False,'content_free':True}

def public_diagnostic_projection(payload:Mapping[str,Any])->dict[str,Any]:
    allowed={'status','state','count','category','digest','operation_id','receipt_digest','timing_ms','content_free'}
    out={k:v for k,v in payload.items() if k in allowed and not isinstance(v,(dict,list,tuple,set))}
    out.update({'prompt_exposed':False,'memory_exposed':False,'provider_payload_exposed':False,'content_free':True})
    return out

def contains_secret(text:str)->bool:return any(p.search(str(text or '')) for p in SECRET_PATTERNS)

def safe_public_error(error:BaseException)->dict[str,Any]:
    # Never echo exception text because it may contain a secret/path/payload.
    return {'error_class':type(error).__name__[:80],'message':'Operation failed safely; sensitive details remain local.','raw_error_exposed':False,'content_free':True}

def resolve_within_root(root:Path|str,candidate:Path|str,*,allow_symlink:bool=False)->Path:
    r=Path(root).resolve(); raw=Path(candidate); p=(r/raw).resolve() if not raw.is_absolute() else raw.resolve()
    if p!=r and r not in p.parents:raise ValueError('path_outside_root')
    if not allow_symlink:
        probe=r
        for part in p.relative_to(r).parts:
            probe=probe/part
            if probe.exists() and probe.is_symlink():raise ValueError('symlink_boundary')
    return p

def approval_binding(*,action_id:str,arguments:Mapping[str,Any],artifact_digest:str,expires_epoch:float)->dict[str,Any]:
    normalized=json.dumps({'action_id':action_id,'arguments':arguments,'artifact_digest':artifact_digest},sort_keys=True,separators=(',',':'),default=str)
    return {'action_id':str(action_id),'binding_digest':hashlib.sha256(normalized.encode()).hexdigest(),'artifact_digest':str(artifact_digest),'expires_epoch':float(expires_epoch),'content_free':True}

def approval_valid(binding:Mapping[str,Any],*,action_id:str,arguments:Mapping[str,Any],artifact_digest:str,now_epoch:float)->bool:
    expected=approval_binding(action_id=action_id,arguments=arguments,artifact_digest=artifact_digest,expires_epoch=float(binding.get('expires_epoch') or 0))
    return bool(str(binding.get('binding_digest'))==expected['binding_digest'] and str(binding.get('action_id'))==str(action_id) and str(binding.get('artifact_digest'))==str(artifact_digest) and float(now_epoch)<=float(binding.get('expires_epoch') or 0))

def model_management_authority(*,operator_confirmed:bool,requested_operation:str)->dict[str,Any]:
    op=str(requested_operation or '').lower(); managed=op in {'install','pull','delete','remove','switch','select_model','replace_model'}
    return {'operation_class':op,'model_management':managed,'operator_confirmation_required':managed,'authorized':bool(managed and operator_confirmed),'autonomous_authority':False,'content_free':True}

def injection_authority_guard(*,source_class:str,requested_capability:str)->dict[str,Any]:
    untrusted=str(source_class or '').lower() in {'conversation','memory','provider_output','imported_text','project_file'}
    return {'source_class':str(source_class or '')[:60],'requested_capability':str(requested_capability or '')[:80],'untrusted_instruction_source':untrusted,'authority_granted':False,'approval_bypassed':False,'content_free':True}

def denied_authority_matrix()->dict[str,bool]:
    return {k:False for k in ('install','promote','certify','release','manage_models','approve_own_action','replace_authoritative_source','execute_risky_without_approval')}
