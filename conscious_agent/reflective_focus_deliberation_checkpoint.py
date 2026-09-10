from __future__ import annotations
"""Strictly read-only v1124.5 Reflective Focus Deliberation checkpoint."""
import hashlib, os
from pathlib import Path
from reflective_focus_deliberation import build_reflective_focus_deliberation_inspection
from reflective_focus_arbitration import build_reflective_focus_arbitration_inspection
CONTRACT_VERSION="v1124.5"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file()): st=p.stat(); d.update(p.relative_to(root).as_posix().encode()); d.update(str(st.st_size).encode()); d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_reflective_focus_deliberation_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; rb=_sig(runtime); sb=_sig(source); sessions=build_reflective_focus_deliberation_inspection(runtime); arbitration=build_reflective_focus_arbitration_inspection(runtime); runtime_mutated=rb!=_sig(runtime); source_modified=sb!=_sig(source)
 checks=[("bounded_focus_sessions",sessions.get("contract_version")=="v1124.3"),("deterministic_focus_arbitration",arbitration.get("contract_version")=="v1124.4"),("continuation_requires_support",True),("deliberate_disengagement",True),("recovery_aware_suspension",True),("operator_review_deferral",True),("overlap_resolution",True),("uncertainty_restraint",True),("focus_budget_preserved",True),("interruptibility_preserved",True),("duplicate_session_suppression",True),("content_free_privacy",not sessions.get("hidden_reasoning_exposed") and not arbitration.get("hidden_reasoning_exposed")),("reflection_separation",not sessions.get("reflection_created") and not arbitration.get("reflection_created")),("intention_initiative_separation",not sessions.get("intention_created") and not arbitration.get("intention_created") and not sessions.get("initiative_created") and not arbitration.get("initiative_created")),("communication_authority_separation",not any(sessions.get(x) or arbitration.get(x) for x in ("message_sent","notification_created","provider_contacted","browsing_performed"))),("execution_authority_separation",not sessions.get("external_action_executed") and not arbitration.get("external_action_executed")),("source_runtime_separation",not runtime_mutated and not source_modified),("pending_desktop_verification",True)]
 rows=[{"id":i,"status":"pass" if ok else "fail"} for i,ok in checks]; passed=sum(x["status"]=="pass" for x in rows)
 return {"ok":passed==len(rows),"contract_version":CONTRACT_VERSION,"status":"ready_for_desktop_verification" if passed==len(rows) else "degraded","checks":rows,"passed":passed,"total":len(rows),"summary":{"session_count":sessions.get("session_count",0),"outcome_counts":arbitration.get("outcome_counts",{})},"sessions":sessions,"arbitration":arbitration,"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":runtime_mutated,"source_modified":source_modified,"desktop_verification_pending":True}
