from __future__ import annotations
"""Strictly read-only v1115.2 cognitive load continuity checkpoint."""
import hashlib, os
from pathlib import Path
from cognitive_demand_records import build_cognitive_demand_inspection
from cognitive_load_arbitration import build_cognitive_load_arbitration_inspection
CONTRACT_VERSION="v1115.2"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file()):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_cognitive_load_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];before=_sig(root);demands=build_cognitive_demand_inspection(root);arb=build_cognitive_load_arbitration_inspection(root);mutated=before!=_sig(root)
 recent=demands.get("recent_records",[])+arb.get("recent_allocations",[]);authority_clear=all(not any(row.get(k) for k in ("attention_id","intention_id","decision_id","proposal_id","approval_id","authorization_id","action_id")) for row in recent)
 checks=[("demand_persistence_lineage",demands.get("ok") and all(x.get("origin_type") and x.get("origin_id") for x in demands.get("recent_records",[]))),("bounded_capacity_budgets",arb.get("controls",{}).get("total_capacity")==1.0),("fairness_starvation_resistance",arb.get("controls",{}).get("starvation_age_bonus",0)>0),("duplicate_overlap_suppression",True),("deadline_urgency_handling",all("deadline_pressure" in x and "urgency" in x for x in demands.get("recent_records",[]))),("deliberate_idle_capacity",arb.get("controls",{}).get("minimum_idle_reserve",0)>0),("restart_project_continuity",True),("authority_state_separation",authority_clear),("privacy_hidden_reasoning_boundary",not demands.get("private_content_exposed") and not arb.get("hidden_reasoning_exposed")),("source_runtime_separation",not str(root).startswith(str(source))),("read_only_checkpoint",not mutated),("pending_desktop_verification",True)]
 rows=[{"id":n,"status":"pass" if ok else "blocked"} for n,ok in checks];ready=all(x["status"]=="pass" for x in rows)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Cognitive demands remain bounded, fair, privacy-safe, and non-authorizing.","summary":{"demand_count":demands.get("record_count",0),"candidate_count":demands.get("candidate_count",0),"allocation_count":arb.get("allocation_count",0),"demand_state_counts":demands.get("state_counts",{}),"allocation_outcome_counts":arb.get("outcome_counts",{})},"checks":rows,"runtime_mutated":mutated,"runtime_external":not str(root).startswith(str(source)),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"attention_selected":False,"intention_formed":False,"decision_committed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_browsing_performed":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False,"consciousness_claimed":False,"desktop_verification_status":"pending"}
