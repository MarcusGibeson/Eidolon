from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    BANDS: Any
    MAX_APPROACHES: Any
    Mapping: Any
    PLAN_DENIED_AUTHORITY: Any
    PLAN_STATUSES: Any
    _digest: Any
    _expected_approach_score: Any
    validate_backlog_reliability: Any
    validate_priority_selection: Any



def validate_alternative_plan(plan: _deps.Mapping[str, Any], selection: _deps.Mapping[str, Any], backlog: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    lineage_valid = bool(_deps.validate_backlog_reliability(backlog).get('ok')) and bool(_deps.validate_priority_selection(selection, backlog).get('ok'))
    supplied = str(plan.get('plan_digest') or '')
    digest_ok = bool(supplied and supplied == _deps._digest({k: v for k, v in plan.items() if k != 'plan_digest'}))
    binding_ok = str(plan.get('selection_digest') or '') == str(selection.get('selection_digest') or '') and str(plan.get('backlog_digest') or '') == str(backlog.get('backlog_digest') or '') and (str(plan.get('assessment_digest') or '') == str(backlog.get('assessment_digest') or '')) and (str(plan.get('source_manifest_digest') or '') == str(backlog.get('source_manifest_digest') or ''))
    status = str(plan.get('status') or '')
    status_ok = status in _deps.PLAN_STATUSES
    if status == 'no_defensible_plan_no_priority_selection':
        semantic_ok = str(selection.get('status') or '') != 'priority_selected' and plan.get('selected_approach_id') is None and (not list(plan.get('approaches') or []))
    else:
        item_id = str(selection.get('selected_work_item_id') or '')
        item = next((row for row in backlog.get('items') or [] if str(row.get('work_item_id') or '') == item_id), None)
        approaches = list(plan.get('approaches') or [])
        ids = [str(row.get('approach_id') or '') for row in approaches]
        approaches_ok = bool(item) and 2 <= len(approaches) <= _deps.MAX_APPROACHES and (len(ids) == len(set(ids))) and all(ids)
        approach_digests_ok = all((str(row.get('approach_digest') or '') == _deps._digest({k: v for k, v in row.items() if k != 'approach_digest'}) for row in approaches))
        scores_ok = all((_deps._expected_approach_score(row) == row.get('simulation_score') for row in approaches))
        bindings_ok = bool(item) and all((str(row.get('work_item_id') or '') == item_id and str(row.get('work_item_digest') or '') == str(item.get('work_item_digest') or '') for row in approaches))
        failure_modes_ok = all((row.get('predicted_failure_modes') and row.get('failure_mode_count') == len(row.get('predicted_failure_modes') or []) and bool(row.get('implementation_steps')) and bool(row.get('verification_steps')) and all((str(fm.get('failure_mode_digest') or '') == _deps._digest({k: v for k, v in fm.items() if k != 'failure_mode_digest'}) and str(fm.get('likelihood') or '') in _deps.BANDS and (str(fm.get('impact') or '') in _deps.BANDS) and bool(str(fm.get('failure_code') or '')) and bool(str(fm.get('mitigation_code') or '')) and bool(str(fm.get('falsification_condition') or '')) and (fm.get('epistemic_status') == 'predicted') and (fm.get('content_minimized') is True) for fm in row.get('predicted_failure_modes') or [])) for row in approaches))
        ordered = sorted(approaches, key=lambda row: (-int(row.get('simulation_score') or 0), str(row.get('strategy_code') or ''), str(row.get('approach_id') or ''))) if approaches else []
        tied = [row for row in ordered if ordered and int(row.get('simulation_score') or 0) == int(ordered[0].get('simulation_score') or 0)]
        if len(tied) > 1:
            selection_ok = status == 'no_defensible_plan_approach_tie' and plan.get('selected_approach_id') is None
        else:
            expected_id = ordered[0].get('approach_id') if ordered else None
            selection_ok = status == 'alternative_plan_selected' and plan.get('selected_approach_id') == expected_id
        semantic_ok = approaches_ok and approach_digests_ok and scores_ok and bindings_ok and failure_modes_ok and selection_ok
    authority_ok = all((plan.get(key) is expected for key, expected in _deps.PLAN_DENIED_AUTHORITY.items()))
    ok = lineage_valid and digest_ok and binding_ok and status_ok and semantic_ok and authority_ok and (plan.get('read_only') is True) and (plan.get('content_minimized') is True)
    return {'ok': ok, 'status': 'alternative_plan_valid' if ok else 'alternative_plan_invalid', 'lineage_valid': lineage_valid, 'digest_valid': digest_ok, 'binding_valid': binding_ok, 'semantic_valid': semantic_ok, 'authority_denied': authority_ok, 'plan_digest': supplied, 'read_only': True, **_deps.PLAN_DENIED_AUTHORITY}


def public_alternative_plan(plan: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    selected = next((row for row in plan.get('approaches') or [] if row.get('approach_id') == plan.get('selected_approach_id')), None)
    return {'ok': bool(plan.get('ok')), 'status': str(plan.get('status') or ''), 'objective_code': str(plan.get('objective_code') or ''), 'approach_count': int(plan.get('approach_count') or 0), 'strategy_codes': [str(row.get('strategy_code') or '') for row in plan.get('approaches') or []], 'selected_strategy_code': str((selected or {}).get('strategy_code') or ''), 'selection_confidence': str(plan.get('selection_confidence') or 'none'), 'selection_margin': plan.get('selection_margin'), 'predicted_failure_mode_count': sum((len(row.get('predicted_failure_modes') or []) for row in plan.get('approaches') or [])), 'plan_digest': str(plan.get('plan_digest') or ''), 'selection_digest': str(plan.get('selection_digest') or ''), 'operator_review_required': True, 'raw_paths_exposed': False, 'raw_source_content_exposed': False, 'content_minimized': True, 'read_only': True, **_deps.PLAN_DENIED_AUTHORITY}
