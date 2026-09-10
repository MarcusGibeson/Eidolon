from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    CONTRACT_VERSION: Any
    DENIED_AUTHORITY: Any
    Iterable: Any
    MIN_MULTI_FILE_CHANGE: Any
    Mapping: Any
    build_product_quality_judgment: Any
    digest: Any



def build_cognitive_coding_result(campaign: _deps.Mapping[str, Any], *, assumption_revisions: _deps.Iterable[_deps.Mapping[str, Any]], diagnostic_results: _deps.Iterable[_deps.Mapping[str, Any]], changed_paths: _deps.Iterable[str], verification_results: _deps.Iterable[_deps.Mapping[str, Any]], quality_evidence: _deps.Iterable[_deps.Mapping[str, Any]], _deps: SymbolDependencies) -> dict[str, Any]:
    revisions = [dict(x) for x in assumption_revisions]
    diagnostics = [dict(x) for x in diagnostic_results]
    paths = sorted({str(x).replace('\\', '/').strip('/') for x in changed_paths if str(x).strip()})
    verification = [dict(x) for x in verification_results]
    quality = _deps.build_product_quality_judgment(quality_evidence, scope_digest=str(campaign.get('project_manifest_digest') or ''))
    revised_mistake = any((x.get('outcome') in {'revised', 'rejected'} and x.get('contradicting_evidence_digest') for x in revisions))
    discriminating_observed = any((bool(x.get('observed')) and len(set(x.get('distinguishes') or [])) >= 2 for x in diagnostics))
    focused_pass = any((x.get('tier') == 'focused' and x.get('passed') is True for x in verification))
    regression_pass = any((x.get('tier') == 'regression' and x.get('passed') is True for x in verification))
    failed_verification = any((x.get('passed') is False for x in verification))
    checks = {'objective_preserved': len(str(campaign.get('objective_digest') or '')) == 64, 'project_identity_preserved': len(str(campaign.get('project_manifest_digest') or '')) == 64, 'multi_file_project_completed': len(paths) >= _deps.MIN_MULTI_FILE_CHANGE, 'mistaken_assumption_revised': revised_mistake, 'discriminating_diagnostic_observed': discriminating_observed, 'focused_verification_passed': focused_pass, 'regression_verification_passed': regression_pass, 'no_failed_verification_remaining': not failed_verification, 'product_quality_operator_ready_candidate': quality.get('disposition') == 'operator_ready_candidate', 'product_quality_not_release_authority': quality.get('release_ready_claimed') is False}
    result = {'contract_version': _deps.CONTRACT_VERSION, 'campaign_id': campaign.get('campaign_id'), 'objective_digest': campaign.get('objective_digest'), 'project_manifest_digest': campaign.get('project_manifest_digest'), 'checks': checks, 'ok': all(checks.values()), 'status': 'cognitive_coding_benchmark_complete' if all(checks.values()) else 'cognitive_coding_benchmark_incomplete', 'changed_path_count': len(paths), 'changed_paths_digest': _deps.digest(paths), 'assumption_revision_count': len(revisions), 'diagnostic_result_count': len(diagnostics), 'verification_result_count': len(verification), 'quality_disposition': quality.get('disposition'), 'quality_judgment_digest': quality.get('judgment_digest'), 'release_ready_claimed': False, 'completion_is_authorization': False, 'content_free': True, 'read_only_coordinator': True, **_deps.DENIED_AUTHORITY}
    result['result_digest'] = _deps.digest(result)
    return result


def public_cognitive_coding_result(result: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    keys = ('contract_version', 'campaign_id', 'objective_digest', 'project_manifest_digest', 'ok', 'status', 'checks', 'changed_path_count', 'changed_paths_digest', 'assumption_revision_count', 'diagnostic_result_count', 'verification_result_count', 'quality_disposition', 'quality_judgment_digest', 'release_ready_claimed', 'completion_is_authorization', 'result_digest', 'content_free', 'read_only_coordinator')
    return {k: result.get(k) for k in keys} | _deps.DENIED_AUTHORITY
