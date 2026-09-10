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
    Mapping: Any
    SCHEMA_VERSION: Any
    STAGES: Any
    _digest: Any



def build_coding_alpha_contract(*, _deps: SymbolDependencies) -> dict[str, Any]:
    stages = [{'ordinal': i, 'stage': name, 'owner': owner, 'authority_boundary': boundary, 'stage_digest': _deps._digest({'ordinal': i, 'stage': name, 'owner': owner, 'authority_boundary': boundary})} for i, (name, owner, boundary) in enumerate(_deps.STAGES, 1)]
    contract = {'ok': True, 'schema_version': _deps.SCHEMA_VERSION, 'contract_version': _deps.CONTRACT_VERSION, 'status': 'coding_alpha_campaign_contract_ready', 'scenario_id': 'calculator_webpage_supervised_end_to_end', 'ordinary_request': 'Build me a complete responsive accessible calculator webpage.', 'scenario_artifacts': ['index.html', 'app.js', 'styles.css', 'package.json', 'tests/app.test.js', 'README.md'], 'required_behaviors': ['add', 'subtract', 'multiply', 'divide', 'clear'], 'quality_dimensions': ['interface_coherence', 'dependency_coherence', 'configuration_coherence', 'test_coverage', 'documentation_completeness', 'accessibility', 'responsive_behavior'], 'stages': stages, 'stage_count': len(stages), 'restart_required_between': ['implementation_verification', 'controlled_application'], 'mandatory_failure_repair_evidence': True, 'selected_project_must_remain_unchanged_until_application': True, 'application_and_rollback_require_distinct_exact_authorizations': True, 'rollback_must_restore_pre_apply_tree_digest': True, 'generic_authorization_must_never_be_consumed': True, 'provider_replay_on_resume_forbidden': True, 'content_minimized_public_evidence': True, 'v1260_creates_no_new_mutation_authority': True, **_deps.DENIED_AUTHORITY}
    contract['contract_digest'] = _deps._digest(contract)
    return contract


def public_coding_alpha_contract(value: _deps.Mapping[str, Any] | None=None, *, _deps: SymbolDependencies) -> dict[str, Any]:
    contract = dict(value or build_coding_alpha_contract(_deps=_deps))
    return {'ok': bool(contract.get('ok')), 'contract_version': contract.get('contract_version', ''), 'status': contract.get('status', ''), 'scenario_id': contract.get('scenario_id', ''), 'stage_count': int(contract.get('stage_count') or 0), 'stages': list(contract.get('stages') or []), 'quality_dimensions': list(contract.get('quality_dimensions') or []), 'contract_digest': contract.get('contract_digest', ''), 'raw_operator_content_exposed': False, 'private_paths_exposed': False, 'content_minimized': True, **_deps.DENIED_AUTHORITY}
