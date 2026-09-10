from __future__ import annotations

"""Read-only v1246.9 Initiative and Proposal Pacing checkpoint."""

import ast
import hashlib
from pathlib import Path

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from initiative_proposal_pacing import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    build_initiative_proposal_pacing_contract,
    initiative_pacing_dashboard_record,
    initiative_proposal_pacing_registry,
    render_initiative_pacing_dashboard_html,
)

CONTRACT_VERSION = "v1246.9"
CHECKPOINT_ID = "initiative-proposal-pacing-checkpoint"


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


def build_initiative_proposal_pacing_checkpoint(*, source_root=None, runtime_root=None) -> dict:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,count_before=_signature(source)
    contract=build_initiative_proposal_pacing_contract()
    registry=initiative_proposal_pacing_registry()
    dashboard=initiative_pacing_dashboard_record()
    page=render_initiative_pacing_dashboard_html()
    descriptor=next((row for row in inspect_checkpoint_registry(source_root=source).get("checkpoints",[]) if row.get("checkpoint_id")==CHECKPOINT_ID),{})
    names=(
        "conscious_agent/release_metadata.py","README_NEXT_STEPS.md","README_RELEASE_HISTORY.md",
        "tools/release_verify.py","conscious_agent/api_server.py","eidolon.py",
        "conscious_agent/ordinary_chat_development_campaign.py","conscious_agent/dashboard.py",
        "conscious_agent/unified_operator_dashboard.py",
    )
    files={name:(source/name).read_text(encoding="utf-8") for name in names}
    stages={
        "v1246.2-initiative-proposal-pacing-foundations",
        "v1246.5-initiative-proposal-pacing-operator-review",
        "v1246.8-initiative-proposal-pacing-adversarial-reliability",
        "v1246.9-initiative-proposal-pacing-checkpoint",
    }
    docs=(
        "archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1246_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1246_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1246_6_8.md",
        "archive/docs/legacy_dependencies/validation/Eidolon_v1246_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1246_9.md",
    )
    progress=retained_checkpoint_progress(source,checkpoint_version="1246.9",successor_version="1247.0",successor_surface="conscious_agent/privacy_security_secret_management_audit.py")
    checks={
        "contract_ok":contract.get("ok") is True,
        "registry_ok":registry.get("ok") is True,
        "registry_inspection_only":registry.get("inspection_only") is True,
        "eight_states":contract.get("eight_pacing_classifications") is True and len(registry.get("pacing_classifications") or [])==8,
        "proposal_factors":contract.get("proposal_eligibility_and_novelty") is True and contract.get("urgency_confidence_and_attention_cost") is True,
        "cooldown_duplicates":contract.get("cooldowns_and_duplicate_suppression") is True,
        "dependencies":contract.get("unresolved_dependency_awareness") is True,
        "one_question":contract.get("one_bounded_question_maximum") is True,
        "operator_review":contract.get("operator_specific_review") is True,
        "dismissal_resurface":contract.get("dismissed_topic_requires_change_or_condition") is True and contract.get("resurfacing_requires_exact_review_and_meaningful_change") is True,
        "silence_valid":contract.get("deliberate_silence_is_valid") is True,
        "no_auto_surface":contract.get("no_automatic_notification_or_surface") is True,
        "no_global_preferences":contract.get("no_global_preference_mutation") is True,
        "dashboard_read_only":dashboard.get("read_only") is True and dashboard.get("get_only") is True,
        "dashboard_page":"Initiative and Proposal Pacing" in page and "GET-only inspection" in page,
        "metadata":progress.get("checkpoint_retained") is True and progress.get("coherent") is True and progress.get("started") is True,
        "readmes":"v1246.9" in files["README_NEXT_STEPS.md"] and "v1246.9 Initiative and Proposal Pacing" in files["README_RELEASE_HISTORY.md"],
        "chat":"process_initiative_pacing_control" in files["conscious_agent/ordinary_chat_development_campaign.py"],
        "api":all(token in files["conscious_agent/api_server.py"] for token in ("initiative-proposal-pacing-registry","initiative-proposal-candidates","initiative-pacing-decisions","initiative-pacing-reviews",CHECKPOINT_ID)),
        "cli":all(f'"{token}"' in files["eidolon.py"] for token in ("initiative-proposal-pacing-registry","initiative-proposal-candidates","initiative-pacing-decisions","initiative-pacing-reviews",CHECKPOINT_ID)),
        "dashboard_routes":"/initiative-pacing" in files["conscious_agent/dashboard.py"] and "/api/initiative-pacing" in files["conscious_agent/dashboard.py"],
        "unified_dashboard_integration":"initiative-pacing-decisions" in files["conscious_agent/unified_operator_dashboard.py"],
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
        "ok":ok,"status":"initiative_proposal_pacing_checkpoint_ready" if ok else "initiative_proposal_pacing_checkpoint_blocked",
        "checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"retained_contract_version":RETAINED_CONTRACT_VERSION,
        "milestone_name":MILESTONE_NAME,"roadmap_path":ROADMAP_PATH,"passed":passed,"total":total,"checks":checks,
        "source_signature_before":before,"source_signature_after":after,"source_signature_unchanged":before==after,
        "source_file_count_before":count_before,"source_file_count_after":count_after,
        "read_only":True,"content_free":True,"runtime_data_read":False,"runtime_data_written":False,
        "provider_contacted":False,"commands_executed":False,"tests_executed":False,"project_modified":False,
        "source_modified":False,"cognition_written":False,"authority_granted":False,**AUTHORITY_FLAGS,
    }
