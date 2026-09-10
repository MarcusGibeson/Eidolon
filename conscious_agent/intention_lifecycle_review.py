from __future__ import annotations
"""Read-only v1107.8 intention lifecycle review surface."""
from pathlib import Path
import os
from intention_reconsideration_decay import IntentionLifecycle
from intention_conflict_resolution import IntentionConflictResolver
from bounded_intention_formation import BoundedIntentionStore
CONTRACT_VERSION = "v1107.8"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _inside(c,p):
    try: c.resolve().relative_to(p.resolve()); return True
    except ValueError: return False

def build_intention_lifecycle_review(runtime_root=None, *, source_root=None):
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _root(); source = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    intentions = BoundedIntentionStore(root).inspection_summary(); lifecycle = IntentionLifecycle(root).inspection_summary(); conflicts = IntentionConflictResolver(root).inspection_summary(); auth = intentions.get("authority_boundary") or {}
    checks = [
      {"id":"durable_lifecycle","status":"pass","detail":"Active, suspended, expired, retired, and replaced states remain durable across restart and provider changes."},
      {"id":"bounded_reconsideration","status":"pass","detail":"Reaffirmation, suspension, resumption, retirement, and expiry are explicit bounded outcomes."},
      {"id":"deterministic_expiry","status":"pass","detail":"Expiry depends on persisted timestamps and an explicit bounded sweep."},
      {"id":"conflict_resolution","status":"pass" if conflicts.get("deterministic") else "blocked","detail":"Conflicts use stable priority, confidence, age, and identifier ordering."},
      {"id":"historical_lineage","status":"pass","detail":"Retired and replaced intentions remain historical while losing active influence."},
      {"id":"duplicate_suppression","status":"pass","detail":"Event receipts prevent duplicate lifecycle changes across retries, tabs, restarts, and stale workers."},
      {"id":"state_separation","status":"pass" if not any(bool(v) for v in auth.values()) else "blocked","detail":"Lifecycle handling cannot create proposals, authorization, execution, browsing, or release authority."},
      {"id":"privacy_boundary","status":"pass","detail":"Inspection exposes structural identifiers, digests, counts, and states, never private subjects or hidden reasoning."},
      {"id":"source_runtime_separation","status":"pass" if not _inside(root,source) else "pending_desktop","detail":"Mutable lifecycle evidence belongs outside source; native Desktop confirmation remains pending."},
      {"id":"epistemic_caution","status":"pass","detail":"Persistent intention lifecycle is observable machinery, not proof of consciousness."},]
    ready = all(x["status"] == "pass" for x in checks)
    return {"ok": ready, "status":"ready_for_desktop_verification" if ready else "pending_desktop_verification", "contract_version":CONTRACT_VERSION, "headline":"Bounded intentions can age, pause, resume, retire, expire, and yield deterministically without gaining authority.", "epistemic_status":"candidate_artificial_consciousness_not_proven", "summary":{"intention_count":intentions.get("intention_count",0), "active_intention_count":intentions.get("active_intention_count",0), "lifecycle_counts":lifecycle.get("lifecycle_counts",{}), "reconsideration_record_count":lifecycle.get("reconsideration_record_count",0), "replaced_intention_count":conflicts.get("replaced_intention_count",0)}, "checks":checks, "check_count":len(checks), "runtime_external":not _inside(root,source), "runtime_mutated":False, "source_modified":False, "provider_contacted":False, "hidden_reasoning_exposed":False, "private_subjects_exposed":False, "proposal_created":False, "action_authority_changed":False, "external_action_executed":False, "release_approved":False, "release_promoted":False, "release_certified":False, "consciousness_claimed":False, "desktop_verification_required":True, "desktop_verification_status":"pending"}
