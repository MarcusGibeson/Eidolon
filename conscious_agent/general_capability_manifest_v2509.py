from __future__ import annotations

"""v2509 general capability manifest contracts.

A manifest describes what a capability *could* require. It is never an authority
or execution grant. The model is intentionally independent of software-
development-specific tools so later adapters can describe calendar, files,
communication, applications, or other bounded systems through one vocabulary.
"""

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable, Mapping

CONTRACT_VERSION = "v2509.0"
CAPABILITY_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,79}$")
SIDE_EFFECT_CLASSES = frozenset({"none", "local_reversible", "external_reversible", "external_irreversible", "destructive"})
PRIVACY_SCOPES = frozenset({"public", "workspace", "personal", "sensitive_personal", "secret"})
APPROVAL_CLASSES = frozenset({"none", "operator_once", "operator_each_time", "protected_action"})
ACCESS_SURFACES = frozenset({"provider", "network", "filesystem", "communication", "external_system", "process", "browser", "device"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _bounded_tokens(values: Iterable[Any], allowed: frozenset[str], *, limit: int = 16) -> list[str]:
    out: list[str] = []
    for raw in values or ():
        token = str(raw or "").strip().lower()
        if token not in allowed:
            raise ValueError(f"unsupported token: {token}")
        if token not in out:
            out.append(token)
        if len(out) >= limit:
            break
    return sorted(out)


def build_capability_manifest(
    *,
    capability_id: str,
    description_code: str,
    side_effect_class: str = "none",
    privacy_scope: str = "workspace",
    approval_class: str = "operator_each_time",
    access_surfaces: Iterable[str] = (),
    reversible: bool = False,
    cancellation_supported: bool = False,
    rollback_supported: bool = False,
    required_evidence_codes: Iterable[str] = (),
    max_operations_per_hour: int = 0,
    max_runtime_seconds: int = 0,
) -> dict[str, Any]:
    cid = str(capability_id or "").strip().lower()
    if not CAPABILITY_ID_RE.fullmatch(cid):
        raise ValueError("invalid capability_id")
    desc = str(description_code or "").strip().lower()[:120]
    if not desc:
        raise ValueError("description_code_required")
    side = str(side_effect_class or "").strip().lower()
    privacy = str(privacy_scope or "").strip().lower()
    approval = str(approval_class or "").strip().lower()
    if side not in SIDE_EFFECT_CLASSES:
        raise ValueError("invalid side_effect_class")
    if privacy not in PRIVACY_SCOPES:
        raise ValueError("invalid privacy_scope")
    if approval not in APPROVAL_CLASSES:
        raise ValueError("invalid approval_class")
    surfaces = _bounded_tokens(access_surfaces, ACCESS_SURFACES)
    evidence_codes = sorted({str(x or "").strip().lower()[:80] for x in required_evidence_codes or () if str(x or "").strip()})[:16]
    if side != "none" and approval == "none":
        raise ValueError("side_effecting_capability_requires_approval_class")
    if side in {"external_irreversible", "destructive"} and approval != "protected_action":
        raise ValueError("high_risk_capability_requires_protected_action")
    if rollback_supported and not reversible:
        raise ValueError("rollback_requires_reversible_capability")
    manifest: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "capability_id": cid,
        "description_code": desc,
        "side_effect_class": side,
        "privacy_scope": privacy,
        "approval_class": approval,
        "access_surfaces": surfaces,
        "reversible": bool(reversible),
        "cancellation_supported": bool(cancellation_supported),
        "rollback_supported": bool(rollback_supported),
        "required_evidence_codes": evidence_codes,
        "limits": {
            "max_operations_per_hour": max(0, min(10000, int(max_operations_per_hour or 0))),
            "max_runtime_seconds": max(0, min(86400, int(max_runtime_seconds or 0))),
        },
        "manifest_is_authority_grant": False,
        "execution_authorized": False,
        "provider_contact_authorized": False,
        "network_contact_authorized": False,
        "communication_authorized": False,
        "source_mutation_authorized": False,
        "independent_authority_granted": False,
    }
    manifest["manifest_digest"] = _digest(manifest)
    return manifest


def validate_capability_manifest(row: Mapping[str, Any]) -> dict[str, Any]:
    body = deepcopy(dict(row or {}))
    supplied = str(body.pop("manifest_digest", ""))
    checks = {
        "contract": body.get("contract_version") == CONTRACT_VERSION,
        "capability_id": bool(CAPABILITY_ID_RE.fullmatch(str(body.get("capability_id") or ""))),
        "side_effect_class": body.get("side_effect_class") in SIDE_EFFECT_CLASSES,
        "privacy_scope": body.get("privacy_scope") in PRIVACY_SCOPES,
        "approval_class": body.get("approval_class") in APPROVAL_CLASSES,
        "access_surfaces": set(body.get("access_surfaces") or []).issubset(ACCESS_SURFACES),
        "digest": supplied == _digest(body),
        "not_authority": body.get("manifest_is_authority_grant") is False and not any(bool(body.get(k)) for k in (
            "execution_authorized", "provider_contact_authorized", "network_contact_authorized", "communication_authorized", "source_mutation_authorized", "independent_authority_granted"
        )),
    }
    return {"ok": all(checks.values()), "checks": checks, "capability_id": str(body.get("capability_id") or "")}


__all__ = [
    "CONTRACT_VERSION", "SIDE_EFFECT_CLASSES", "PRIVACY_SCOPES", "APPROVAL_CLASSES", "ACCESS_SURFACES",
    "build_capability_manifest", "validate_capability_manifest",
]
