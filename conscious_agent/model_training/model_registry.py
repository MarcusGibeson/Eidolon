from __future__ import annotations
"""Runtime-only immutable registry for future trained-model candidates. Registration is not promotion."""
import hashlib,json,time
from pathlib import Path
from typing import Any,Mapping
from model_training.training_record import _atomic_json, _training_root
from model_training.training_eval import validate_evaluation_result
CONTRACT_VERSION="v2503.4.30.1"
def register_model_candidate(*,runtime_root:str|Path|None,model_id:str,parent_model:str,dataset_manifest_digest:str,training_config_digest:str,artifact_digest:str,evaluation:Mapping[str,Any],operator_authorized:bool)->dict[str,Any]:
    if operator_authorized is not True: return {"ok":False,"status":"model_candidate_registration_authorization_required","model_promotion_authorized":False}
    hex64=lambda x: len(str(x))==64 and all(c in "0123456789abcdefABCDEF" for c in str(x))
    if not all(hex64(x) for x in (dataset_manifest_digest,training_config_digest,artifact_digest)): return {"ok":False,"status":"model_candidate_digest_invalid","model_promotion_authorized":False}
    safe="".join(c if c.isalnum() or c in "._-" else "-" for c in str(model_id))[:96].strip(".-")
    if not safe or not str(parent_model).strip(): return {"ok":False,"status":"model_candidate_identity_invalid","model_promotion_authorized":False}
    if not validate_evaluation_result(evaluation) or evaluation.get("complete") is not True or str(evaluation.get("model_id") or "") != safe:
        return {"ok":False,"status":"model_candidate_evaluation_invalid","model_promotion_authorized":False}
    row={"contract_version":CONTRACT_VERSION,"model_id":safe,"parent_model":str(parent_model),"dataset_manifest_digest":dataset_manifest_digest,"training_config_digest":training_config_digest,"artifact_digest":artifact_digest,"evaluation":dict(evaluation),"registered_at_ns":time.time_ns(),"status":"candidate","runtime_only":True,"provider_selected":False,"model_promotion_authorized":False,"rollback_required_if_promoted":True}
    # identity excludes registration time so retries can be recognized
    identity={k:v for k,v in row.items() if k!="registered_at_ns"}; row["registry_digest"]=hashlib.sha256(json.dumps(identity,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode()).hexdigest(); path=_training_root(runtime_root)/"models"/f"{safe}.json"
    if path.exists():
        try: existing=json.loads(path.read_text(encoding="utf-8"))
        except Exception: existing={}
        comparable={k:v for k,v in existing.items() if k not in {"registered_at_ns","registry_digest"}}
        if comparable==identity: return {"ok":True,"status":"model_candidate_restored","record":existing,"runtime_path":str(path),"model_promotion_authorized":False}
        return {"ok":False,"status":"model_candidate_identity_conflict","runtime_path":str(path),"model_promotion_authorized":False}
    _atomic_json(path,row); return {"ok":True,"status":"model_candidate_registered","record":row,"runtime_path":str(path),"model_promotion_authorized":False}
