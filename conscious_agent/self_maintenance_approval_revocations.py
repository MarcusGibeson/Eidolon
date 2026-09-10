from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    APPROVAL_REVOCATIONS_DIR: Any
    ROOT_DIR: Any
    _is_hex_sha256: Any
    _report_path: Any
    _runtime_private_marker_scan: Any
    _sha256_text: Any
    _status_from: Any



def _revocation_record_files(*, _deps: SymbolDependencies) -> list[Path]:
    """Return persisted publish approval revocation records from runtime-only storage."""
    if not _deps.APPROVAL_REVOCATIONS_DIR.exists():
        return []
    return sorted((path for path in _deps.APPROVAL_REVOCATIONS_DIR.glob('*.json') if path.is_file()))


def _read_revocation_payload(path: Path, *, _deps: SymbolDependencies) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return (None, f'malformed json: {type(exc).__name__}')
    if not isinstance(payload, dict):
        return (None, 'revocation record is not a JSON object')
    return (payload, None)


def _revocation_record_id(record: dict[str, Any], fallback: str='', *, _deps: SymbolDependencies) -> str:
    for key in ('revocation_id', 'revocation_record_id', 'record_id'):
        if record.get(key):
            return str(record.get(key))
    digest = record.get('revocation_record_hash') or _deps._sha256_text(record)
    return f'revocation-{str(digest)[:16]}' if digest else fallback


def _revocation_validator_rows(record: dict[str, Any], *, _deps: SymbolDependencies) -> list[dict[str, Any]]:
    required = ['target_approval_record_id', 'target_approval_record_hash', 'target_artifact_hashes', 'revocation_reason', 'revoked_at', 'revoked_by_label', 'confirmation_marker', 'revocation_scope', 'rollback_approved', 'live_apply_approved']
    missing = [field for field in required if field not in record]
    rows: list[dict[str, Any]] = [{'name': 'required-fields-present', 'status': 'pass' if not missing else 'blocked', 'message': ', '.join(missing) if missing else 'all required revocation fields are present'}, {'name': 'target-approval-hash', 'status': 'pass' if _deps._is_hex_sha256(record.get('target_approval_record_hash')) else 'blocked', 'message': str(record.get('target_approval_record_hash'))}, {'name': 'revocation-scope', 'status': 'pass' if record.get('revocation_scope') == 'publish_approval_only' else 'blocked', 'message': str(record.get('revocation_scope'))}, {'name': 'rollback-separated', 'status': 'pass' if record.get('rollback_approved') is False else 'blocked', 'message': 'revocation cannot approve rollback'}, {'name': 'live-apply-separated', 'status': 'pass' if record.get('live_apply_approved') is False else 'blocked', 'message': 'revocation cannot approve live apply'}, {'name': 'confirmation-marker', 'status': 'pass' if str(record.get('confirmation_marker', '')).startswith('sha256:') else 'blocked', 'message': str(record.get('confirmation_marker'))}, {'name': 'private-key-boundary', 'status': 'pass' if not _deps._runtime_private_marker_scan(record) else 'blocked', 'message': 'revocation records reject private key marker strings'}]
    return rows


def _read_revocation_summaries(*, _deps: SymbolDependencies) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path in _revocation_record_files(_deps=_deps):
        payload, error = _read_revocation_payload(path, _deps=_deps)
        if payload is None:
            summaries.append({'path': _deps._report_path(str(path.relative_to(_deps.ROOT_DIR) if path.is_relative_to(_deps.ROOT_DIR) else path)), 'valid': False, 'error': error or 'unreadable revocation record'})
            continue
        rows = _revocation_validator_rows(payload, _deps=_deps)
        valid = _deps._status_from(rows) != 'blocked'
        summaries.append({'revocation_id': _revocation_record_id(payload, path.stem, _deps=_deps), 'path': _deps._report_path(str(path.relative_to(_deps.ROOT_DIR) if path.is_relative_to(_deps.ROOT_DIR) else path)), 'valid': valid, 'target_approval_record_id': payload.get('target_approval_record_id'), 'target_approval_record_hash': payload.get('target_approval_record_hash'), 'revocation_reason': payload.get('revocation_reason'), 'revoked_at': payload.get('revoked_at'), 'revoked_by_label': payload.get('revoked_by_label'), 'revocation_scope': payload.get('revocation_scope'), 'rollback_approved': bool(payload.get('rollback_approved')), 'live_apply_approved': bool(payload.get('live_apply_approved')), 'revocation_record_hash': payload.get('revocation_record_hash') or _deps._sha256_text(payload), 'validation_status': _deps._status_from(rows), 'validation_rows': rows})
    return summaries
