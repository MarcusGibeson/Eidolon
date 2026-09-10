from __future__ import annotations

"""Read-only v1235.9 Evidence-Backed Lessons from Development Outcomes checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from evidence_backed_development_outcome_lessons import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    LESSON_CODES,
    RECONSIDERATION_DECISIONS,
    REVIEW_DISPOSITIONS,
    build_evidence_backed_development_outcome_lessons_contract,
)

CONTRACT_VERSION = "v1235.9"
CHECKPOINT_ID = "evidence-backed-development-outcome-lessons-checkpoint"
MILESTONE_NAME = "Evidence-Backed Lessons from Development Outcomes"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"


def _tree_signature(root: Path) -> tuple[str, int]:
    rows=[]; count=0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {"QUICK_STAGE_NAMES","LEGACY_QUICK_STAGE_NAMES"} for t in node.targets):
                value=ast.literal_eval(node.value)
                names.update(str(item) for item in value)
    except Exception:
        pass
    return names


def build_evidence_backed_development_outcome_lessons_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,before_count=_tree_signature(source)
    contract=build_evidence_backed_development_outcome_lessons_contract()
    registry=inspect_checkpoint_registry(source_root=source)
    descriptor=next((row for row in registry.get("checkpoints",[]) if row.get("checkpoint_id")==CHECKPOINT_ID),{})
    module=(source/"conscious_agent/evidence_backed_development_outcome_lessons.py").read_text(encoding="utf-8")
    chat=(source/"conscious_agent/ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api=(source/"conscious_agent/api_server.py").read_text(encoding="utf-8")
    cli=(source/"eidolon.py").read_text(encoding="utf-8")
    metadata=(source/"conscious_agent/release_metadata.py").read_text(encoding="utf-8")
    roadmap=(source/"README_NEXT_STEPS.md").read_text(encoding="utf-8")
    history=(source/"README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    verifier=(source/"tools/release_verify.py").read_text(encoding="utf-8")
    progress=retained_checkpoint_progress(
        source,
        checkpoint_version="1235.9",
        successor_version="1236.0",
        successor_surface="conscious_agent/goal_motivation_work_priority_integration.py",
    )
    expected_stages={
        "v1235.2-evidence-backed-development-outcome-lessons-foundations",
        "v1235.5-evidence-backed-development-outcome-lessons-operator-review",
        "v1235.8-evidence-backed-development-outcome-lessons-adversarial-reliability",
        "v1235.9-evidence-backed-development-outcome-lessons-checkpoint",
    }
    expected_docs=(
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1235_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1235_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1235_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1235_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1235_9.md",
    )
    checks={
        "contract_ok":contract.get("ok") is True,
        "retained_contract_version":contract.get("contract_version")==RETAINED_CONTRACT_VERSION,
        "roadmap_path":contract.get("roadmap_path")==ROADMAP_PATH,
        "exact_quality_binding":contract.get("exact_quality_assessment_and_review_binding") is True,
        "outcome_lineage_retained":contract.get("optional_sealed_outcome_lineage_retained") is True,
        "deterministic_derivation":contract.get("deterministic_lesson_derivation") is True,
        "confidence_uncertainty":contract.get("evidence_strength_and_uncertainty_visible") is True,
        "project_scope":contract.get("project_scoped_external_revisable_learning") is True,
        "later_evidence":contract.get("later_evidence_reconsideration") is True,
        "deliberate_silence":contract.get("deliberate_silence_supported") is True,
        "exact_chat_controls":contract.get("ordinary_chat_exact_controls") is True,
        "hardening_required":contract.get("restart_replay_stale_tamper_privacy_contradiction_hardening_required") is True,
        "no_cognition":contract.get("accepted_lessons_do_not_write_cognition") is True,
        "no_execution_authority":contract.get("accepted_lessons_do_not_grant_execution_authority") is True,
        "lesson_code_coverage":len(LESSON_CODES)>=12,
        "review_dispositions":REVIEW_DISPOSITIONS=={"accept","reject","defer","revise","suspend"},
        "reconsideration_decisions":RECONSIDERATION_DECISIONS=={"retain","revise","suspend","reopen","unresolved"},
        "module_prepare":"def prepare_evidence_backed_development_lesson(" in module,
        "module_review":"def review_evidence_backed_development_lesson(" in module,
        "module_reconsider":"def reconsider_evidence_backed_development_lesson(" in module,
        "module_public_candidates":"def public_evidence_backed_development_lessons(" in module,
        "module_public_reviews":"def public_evidence_backed_development_lesson_reviews(" in module,
        "module_public_reconsiderations":"def public_evidence_backed_development_lesson_reconsiderations(" in module,
        "module_exact_quality_basis":"def _quality_basis(" in module,
        "module_no_cognition":'"lesson_writes_cognition": False' in module,
        "module_no_execution":'"lesson_is_execution_authority": False' in module,
        "module_no_project_mutation":'"project_mutation_authorized": False' in module,
        "module_no_test_execution":'"test_execution_authorized": False' in module,
        "chat_route":"process_evidence_backed_development_lesson_control" in chat,
        "api_candidates":"evidence-backed-development-lessons" in api,
        "api_reviews":"evidence-backed-development-lesson-reviews" in api,
        "api_reconsiderations":"evidence-backed-development-lesson-reconsiderations" in api,
        "api_checkpoint":CHECKPOINT_ID in api,
        "cli_candidates":'"evidence-backed-development-lessons"' in cli,
        "cli_reviews":'"evidence-backed-development-lesson-reviews"' in cli,
        "cli_reconsiderations":'"evidence-backed-development-lesson-reconsiderations"' in cli,
        "cli_checkpoint":f'"{CHECKPOINT_ID}"' in cli,
        "metadata_version":progress.get("checkpoint_retained") is True,
        "metadata_milestone":progress.get("coherent") is True,
        "metadata_next":progress.get("started") is True,
        "roadmap_current":"v1235.9" in roadmap,
        "roadmap_next":"v1236" in roadmap,
        "history_current":"v1235.9" in history,
        "release_stages_registered":expected_stages.issubset(_quick_stage_names(verifier)),
        "release_commands_registered":all(stage in verifier for stage in expected_stages),
        "docs_present":all((source/name).is_file() for name in expected_docs),
        "registry_present":bool(descriptor),
        "registry_version":descriptor.get("contract_version")==CONTRACT_VERSION,
        "registry_read_only":descriptor.get("read_only") is True,
        "registry_no_inputs":descriptor.get("required_input_count")==0,
    }
    for key,expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"]=contract.get(key) is expected
    after,after_count=_tree_signature(source)
    unchanged=before==after and before_count==after_count
    checks["source_signature_unchanged"]=unchanged
    passed=sum(bool(value) for value in checks.values()); total=len(checks); ok=passed==total
    return {
        "ok":ok,
        "status":"evidence_backed_development_outcome_lessons_checkpoint_ready" if ok else "evidence_backed_development_outcome_lessons_checkpoint_blocked",
        "checkpoint_id":CHECKPOINT_ID,
        "contract_version":CONTRACT_VERSION,
        "retained_contract_version":RETAINED_CONTRACT_VERSION,
        "milestone_name":MILESTONE_NAME,
        "roadmap_path":ROADMAP_PATH,
        "checks":checks,"passed":passed,"total":total,
        "read_only":True,"content_free":True,"project_scoped":True,
        "source_signature_before":before,"source_signature_after":after,"source_signature_unchanged":unchanged,
        "source_file_count_before":before_count,"source_file_count_after":after_count,
        "runtime_data_read":False,"runtime_data_written":False,
        "provider_contacted":False,"commands_executed":False,"tests_executed":False,
        "project_modified":False,"requirements_modified":False,"queue_modified":False,"schedule_modified":False,
        "cognition_written":False,"source_modified":False,"authority_granted":False,
        **AUTHORITY_FLAGS,
    }
