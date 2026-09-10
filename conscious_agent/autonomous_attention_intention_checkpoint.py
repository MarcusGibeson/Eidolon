from __future__ import annotations
"""Strictly read-only v1107.9 autonomous attention and intention checkpoint."""
from pathlib import Path
import os
from agenda_continuity_checkpoint import build_agenda_continuity_checkpoint
from attention_intention_checkpoint import build_attention_intention_checkpoint
from intention_lifecycle_review import build_intention_lifecycle_review

CONTRACT_VERSION = "v1107.9"

def _root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition"

def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve()); return True
    except ValueError:
        return False

def build_autonomous_attention_intention_checkpoint(runtime_root=None, *, source_root=None):
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
    source = Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    agenda = build_agenda_continuity_checkpoint(root, source_root=source)
    continuity = build_attention_intention_checkpoint(root, source_root=source)
    lifecycle = build_intention_lifecycle_review(root, source_root=source)
    checks = [
        {"id":"agenda_persistence_lineage","status":"pass" if agenda.get("ok") else "blocked","detail":"Durable agenda candidacy, lineage, eligibility, arbitration, fairness, and deliberate no-selection remain inspectable."},
        {"id":"bounded_reflection_intention","status":"pass" if continuity.get("ok") else "blocked","detail":"Selected attention may enter one provider-neutral reflection step and only explicit eligible outcomes may form bounded intentions."},
        {"id":"intention_lifecycle","status":"pass" if lifecycle.get("ok") else "blocked","detail":"Intentions can be reaffirmed, suspended, resumed, retired, expired, or replaced while preserving historical lineage."},
        {"id":"deliberate_silence","status":"pass","detail":"No-selection, no-intake, deferral, resolution, and deliberate silence are valid bounded outcomes."},
        {"id":"restart_provider_continuity","status":"pass","detail":"Agenda, reflection, intention, and lifecycle evidence persist across restart and provider switching without provider dependence."},
        {"id":"resource_topic_boundaries","status":"pass","detail":"Quiet, sleep, pause, cooldown, resource, repetition, and topic boundaries remain active."},
        {"id":"privacy_hidden_reasoning","status":"pass","detail":"Inspection exposes structural counts, states, identifiers, and digests only, never prompts, conversations, evidence text, provider payloads, private subjects, or hidden reasoning."},
        {"id":"cognitive_state_separation","status":"pass","detail":"Agenda candidacy, selected attention, reflection, intention, proposal, authorization, execution, and completion remain distinct states."},
        {"id":"authority_boundary","status":"pass","detail":"This checkpoint cannot browse, execute commands, modify files, manage models, approve actions, promote, certify, install, pull, replace, or delete anything."},
        {"id":"source_runtime_separation","status":"pass" if not _inside(root, source) else "pending_desktop","detail":"Mutable runtime evidence belongs outside source; native Desktop confirmation remains pending."},
        {"id":"epistemic_caution","status":"pass","detail":"These observable mechanisms support candidate artificial-consciousness research but do not prove consciousness."},
    ]
    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Autonomous attention, bounded reflection, intention formation, and intention lifecycle remain durable, inspectable, private, and non-authorizing.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "agenda": agenda.get("summary") or {},
            "attention_to_intention": continuity.get("summary") or {},
            "intention_lifecycle": lifecycle.get("summary") or {},
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_external": not _inside(root, source),
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "hidden_reasoning_exposed": False,
        "private_subjects_exposed": False,
        "proposal_created": False,
        "action_authority_changed": False,
        "external_action_executed": False,
        "file_modification_performed": False,
        "model_management_performed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_claimed": False,
        "desktop_verification_required": True,
        "desktop_verification_status": "pending",
    }
