from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    ARCHITECTURE_LINEAGE: Any
    CONTRACT_VERSION: Any
    DENIED_AUTHORITY: Any
    EVIDENCE_DOMAINS: Any
    Iterable: Any
    Mapping: Any
    digest: Any
    evidence_record: Any
    valid_digest: Any



def combine_verification_evidence(records: _deps.Iterable[_deps.Mapping[str, Any]], *, _deps: SymbolDependencies) -> dict[str, Any]:
    rows = [dict(r) for r in records]
    by_domain = {}
    violations = []
    for row in rows:
        d = str(row.get('domain') or '')
        if d in by_domain:
            violations.append(f'duplicate_domain:{d}')
        by_domain[d] = row
    source = {str(r.get('source_tree_digest') or '') for r in rows}
    candidate = {str(r.get('candidate_digest') or '') for r in rows}
    if len(source) != 1 or not source or (not all((_deps.valid_digest(x) for x in source))):
        violations.append('source_tree_identity_mismatch')
    if len(candidate) != 1 or not candidate or (not all((_deps.valid_digest(x) for x in candidate))):
        violations.append('candidate_identity_mismatch')
    missing = [d for d in _deps.EVIDENCE_DOMAINS if d not in by_domain]
    for d in missing:
        violations.append(f'missing_required_domain:{d}')
    domain_states = {d: str(by_domain.get(d, {}).get('status') or 'missing') for d in _deps.EVIDENCE_DOMAINS}
    for d, row in by_domain.items():
        if row.get('required', True) and (not row.get('fresh', False)):
            violations.append(f'stale_required_evidence:{d}')
        if any((bool(row.get(k)) for k in _deps.DENIED_AUTHORITY)):
            violations.append(f'authority_expansion:{d}')
    native = by_domain.get('native_windows', {})
    native_pass = native.get('status') == 'passed' and native.get('native') is True and (native.get('native_attested') is True) and (str(native.get('platform_name') or '').lower() == 'windows')
    failed = [d for d, s in domain_states.items() if s == 'failed']
    blocked = [d for d, s in domain_states.items() if s == 'blocked']
    unavailable = [d for d, s in domain_states.items() if s == 'unavailable']
    pending = [d for d, s in domain_states.items() if s == 'pending']
    nonnative = [d for d in _deps.EVIDENCE_DOMAINS if d != 'native_windows']
    portable_pass = all((domain_states[d] == 'passed' for d in nonnative))
    if violations:
        status = 'verification_integrity_blocked'
        ok = False
    elif failed:
        status = 'verification_failed'
        ok = False
    elif blocked:
        status = 'verification_blocked'
        ok = False
    elif portable_pass and (not native_pass):
        status = 'portable_verification_complete_native_pending'
        ok = False
    elif all((domain_states[d] == 'passed' for d in _deps.EVIDENCE_DOMAINS)) and native_pass:
        status = 'comprehensive_verification_passed'
        ok = True
    else:
        status = 'verification_incomplete'
        ok = False
    out = {'contract_version': _deps.CONTRACT_VERSION, 'ok': ok, 'status': status, 'domain_states': domain_states, 'required_domain_count': len(_deps.EVIDENCE_DOMAINS), 'provided_domain_count': len(by_domain), 'portable_evidence_complete': portable_pass, 'native_windows_passed': native_pass, 'failed_domains': failed, 'blocked_domains': blocked, 'unavailable_domains': unavailable, 'pending_domains': pending, 'integrity_violations': violations, 'source_tree_digest': next(iter(source)) if len(source) == 1 else '', 'candidate_digest': next(iter(candidate)) if len(candidate) == 1 else '', 'missing_native_is_pass': False, 'missing_evidence_is_pass': False, 'verification_is_release_authority': False, 'architecture_lineage': dict(_deps.ARCHITECTURE_LINEAGE), 'content_free': True, 'read_only': True, **_deps.DENIED_AUTHORITY}
    out['verification_digest'] = _deps.digest(out)
    return out


def evidence_from_suite(*, domain: str, passed: int, total: int, source_tree_digest: str, candidate_digest: str, evidence_digest: str, _deps: SymbolDependencies) -> dict[str, Any]:
    from comprehensive_verification_foundations import evidence_record
    p = max(0, int(passed))
    t = max(0, int(total))
    status = 'passed' if t > 0 and p == t else 'failed'
    return _deps.evidence_record(domain, status=status, source_tree_digest=source_tree_digest, candidate_digest=candidate_digest, evidence_digest=evidence_digest, summary={'passed': p, 'total': t, 'all_passed': p == t and t > 0})
