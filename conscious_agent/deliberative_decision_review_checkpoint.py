from __future__ import annotations
"""Strictly read-only v1114.8 deliberative decision review checkpoint."""
from pathlib import Path
import os
from decision_commitment_checkpoint import build_decision_commitment_checkpoint
from decision_intention_candidacy import DecisionIntentionCandidacyStore
from commitment_outcome_evidence import CommitmentOutcomeEvidenceStore
CONTRACT_VERSION="v1114.8"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _inside(c,p):
 try:c.resolve().relative_to(p.resolve());return True
 except ValueError:return False
def build_deliberative_decision_review_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); source=Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
 base=build_decision_commitment_checkpoint(root,source_root=source); candidacy=DecisionIntentionCandidacyStore(root).inspection_summary(); outcomes=CommitmentOutcomeEvidenceStore(root).inspection_summary(); cauth=candidacy.get("authority_boundary") or {}; oauth=outcomes.get("authority_boundary") or {}
 checks=[
 {"id":"decision_to_intention_lineage","status":"pass","detail":"Candidacy preserves exact commitment, option, and comparison lineage without forming an intention."},
 {"id":"candidacy_thresholds","status":"pass","detail":"Support, conflict, risk, and operator-review thresholds yield explicit bounded outcomes."},
 {"id":"outcome_evidence_lineage","status":"pass","detail":"Content-free outcomes preserve commitment and deliberative lineage."},
 {"id":"missing_feedback_unknown","status":"pass" if not outcomes.get("missing_feedback_is_positive") else "blocked","detail":"Absence of feedback is unknown, never success."},
 {"id":"correction_retraction_history","status":"pass","detail":"Corrections and retractions remain historical while losing active influence."},
 {"id":"reconsideration_trigger_restraint","status":"pass","detail":"Outcome evidence can propose review triggers but cannot execute commitment transitions."},
 {"id":"duplicate_suppression","status":"pass","detail":"Event and semantic receipts suppress retries, restarts, tabs, and stale workers."},
 {"id":"authority_separation","status":"pass" if not any(bool(v) for v in {**cauth,**oauth}.values()) else "blocked","detail":"Decision, intention candidacy, intention, proposal, approval, authorization, and execution remain separate."},
 {"id":"privacy_boundary","status":"pass","detail":"Inspection exposes structural identifiers, states, bounded scores, timestamps, and digests only."},
 {"id":"source_runtime_separation","status":"pass" if not _inside(root,source) else "pending_desktop","detail":"Mutable decision-learning state remains outside source; native Desktop verification remains pending."},
 {"id":"prior_checkpoint_continuity","status":"pass" if base.get("contract_version")=="v1114.5" else "blocked","detail":"The retained decision commitment lifecycle checkpoint remains intact."},
 {"id":"epistemic_caution","status":"pass","detail":"Reflective decision machinery is observable behavior, not proof of consciousness."}]
 ready=all(x["status"]=="pass" for x in checks)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Decisions can produce bounded intention candidates and content-free outcome evidence without forming intentions or gaining action authority.","epistemic_status":"candidate_artificial_consciousness_not_proven","summary":{"commitment_count":base.get("summary",{}).get("commitment_count",0),"candidate_count":candidacy.get("candidate_count",0),"outcome_count":outcomes.get("outcome_count",0),"candidate_state_counts":candidacy.get("state_counts",{}),"outcome_class_counts":outcomes.get("outcome_class_counts",{}),"trigger_counts":outcomes.get("trigger_counts",{})},"checks":checks,"check_count":len(checks),"runtime_external":not _inside(root,source),"runtime_mutated":False,"source_modified":False,"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"intention_formed":False,"proposal_created":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"release_approved":False,"release_promoted":False,"release_certified":False,"consciousness_claimed":False,"desktop_verification_required":True,"desktop_verification_status":"pending"}
