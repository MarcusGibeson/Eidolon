from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    RELEASE_APPROVALS_DIR: Any
    ROOT_DIR: Any
    _approval_record_validator_rows: Any
    _report_path: Any
    _sha256_text: Any
    _status_from: Any



def _approval_record_files(*, _deps: SymbolDependencies) -> list[Path]:
    """Return persisted publish approval records from the runtime-only approval ledger."""
    if not _deps.RELEASE_APPROVALS_DIR.exists():
        return []
    return sorted((path for path in _deps.RELEASE_APPROVALS_DIR.glob('*.json') if path.is_file()))


def _safe_approval_record_from_path(path: Path, *, _deps: SymbolDependencies) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return (None, f'malformed json: {type(exc).__name__}')
    if not isinstance(payload, dict):
        return (None, 'approval record is not a JSON object')
    return (payload, None)


def _approval_record_id(record: dict[str, Any], fallback: str='', *, _deps: SymbolDependencies) -> str:
    for key in ('approval_id', 'approval_record_id', 'record_id'):
        if record.get(key):
            return str(record.get(key))
    digest = record.get('approval_record_hash') or _deps._sha256_text(record)
    return f'approval-{str(digest)[:16]}' if digest else fallback


def _approval_record_summary(path: Path, record: dict[str, Any] | None, error: str | None=None, *, _deps: SymbolDependencies) -> dict[str, Any]:
    if record is None:
        return {'path': _deps._report_path(str(path.relative_to(_deps.ROOT_DIR) if path.is_relative_to(_deps.ROOT_DIR) else path)), 'valid': False, 'error': error or 'unreadable approval record'}
    rows = _deps._approval_record_validator_rows(record)
    valid = _deps._status_from(rows) != 'blocked'
    return {'approval_id': _approval_record_id(record, path.stem, _deps=_deps), 'path': _deps._report_path(str(path.relative_to(_deps.ROOT_DIR) if path.is_relative_to(_deps.ROOT_DIR) else path)), 'valid': valid, 'schema_version': record.get('schema_version'), 'package_sha256': record.get('package_sha256'), 'canonical_manifest_hash': record.get('canonical_manifest_hash'), 'canonical_evidence_hash': record.get('canonical_evidence_hash'), 'signing_payload_hash': record.get('signing_payload_hash'), 'signature_sidecar_hash': record.get('signature_sidecar_hash'), 'signer_fingerprint': record.get('signer_fingerprint'), 'candidate_review_id': record.get('candidate_review_id'), 'approval_timestamp': record.get('approval_timestamp') or record.get('created_at'), 'approver_label': record.get('approver_label') or record.get('created_by_label'), 'publish_approved': bool(record.get('publish_approved')), 'live_apply_approved': bool(record.get('live_apply_approved')), 'approval_scope': record.get('approval_scope'), 'approval_record_hash': record.get('approval_record_hash') or _deps._sha256_text(record), 'validation_status': _deps._status_from(rows), 'validation_rows': rows}


def _read_approval_record_summaries(*, _deps: SymbolDependencies) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for path in _approval_record_files(_deps=_deps):
        record, error = _safe_approval_record_from_path(path, _deps=_deps)
        summaries.append(_approval_record_summary(path, record, error, _deps=_deps))
    return summaries


def _approval_record_matches_binding(summary: dict[str, Any], binding: dict[str, Any], *, _deps: SymbolDependencies) -> bool:
    return all((str(summary.get(key) or '') == str(binding.get(key) or '') for key in ('package_sha256', 'canonical_manifest_hash', 'canonical_evidence_hash', 'signing_payload_hash')))
