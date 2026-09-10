from __future__ import annotations
"""Strictly read-only v1126.2 Reflection Quality Intake checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from reflection_quality_signals import build_reflection_quality_signal_inspection, CATEGORIES
from reflection_quality_evaluation_candidates import build_reflection_quality_evaluation_candidate_inspection, STATES
CONTRACT_VERSION="v1126.2"
def _runtime_root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root:Path):
 d=hashlib.sha256()
 if not root.exists(): return d.hexdigest()
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc'):
  try: st=p.stat(); rel=p.relative_to(root).as_posix()
  except (OSError,ValueError): continue
  d.update(rel.encode());d.update(b'\0');d.update(str(st.st_size).encode());d.update(b'\0');d.update(str(st.st_mtime_ns).encode());d.update(b'\n')
 return d.hexdigest()
def build_reflection_quality_intake_checkpoint(runtime_root=None,*,source_root=None)->dict[str,Any]:
 runtime=Path(runtime_root).resolve() if runtime_root else _runtime_root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
 rb,sb=_sig(runtime),_sig(source);signals=build_reflection_quality_signal_inspection(runtime);candidates=build_reflection_quality_evaluation_candidate_inspection(runtime);rm,sm=rb!=_sig(runtime),sb!=_sig(source)
 checks=[
  ("quality_signal_contract",signals.get("contract_version")=="v1126.0"),
  ("quality_candidate_contract",candidates.get("contract_version")=="v1126.1"),
  ("recognized_quality_categories",set(CATEGORIES)==set(signals.get("category_counts",{})) or set(signals.get("category_counts",{})).issubset(CATEGORIES)),
  ("recognized_candidate_states",set(candidates.get("recognized_states",[]))==set(STATES)),
  ("unsupported_conclusion_separated","unsupported_conclusion" in CATEGORIES),
  ("contradiction_separated","contradiction" in CATEGORIES),
  ("confidence_mismatch_separated","confidence_mismatch" in CATEGORIES),
  ("provider_failure_recovery_separated",{"provider_failure","provider_recovery"}.issubset(CATEGORIES)),
  ("structural_lineage_preserved",all(x.get("outcome_id") and x.get("structural_digest") for x in signals.get("recent_signals",[]))),
  ("recovery_and_load_restraint",all(x.get("state") in STATES for x in candidates.get("recent_candidates",[]))),
  ("conclusions_not_exposed",signals.get("conclusions_exposed") is False and candidates.get("conclusions_exposed") is False),
  ("hidden_reasoning_not_exposed",signals.get("hidden_reasoning_exposed") is False and candidates.get("hidden_reasoning_exposed") is False),
  ("no_internal_revision",all(r.get(k) is False for r in (signals,candidates) for k in ("belief_updated","goal_updated","self_model_updated"))),
  ("no_provider_contact",signals.get("provider_contacted") is False and candidates.get("provider_contacted") is False),
  ("no_message_or_action",all(r.get("message_sent") is False and r.get("external_action_executed") is False for r in (signals,candidates))),
  ("runtime_read_only",not rm),("source_read_only",not sm),("checkpoint_is_observational",True)]
 rows=[{"id":i,"status":"pass" if ok else "fail"} for i,ok in checks]
 return {"ok":all(x[1] for x in checks),"contract_version":CONTRACT_VERSION,"checkpoint_name":"Reflection Quality Intake","checks":rows,"passed":sum(1 for _,ok in checks if ok),"total":len(checks),"signals":signals,"candidates":candidates,"runtime_mutated":rm,"source_modified":sm,"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"conclusions_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"message_sent":False,"provider_contacted":False,"external_action_executed":False}
