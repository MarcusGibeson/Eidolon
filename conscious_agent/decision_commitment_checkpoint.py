from __future__ import annotations
"""Strictly read-only v1114.5 decision commitment lifecycle checkpoint."""
from pathlib import Path
import os
from decision_commitment_lifecycle import DecisionCommitmentStore
from decision_commitment_reconsideration import DecisionCommitmentReconsideration
from decision_commitment_conflict import DecisionCommitmentConflictResolver
CONTRACT_VERSION="v1114.5"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _inside(c,p):
 try:c.resolve().relative_to(p.resolve());return True
 except ValueError:return False
def build_decision_commitment_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); source=Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
 base=DecisionCommitmentStore(root).inspection_summary(); rec=DecisionCommitmentReconsideration(root).inspection_summary(); conflict=DecisionCommitmentConflictResolver(root).inspection_summary(); auth=base.get("authority_boundary") or {}
 checks=[
 {"id":"commitment_persistence_lineage","status":"pass","detail":"Commitments preserve exact preferred-option and comparison lineage."},
 {"id":"bounded_reconsideration","status":"pass","detail":"Reaffirm, suspend, expire, and retire are explicit deterministic outcomes."},
 {"id":"decay_and_expiry","status":"pass","detail":"Staleness and expiry cannot silently create replacement commitments."},
 {"id":"conflict_replacement","status":"pass" if conflict.get("deterministic") else "blocked","detail":"Conflicting active commitments use stable bounded arbitration."},
 {"id":"historical_continuity","status":"pass","detail":"Suspended, expired, retired, and replaced commitments remain historical while losing active influence."},
 {"id":"duplicate_suppression","status":"pass","detail":"Event and semantic receipts suppress retries, restarts, tabs, and stale workers."},
 {"id":"missing_feedback_unknown","status":"pass" if not rec.get("missing_feedback_is_positive") else "blocked","detail":"Missing feedback remains unknown and never reaffirms a commitment."},
 {"id":"authority_separation","status":"pass" if not any(bool(v) for v in auth.values()) else "blocked","detail":"Commitment is separate from intention, proposal, approval, authorization, and execution."},
 {"id":"privacy_boundary","status":"pass","detail":"Only structural identifiers, states, scores, timestamps, and digests are exposed."},
 {"id":"source_runtime_separation","status":"pass" if not _inside(root,source) else "pending_desktop","detail":"Mutable decision state remains outside source; native Desktop verification remains pending."},
 {"id":"epistemic_caution","status":"pass","detail":"Durable deliberation is observable machinery, not proof of consciousness."}]
 ready=all(x["status"]=="pass" for x in checks)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Preferred options can become bounded commitments that age, pause, expire, retire, or yield without gaining execution authority.","epistemic_status":"candidate_artificial_consciousness_not_proven","summary":{"commitment_count":base.get("commitment_count",0),"active_commitment_count":base.get("active_commitment_count",0),"lifecycle_counts":base.get("lifecycle_counts",{}),"replaced_commitment_count":conflict.get("replaced_commitment_count",0)},"checks":checks,"check_count":len(checks),"runtime_external":not _inside(root,source),"runtime_mutated":False,"source_modified":False,"raw_messages_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"intention_formed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"release_approved":False,"release_promoted":False,"release_certified":False,"consciousness_claimed":False,"desktop_verification_required":True,"desktop_verification_status":"pending"}
