from __future__ import annotations

"""Read-only v1249.9 Feature Freeze and Final Hardening checkpoint."""

import ast
import hashlib
from pathlib import Path

from checkpoint_registry import inspect_checkpoint_registry
from feature_freeze_final_hardening import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    build_feature_freeze_manifest,
    build_final_hardening_report,
    feature_freeze_dashboard_record,
    feature_freeze_registry,
    render_feature_freeze_dashboard_html,
)

CONTRACT_VERSION = "v1249.9"
CHECKPOINT_ID = "feature-freeze-final-hardening-checkpoint"


def _signature(root: Path) -> tuple[str, int]:
    rows=[]; count=0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in {"data","__pycache__",".git"} for part in path.relative_to(root).parts):
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}"); count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(
                isinstance(t,ast.Name) and t.id in {"QUICK_STAGE_NAMES","LEGACY_QUICK_STAGE_NAMES"}
                for t in node.targets
            ):
                names.update(ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_feature_freeze_final_hardening_checkpoint(*, source_root=None, runtime_root=None) -> dict:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,count_before=_signature(source)
    registry=feature_freeze_registry(); manifest=build_feature_freeze_manifest(source_root=source); report=build_final_hardening_report(source_root=source)
    dashboard=feature_freeze_dashboard_record(); page=render_feature_freeze_dashboard_html()
    descriptor=next((x for x in inspect_checkpoint_registry(source_root=source).get("checkpoints",[]) if x.get("checkpoint_id")==CHECKPOINT_ID),{})
    names=("conscious_agent/release_metadata.py","README_NEXT_STEPS.md","README_RELEASE_HISTORY.md","tools/release_verify.py","conscious_agent/api_server.py","eidolon.py","conscious_agent/ordinary_chat_development_campaign.py","conscious_agent/dashboard.py","conscious_agent/unified_operator_dashboard.py")
    files={name:(source/name).read_text(encoding="utf-8") for name in names}
    stages={"v1249.2-feature-freeze-final-hardening-foundations","v1249.5-feature-freeze-review-and-interface-stability","v1249.8-feature-freeze-adversarial-reliability","v1249.9-feature-freeze-final-hardening-checkpoint"}
    docs=("archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1249_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1249_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1249_6_8.md","archive/docs/legacy_dependencies/validation/Eidolon_v1249_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1249_9.md")
    checks={
        "registry_ok":registry.get("ok") is True and registry.get("domain_count")==12,
        "freeze_active":registry.get("feature_freeze_active") is True and registry.get("new_capability_work_blocked") is True,
        "manifest_ok":manifest.get("ok") is True and manifest.get("public_interfaces_frozen") is True,
        "hardening_ok":report.get("ok") is True and report.get("passed")==report.get("total"),
        "syntax_clean":report.get("syntax_failure_count")==0,
        "source_only_clean":report.get("forbidden_source_entry_count")==0,
        "retained_lineage":report.get("retained_checkpoint_present_count")==report.get("retained_checkpoint_required_count")==19,
        "dashboard":dashboard.get("get_only") is True and MILESTONE_NAME in page,
        "metadata":'WORKING_SOURCE_VERSION = "1249.9"' in files["conscious_agent/release_metadata.py"] and "v1249.9 Feature Freeze and Final Hardening Checkpoint" in files["conscious_agent/release_metadata.py"] and "v1250.0-v1250.2 Desktop Codex Integrated Beta Milestone Foundations" in files["conscious_agent/release_metadata.py"],
        "readmes":"v1249.9" in files["README_NEXT_STEPS.md"] and "v1249.9 Feature Freeze and Final Hardening" in files["README_RELEASE_HISTORY.md"],
        "chat":"process_feature_freeze_final_hardening_control" in files["conscious_agent/ordinary_chat_development_campaign.py"],
        "api":all(token in files["conscious_agent/api_server.py"] for token in ("feature-freeze-registry","feature-freeze-manifest","feature-freeze-final-hardening-report",CHECKPOINT_ID)),
        "cli":all(f'"{token}"' in files["eidolon.py"] for token in ("feature-freeze-registry","feature-freeze-manifest","feature-freeze-final-hardening-report",CHECKPOINT_ID)),
        "dashboard_routes":"/feature-freeze-final-hardening" in files["conscious_agent/dashboard.py"],
        "unified_dashboard":"feature-freeze-final-hardening" in files["conscious_agent/unified_operator_dashboard.py"],
        "release_stages":stages.issubset(_quick_stage_names(files["tools/release_verify.py"])),
        "release_commands":all(stage in files["tools/release_verify.py"] for stage in stages),
        "docs":all((source/name).is_file() for name in docs),
        "registry_present":bool(descriptor),
        "registry_version":descriptor.get("contract_version")==CONTRACT_VERSION,
        "registry_read_only":descriptor.get("read_only") is True,
        "registry_no_inputs":descriptor.get("required_input_count")==0,
    }
    for key,expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"]=registry.get(key) is expected and manifest.get(key) is expected and report.get(key) is expected and dashboard.get(key) is expected
    after,count_after=_signature(source); checks["source_unchanged"]=before==after and count_before==count_after
    passed=sum(map(bool,checks.values())); total=len(checks); ok=passed==total
    return {"ok":ok,"status":"feature_freeze_final_hardening_checkpoint_ready" if ok else "feature_freeze_final_hardening_checkpoint_blocked","checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"retained_contract_version":RETAINED_CONTRACT_VERSION,"milestone_name":MILESTONE_NAME,"roadmap_path":ROADMAP_PATH,"passed":passed,"total":total,"checks":checks,"source_signature_before":before,"source_signature_after":after,"source_signature_unchanged":before==after,"source_file_count_before":count_before,"source_file_count_after":count_after,"read_only":True,"content_free":True,"runtime_data_read":False,"runtime_data_written":False,"source_modified":False,"authority_granted":False,**AUTHORITY_FLAGS}
