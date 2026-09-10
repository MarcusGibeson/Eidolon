from __future__ import annotations

"""Read-only v1245.9 Cross-Session Project Understanding checkpoint."""

import ast
import hashlib
from pathlib import Path

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from cross_session_project_understanding import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    build_cross_session_project_understanding_contract,
    cross_session_project_understanding_registry,
    project_understanding_dashboard_record,
    render_project_understanding_dashboard_html,
)

CONTRACT_VERSION = "v1245.9"
CHECKPOINT_ID = "cross-session-project-understanding-checkpoint"


def _signature(root: Path) -> tuple[str, int]:
    rows=[]; count=0
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
            count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {"QUICK_STAGE_NAMES","LEGACY_QUICK_STAGE_NAMES"} for target in node.targets):
                names.update(ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_cross_session_project_understanding_checkpoint(*, source_root=None, runtime_root=None) -> dict:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,count_before=_signature(source)
    contract=build_cross_session_project_understanding_contract()
    registry=cross_session_project_understanding_registry()
    dashboard=project_understanding_dashboard_record()
    page=render_project_understanding_dashboard_html()
    descriptor=next((row for row in inspect_checkpoint_registry(source_root=source).get("checkpoints",[]) if row.get("checkpoint_id")==CHECKPOINT_ID),{})
    names=(
        "conscious_agent/release_metadata.py","README_NEXT_STEPS.md","README_RELEASE_HISTORY.md",
        "tools/release_verify.py","conscious_agent/api_server.py","eidolon.py",
        "conscious_agent/ordinary_chat_development_campaign.py","conscious_agent/dashboard.py",
        "conscious_agent/unified_operator_dashboard.py",
    )
    files={name:(source/name).read_text(encoding="utf-8") for name in names}
    stages={
        "v1245.2-cross-session-project-understanding-foundations",
        "v1245.5-cross-session-project-understanding-reconciliation-review",
        "v1245.8-cross-session-project-understanding-adversarial-reliability",
        "v1245.9-cross-session-project-understanding-checkpoint",
    }
    docs=(
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1245_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1245_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1245_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1245_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1245_9.md",
    )
    progress=retained_checkpoint_progress(source,checkpoint_version="1245.9",successor_version="1246.0",successor_surface="conscious_agent/initiative_proposal_pacing.py")
    checks={
        "contract_ok":contract.get("ok") is True,
        "registry_ok":registry.get("ok") is True,
        "registry_inspection_only":registry.get("inspection_only") is True,
        "durable_summaries":contract.get("durable_project_summaries") is True,
        "architecture_relationships":contract.get("architecture_components_and_relationships") is True,
        "confidence_freshness":contract.get("confidence_provenance_and_freshness") is True,
        "immutable_lineage":contract.get("immutable_revision_lineage") is True,
        "cross_session_reconciliation":contract.get("cross_session_reconciliation") is True,
        "seven_states":contract.get("seven_classification_states") is True and len(registry.get("classifications") or [])==7,
        "identity_bound":contract.get("project_identity_and_repository_fingerprint_bound") is True,
        "copied_repo_closed":contract.get("copied_repository_confusion_fails_closed") is True,
        "partial_scan_unverified":contract.get("partial_scan_preserves_unverified_state") is True,
        "contradictions_preserved":contract.get("contradictions_remain_unresolved") is True,
        "accepted_review_no_snapshot":contract.get("accepted_review_does_not_create_snapshot") is True,
        "revision_exact_review":contract.get("revised_snapshot_requires_exact_accepted_review") is True,
        "memory_not_truth":contract.get("remembered_state_never_current_without_revalidation") is True,
        "review_interpretation_only":contract.get("operator_review_is_interpretation_only") is True,
        "dashboard_read_only":dashboard.get("read_only") is True and dashboard.get("get_only") is True,
        "dashboard_no_mutation":dashboard.get("project_mutation_authorized") is False and dashboard.get("cognition_write_authorized") is False,
        "dashboard_page":"Cross-Session Project Understanding" in page and "GET-only inspection" in page,
        "metadata":progress.get("checkpoint_retained") is True and progress.get("coherent") is True and progress.get("started") is True,
        "readmes":"v1245.9" in files["README_NEXT_STEPS.md"] and "v1245.9 Cross-Session Project Understanding" in files["README_RELEASE_HISTORY.md"],
        "chat":"process_project_understanding_control" in files["conscious_agent/ordinary_chat_development_campaign.py"],
        "api":all(token in files["conscious_agent/api_server.py"] for token in ("cross-session-project-understanding-registry","project-understanding-snapshots","project-understanding-reconciliations","project-understanding-reviews",CHECKPOINT_ID)),
        "cli":all(f'"{token}"' in files["eidolon.py"] for token in ("cross-session-project-understanding-registry","project-understanding-snapshots","project-understanding-reconciliations","project-understanding-reviews",CHECKPOINT_ID)),
        "dashboard_routes":"/project-understanding" in files["conscious_agent/dashboard.py"] and "/api/project-understanding" in files["conscious_agent/dashboard.py"],
        "unified_dashboard_integration":"project-understanding-reconciliations" in files["conscious_agent/unified_operator_dashboard.py"],
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
        "ok":ok,"status":"cross_session_project_understanding_checkpoint_ready" if ok else "cross_session_project_understanding_checkpoint_blocked",
        "checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"retained_contract_version":RETAINED_CONTRACT_VERSION,
        "milestone_name":MILESTONE_NAME,"roadmap_path":ROADMAP_PATH,"passed":passed,"total":total,"checks":checks,
        "source_signature_before":before,"source_signature_after":after,"source_signature_unchanged":before==after,
        "source_file_count_before":count_before,"source_file_count_after":count_after,
        "read_only":True,"content_free":True,"runtime_data_read":False,"runtime_data_written":False,
        "provider_contacted":False,"commands_executed":False,"tests_executed":False,"project_modified":False,
        "source_modified":False,"cognition_written":False,"authority_granted":False,**AUTHORITY_FLAGS,
    }
