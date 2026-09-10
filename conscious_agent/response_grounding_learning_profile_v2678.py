from __future__ import annotations
"""v2678 bounded longitudinal learning profile for response-grounding calibration."""
from typing import Any, Iterable, Mapping
from pathlib import Path
import hashlib, json, os
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic
CONTRACT_VERSION="v2678.0"; MAX_ROWS=64
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def _history_path(runtime_root: str|Path|None=None)->Path:
    if runtime_root is not None: root=Path(runtime_root).expanduser().resolve()
    else: root=Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
    return root/"response_grounding_outcome_history_v2678.json"

def append_response_grounding_feedback(feedback:Mapping[str,Any], *, runtime_root: str|Path|None=None)->dict[str,Any]:
    path=_history_path(runtime_root); path.parent.mkdir(parents=True,exist_ok=True)
    state=load_json_file(path,{"rows":[]},expected_type=dict); rows=list(state.get("rows") or [])
    if bool(feedback.get("evidence_recorded")):
        row={k:feedback.get(k) for k in ("prior_assertiveness","prior_memory_state","disposition","adverse_calibration_evidence","explicit_correction","explicit_retraction","feedback_digest")}; row["evidence_recorded"]=True
        row["row_digest"]=_digest(row)
        if not any(isinstance(r,Mapping) and r.get("row_digest")==row["row_digest"] for r in rows): rows.append(row)
    rows=rows[-MAX_ROWS:]
    payload={"contract_version":CONTRACT_VERSION,"rows":rows,"raw_prompt_stored":False,"raw_response_stored":False,"raw_correction_text_stored":False,"authority_granted":False}; payload["history_digest"]=_digest(payload)
    write_json_atomic(path,payload,expected_type=dict,sort_keys=True); return payload

def load_response_grounding_feedback_history(runtime_root: str|Path|None=None)->dict[str,Any]:
    state=load_json_file(_history_path(runtime_root),{"rows":[]},expected_type=dict)
    return {"contract_version":CONTRACT_VERSION,"rows":list(state.get("rows") or [])[-MAX_ROWS:],"raw_prompt_stored":False,"raw_response_stored":False,"authority_granted":False}

def build_response_grounding_learning_profile(rows:Iterable[Mapping[str,Any]])->dict[str,Any]:
    items=[dict(r) for r in rows if isinstance(r,Mapping)][-MAX_ROWS:]
    evidence=[r for r in items if bool(r.get("evidence_recorded"))]
    adverse=sum(bool(r.get("adverse_calibration_evidence")) for r in evidence)
    cautious=sum(str(r.get("disposition"))=="cautious_response_corrected" for r in evidence)
    total=len(evidence)
    if total<2: state="insufficient_history"
    elif adverse>=3 and adverse/total>=0.6: state="overassertion_review_due"
    elif adverse: state="mixed_calibration_evidence"
    else: state="no_adverse_calibration_evidence"
    out={"ok":True,"contract_version":CONTRACT_VERSION,"evidence_count":total,"adverse_count":adverse,"cautious_correction_count":cautious,"state":state,
         "automatic_policy_change":False,"silence_treated_as_validation":False,"response_policy_mutated":False,"authority_granted":False}
    out["profile_digest"]=_digest(out);return out

def build_response_grounding_policy_review(profile:Mapping[str,Any])->dict[str,Any]:
    due=str(profile.get("state"))=="overassertion_review_due"
    out={"ok":True,"contract_version":CONTRACT_VERSION,"review_due":due,"review_reason":"repeated_grounded_claim_corrections" if due else "no_policy_review_required",
         "recommended_action":"operator_review_response_grounding_policy" if due else "retain_current_policy",
         "automatic_threshold_change":False,"automatic_policy_change":False,"response_policy_mutated":False,"authority_granted":False}
    out["review_digest"]=_digest(out);return out
__all__=["CONTRACT_VERSION","append_response_grounding_feedback","load_response_grounding_feedback_history","build_response_grounding_learning_profile","build_response_grounding_policy_review"]
