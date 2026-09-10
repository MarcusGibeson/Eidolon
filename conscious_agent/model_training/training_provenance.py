from __future__ import annotations
"""Approved-store provenance certificates for immutable training dataset manifests."""
import hashlib, json, time
from pathlib import Path
from typing import Any, Mapping
from model_training.training_dataset import validate_dataset_manifest
from model_training.training_record import _training_root, _atomic_json, load_training_record
CONTRACT_VERSION='v2503.4.30.1'

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, ensure_ascii=True, sort_keys=True, separators=(',',':')).encode()).hexdigest()

def validate_dataset_provenance(certificate: Mapping[str,Any], *, manifest: Mapping[str,Any]|None=None) -> bool:
    if not isinstance(certificate, Mapping) or certificate.get('approved_store_verified') is not True:
        return False
    body={k:v for k,v in certificate.items() if k!='certificate_digest'}
    if certificate.get('certificate_digest') != _digest(body): return False
    if manifest is not None:
        if not validate_dataset_manifest(manifest): return False
        if certificate.get('dataset_manifest_digest') != manifest.get('manifest_digest'): return False
        if int(certificate.get('record_count') or -1) != int(manifest.get('record_count') or 0): return False
    return certificate.get('runtime_only') is True and certificate.get('model_training_authorized') is False



def validate_dataset_provenance_against_store(certificate: Mapping[str,Any], *, manifest: Mapping[str,Any], runtime_root) -> bool:
    """Revalidate a provenance certificate against the live approved runtime store.

    A self-hash alone proves only certificate integrity. This check proves that every
    manifest-bound approved record currently exists with the exact sealed digest.
    """
    if not validate_dataset_provenance(certificate, manifest=manifest):
        return False
    verified=[]
    for binding in manifest.get('record_bindings',[]):
        rid=str(binding.get('record_id') or '')
        expected=str(binding.get('record_digest') or '')
        row=load_training_record(rid,runtime_root=runtime_root,stage='approved')
        if not row or row.get('approved_for_training') is not True or row.get('sanitized') is not True:
            return False
        actual=str(row.get('record_digest') or row.get('normalized_digest') or '')
        if actual != expected:
            return False
        verified.append({'record_id':rid,'record_digest':actual})
    return (
        int(certificate.get('record_count') or -1)==len(verified)
        and certificate.get('approved_record_bindings_digest')==_digest(verified)
    )

def materialize_dataset_provenance(*, runtime_root, manifest: Mapping[str,Any], operator_authorized: bool) -> dict[str,Any]:
    if operator_authorized is not True: return {'ok':False,'status':'dataset_provenance_operator_authorization_required','model_training_authorized':False}
    if not validate_dataset_manifest(manifest): return {'ok':False,'status':'dataset_manifest_invalid','model_training_authorized':False}
    root=_training_root(runtime_root); verified=[]
    for binding in manifest.get('record_bindings',[]):
        rid=str(binding.get('record_id') or ''); expected=str(binding.get('record_digest') or '')
        row=load_training_record(rid,runtime_root=runtime_root,stage='approved')
        if not row or row.get('approved_for_training') is not True or row.get('sanitized') is not True:
            return {'ok':False,'status':'dataset_provenance_approved_record_missing','record_id':rid,'model_training_authorized':False}
        actual=str(row.get('record_digest') or row.get('normalized_digest') or '')
        if actual != expected:
            return {'ok':False,'status':'dataset_provenance_record_digest_mismatch','record_id':rid,'model_training_authorized':False}
        verified.append({'record_id':rid,'record_digest':actual})
    payload={'contract_version':CONTRACT_VERSION,'dataset_version':manifest.get('dataset_version'),'dataset_manifest_digest':manifest.get('manifest_digest'),'record_count':len(verified),'approved_record_bindings_digest':_digest(verified),'approved_store_verified':True,'verified_at_ns':time.time_ns(),'runtime_only':True,'model_training_authorized':False,'model_promotion_authorized':False}
    identity={k:v for k,v in payload.items() if k!='verified_at_ns'}; payload['certificate_digest']=_digest(payload)
    safe=''.join(c if c.isalnum() or c in '._-' else '-' for c in str(manifest.get('dataset_version') or 'dataset'))[:96]
    path=root/'datasets'/f'{safe}.provenance.json'
    if path.exists():
        try: existing=json.loads(path.read_text(encoding='utf-8'))
        except Exception: existing={}
        comparable=lambda x:{k:v for k,v in dict(x).items() if k not in {'verified_at_ns','certificate_digest'}}
        if validate_dataset_provenance(existing,manifest=manifest) and comparable(existing)==identity:
            return {'ok':True,'status':'dataset_provenance_restored','certificate':existing,'runtime_path':str(path),'model_training_authorized':False}
        return {'ok':False,'status':'dataset_provenance_identity_conflict','runtime_path':str(path),'model_training_authorized':False}
    _atomic_json(path,payload)
    return {'ok':True,'status':'dataset_provenance_materialized','certificate':payload,'runtime_path':str(path),'model_training_authorized':False}
