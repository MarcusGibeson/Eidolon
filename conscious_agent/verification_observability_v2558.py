from __future__ import annotations
"""v2558 read-only verification observability projection."""
from pathlib import Path
from typing import Any
import os, hashlib, json
from verification_history_v2547 import load_history
from verification_health_v2556 import build_verification_health
from verification_health_trends_v2557 import build_verification_health_trends

CONTRACT_VERSION = 'v2558.0'

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode()).hexdigest()

def _default_history_path(runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        root = Path(runtime_root).expanduser().resolve()
    else:
        root = Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1] / 'data').expanduser().resolve()
    return root / 'verification' / 'tiered_verification_history.json'

def build_verification_observability(runtime_root: str | Path | None = None, *, history_path: str | Path | None = None, window_size: int = 8) -> dict[str, Any]:
    path = Path(history_path).expanduser().resolve() if history_path is not None else _default_history_path(runtime_root)
    history = load_history(path)
    health = build_verification_health(history)
    trends = build_verification_health_trends(history, window_size=window_size)
    concerns = []
    from historical_verification_feedback_v2552 import build_historical_verification_feedback
    feedback = build_historical_verification_feedback(history)
    for row in list(feedback.get('concerns') or [])[:12]:
        concerns.append({
            'test': str(row.get('test') or '')[:240],
            'flakiness': str(row.get('flakiness') or '')[:48],
            'performance': str(row.get('performance') or '')[:48],
            'required_test_still_required': bool(row.get('required_test_still_required', True)),
        })
    out = {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'health': health,
        'trends': trends,
        'concerns': concerns,
        'history_present': bool(history),
        'history_path_exposed': False,
        'raw_test_output_stored': False,
        'authority_boundary': {
            'read_only': True,
            'can_suppress_test': False,
            'can_waive_test': False,
            'can_change_timeout': False,
            'can_certify_release': False,
            'can_execute_action': False,
        },
    }
    out['snapshot_digest'] = _digest({'health': health.get('health_digest'), 'trends': trends.get('trend_digest'), 'concerns': concerns})
    return out

__all__ = ['CONTRACT_VERSION', 'build_verification_observability']
