from __future__ import annotations
"""Era 2 portable integration surface across project/language/test/release evidence.

This is a read-only coordinator. Established evidence owners remain authoritative;
no execution, installation, dependency change, provider contact, promotion, or
certification is granted by this projection.
"""
from pathlib import Path
from typing import Any, Iterable

from project_evidence_store import DENIED_AUTHORITY, digest
from deep_project_understanding import build_deep_repository_model, build_change_impact_reasoning
from software_language_capabilities import build_language_capability_model, analyze_build_dependency_boundary
from test_debug_performance_intelligence import build_test_intelligence_plan
from portable_release_upgrade_engineering import build_candidate_coherence

CONTRACT_VERSION = "v1699.9"


def build_broad_software_engineering_assessment(source_root: str|Path, *, changed_paths: Iterable[str]=(), candidate_version: str="", runtime_root=None) -> dict[str,Any]:
    root=Path(source_root).resolve();changed=list(changed_paths or [])
    project=build_deep_repository_model(root,runtime_root=runtime_root)['repository_model']
    impact=build_change_impact_reasoning(root,changed,runtime_root=runtime_root)['impact_analysis']
    languages=build_language_capability_model(root,runtime_root=runtime_root)['language_model']
    boundary=analyze_build_dependency_boundary(root,runtime_root=runtime_root)['boundary']
    tests=build_test_intelligence_plan(root,changed,runtime_root=runtime_root)['plan']
    candidate=build_candidate_coherence(root,candidate_version=candidate_version or 'unversioned-portable-assessment',changed_paths=changed,runtime_root=runtime_root)['candidate']
    consistent=len({str(x.get('source_manifest_digest') or '') for x in (project,impact,languages,boundary,tests)})==1
    result={
        'contract_version':CONTRACT_VERSION,'status':'broad_software_engineering_assessment_ready' if consistent else 'broad_software_engineering_manifest_conflict',
        'manifest_consistent':consistent,'workspace_digest':project.get('workspace_digest'),'source_manifest_digest':project.get('source_manifest_digest'),
        'project_model_digest':digest(project),'impact_digest':digest(impact),'language_model_digest':digest(languages),'dependency_boundary_digest':str(boundary.get('boundary_digest') or digest(boundary)),'test_plan_digest':digest(tests),'candidate_digest':digest(candidate),
        'project_issue_count':int(project.get('issue_count') or 0),'impact_uncertainty_count':int(impact.get('uncertainty_count') or 0),'language_count':int(languages.get('language_count') or 0),'selected_test_kinds':list(tests.get('selected_test_kinds') or []),'candidate_coherent':bool(candidate.get('candidate_coherent')),
        'tests_executed':False,'dependencies_installed':False,'network_contacted':False,'provider_contacted':False,'source_modified':False,'installation_performed':False,'promotion_performed':False,'certification_performed':False,'native_windows_verified':False,'action_executed':False,**DENIED_AUTHORITY,
    }
    result['assessment_digest']=digest(result)
    return {'ok':consistent and bool(candidate.get('candidate_coherent')),'status':result['status'],'assessment':result,'action_executed':False,**DENIED_AUTHORITY}


def process_broad_software_engineering_control(text:str,*,project_root=None,changed_paths=(),runtime_root=None)->dict[str,Any]:
    raw=str(text or '').strip();low=raw.lower()
    if low not in {'inspect broad software engineering','show broad software engineering assessment'}:
        if ('software engineering' in low or 'project engineering' in low) and any(x in low for x in ('install','apply','delete','promote','certify','download dependencies')):
            return {'active':True,'ok':False,'status':'read_only_engineering_scope_expansion_rejected','action_executed':False,**DENIED_AUTHORITY}
        return {'active':False}
    if not project_root:return {'active':True,'ok':False,'status':'project_root_required','action_executed':False,**DENIED_AUTHORITY}
    return {'active':True,**build_broad_software_engineering_assessment(project_root,changed_paths=changed_paths,runtime_root=runtime_root)}

__all__=['CONTRACT_VERSION','build_broad_software_engineering_assessment','process_broad_software_engineering_control']
