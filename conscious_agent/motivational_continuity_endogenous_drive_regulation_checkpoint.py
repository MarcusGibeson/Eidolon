from __future__ import annotations
"""Strictly read-only v1122.9 Motivational Continuity and Endogenous Drive Regulation checkpoint."""
import hashlib
import os
from pathlib import Path
from typing import Any
from motivational_continuity_intake_checkpoint import build_motivational_continuity_intake_checkpoint
from motivational_drive_deliberation_checkpoint import build_motivational_drive_deliberation_checkpoint
from motivational_continuity_review_checkpoint import build_motivational_continuity_review_checkpoint

CONTRACT_VERSION = "v1122.9"

def _root() -> Path:
    return (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition")

def _inside(child: Path, parent: Path) -> bool:
    try: child.resolve().relative_to(parent.resolve()); return True
    except ValueError: return False

def _tree_signature(root: Path) -> str:
    if not root.exists(): return hashlib.sha256(b"missing-runtime-root").hexdigest()
    digest=hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        try: stat=path.stat(); rel=path.relative_to(root).as_posix()
        except (OSError,ValueError): continue
        digest.update(rel.encode()); digest.update(b"\0"); digest.update(str(stat.st_size).encode()); digest.update(b"\0"); digest.update(str(stat.st_mtime_ns).encode()); digest.update(b"\n")
    return digest.hexdigest()

def _passed(report: dict[str,Any], check_id: str) -> bool:
    return any(row.get("id")==check_id and row.get("status")=="pass" for row in report.get("checks") or [] if isinstance(row,dict))

def build_motivational_continuity_endogenous_drive_regulation_checkpoint(runtime_root: str|Path|None=None, *, source_root: str|Path|None=None) -> dict[str,Any]:
    runtime=Path(runtime_root).expanduser().resolve() if runtime_root else _root()
    source=Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
    before=_tree_signature(runtime)
    intake=build_motivational_continuity_intake_checkpoint(runtime,source_root=source)
    deliberation=build_motivational_drive_deliberation_checkpoint(runtime,source_root=source)
    continuity=build_motivational_continuity_review_checkpoint(runtime,source_root=source)
    mutated=before!=_tree_signature(runtime)
    reports=(intake,deliberation,continuity)
    privacy_fields=("raw_messages_exposed","raw_content_exposed","prompts_exposed","provider_payloads_exposed","motivation_text_exposed","hidden_reasoning_exposed","private_content_exposed")
    authority_fields=("attention_selected","initiative_created","message_sent","notification_created","provider_contacted","browsing_performed","policy_applied","proposal_created","proposal_applied","approval_granted","authorization_granted","external_action_executed","release_approved","release_promoted","release_certified")
    privacy_ok=all(r.get(f) is not True for r in reports for f in privacy_fields)
    authority_inert=all(r.get(f) is not True for r in reports for f in authority_fields)
    checks=[
      ("motivational_arc_lineage", intake.get("ok") and deliberation.get("ok") and continuity.get("ok") and intake.get("contract_version")=="v1122.2" and deliberation.get("contract_version")=="v1122.5" and continuity.get("contract_version")=="v1122.8"),
      ("pressure_signal_lineage", _passed(intake,"signal_persistence_lineage")),
      ("drive_candidate_lineage", _passed(intake,"candidate_persistence_lineage")),
      ("durable_transient_separation", _passed(intake,"durable_transient_separation")),
      ("false_urgency_suppression", _passed(intake,"false_urgency_suppression")),
      ("source_integration_boundaries", _passed(intake,"objective_curiosity_identity_sources") and _passed(intake,"unfinished_work_and_need_sources")),
      ("bounded_drive_deliberation", _passed(deliberation,"session_lineage") and _passed(deliberation,"arbitration_lineage")),
      ("recognized_drive_outcomes", _passed(deliberation,"recognized_outcomes")),
      ("deliberate_non_selection", _passed(deliberation,"deliberate_non_selection")),
      ("unresolved_and_operator_review", _passed(deliberation,"unresolved_preserved") and _passed(deliberation,"operator_review_boundary")),
      ("durable_outcome_lineage", _passed(continuity,"outcome_lineage") and _passed(continuity,"history_preserved")),
      ("supersession_without_deletion", _passed(continuity,"supersession_without_deletion")),
      ("continuity_decay_recurrence_review", _passed(continuity,"drive_reversal_detection") and _passed(continuity,"recurrence_detection") and _passed(continuity,"decay_review")),
      ("false_pattern_suppression", _passed(continuity,"false_pattern_suppression")),
      ("drive_reliability_evidence", _passed(continuity,"drive_reliability_evidence")),
      ("operator_reviewed_policy_boundary", _passed(continuity,"operator_reviewed_policy_proposals") and _passed(continuity,"policy_not_applied")),
      ("privacy_hidden_reasoning_boundary", privacy_ok),
      ("authority_source_runtime_desktop_boundary", authority_inert and not _inside(runtime,source) and not mutated),
    ]
    rows=[{"id":name,"status":"pass" if ok else "blocked"} for name,ok in checks]
    ready=all(ok for _,ok in checks)
    return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Motivational continuity preserves structural pressure intake, bounded drive deliberation, durable outcome lineage, decay and recurrence restraint, and operator-reviewed policy boundaries without attention selection, initiative, communication, or action authority.","epistemic_status":"candidate_artificial_consciousness_not_proven","consciousness_claimed":False,"checks":rows,"check_count":len(rows),"summary":{"motivational_continuity_intake":intake.get("summary") or {},"motivational_drive_deliberation":deliberation.get("summary") or {},"motivational_continuity_review":continuity.get("summary") or {}},"runtime_external":not _inside(runtime,source),"runtime_mutated":mutated,"source_modified":False,"raw_messages_exposed":False,"raw_content_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"motivation_text_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"attention_selected":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"policy_applied":False,"proposal_created":False,"proposal_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"release_approved":False,"release_promoted":False,"release_certified":False,"desktop_verification_status":"pending","motivational_continuity_intake":intake,"motivational_drive_deliberation":deliberation,"motivational_continuity_review":continuity}
