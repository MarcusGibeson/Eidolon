from __future__ import annotations

"""v2517 user-facing activity projections for the general capability lifecycle."""
import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION="v2517.0"
_STAGE_SUMMARIES={
 "adapter_registered":"A capability adapter is known to the registry but has not been authorized.",
 "adapter_resolved":"A compatible enabled adapter was resolved for the selected capability.",
 "awaiting_authority":"The action is prepared and remains blocked pending exact authority.",
 "action_admitted":"The exact capability action passed its governance and authority gates.",
 "preview_started":"Running a bounded inert capability preview.",
 "preview_completed":"The inert capability preview completed without an external side effect.",
 "action_blocked":"The capability action remained blocked by its governance boundary.",
}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()

def project_capability_activity(*, stage: str, source: Mapping[str,Any]) -> dict[str,Any]:
    token=str(stage or "").strip().lower()
    if token not in _STAGE_SUMMARIES: raise ValueError("unsupported_capability_activity_stage")
    row={"event":"activity","contract_version":CONTRACT_VERSION,"activity_kind":"milestone" if token.endswith(("completed","admitted","blocked")) else "activity","stage":token,"summary":_STAGE_SUMMARIES[token],"capability_id":str(source.get("capability_id") or "")[:80],"adapter_id":str(source.get("adapter_id") or "")[:96],"source_digest":_digest({"stage":token,"capability_id":source.get("capability_id"),"adapter_id":source.get("adapter_id"),"binding":source.get("admission_digest") or source.get("envelope_digest") or source.get("adapter_digest")}),"hidden_reasoning_exposed":False,"raw_arguments_stored":False,"raw_output_stored":False,"authority_inferred":False,"content_minimized":True}
    row["activity_digest"]=_digest(row);return row

__all__=["CONTRACT_VERSION","project_capability_activity"]
