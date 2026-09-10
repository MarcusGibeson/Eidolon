from __future__ import annotations
"""v2557 bounded verification-health trend projection.

Summarizes changes across bounded historical windows. Advisory only: no test
waiver, timeout change, release, or certification authority is introduced.
"""
from typing import Any, Mapping, Sequence
import hashlib, json, statistics
from historical_verification_feedback_v2552 import build_historical_verification_feedback

CONTRACT_VERSION = 'v2557.0'
AUTHORITY = {
    'test_suppression_authorized': False,
    'required_test_waiver_authorized': False,
    'timeout_change_authorized': False,
    'release_authorized': False,
    'certification_authorized': False,
    'independent_authority_granted': False,
}

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode()).hexdigest()

def _window(history: Mapping[str, Sequence[Mapping[str, Any]]], count: int, *, offset: int = 0) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for test, rows in history.items():
        seq = [dict(r) for r in rows if isinstance(r, Mapping)]
        end = max(0, len(seq) - offset)
        start = max(0, end - count)
        if start < end:
            out[str(test)] = seq[start:end]
    return out

def build_verification_health_trends(history: Mapping[str, Sequence[Mapping[str, Any]]], *, window_size: int = 8) -> dict[str, Any]:
    size = max(2, min(32, int(window_size or 8)))
    current = build_historical_verification_feedback(_window(history, size))
    previous = build_historical_verification_feedback(_window(history, size, offset=size))
    # Performance trend compares the current bounded window against the prior
    # bounded window directly. The per-window historical feedback classifier
    # intentionally measures drift *within* one slice, which is insufficient
    # when the whole recent slice became uniformly slower.
    current_rows = _window(history, size)
    previous_rows = _window(history, size, offset=size)
    cross_window_regressions = 0
    for test in set(current_rows).intersection(previous_rows):
        cur = [float(r.get('elapsed_seconds') or 0.0) for r in current_rows[test] if float(r.get('elapsed_seconds') or 0.0) > 0]
        prev = [float(r.get('elapsed_seconds') or 0.0) for r in previous_rows[test] if float(r.get('elapsed_seconds') or 0.0) > 0]
        if cur and prev:
            cmed, pmed = statistics.median(cur), statistics.median(prev)
            if pmed > 0 and cmed / pmed >= 1.5 and cmed - pmed >= 0.5:
                cross_window_regressions += 1
    fields = ('persistent_failure_count', 'intermittent_count', 'timeout_prone_count', 'concern_count')
    deltas = {name: int(current.get(name, 0)) - int(previous.get(name, 0)) for name in fields}
    deltas['performance_regression_count'] = cross_window_regressions
    worsening = sum(max(0, value) for value in deltas.values())
    improving = sum(max(0, -value) for value in deltas.values())
    if worsening and worsening > improving:
        direction = 'worsening'
    elif improving and improving > worsening:
        direction = 'improving'
    elif any(deltas.values()):
        direction = 'mixed'
    else:
        direction = 'stable_or_insufficient_history'
    out = {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'direction': direction,
        'window_size': size,
        'current': {**{name: int(current.get(name, 0)) for name in fields}, 'performance_regression_count': cross_window_regressions},
        'previous': {**{name: int(previous.get(name, 0)) for name in fields}, 'performance_regression_count': 0},
        'deltas': deltas,
        'raw_test_output_stored': False,
        'required_tests_waived': 0,
        **AUTHORITY,
    }
    out['trend_digest'] = _digest(out)
    return out

__all__ = ['CONTRACT_VERSION', 'build_verification_health_trends']
