from __future__ import annotations
"""Cross-surface conversation operation identity and recovery contract."""
from dataclasses import dataclass,asdict
import hashlib,json
from typing import Any,Mapping

SURFACES=frozenset({'browser','desktop','api','runtime'})
@dataclass(frozen=True)
class OperationIdentityProjection:
    surface:str; operation_id:str; session_id:str; acceptance_identity_digest:str
    public_state:str; cancellation_requested:bool; client_disconnected:bool
    recovery_mode:str; automatic_reexecution_allowed:bool=False; content_free:bool=True; schema_version:str='1'
    def public_summary(self)->dict[str,Any]:
        d=asdict(self); d['projection_digest']=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return d

def _acceptance_digest(marker:Mapping[str,Any])->str:
    key=str(marker.get('acceptance_key') or '')
    return hashlib.sha256(key.encode()).hexdigest() if key else ''

def recovery_mode_for_marker(marker:Mapping[str,Any])->str:
    state=str(marker.get('public_state') or 'uncertain').lower()
    if state=='completed': return 'read_only_reconcile'
    if state=='running': return 'reconcile_only'
    if state in {'failed','cancelled','uncertain'}: return 'explicit_retry_required'
    return 'reconcile_only'

def public_operation_identity(marker:Mapping[str,Any],*,surface:str)->OperationIdentityProjection:
    surf=str(surface or '').lower()
    if surf not in SURFACES: raise ValueError('Unsupported conversation surface.')
    return OperationIdentityProjection(
        surface=surf,operation_id=str(marker.get('operation_id') or ''),session_id=str(marker.get('session_id') or ''),
        acceptance_identity_digest=_acceptance_digest(marker),public_state=str(marker.get('public_state') or 'uncertain'),
        cancellation_requested=bool(marker.get('cancellation_requested')),client_disconnected=bool(marker.get('client_disconnected')),
        recovery_mode=recovery_mode_for_marker(marker),automatic_reexecution_allowed=False,
    )

def operation_identity_equivalent(a:OperationIdentityProjection,b:OperationIdentityProjection)->bool:
    return bool(a.operation_id and a.operation_id==b.operation_id and a.session_id==b.session_id and a.acceptance_identity_digest==b.acceptance_identity_digest)
