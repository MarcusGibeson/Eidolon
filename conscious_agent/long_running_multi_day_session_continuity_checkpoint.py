from __future__ import annotations

"""Read-only v1244.9 Long-Running and Multi-Day Session Continuity checkpoint."""

import ast
import hashlib
from pathlib import Path

from checkpoint_registry import inspect_checkpoint_registry
from long_running_multi_day_session_continuity import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    build_long_running_session_continuity_contract,
    long_running_session_continuity_registry,
    render_session_continuity_dashboard_html,
    session_continuity_dashboard_record,
)

CONTRACT_VERSION = "v1244.9"
CHECKPOINT_ID = "long-running-multi-day-session-continuity-checkpoint"


def _signature(root: Path) -> tuple[str, int]:
    rows=[]; count=0
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
            count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id=="QUICK_STAGE_NAMES" for target in node.targets):
                return set(ast.literal_eval(node.value))
    except Exception:
        pass
    return set()


def build_long_running_multi_day_session_continuity_checkpoint(*, source_root=None, runtime_root=None) -> dict:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,count_before=_signature(source)
    contract=build_long_running_session_continuity_contract()
    registry=long_running_session_continuity_registry()
    dashboard=session_continuity_dashboard_record()
    page=render_session_continuity_dashboard_html()
    descriptor=next((row for row in inspect_checkpoint_registry(source_root=source).get("checkpoints",[]) if row.get("checkpoint_id")==CHECKPOINT_ID),{})
    names=(
        "conscious_agent/release_metadata.py","README_NEXT_STEPS.md","README_RELEASE_HISTORY.md",
        "tools/release_verify.py","conscious_agent/api_server.py","eidolon.py",
        "conscious_agent/ordinary_chat_development_campaign.py","conscious_agent/dashboard.py",
        "conscious_agent/unified_operator_dashboard.py",
    )
    files={name:(source/name).read_text(encoding="utf-8") for name in names}
    stages={
        "v1244.2-long-running-multi-day-session-continuity-foundations",
        "v1244.5-long-running-multi-day-session-continuity-operator-workflows",
        "v1244.8-long-running-multi-day-session-continuity-adversarial-reliability",
        "v1244.9-long-running-multi-day-session-continuity-checkpoint",
    }
    docs=(
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1244_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1244_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1244_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1244_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1244_9.md",
    )
    checks={
        "contract_ok":contract.get("ok") is True,
        "registry_ok":registry.get("ok") is True,
        "registry_inspection_only":registry.get("inspection_only") is True,
        "durable_epochs":contract.get("durable_session_epochs") is True,
        "progress_lineage":contract.get("progress_checkpoint_lineage") is True,
        "manifest_generations":contract.get("sequential_manifest_generations_required") is True,
        "freshness_enforced":contract.get("freshness_windows_enforced") is True,
        "clock_drift_closed":contract.get("clock_drift_fails_closed") is True,
        "changed_plan_review":contract.get("changed_project_or_plan_requires_revision_review") is True,
        "lost_workspace_recovery":contract.get("lost_workspace_requires_recovery") is True,
        "provider_tool_revalidation":contract.get("provider_and_tool_state_revalidated") is True,
        "restart_replay":contract.get("duplicate_restart_and_replay_deterministic") is True,
        "cross_session_rejected":contract.get("cross_project_and_cross_session_confusion_rejected") is True,
        "old_authority_not_reused":contract.get("old_authority_never_reused") is True,
        "fresh_resume_authority":contract.get("resume_requires_fresh_exact_separate_authority") is True,
        "review_interpretation_only":contract.get("operator_review_is_interpretation_only") is True,
        "dashboard_read_only":dashboard.get("read_only") is True and dashboard.get("get_only") is True,
        "dashboard_no_resume":dashboard.get("resume_authorized") is False,
        "dashboard_page":"Long-Running and Multi-Day Session Continuity" in page and "GET-only inspection" in page,
        "metadata":'WORKING_SOURCE_VERSION = "1244.9"' in files["conscious_agent/release_metadata.py"] and "v1244.9 Long-Running and Multi-Day Session Continuity Checkpoint" in files["conscious_agent/release_metadata.py"] and "v1245.0-v1245.2 Cross-Session Project Understanding Foundations" in files["conscious_agent/release_metadata.py"],
        "readmes":"v1244.9" in files["README_NEXT_STEPS.md"] and "v1244.9 Long-Running and Multi-Day Session Continuity" in files["README_RELEASE_HISTORY.md"],
        "chat":"process_session_continuity_control" in files["conscious_agent/ordinary_chat_development_campaign.py"],
        "api":all(token in files["conscious_agent/api_server.py"] for token in ("long-running-session-continuity-registry","session-continuity-progress","session-continuity-manifests","session-continuity-assessments","session-continuity-reviews",CHECKPOINT_ID)),
        "cli":all(f'"{token}"' in files["eidolon.py"] for token in ("long-running-session-continuity-registry","session-continuity-progress","session-continuity-manifests","session-continuity-assessments","session-continuity-reviews",CHECKPOINT_ID)),
        "dashboard_routes":"/session-continuity" in files["conscious_agent/dashboard.py"] and "/api/session-continuity" in files["conscious_agent/dashboard.py"],
        "unified_dashboard_integration":"session-continuity-assessments" in files["conscious_agent/unified_operator_dashboard.py"],
        "release_stages":stages.issubset(_quick_stage_names(files["tools/release_verify.py"])),
        "release_commands":all(stage in files["tools/release_verify.py"] for stage in stages),
        "docs":all((source/name).is_file() for name in docs),
        "registry_present":bool(descriptor),
        "registry_version":descriptor.get("contract_version")==CONTRACT_VERSION,
        "registry_read_only":descriptor.get("read_only") is True,
        "registry_no_inputs":descriptor.get("required_input_count")==0,
    }
    for key,expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"]=contract.get(key) is expected and registry.get(key) is expected and dashboard.get(key) is expected
    after,count_after=_signature(source)
    checks["source_unchanged"]=before==after and count_before==count_after
    passed=sum(map(bool,checks.values())); total=len(checks); ok=passed==total
    return {
        "ok":ok,"status":"long_running_multi_day_session_continuity_checkpoint_ready" if ok else "long_running_multi_day_session_continuity_checkpoint_blocked",
        "checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"retained_contract_version":RETAINED_CONTRACT_VERSION,
        "milestone_name":MILESTONE_NAME,"roadmap_path":ROADMAP_PATH,"passed":passed,"total":total,"checks":checks,
        "source_signature_before":before,"source_signature_after":after,"source_signature_unchanged":before==after,
        "source_file_count_before":count_before,"source_file_count_after":count_after,
        "read_only":True,"content_free":True,"runtime_data_read":False,"runtime_data_written":False,
        "provider_contacted":False,"commands_executed":False,"tests_executed":False,"project_modified":False,
        "source_modified":False,"cognition_written":False,"authority_granted":False,**AUTHORITY_FLAGS,
    }
