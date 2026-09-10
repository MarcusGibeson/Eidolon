from __future__ import annotations

"""Era 8 trust-zone and untrusted-content defense.

All project/provider/web/memory/generated material is data unless separately
admitted by an established authority path.  This module labels provenance and
produces content-free attack findings without executing embedded instructions.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from security_hardening import untrusted_content_defense, secret_handling

CONTRACT_VERSION = "v2250.9"
TRUST_ZONES = (
    "system_policy", "operator_instruction", "approved_authority_receipt",
    "project_content", "provider_output", "web_content", "memory_record", "generated_artifact",
)
TRUST_LEVEL = {
    "system_policy": 100,
    "operator_instruction": 90,
    "approved_authority_receipt": 85,
    "memory_record": 50,
    "project_content": 30,
    "provider_output": 20,
    "web_content": 15,
    "generated_artifact": 10,
}
_ATTACK_PATTERNS = {
    "prompt_injection": re.compile(r"(?i)(ignore (?:all |the )?(?:previous|prior)|system prompt|developer message|you are now|override instructions)"),
    "authority_forgery": re.compile(r"(?i)(grant (?:me |yourself )?authority|approval (?:is|was) granted|authorization receipt|operator approved|bypass approval)"),
    "secret_exfiltration": re.compile(r"(?i)(api[_ -]?key|password|secret|token|credentials?).{0,40}(send|upload|print|reveal|exfiltrate|post)"),
    "destructive_request": re.compile(r"(?i)(delete all|rm\s+-rf|format disk|wipe (?:the )?(?:drive|system)|disable safety)"),
    "memory_poisoning": re.compile(r"(?i)(remember (?:that )?.{0,80}(?:always|never|authority|password|secret)|store this as fact|treat this as verified)"),
    "scope_expansion": re.compile(r"(?i)(also (?:modify|install|delete|upload|execute)|expand (?:the )?scope|outside (?:the )?(?:workspace|allowlist))"),
}

_DENIED = {
    "embedded_instruction_executed": False,
    "authority_changed": False,
    "approval_forgery_accepted": False,
    "secret_disclosed": False,
    "memory_modified": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def classify_trust_zone(source_kind: str, *, authoritative_receipt: bool = False) -> dict[str, Any]:
    zone = str(source_kind or "").strip().lower()
    if zone not in TRUST_ZONES:
        zone = "generated_artifact"
    level = TRUST_LEVEL[zone]
    authority_claim_present = bool(authoritative_receipt) or zone in {"system_policy", "approved_authority_receipt"}
    result = {
        "ok": True,
        "status": "trust_zone_classified",
        "contract_version": CONTRACT_VERSION,
        "trust_zone": zone,
        "trust_level": level,
        "may_define_authority": False,
        "authority_claim_present": authority_claim_present,
        "authority_validation_owned_by_established_governance": authority_claim_present,
        "classification_is_not_authority_validation": True,
        "operator_instruction_requires_existing_authority_path": zone == "operator_instruction",
        "treated_as_data": True,
        **_DENIED,
    }
    result["classification_digest"] = _digest(result)
    return result


def inspect_untrusted_item(item: Mapping[str, Any]) -> dict[str, Any]:
    text = str(item.get("text") or "")
    source_kind = str(item.get("source_kind") or item.get("source") or "generated_artifact")
    # Untrusted content cannot self-attest into the approved-receipt zone.
    # Receipt validation must happen in the established approval/authority owner.
    zone = classify_trust_zone(source_kind, authoritative_receipt=False)
    findings = [code for code, pattern in _ATTACK_PATTERNS.items() if pattern.search(text)]
    retained = untrusted_content_defense([{"source": zone["trust_zone"], "text": text}])
    secrets = secret_handling([text])
    secret_count = int((secrets.get("payload") or {}).get("finding_count") or 0)
    instruction_like = bool(findings or int((retained.get("payload") or {}).get("authority_redefinition_attempts") or 0))
    result = {
        "ok": True,
        "status": "untrusted_item_inspected",
        "contract_version": CONTRACT_VERSION,
        "trust_zone": zone["trust_zone"],
        "trust_level": zone["trust_level"],
        "content_digest": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "finding_codes": sorted(set(findings)),
        "finding_count": len(set(findings)),
        "secret_pattern_count": secret_count,
        "instruction_like": instruction_like,
        "must_treat_as_data": zone["treated_as_data"],
        "may_define_authority": zone["may_define_authority"] and not instruction_like,
        "raw_content_retained": False,
        "safe_for_reasoning_as_data": True,
        **_DENIED,
    }
    result["inspection_digest"] = _digest(result)
    return result


def evaluate_attack_fixture(items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [inspect_untrusted_item(row) for row in list(items)[:128] if isinstance(row, Mapping)]
    high_codes = {"authority_forgery", "secret_exfiltration", "destructive_request", "scope_expansion"}
    high = [row for row in rows if high_codes.intersection(row.get("finding_codes") or [])]
    result = {
        "ok": True,
        "status": "untrusted_attack_fixture_evaluated",
        "contract_version": CONTRACT_VERSION,
        "item_count": len(rows),
        "finding_count": sum(int(row.get("finding_count") or 0) for row in rows),
        "high_risk_item_count": len(high),
        "items": [{
            "trust_zone": row["trust_zone"], "content_digest": row["content_digest"],
            "finding_codes": row["finding_codes"], "secret_pattern_count": row["secret_pattern_count"],
        } for row in rows],
        "fail_closed_required": bool(high),
        "raw_content_exposed": False,
        **_DENIED,
    }
    result["fixture_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "TRUST_ZONES", "classify_trust_zone", "inspect_untrusted_item", "evaluate_attack_fixture"]
