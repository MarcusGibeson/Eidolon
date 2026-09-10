from __future__ import annotations
"""Read-only v1240.9 Integrated Developer Beta checkpoint."""
import ast, hashlib, json
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from integrated_developer_beta import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, MILESTONE_NAME, ROADMAP_PATH, RETAINED_CHECKPOINTS, build_integrated_developer_beta_contract, scenario_registry
CONTRACT_VERSION="v1240.9"
CHECKPOINT_ID="integrated-developer-beta-checkpoint"

def _sig(root: Path):
    rows=[]; count=0
    for p in sorted(root.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}"); count+=1
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),count

def _quick(text):
    names=set()
    try:
        t=ast.parse(text)
        for n in t.body:
            if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in {'QUICK_STAGE_NAMES','LEGACY_QUICK_STAGE_NAMES'} for x in n.targets):
                names.update(ast.literal_eval(n.value))
    except Exception: pass
    return names

def build_integrated_developer_beta_checkpoint(*,source_root: str|Path|None=None,runtime_root=None)->dict[str,Any]:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); before,count_before=_sig(source)
    contract=build_integrated_developer_beta_contract(source_root=source); registry=scenario_registry()
    descriptors=inspect_checkpoint_registry(source_root=source); desc=next((x for x in descriptors.get('checkpoints',[]) if x.get('checkpoint_id')==CHECKPOINT_ID),{})
    files={name:(source/name).read_text(encoding='utf-8') for name in ('conscious_agent/release_metadata.py','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','tools/release_verify.py','conscious_agent/api_server.py','eidolon.py','conscious_agent/ordinary_chat_development_campaign.py')}
    stages={"v1240.2-integrated-developer-beta-foundations","v1240.5-integrated-developer-beta-end-to-end-scenarios","v1240.8-integrated-developer-beta-adversarial-reliability","v1240.9-integrated-developer-beta-checkpoint"}
    docs=('archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1240_0_2.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1240_3_5.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1240_6_8.md','archive/docs/legacy_dependencies/validation/Eidolon_v1240_9_FINAL_VALIDATION.md','archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1240_9.md')
    checks={
      'contract_ok':contract.get('ok') is True,'retained_version':contract.get('contract_version')==RETAINED_CONTRACT_VERSION,'stage_count':contract.get('retained_stage_count')==10,'scenario_count':registry.get('scenario_count')==10,'versions_match':contract.get('retained_versions_match') is True,'retained_pass':contract.get('retained_checkpoints_pass') is True,'order':contract.get('complete_stage_order') is True,
      'metadata_version':'WORKING_SOURCE_VERSION = "1240.9"' in files['conscious_agent/release_metadata.py'],'metadata_milestone':'v1240.9 Integrated Developer Beta Checkpoint' in files['conscious_agent/release_metadata.py'],'metadata_next':'v1241.0-v1241.2 Unified Operator Dashboard Foundations' in files['conscious_agent/release_metadata.py'],'roadmap_current':'v1240.9' in files['README_NEXT_STEPS.md'],'history_current':'v1240.9' in files['README_RELEASE_HISTORY.md'],
      'chat_route':'process_integrated_developer_beta_control' in files['conscious_agent/ordinary_chat_development_campaign.py'],'api_registry':'integrated-developer-beta-scenario-registry' in files['conscious_agent/api_server.py'],'api_benchmark':'integrated-developer-beta-benchmark' in files['conscious_agent/api_server.py'],'api_checkpoint':CHECKPOINT_ID in files['conscious_agent/api_server.py'],'cli_registry':'"integrated-developer-beta-scenario-registry"' in files['eidolon.py'],'cli_benchmark':'"integrated-developer-beta-benchmark"' in files['eidolon.py'],'cli_checkpoint':f'"{CHECKPOINT_ID}"' in files['eidolon.py'],'release_stages':stages.issubset(_quick(files['tools/release_verify.py'])),'release_commands':all(x in files['tools/release_verify.py'] for x in stages),'docs':all((source/x).is_file() for x in docs),'registry_present':bool(desc),'registry_version':desc.get('contract_version')==CONTRACT_VERSION,'registry_read_only':desc.get('read_only') is True,'registry_no_inputs':desc.get('required_input_count')==0,
      'historical_receipts':contract.get('historical_receipts_remain_immutable') is True,'missing_never_passes':contract.get('missing_timeout_or_incomplete_evidence_never_passes') is True,'adversarial_fail_closed':contract.get('adversarial_fail_closed') is True,'sandbox_truth':contract.get('os_level_sandbox_not_claimed') is True,
    }
    for k,v in AUTHORITY_FLAGS.items(): checks['authority_'+k]=contract.get(k) is v
    after,count_after=_sig(source); checks['source_unchanged']=before==after and count_before==count_after
    passed=sum(bool(x) for x in checks.values()); total=len(checks); ok=passed==total
    return {'ok':ok,'status':'integrated_developer_beta_checkpoint_ready' if ok else 'integrated_developer_beta_checkpoint_blocked','checkpoint_id':CHECKPOINT_ID,'contract_version':CONTRACT_VERSION,'retained_contract_version':RETAINED_CONTRACT_VERSION,'milestone_name':MILESTONE_NAME,'roadmap_path':ROADMAP_PATH,'passed':passed,'total':total,'checks':checks,'source_signature_before':before,'source_signature_after':after,'source_signature_unchanged':before==after,'source_file_count_before':count_before,'source_file_count_after':count_after,'read_only':True,'content_free':True,'runtime_data_read':False,'runtime_data_written':False,'provider_contacted':False,'commands_executed':False,'tests_executed':False,'project_modified':False,'source_modified':False,'cognition_written':False,'authority_granted':False,**AUTHORITY_FLAGS}
