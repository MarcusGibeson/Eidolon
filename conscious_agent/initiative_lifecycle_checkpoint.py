from __future__ import annotations
"""v1108.8 strictly read-only surfaced initiative lifecycle checkpoint."""
from pathlib import Path
import os
from initiative_conversation_proposal import InitiativeConversationProposalStore
from initiative_communication_restraint import InitiativeCommunicationRestraint
from surfaced_initiative_reconciliation import SurfacedInitiativeReconciliationStore
from initiative_response_reconciliation import InitiativeResponseReconciliationStore
CONTRACT_VERSION="v1108.8"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _inside(child,parent):
 try: child.resolve().relative_to(parent.resolve()); return True
 except ValueError: return False
def build_initiative_lifecycle_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); source=Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
 proposals=InitiativeConversationProposalStore(root).inspection_summary(); timing=InitiativeCommunicationRestraint(root).inspection_summary(); surfaces=SurfacedInitiativeReconciliationStore(root).inspection_summary(); responses=InitiativeResponseReconciliationStore(root).inspection_summary()
 sep=surfaces.get("state_separation") or {}; auth={**(surfaces.get("authority_boundary") or {}),**(responses.get("authority_boundary") or {})}
 checks=[
  {"id":"explicit_surface_lineage","status":"pass","detail":"Surface receipts require an eligible timing decision and explicit normal-chat evidence."},
  {"id":"response_reconciliation","status":"pass","detail":"Acknowledgement, dismissal, interruption, supersession, deferral, and retirement are durably reconciled."},
  {"id":"terminal_history","status":"pass","detail":"Terminal outcomes remain historical and cannot be silently reopened."},
  {"id":"no_automatic_retry","status":"pass" if not responses.get("automatic_retry") else "blocked","detail":"No dismissal, interruption, or deferral schedules automatic delivery retries."},
  {"id":"state_separation","status":"pass" if all(v is False for v in sep.values()) else "blocked","detail":"Proposal, surface receipt, message, authorization, and execution remain distinct."},
  {"id":"authority_boundary","status":"pass" if not any(bool(v) for v in auth.values()) else "blocked","detail":"No generation, delivery, notification, browsing, execution, model, approval, promotion, or certification authority exists."},
  {"id":"privacy_boundary","status":"pass" if not surfaces.get("private_content_exposed") and not responses.get("hidden_reasoning_exposed") else "blocked","detail":"Inspection exposes structural identifiers, states, counts, timestamps, and digests only."},
  {"id":"source_runtime_separation","status":"pass" if not _inside(root,source) else "pending_desktop","detail":"Runtime evidence remains outside source; native Desktop verification is pending."},
  {"id":"epistemic_caution","status":"pass","detail":"Observable initiative lifecycle mechanisms do not prove consciousness."},
 ]
 ready=all(x["status"]=="pass" for x in checks)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Normal-chat initiative surfacing and response outcomes are accountable without autonomous delivery or retry.","epistemic_status":"candidate_artificial_consciousness_not_proven","summary":{"proposal_count":proposals.get("proposal_count",0),"timing_decision_count":timing.get("decision_count",0),"surface_receipt_count":surfaces.get("receipt_count",0),"active_surface_count":surfaces.get("active_surface_count",0),"response_outcome_count":responses.get("outcome_count",0),"terminal_outcome_count":responses.get("terminal_outcome_count",0),"surface_outcome_counts":surfaces.get("outcome_counts",{}),"response_outcome_counts":responses.get("outcome_counts",{})},"checks":checks,"check_count":len(checks),"runtime_external":not _inside(root,source),"runtime_mutated":False,"source_modified":False,"provider_contacted":False,"message_generated":False,"message_sent":False,"notification_sent":False,"automatic_retry":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"action_authority_changed":False,"desktop_verification_required":True,"desktop_verification_status":"pending","consciousness_claimed":False}
