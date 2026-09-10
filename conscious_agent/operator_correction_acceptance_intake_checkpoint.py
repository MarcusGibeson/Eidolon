from __future__ import annotations
"""Strictly read-only v1142.2 Operator Correction and Acceptance Intake checkpoint."""
import hashlib, os
from pathlib import Path
from operator_correction_acceptance_eligibility import build_operator_correction_acceptance_eligibility_inspection, STATES as ELIGIBILITY_STATES
from operator_correction_acceptance_guidance import build_operator_correction_acceptance_guidance_inspection, STATES as GUIDANCE_STATES
CONTRACT_VERSION="v1142.2"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root:Path):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file() and x.suffix not in {".pyc",".pyo"} and "__pycache__" not in x.parts):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_operator_correction_acceptance_intake_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; rb=_sig(runtime); sb=_sig(source)
 eligibility=build_operator_correction_acceptance_eligibility_inspection(runtime); guidance=build_operator_correction_acceptance_guidance_inspection(runtime); er=eligibility.get("recent_records",[]); gr=guidance.get("recent_records",[])
 checks=[
  ("eligibility_contract",eligibility.get("contract_version")=="v1142.0"),("guidance_contract",guidance.get("contract_version")=="v1142.1"),
  ("explicit_operator_decisions",all(r.get("explicit_operator_decision") for r in er)),("exact_target_lineage",all(r.get("target_id") and r.get("source_record_id") and r.get("source_revision_id") for r in er if r.get("state")=="eligible")),
  ("correction_acceptance_distinguished",all(r.get("decision_kind") in {"correction","acceptance","rejection","clarification","qualification","withdrawal"} for r in er)),
  ("historical_truth_preserved",all(r.get("historical_record_preserved") and not r.get("original_state_mutated") for r in er) and all(r.get("historical_record_preserved") and not r.get("original_state_mutated") for r in gr)),
  ("future_reasoning_advisory",all(r.get("advisory_only") and not r.get("reasoning_mutated_at_record_time") for r in gr)),
  ("exact_eligibility_lineage",all(r.get("eligibility_id") and r.get("operator_decision_id") and r.get("source_revision_id") for r in gr)),
  ("bounded_reasoning_scopes",all(r.get("reasoning_scope_ids") and 0<=int(r.get("priority") or 0)<=100 for r in gr)),
  ("supersession_retraction_visible",all(r.get("contradiction_ids") is not None and r.get("retraction_ids") is not None and r.get("supersession_ids") is not None and r.get("retirement_ids") is not None for r in er+gr)),
  ("eligibility_states",{"eligible","awaiting_target","awaiting_lineage","requires_operator_review","suppressed","superseded","retracted","retired"}<=ELIGIBILITY_STATES),
  ("guidance_states",{"active","suppressed","deferred","requires_operator_review","superseded","retracted","retired"}<=GUIDANCE_STATES),
  ("privacy",not eligibility.get("raw_content_exposed") and not eligibility.get("operator_text_exposed") and not eligibility.get("reasoning_text_exposed") and not guidance.get("raw_content_exposed") and not guidance.get("operator_text_exposed") and not guidance.get("reasoning_text_exposed")),
  ("authority_separation",not any(eligibility.get("authority_boundary",{}).values()) and not any(guidance.get("authority_boundary",{}).values())),
  ("no_history_rewrite",not guidance.get("history_rewritten")),("no_future_reasoning_execution",not guidance.get("future_reasoning_executed")),
  ("read_only",rb==_sig(runtime) and sb==_sig(source)),("desktop_verification_pending",True)]
 passed=sum(bool(v) for _,v in checks)
 return {"ok":passed==len(checks),"status":"ready_for_desktop_verification" if passed==len(checks) else "review_required","contract_version":CONTRACT_VERSION,"passed":passed,"total":len(checks),"checks":[{"id":k,"status":"pass" if v else "fail"} for k,v in checks],"eligibility":eligibility,"guidance":guidance,"runtime_mutated":rb!=_sig(runtime),"source_modified":sb!=_sig(source),"raw_content_exposed":False,"operator_text_exposed":False,"reasoning_text_exposed":False,"history_rewritten":False,"belief_mutated":False,"goal_mutated":False,"motivation_mutated":False,"self_model_mutated":False,"future_reasoning_executed":False,"approval_created":False,"authorization_created":False,"external_action_executed":False,"consciousness_proven":False,"desktop_verification":"pending"}
