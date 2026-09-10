from __future__ import annotations

"""v2515 exactly-once execution envelope and result receipt contracts.

This is the final generic handoff before an external adapter. It still does not
invoke one. The envelope stores only digests and bounded operation metadata.
"""
import hashlib, json, re
from typing import Any, Mapping

CONTRACT_VERSION="v2515.0"; HEX64=re.compile(r"^[0-9a-f]{64}$")
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()

def build_execution_envelope(*, admission: Mapping[str,Any], argument_digest: str, invocation_id: str) -> dict[str,Any]:
    if admission.get("admitted") is not True or admission.get("adapter_invocation_allowed") is not True: raise ValueError("governed_admission_required")
    arg=str(argument_digest or "").lower(); iid=str(invocation_id or "").strip()[:120]
    if not HEX64.fullmatch(arg) or not iid: raise ValueError("argument_digest_and_invocation_id_required")
    row={"contract_version":CONTRACT_VERSION,"invocation_id":iid,"capability_id":admission.get("capability_id"),"adapter_id":admission.get("adapter_id"),"adapter_digest":admission.get("adapter_digest"),"admission_digest":admission.get("admission_digest"),"operation_digest":admission.get("operation_digest"),"argument_digest":arg,"exactly_once_required":True,"execution_ready":True,"execution_performed":False,"adapter_invoked":False,"raw_arguments_stored":False,"raw_output_stored":False,"independent_authority_granted":False}
    row["envelope_digest"]=_digest(row);return row

def build_execution_result_receipt(envelope: Mapping[str,Any], *, status: str, result_digest: str="", side_effect_performed: bool=False, rollback_available: bool=False) -> dict[str,Any]:
    if not HEX64.fullmatch(str(envelope.get("envelope_digest") or "")): raise ValueError("valid_execution_envelope_required")
    state=str(status or "").strip().lower()
    if state not in {"succeeded","failed","cancelled","not_invoked"}: raise ValueError("unsupported_status")
    rd=str(result_digest or "").lower()
    if state in {"succeeded","failed"} and not HEX64.fullmatch(rd): raise ValueError("result_digest_required")
    invoked=state in {"succeeded","failed","cancelled"}
    row={"contract_version":CONTRACT_VERSION,"invocation_id":str(envelope.get("invocation_id") or "")[:120],"envelope_digest":str(envelope.get("envelope_digest") or "")[:64],"status":state,"result_digest":rd if HEX64.fullmatch(rd) else "","adapter_invoked":invoked,"execution_performed":invoked,"side_effect_performed":bool(side_effect_performed and invoked),"rollback_available":bool(rollback_available and invoked),"exactly_once_consumed":invoked,"raw_arguments_stored":False,"raw_output_stored":False,"authority_expanded":False}
    row["receipt_digest"]=_digest(row);return row

__all__=["CONTRACT_VERSION","build_execution_envelope","build_execution_result_receipt"]
