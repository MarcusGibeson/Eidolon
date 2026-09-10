from __future__ import annotations

"""Read-only v1237.9 Multi-Tool Orchestration checkpoint."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from multi_tool_orchestration import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    HANDOFF_DISPOSITIONS,
    ORCHESTRATION_STATES,
    PLAN_DISPOSITIONS,
    STEP_OUTCOMES,
    build_multi_tool_orchestration_contract,
)

CONTRACT_VERSION = "v1237.9"
CHECKPOINT_ID = "multi-tool-orchestration-checkpoint"
MILESTONE_NAME = "Multi-Tool Orchestration"
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


def build_multi_tool_orchestration_checkpoint(*, source_root: str | Path | None = None, runtime_root=None) -> dict[str, Any]:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,before_count=_tree_signature(source)
    contract=build_multi_tool_orchestration_contract()
    registry=inspect_checkpoint_registry(source_root=source)
    descriptor=next((row for row in registry.get('checkpoints',[]) if row.get('checkpoint_id')==CHECKPOINT_ID),{})
    module=(source/'conscious_agent/multi_tool_orchestration.py').read_text(encoding='utf-8')
    chat=(source/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
    api=(source/'conscious_agent/api_server.py').read_text(encoding='utf-8')
    cli=(source/'eidolon.py').read_text(encoding='utf-8')
    metadata=(source/'conscious_agent/release_metadata.py').read_text(encoding='utf-8')
    roadmap=(source/'README_NEXT_STEPS.md').read_text(encoding='utf-8')
    history=(source/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8')
    verifier=(source/'tools/release_verify.py').read_text(encoding='utf-8')
    expected_stages={
        'v1237.2-multi-tool-orchestration-foundations',
        'v1237.5-multi-tool-orchestration-operator-review',
        'v1237.8-multi-tool-orchestration-adversarial-reliability',
        'v1237.9-multi-tool-orchestration-checkpoint',
    }
    expected_docs=(
        'archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1237_0_2.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1237_3_5.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1237_6_8.md',
        'archive/docs/legacy_dependencies/validation/Eidolon_v1237_9_FINAL_VALIDATION.md','archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1237_9.md',
    )
    progress=retained_checkpoint_progress(source,checkpoint_version='1237.9',successor_version='1238.0',successor_surface='conscious_agent/broader_project_language_adapters.py')
    checks={
        'contract_ok':contract.get('ok') is True,
        'retained_contract_version':contract.get('contract_version')==RETAINED_CONTRACT_VERSION,
        'roadmap_path':contract.get('roadmap_path')==ROADMAP_PATH,
        'exact_alignment_binding':contract.get('exact_accepted_v1236_alignment_binding') is True,
        'optional_quality_binding':contract.get('optional_exact_v1234_quality_binding') is True,
        'sealed_registry':contract.get('sealed_content_free_tool_registry') is True,
        'ordered_graph':contract.get('ordered_contract_checked_step_graph') is True,
        'compatibility':contract.get('deterministic_tool_compatibility_evaluation') is True,
        'external_results':contract.get('bounded_external_step_result_recording') is True,
        'handoff_review':contract.get('operator_reviewed_handoff_proposals') is True,
        'failure_stop':contract.get('failure_routes_stop_for_operator_review') is True,
        'exact_chat':contract.get('ordinary_chat_exact_controls') is True,
        'get_only':contract.get('get_only_api_inspection') is True,
        'hardening':contract.get('restart_replay_stale_tamper_privacy_contradiction_hardening_required') is True,
        'no_plan_authority':contract.get('accepted_plan_does_not_authorize_tools') is True,
        'no_result_authority':contract.get('completed_step_does_not_authorize_next_tool') is True,
        'no_handoff_authority':contract.get('accepted_handoff_does_not_authorize_next_tool') is True,
        'no_auto':contract.get('no_automatic_continuation_or_retry') is True,
        'plan_dispositions':PLAN_DISPOSITIONS=={'accept_plan','hold','reject','request_changes'},
        'handoff_dispositions':HANDOFF_DISPOSITIONS=={'accept_handoff','hold','reject','request_changes'},
        'step_outcomes':len(STEP_OUTCOMES)==6,
        'orchestration_states':len(ORCHESTRATION_STATES)==5,
        'module_prepare':'def prepare_multi_tool_orchestration_plan(' in module,
        'module_review':'def review_multi_tool_orchestration_plan(' in module,
        'module_result':'def record_multi_tool_orchestration_step_result(' in module,
        'module_handoff':'def prepare_multi_tool_orchestration_handoff(' in module,
        'module_handoff_review':'def review_multi_tool_orchestration_handoff(' in module,
        'module_no_tool':'"tool_invocation_authorized": False' in module,
        'module_no_auto':'"automatic_continuation_authorized": False' in module,
        'module_no_retry':'"automatic_retry_authorized": False' in module,
        'chat_route':'process_multi_tool_orchestration_control' in chat,
        'api_plans':'multi-tool-orchestration-plans' in api,
        'api_results':'multi-tool-orchestration-results' in api,
        'api_handoffs':'multi-tool-orchestration-handoffs' in api,
        'api_checkpoint':CHECKPOINT_ID in api,
        'cli_plans':'"multi-tool-orchestration-plans"' in cli,
        'cli_results':'"multi-tool-orchestration-results"' in cli,
        'cli_handoffs':'"multi-tool-orchestration-handoffs"' in cli,
        'cli_checkpoint':f'"{CHECKPOINT_ID}"' in cli,
        'metadata_version':progress.get('checkpoint_retained') is True,
        'metadata_milestone':progress.get('coherent') is True,
        'metadata_next':progress.get('started') is True,
        'retained_v1236_marker':'v1236.9 Goal, Motivation, and Work-Priority Integration' in metadata,
        'roadmap_current':'v1237.9' in roadmap,
        'roadmap_next':'v1238' in roadmap,
        'history_current':'v1237.9' in history,
        'release_stages_registered':expected_stages.issubset(_quick_stage_names(verifier)),
        'release_commands_registered':all(stage in verifier for stage in expected_stages),
        'docs_present':all((source/name).is_file() for name in expected_docs),
        'registry_present':bool(descriptor),
        'registry_version':descriptor.get('contract_version')==CONTRACT_VERSION,
        'registry_read_only':descriptor.get('read_only') is True,
        'registry_no_inputs':descriptor.get('required_input_count')==0,
    }
    for key,expected in AUTHORITY_FLAGS.items(): checks[f'authority_{key}']=contract.get(key) is expected
    after,after_count=_tree_signature(source); unchanged=before==after and before_count==after_count
    checks['source_signature_unchanged']=unchanged
    passed=sum(bool(v) for v in checks.values()); total=len(checks); ok=passed==total
    return {
        'ok':ok,'status':'multi_tool_orchestration_checkpoint_ready' if ok else 'multi_tool_orchestration_checkpoint_blocked',
        'checkpoint_id':CHECKPOINT_ID,'contract_version':CONTRACT_VERSION,'retained_contract_version':RETAINED_CONTRACT_VERSION,
        'milestone_name':MILESTONE_NAME,'roadmap_path':ROADMAP_PATH,'checks':checks,'passed':passed,'total':total,
        'read_only':True,'content_free':True,'project_scoped':True,
        'source_signature_before':before,'source_signature_after':after,'source_signature_unchanged':unchanged,
        'source_file_count_before':before_count,'source_file_count_after':after_count,
        'runtime_data_read':False,'runtime_data_written':False,'provider_contacted':False,'commands_executed':False,
        'tests_executed':False,'project_modified':False,'queue_modified':False,'schedule_modified':False,
        'cognition_written':False,'source_modified':False,'authority_granted':False,**AUTHORITY_FLAGS,
    }
