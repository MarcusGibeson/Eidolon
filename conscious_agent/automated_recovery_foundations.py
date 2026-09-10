from __future__ import annotations
"""v1297.0-v1297.2 bounded post-update automatic-recovery foundations.

Automatic recovery is limited to restoring the exact pre-update backup for an
already authorized and successfully applied v1269 update when a defined health
failure occurs inside a bounded observation window. It is not general rollback
authority and cannot apply any candidate or arbitrary content.
"""
from hashlib import sha256
import json,time
from pathlib import Path
from typing import Any, Mapping
from governed_self_update_foundations import DENIED_AUTHORITY as V1269_DENIED, load_governed_self_update, validate_governed_self_update_packet, _backup_path, _read_json, _digest
from governed_self_update import _current_state
from automated_recovery_foundations_recovery import (
    SymbolDependencies as _AutomatedRecoveryFoundationsRecoverySymbolDependencies,
    prepare_recovery_contract as _prepare_recovery_contract_implementation,
    recovery_trigger as _recovery_trigger_implementation,
)


CONTRACT_VERSION="v1297.2"
TRIGGER_CODES=frozenset({"startup_failure","defined_behavior_regression","candidate_manifest_mismatch","privacy_security_regression"})
MAX_OBSERVATION_WINDOW_SECONDS=3600
DENIED_AUTHORITY={**V1269_DENIED,"new_update_authorization_granted":False,"general_rollback_authorized":False,"arbitrary_restore_authorized":False,"standing_recovery_authority_granted":False,"release_authorized":False}

def digest(v:Any)->str:return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def valid_digest(v:Any)->bool:
 t=str(v or '').lower().strip();return len(t)==64 and all(c in '0123456789abcdef' for c in t)

def _build_automated_recovery_foundations_recovery_dependencies() -> _AutomatedRecoveryFoundationsRecoverySymbolDependencies:
    return _AutomatedRecoveryFoundationsRecoverySymbolDependencies(
        CONTRACT_VERSION=CONTRACT_VERSION,
        DENIED_AUTHORITY=DENIED_AUTHORITY,
        MAX_OBSERVATION_WINDOW_SECONDS=MAX_OBSERVATION_WINDOW_SECONDS,
        Mapping=Mapping,
        TRIGGER_CODES=TRIGGER_CODES,
        _backup_path=_backup_path,
        _current_state=_current_state,
        _read_json=_read_json,
        digest=digest,
        load_governed_self_update=load_governed_self_update,
        time=time,
        valid_digest=valid_digest,
        validate_governed_self_update_packet=validate_governed_self_update_packet,
    )

def prepare_recovery_contract(update_id: str, source_root: str | Path, *, runtime_root: str | Path, health_policy_digest: str, observation_window_seconds: int=900, prepared_unix: float | None=None) -> dict[str, Any]:
    return _prepare_recovery_contract_implementation(update_id, source_root, runtime_root=runtime_root, health_policy_digest=health_policy_digest, observation_window_seconds=observation_window_seconds, prepared_unix=prepared_unix, _deps=_build_automated_recovery_foundations_recovery_dependencies())


def recovery_trigger(contract: Mapping[str, Any], *, trigger_code: str, evidence_digest: str, observed_unix: float, source_state: str='candidate', fresh: bool=True, private_finding_count: int=0) -> dict[str, Any]:
    return _recovery_trigger_implementation(contract, trigger_code=trigger_code, evidence_digest=evidence_digest, observed_unix=observed_unix, source_state=source_state, fresh=fresh, private_finding_count=private_finding_count, _deps=_build_automated_recovery_foundations_recovery_dependencies())

