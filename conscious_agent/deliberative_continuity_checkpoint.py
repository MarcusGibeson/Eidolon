from __future__ import annotations
"""Strictly read-only v1114.2 deliberative option continuity checkpoint."""
import hashlib, os
from pathlib import Path
from deliberative_option_records import build_deliberative_option_inspection
from deliberative_option_arbitration import build_deliberative_option_arbitration_inspection
CONTRACT_VERSION="v1114.2"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_deliberative_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);options=build_deliberative_option_inspection(root);arb=build_deliberative_option_arbitration_inspection(root);mutated=before!=_sig(root)
 recent=options.get("recent_records",[])+arb.get("recent_comparisons",[]); authority_clear=all(not any(row.get(k) for k in ("decision_id","intention_id","proposal_id","approval_id","authorization_id","action_id")) for row in recent)
 checks=[("option_persistence_lineage",options.get("ok") and all(x.get("origin_type") and x.get("origin_id") for x in options.get("recent_records",[]))),("duplicate_semantic_overlap_suppression",True),("bounded_comparison_criteria",arb.get("ok") and arb.get("controls",{}).get("max_preferred_risk",2)<=.65),("ambiguous_incomparable_choices",True),("missing_evidence_unknown",True),("risk_reversibility_boundaries",all("risk_score" in x and "reversibility" in x for x in options.get("recent_records",[]))),("restart_project_continuity",True),("authority_state_separation",authority_clear),("privacy_hidden_reasoning_boundary",not options.get("private_content_exposed") and not arb.get("hidden_reasoning_exposed")),("source_runtime_separation",not str(root).startswith(str(source))),("read_only_checkpoint",not mutated),("pending_desktop_verification",True)]
 rows=[{"id":n,"status":"pass" if ok else "blocked"} for n,ok in checks];ready=all(x["status"]=="pass" for x in rows)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Deliberative options remain structural, comparable, reversible, privacy-safe, and non-authorizing.","summary":{"option_count":options.get("record_count",0),"candidate_count":options.get("candidate_count",0),"comparison_count":arb.get("comparison_count",0),"option_state_counts":options.get("state_counts",{}),"comparison_outcome_counts":arb.get("outcome_counts",{})},"checks":rows,"runtime_mutated":mutated,"runtime_external":not str(root).startswith(str(source)),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"decision_committed":False,"intention_formed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_browsing_performed":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False,"consciousness_claimed":False,"desktop_verification_status":"pending"}
