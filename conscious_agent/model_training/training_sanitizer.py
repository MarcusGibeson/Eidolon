from __future__ import annotations

"""Deterministic privacy sanitizer for candidate training records."""

import re
from pathlib import Path
from typing import Any, Mapping

from model_training.training_record import _digest, _seal, _atomic_json, load_training_record, training_record_path

CONTRACT_VERSION = "v2503.4.20"
_SECRET_KEY = re.compile(r"(?:password|passwd|secret|token|api[_-]?key|authorization|cookie|credential|session[_-]?key)", re.I)
_SECRET_VALUE_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:Bearer\s+)[A-Za-z0-9._~+/=-]{12,}\b", re.I),
    re.compile(r"\b[A-Fa-f0-9]{40,}\b"),
]
_WINDOWS_PATH = re.compile(r"\b[A-Za-z]:\\(?:[^\s<>:\"|?*]+\\)*[^\s<>:\"|?*]*")
_HOME_PATH = re.compile(r"(?<![A-Za-z0-9])/(?:home|Users)/[^\s/]+(?:/[^\s]*)?")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")
_IPV4 = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_URL_CREDENTIAL = re.compile(r"(?i)\b(?:https?|ftp)://[^\s/@:]+:[^\s/@]+@")
_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)


def _sanitize_text(text: str) -> tuple[str, list[str]]:
    value = str(text)
    findings: list[str] = []
    for code, pattern, replacement in [
        ("secret_value", _SECRET_VALUE_PATTERNS[0], "[REDACTED_SECRET]"),
        ("bearer_token", _SECRET_VALUE_PATTERNS[1], "[REDACTED_SECRET]"),
        ("long_hex_secret", _SECRET_VALUE_PATTERNS[2], "[REDACTED_SECRET]"),
        ("windows_path", _WINDOWS_PATH, "[REDACTED_PATH]"),
        ("home_path", _HOME_PATH, "[REDACTED_PATH]"),
        ("email", _EMAIL, "[REDACTED_EMAIL]"),
        ("phone", _PHONE, "[REDACTED_PHONE]"),
        ("ipv4", _IPV4, "[REDACTED_IP]"),
        ("url_credential", _URL_CREDENTIAL, "[REDACTED_URL_CREDENTIAL]"),
        ("private_key", _PRIVATE_KEY, "[REDACTED_PRIVATE_KEY]"),
    ]:
        replaced, count = pattern.subn(replacement, value)
        if count:
            findings.append(code)
            value = replaced
    return value, findings


def _sanitize(value: Any, path: tuple[str, ...] = ()) -> tuple[Any, list[str]]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            name = str(key)
            if _SECRET_KEY.search(name):
                clean[name] = "[REDACTED_SECRET]"
                findings.append("secret_key:" + ".".join(path + (name,)))
                continue
            sanitized, nested = _sanitize(item, path + (name,))
            clean[name] = sanitized
            findings.extend(nested)
        return clean, findings
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            sanitized, nested = _sanitize(item, path + (str(index),))
            result.append(sanitized)
            findings.extend(nested)
        return result, findings
    if isinstance(value, tuple):
        sanitized, nested = _sanitize(list(value), path)
        return sanitized, nested
    if isinstance(value, str):
        return _sanitize_text(value)
    return value, findings


def sanitize_training_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record or not str(record.get("record_id") or "").startswith("trn_"):
        raise ValueError("invalid_training_record")
    clean, findings = _sanitize(dict(record))
    clean.pop("record_digest", None)
    clean["contract_version"] = CONTRACT_VERSION
    clean["sanitized"] = True
    clean["approved_for_training"] = False
    clean["sanitization"] = {
        "finding_count": len(findings),
        "finding_codes": sorted(set(findings))[:64],
        "raw_record_digest": str(record.get("record_digest") or ""),
        "sanitized_content_digest": _digest({k: v for k, v in clean.items() if k != "sanitization"}),
        "human_review_required_before_training": True,
    }
    return _seal(clean)


def sanitize_stored_training_record(record_id: str, *, runtime_root: str | Path | None) -> dict[str, Any]:
    raw = load_training_record(record_id, runtime_root=runtime_root, stage="raw")
    if not raw:
        return {"ok": False, "status": "training_raw_record_missing_or_invalid"}
    clean = sanitize_training_record(raw)
    path = training_record_path(record_id, runtime_root=runtime_root, stage="sanitized")
    _atomic_json(path, clean)
    return {"ok": True, "status": "training_record_sanitized", "record": clean, "runtime_path": str(path)}
