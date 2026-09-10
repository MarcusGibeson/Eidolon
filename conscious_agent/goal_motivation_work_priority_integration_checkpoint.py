from __future__ import annotations

"""Read-only v1236.9 Goal, Motivation, and Work-Priority Integration checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from goal_motivation_work_priority_integration import (
    ALIGNMENT_STATES,
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    RECOMMENDATION_CODES,
    REVIEW_DISPOSITIONS,
    build_goal_motivation_work_priority_integration_contract,
)

CONTRACT_VERSION = "v1236.9"
CHECKPOINT_ID = "goal-motivation-work-priority-integration-checkpoint"
MILESTONE_NAME = "Goal, Motivation, and Work-Priority Integration"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"


def _tree_signature(root: Path) -> tuple[str, int]:
    rows=[]; count=0
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in {'.pyc','.pyo'}:
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        count += 1
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id in {'QUICK_STAGE_NAMES','LEGACY_QUICK_STAGE_NAMES'} for target in node.targets):
                names.update(str(item) for item in ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_goal_motivation_work_priority_integration_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,before_count=_tree_signature(source)
    contract=build_goal_motivation_work_priority_integration_contract()
    registry=inspect_checkpoint_registry(source_root=source)
    descriptor=next((row for row in registry.get('checkpoints',[]) if row.get('checkpoint_id')==CHECKPOINT_ID),{})
    module=(source/'conscious_agent/goal_motivation_work_priority_integration.py').read_text(encoding='utf-8')
    chat=(source/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
    api=(source/'conscious_agent/api_server.py').read_text(encoding='utf-8')
    cli=(source/'eidolon.py').read_text(encoding='utf-8')
    metadata=(source/'conscious_agent/release_metadata.py').read_text(encoding='utf-8')
    roadmap=(source/'README_NEXT_STEPS.md').read_text(encoding='utf-8')
    history=(source/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8')
    verifier=(source/'tools/release_verify.py').read_text(encoding='utf-8')
    expected_stages={
        'v1236.2-goal-motivation-work-priority-integration-foundations',
        'v1236.5-goal-motivation-work-priority-integration-operator-review',
        'v1236.8-goal-motivation-work-priority-integration-adversarial-reliability',
        'v1236.9-goal-motivation-work-priority-integration-checkpoint',
    }
    expected_docs=(
        'archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1236_0_2.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1236_3_5.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1236_6_8.md',
        'archive/docs/legacy_dependencies/validation/Eidolon_v1236_9_FINAL_VALIDATION.md','archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1236_9.md',
    )
    progress=retained_checkpoint_progress(source,checkpoint_version='1236.9',successor_version='1237.0',successor_surface='conscious_agent/multi_tool_orchestration.py')
    checks={
        'contract_ok':contract.get('ok') is True,
        'retained_contract_version':contract.get('contract_version')==RETAINED_CONTRACT_VERSION,
        'roadmap_path':contract.get('roadmap_path')==ROADMAP_PATH,
        'exact_priority_binding':contract.get('exact_operator_governed_priority_item_binding') is True,
        'sanitized_snapshot_binding':contract.get('sanitized_goal_and_motivation_snapshot_binding') is True,
        'optional_lesson_binding':contract.get('optional_exact_active_lesson_review_binding') is True,
        'deterministic_assessment':contract.get('deterministic_alignment_assessment') is True,
        'conflict_visible':contract.get('goal_motivation_priority_conflict_visible') is True,
        'operator_priority_preserved':contract.get('operator_priority_and_pinning_preserved') is True,
        'proposal_only':contract.get('priority_change_is_proposal_only') is True,
        'append_only_refresh':contract.get('append_only_refresh_on_state_change') is True,
        'exact_chat_controls':contract.get('ordinary_chat_exact_controls') is True,
        'hardening_required':contract.get('restart_replay_stale_tamper_privacy_contradiction_hardening_required') is True,
        'no_priority_mutation':contract.get('accepted_alignment_does_not_change_priority') is True,
        'no_cognition':contract.get('accepted_alignment_does_not_write_cognition') is True,
        'no_execution':contract.get('accepted_alignment_does_not_grant_execution_authority') is True,
        'alignment_state_coverage':len(ALIGNMENT_STATES)==6,
        'recommendation_coverage':len(RECOMMENDATION_CODES)>=8,
        'review_dispositions':REVIEW_DISPOSITIONS=={'accept_alignment','hold','reject','request_changes','propose_priority_change'},
        'module_prepare':'def prepare_goal_motivation_work_priority_integration(' in module,
        'module_review':'def review_goal_motivation_work_priority_integration(' in module,
        'module_public_assessments':'def public_goal_motivation_work_priority_integrations(' in module,
        'module_public_reviews':'def public_goal_motivation_work_priority_integration_reviews(' in module,
        'module_snapshot':'def _sanitized_motivation_snapshot(' in module,
        'module_priority_basis':'def _priority_basis(' in module,
        'module_lesson_basis':'def _lesson_basis(' in module,
        'module_no_goal_mutation':'"goal_state_mutation_authorized": False' in module,
        'module_no_motivation_mutation':'"motivation_state_mutation_authorized": False' in module,
        'module_no_priority_mutation':'"priority_mutation_authorized": False' in module,
        'module_no_cognition':'"cognition_write_authorized": False' in module,
        'module_no_execution':'"integration_is_execution_authority": False' in module,
        'chat_route':'process_goal_motivation_work_priority_integration_control' in chat,
        'api_assessments':'goal-motivation-work-priority-integrations' in api,
        'api_reviews':'goal-motivation-work-priority-integration-reviews' in api,
        'api_checkpoint':CHECKPOINT_ID in api,
        'cli_assessments':'"goal-motivation-work-priority-integrations"' in cli,
        'cli_reviews':'"goal-motivation-work-priority-integration-reviews"' in cli,
        'cli_checkpoint':f'"{CHECKPOINT_ID}"' in cli,
        'metadata_version':progress.get('checkpoint_retained') is True,
        'metadata_milestone':progress.get('coherent') is True,
        'metadata_next':progress.get('started') is True,
        'retained_v1235_marker':'v1235.9 Evidence-Backed Lessons from Development Outcomes' in metadata,
        'roadmap_current':'v1236.9' in roadmap,
        'roadmap_next':'v1237' in roadmap,
        'history_current':'v1236.9' in history,
        'release_stages_registered':expected_stages.issubset(_quick_stage_names(verifier)),
        'release_commands_registered':all(stage in verifier for stage in expected_stages),
        'docs_present':all((source/name).is_file() for name in expected_docs),
        'registry_present':bool(descriptor),
        'registry_version':descriptor.get('contract_version')==CONTRACT_VERSION,
        'registry_read_only':descriptor.get('read_only') is True,
        'registry_no_inputs':descriptor.get('required_input_count')==0,
    }
    for key,expected in AUTHORITY_FLAGS.items():
        checks[f'authority_{key}']=contract.get(key) is expected
    after,after_count=_tree_signature(source)
    unchanged=before==after and before_count==after_count
    checks['source_signature_unchanged']=unchanged
    passed=sum(bool(value) for value in checks.values()); total=len(checks); ok=passed==total
    return {
        'ok':ok,
        'status':'goal_motivation_work_priority_integration_checkpoint_ready' if ok else 'goal_motivation_work_priority_integration_checkpoint_blocked',
        'checkpoint_id':CHECKPOINT_ID,
        'contract_version':CONTRACT_VERSION,
        'retained_contract_version':RETAINED_CONTRACT_VERSION,
        'milestone_name':MILESTONE_NAME,
        'roadmap_path':ROADMAP_PATH,
        'checks':checks,'passed':passed,'total':total,
        'read_only':True,'content_free':True,'project_scoped':True,
        'source_signature_before':before,'source_signature_after':after,'source_signature_unchanged':unchanged,
        'source_file_count_before':before_count,'source_file_count_after':after_count,
        'runtime_data_read':False,'runtime_data_written':False,
        'provider_contacted':False,'commands_executed':False,'tests_executed':False,
        'project_modified':False,'goals_modified':False,'motivations_modified':False,
        'queue_modified':False,'schedule_modified':False,'cognition_written':False,
        'source_modified':False,'authority_granted':False,
        **AUTHORITY_FLAGS,
    }
