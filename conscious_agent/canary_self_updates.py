from __future__ import annotations
"""v1296.3-v1296.5 baseline/candidate canary comparison."""
from typing import Any, Iterable, Mapping
from canary_self_updates_foundations import DENIED_AUTHORITY, MANDATORY_SIGNALS, NATIVE_SIGNAL, digest, valid_digest

CONTRACT_VERSION = "v1296.5"

def _index(rows: Iterable[Mapping[str, Any]], role: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    out: dict[str, dict[str, Any]] = {}; violations: list[str] = []
    for raw in rows:
        row = dict(raw); signal = str(row.get("signal") or "")
        if row.get("role") != role: violations.append(f"role_mismatch:{signal}")
        if signal in out: violations.append(f"duplicate_observation:{role}:{signal}")
        out[signal] = row
    return out, violations

def evaluate_canary(identity: Mapping[str, Any], baseline_observations: Iterable[Mapping[str, Any]],
                    candidate_observations: Iterable[Mapping[str, Any]], *,
                    max_latency_ratio: float = 1.35, max_quality_drop: float = 0.05) -> dict[str, Any]:
    ident = dict(identity); violations: list[str] = []
    if not valid_digest(ident.get("identity_digest")) or not str(ident.get("canary_id") or "").startswith("canary_"):
        violations.append("invalid_canary_identity")
    baseline, bviol = _index(baseline_observations, "baseline"); candidate, cviol = _index(candidate_observations, "candidate")
    violations.extend(bviol); violations.extend(cviol)
    required = list(MANDATORY_SIGNALS)
    for role, rows in (("baseline", baseline), ("candidate", candidate)):
        for signal in required:
            if signal not in rows: violations.append(f"missing_observation:{role}:{signal}")
        for signal, row in rows.items():
            sealed_payload = {
                key: value
                for key, value in row.items()
                if key != "observation_digest" and key not in DENIED_AUTHORITY
            }
            if row.get("observation_digest") != digest(sealed_payload):
                violations.append(f"observation_digest_mismatch:{role}:{signal}")
            if row.get("canary_id") != ident.get("canary_id") or row.get("identity_digest") != ident.get("identity_digest"):
                violations.append(f"identity_mismatch:{role}:{signal}")
            if not row.get("fresh", False): violations.append(f"stale_observation:{role}:{signal}")
            if int(row.get("private_finding_count") or 0) > 0: violations.append(f"private_leakage:{role}:{signal}")
            if row.get("shared_mutable_runtime") is True: violations.append(f"shared_mutable_runtime:{role}:{signal}")
            if any(bool(row.get(k)) for k in DENIED_AUTHORITY): violations.append(f"authority_expansion:{role}:{signal}")
    regressions: list[str] = []; failures: list[str] = []
    latency_ratio = max(1.0, float(max_latency_ratio)); quality_drop = max(0.0, float(max_quality_drop))
    for signal in required:
        b = baseline.get(signal, {}); c = candidate.get(signal, {})
        if b.get("status") != "passed": failures.append(f"baseline_not_healthy:{signal}")
        if c.get("status") != "passed": failures.append(f"candidate_not_healthy:{signal}")
        if b and c:
            if float(c.get("quality_score") or 0.0) + quality_drop < float(b.get("quality_score") or 0.0): regressions.append(f"quality_regression:{signal}")
            bl = float(b.get("latency_ms") or 0.0); cl = float(c.get("latency_ms") or 0.0)
            if bl > 0 and cl > bl * latency_ratio: regressions.append(f"latency_regression:{signal}")
    native = candidate.get(NATIVE_SIGNAL, {})
    native_pass = bool(native and native.get("status") == "passed" and native.get("platform_name") == "windows" and native.get("native_attested") is True)
    native_pending = not native_pass
    # A legacy conservative-failure fixture may turn a passing observation into
    # a failed one without resealing it.  Preserve the fail-closed outcome while
    # retaining the digest mismatch as evidence.  Any other integrity violation
    # remains integrity-blocking and can never advance a candidate toward review.
    conservative_failure_with_only_seal_mismatch = bool(failures) and bool(violations) and all(
        item.startswith("observation_digest_mismatch:") for item in violations
    )
    if violations and not conservative_failure_with_only_seal_mismatch: status = "canary_integrity_blocked"; ok = False
    elif failures: status = "canary_failed"; ok = False
    elif regressions: status = "canary_regression_detected"; ok = False
    elif native_pending: status = "portable_canary_ready_native_pending"; ok = False
    else: status = "canary_ready_for_operator_replacement_review"; ok = True
    out = {
        "contract_version": CONTRACT_VERSION,
        "ok": ok,
        "status": status,
        "canary_id": ident.get("canary_id", ""),
        "update_id": ident.get("update_id", ""),
        "baseline_source_digest": ident.get("baseline_source_digest", ""),
        "candidate_source_digest": ident.get("candidate_source_digest", ""),
        "required_signal_count": len(required),
        "baseline_observation_count": len(baseline),
        "candidate_observation_count": len(candidate),
        "integrity_violations": violations,
        "failures": failures,
        "regressions": regressions,
        "portable_canary_passed": not violations and not failures and not regressions,
        "native_windows_canary_passed": native_pass,
        "active_replacement_performed": False,
        "replacement_authorization_requested": False,
        "replacement_authorization_granted": False,
        "requires_separate_v1269_exact_authorization": True,
        "canary_success_is_update_authority": False,
        "architecture_lineage": {"v1269":"governed_self_update","v1295":"comprehensive_verification"},
        "read_only": True,
        "content_free": True,
        **DENIED_AUTHORITY,
    }
    out["evaluation_digest"] = digest(out)
    return out
