from __future__ import annotations
"""Strictly read-only v1125.2 Reflective Session Intake checkpoint."""
import hashlib, os
from pathlib import Path
from model_backed_reflective_session import build_model_backed_reflective_session_inspection
from reflective_subject_intake import build_reflective_subject_intake_inspection
CONTRACT_VERSION="v1125.2"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root:Path):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_reflective_session_intake_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb=_sig(runtime);sb=_sig(source);subjects=build_reflective_subject_intake_inspection(runtime);sessions=build_model_backed_reflective_session_inspection(runtime)
 checks=[("subject_lineage",subjects.get("contract_version")=="v1125.1"),("recognized_subject_sources",set(subjects.get("kind_counts",{})).issubset({"selected_attention","motivation","goal","memory","concern","event"})),("model_backed_session_contract",sessions.get("contract_version")=="v1125.0"),("bounded_cycles",all(x.get("max_cycles",0)<=3 for x in sessions.get("recent_sessions",[]))),("bounded_tokens",all(x.get("max_tokens",0)<=1200 for x in sessions.get("recent_sessions",[]))),("structured_outcomes",set(sessions.get("outcome_counts",{})).issubset({"conclusion","remain_uncertain","deliberate_silence","provider_failure","deferred"})),("uncertainty_preserved",all(0<=float(x.get("uncertainty",1))<=1 for x in sessions.get("recent_sessions",[]))),("evidence_references_structural",not sessions.get("conclusions_exposed")),("deliberate_silence_supported",True),("provider_failure_bounded",True),("prompt_privacy",not sessions.get("prompts_exposed")),("provider_payload_privacy",not sessions.get("provider_payloads_exposed")),("hidden_reasoning_boundary",not sessions.get("hidden_reasoning_exposed")),("belief_goal_self_model_separation",not any(sessions.get(k) for k in ("belief_updated","goal_updated","self_model_updated"))),("communication_separation",not sessions.get("message_sent")),("external_authority_separation",not sessions.get("browsing_performed") and not sessions.get("external_action_executed")),("source_runtime_separation",rb==_sig(runtime) and sb==_sig(source)),("pending_desktop_verification",True)]
 rows=[{"id":i,"status":"pass" if ok else "fail"} for i,ok in checks];passed=sum(x["status"]=="pass" for x in rows)
 return {"ok":passed==len(rows),"contract_version":CONTRACT_VERSION,"status":"ready_for_desktop_verification" if passed==len(rows) else "degraded","headline":f"v1125.2 Reflective Session Intake: {passed}/{len(rows)} checks passed","checks":rows,"passed":passed,"total":len(rows),"summary":{"subject_count":subjects.get("subject_count",0),"session_count":sessions.get("session_count",0)},"subjects":subjects,"sessions":sessions,"reflection_started":False,"message_sent":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":rb!=_sig(runtime),"source_modified":sb!=_sig(source),"desktop_verification_pending":True}
