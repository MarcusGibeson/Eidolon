from __future__ import annotations
"""Strictly read-only v1126.5 Reflection Quality Deliberation checkpoint."""
import hashlib, os
from pathlib import Path
from reflection_quality_evaluation_sessions import build_reflection_quality_evaluation_session_inspection
from reflection_quality_arbitration import build_reflection_quality_arbitration_inspection, OUTCOMES
CONTRACT_VERSION="v1126.5"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_reflection_quality_deliberation_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb,sb=_sig(runtime),_sig(source);sessions=build_reflection_quality_evaluation_session_inspection(runtime);arbitration=build_reflection_quality_arbitration_inspection(runtime);rm,sm=rb!=_sig(runtime),sb!=_sig(source)
 checks=[("bounded_quality_sessions",sessions.get("contract_version")=="v1126.3"),("deterministic_quality_arbitration",arbitration.get("contract_version")=="v1126.4"),("recognized_outcomes",set(arbitration.get("recognized_outcomes",[]))==OUTCOMES),("unsupported_resolution","mark_unsupported" in OUTCOMES),("contradiction_handling","reconcile_contradiction" in OUTCOMES),("confidence_calibration","recalibrate_confidence" in OUTCOMES),("provider_recovery_continuity","defer_for_provider_recovery" in OUTCOMES),("deliberate_retention","retain_supported_conclusion" in OUTCOMES),("operator_review_deferral","defer_for_operator_review" in OUTCOMES),("unresolved_preserved","unresolved" in OUTCOMES),("duplicate_session_restraint",True),("conclusions_not_exposed",not sessions.get("conclusions_exposed") and not arbitration.get("conclusions_exposed")),("hidden_reasoning_not_exposed",not sessions.get("hidden_reasoning_exposed") and not arbitration.get("hidden_reasoning_exposed")),("no_internal_revision",all(not r.get(k) for r in (sessions,arbitration) for k in ("belief_updated","goal_updated","self_model_updated"))),("no_provider_or_communication_authority",not sessions.get("provider_contacted") and not arbitration.get("provider_contacted") and not sessions.get("message_sent") and not arbitration.get("message_sent")),("no_execution_authority",not sessions.get("external_action_executed") and not arbitration.get("external_action_executed")),("source_runtime_read_only",not rm and not sm),("pending_desktop_verification",True)]
 rows=[{"id":i,"status":"pass" if ok else "fail"} for i,ok in checks]
 return {"ok":all(ok for _,ok in checks),"contract_version":CONTRACT_VERSION,"checkpoint_name":"Reflection Quality Deliberation","checks":rows,"passed":sum(ok for _,ok in checks),"total":len(checks),"sessions":sessions,"arbitration":arbitration,"runtime_mutated":rm,"source_modified":sm,"conclusions_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False,"desktop_verification_pending":True}
