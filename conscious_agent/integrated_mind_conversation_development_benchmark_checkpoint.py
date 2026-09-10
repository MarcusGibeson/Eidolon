from __future__ import annotations

"""Read-only v1248.9 Integrated Mind, Conversation, and Development checkpoint."""

import ast
import hashlib
from pathlib import Path

from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from integrated_mind_conversation_development_benchmark import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    benchmark_dashboard_record,
    benchmark_registry,
    build_integrated_mind_conversation_development_contract,
    render_benchmark_dashboard_html,
)

CONTRACT_VERSION = "v1248.9"
CHECKPOINT_ID = "integrated-mind-conversation-development-benchmark-checkpoint"


def _signature(root: Path) -> tuple[str, int]:
    rows=[]; count=0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in {"data","__pycache__",".git"} for part in path.relative_to(root).parts):
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}"); count+=1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _quick_stage_names(text: str) -> set[str]:
    names: set[str] = set()
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {"QUICK_STAGE_NAMES","LEGACY_QUICK_STAGE_NAMES"} for t in node.targets):
                names.update(ast.literal_eval(node.value))
    except Exception:
        pass
    return names


def build_integrated_mind_conversation_development_benchmark_checkpoint(*, source_root=None, runtime_root=None) -> dict:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before,count_before=_signature(source)
    registry=benchmark_registry()
    contract=build_integrated_mind_conversation_development_contract(source_root=source,include_retained=True)
    dashboard=benchmark_dashboard_record(); page=render_benchmark_dashboard_html()
    descriptor=next((x for x in inspect_checkpoint_registry(source_root=source).get("checkpoints",[]) if x.get("checkpoint_id")==CHECKPOINT_ID),{})
    names=("conscious_agent/release_metadata.py","README_NEXT_STEPS.md","README_RELEASE_HISTORY.md","tools/release_verify.py","conscious_agent/api_server.py","eidolon.py","conscious_agent/ordinary_chat_development_campaign.py","conscious_agent/dashboard.py","conscious_agent/unified_operator_dashboard.py","conscious_agent/natural_language_action_routing.py")
    files={name:(source/name).read_text(encoding="utf-8") for name in names}
    stages={"v1248.2-integrated-mind-conversation-development-benchmark-foundations","v1248.5-integrated-mind-conversation-development-behavioral-scenarios","v1248.8-integrated-mind-conversation-development-adversarial-reliability","v1248.9-integrated-mind-conversation-development-benchmark-checkpoint"}
    docs=("archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1248_0_2.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1248_3_5.md","archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1248_6_8.md","archive/docs/legacy_dependencies/validation/Eidolon_v1248_9_FINAL_VALIDATION.md","archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1248_9.md")
    progress=retained_checkpoint_progress(source,checkpoint_version="1248.9",successor_version="1249.0",successor_surface="conscious_agent/feature_freeze_final_hardening.py")
    checks={
        "registry_ok":registry.get("ok") is True,
        "twelve_scenarios":registry.get("scenario_count")==12,
        "ordinary_chat_path_required":registry.get("ordinary_chat_path_required") is True and registry.get("routing_metadata_alone_is_insufficient") is True,
        "contract_ok":contract.get("ok") is True,
        "ordinary_chat_all_pass":contract.get("ordinary_chat_passed")==contract.get("ordinary_chat_total")==12,
        "mixed_turn_distinguished":contract.get("mixed_conversation_action_distinguished") is True and contract.get("single_proposal_for_mixed_turn") is True,
        "non_actions_inert":contract.get("conversation_wish_hypothetical_quote_suggestion_inert") is True,
        "retained_contracts":contract.get("retained_contracts_included") is True and contract.get("retained_contract_count")==7 and contract.get("retained_contracts_pass") is True,
        "privacy_and_authority":contract.get("privacy_preserved_across_systems") is True and contract.get("authority_granted") is False,
        "dashboard":dashboard.get("get_only") is True and MILESTONE_NAME in page,
        "metadata":progress.get("checkpoint_retained") is True and progress.get("coherent") is True and progress.get("started") is True,
        "readmes":"v1248.9" in files["README_NEXT_STEPS.md"] and "v1248.9 Integrated Mind, Conversation, and Development Benchmark" in files["README_RELEASE_HISTORY.md"],
        "mixed_router":"mixed_conversation_and_action" in files["conscious_agent/natural_language_action_routing.py"],
        "chat":"process_integrated_mind_conversation_development_control" in files["conscious_agent/ordinary_chat_development_campaign.py"],
        "api":all(token in files["conscious_agent/api_server.py"] for token in ("integrated-mind-conversation-development-benchmark-registry","integrated-mind-conversation-development-benchmark",CHECKPOINT_ID)),
        "cli":all(f'"{token}"' in files["eidolon.py"] for token in ("integrated-mind-conversation-development-benchmark-registry","integrated-mind-conversation-development-benchmark",CHECKPOINT_ID)),
        "dashboard_routes":"/integrated-mind-conversation-development-benchmark" in files["conscious_agent/dashboard.py"],
        "unified_dashboard":"integrated-mind-conversation-development-benchmark" in files["conscious_agent/unified_operator_dashboard.py"],
        "release_stages":stages.issubset(_quick_stage_names(files["tools/release_verify.py"])),
        "release_commands":all(stage in files["tools/release_verify.py"] for stage in stages),
        "docs":all((source/name).is_file() for name in docs),
        "registry_present":bool(descriptor),
        "registry_version":descriptor.get("contract_version")==CONTRACT_VERSION,
        "registry_read_only":descriptor.get("read_only") is True,
        "registry_no_inputs":descriptor.get("required_input_count")==0,
    }
    for key,expected in AUTHORITY_FLAGS.items():
        checks[f"authority_{key}"]=registry.get(key) is expected and contract.get(key) is expected and dashboard.get(key) is expected
    after,count_after=_signature(source); checks["source_unchanged"]=before==after and count_before==count_after
    passed=sum(map(bool,checks.values())); total=len(checks); ok=passed==total
    return {"ok":ok,"status":"integrated_mind_conversation_development_benchmark_checkpoint_ready" if ok else "integrated_mind_conversation_development_benchmark_checkpoint_blocked","checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"retained_contract_version":RETAINED_CONTRACT_VERSION,"milestone_name":MILESTONE_NAME,"roadmap_path":ROADMAP_PATH,"passed":passed,"total":total,"checks":checks,"source_signature_before":before,"source_signature_after":after,"source_signature_unchanged":before==after,"source_file_count_before":count_before,"source_file_count_after":count_after,"read_only":True,"content_free":True,"runtime_data_read":False,"runtime_data_written":False,"source_modified":False,"authority_granted":False,**AUTHORITY_FLAGS}
