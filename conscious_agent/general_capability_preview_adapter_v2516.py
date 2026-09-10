from __future__ import annotations

"""v2516 inert preview adapter harness for general capabilities.

The harness recognizes only built-in simulation handlers and never performs I/O,
network/provider access, communication, filesystem mutation, process execution,
or device control. It exists to prove the generic execution-envelope lifecycle
without granting a real capability.
"""
import hashlib, json, re
from typing import Any, Mapping

CONTRACT_VERSION="v2516.0"; HEX64=re.compile(r"^[0-9a-f]{64}$")
SAFE_HANDLERS=frozenset({"fixture.echo_digest","fixture.read_projection","fixture.noop"})

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()

def invoke_inert_preview(*, envelope: Mapping[str,Any], adapter: Mapping[str,Any], preview_payload_digest: str) -> dict[str,Any]:
    if envelope.get("execution_ready") is not True or envelope.get("execution_performed") is True: raise ValueError("ready_unconsumed_envelope_required")
    if str(envelope.get("adapter_digest") or "") != str(adapter.get("adapter_digest") or ""): raise ValueError("adapter_binding_mismatch")
    if adapter.get("enabled") is not True or adapter.get("supports_preview") is not True: raise ValueError("enabled_preview_adapter_required")
    if str(adapter.get("adapter_kind") or "") != "local_read": raise ValueError("inert_preview_requires_local_read_adapter")
    handler=str(adapter.get("handler_code") or "")
    if handler not in SAFE_HANDLERS: raise ValueError("handler_not_in_inert_preview_allowlist")
    pd=str(preview_payload_digest or "").lower()
    if not HEX64.fullmatch(pd): raise ValueError("preview_payload_digest_required")
    result={
        "contract_version":CONTRACT_VERSION,
        "invocation_id":str(envelope.get("invocation_id") or "")[:120],
        "envelope_digest":str(envelope.get("envelope_digest") or "")[:64],
        "adapter_id":str(adapter.get("adapter_id") or "")[:96],
        "handler_code":handler,
        "preview_payload_digest":pd,
        "preview_result_digest":_digest({"handler":handler,"payload":pd,"operation":envelope.get("operation_digest")}),
        "adapter_invoked":True,
        "execution_performed":True,
        "side_effect_performed":False,
        "network_contacted":False,
        "provider_contacted":False,
        "communication_performed":False,
        "filesystem_mutated":False,
        "process_spawned":False,
        "device_control_performed":False,
        "raw_arguments_stored":False,
        "raw_output_stored":False,
        "simulation_only":True,
    }
    result["preview_receipt_digest"]=_digest(result);return result

__all__=["CONTRACT_VERSION","SAFE_HANDLERS","invoke_inert_preview"]
