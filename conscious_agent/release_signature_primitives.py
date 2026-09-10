from __future__ import annotations

"""Pure release-signature primitives extracted from ``self_maintenance`` in v1250.6.

The module contains canonical encoding, RSA-PSS verification, trust-root parsing,
and fixture validation only. It does not sign artifacts, create keys, contact a
provider, publish a release, or grant authority.
"""

import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any

try:
    from paths import DATA_DIR
    from release_installation import _ok_from, _status_from
except ImportError:
    from paths import DATA_DIR  # type: ignore
    from release_installation import _ok_from, _status_from  # type: ignore

CONTRACT_VERSION = "v1250.6"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default

SIGNING_STATUS_VALUES = {"unsigned", "signed", "signed_untrusted", "invalid", "unsupported"}

SIGNATURE_ALGORITHMS = {"rsa-pss-sha256"}

SIGNATURE_SCHEMA_VERSION = "1032.0"

SIGNING_PAYLOAD_SCHEMA_VERSION = "1032.0"

PUBLIC_KEY_POLICY_SCHEMA_VERSION = "1032.0"

TRUST_ROOT_CONFIG_SCHEMA_VERSION = "1032.0"

SIGNING_PAYLOAD_EXPORT_SCHEMA_VERSION = "1032.0"

PUBLISH_GATE_SCHEMA_VERSION = "1032.0"

TRUST_ROOT_CONFIG_PATH = DATA_DIR / "signing" / "trusted_public_keys.json"

_SIGNATURE_FIXTURE_PAYLOAD = {
    "schema_version": SIGNING_PAYLOAD_SCHEMA_VERSION,
    "project_name": "Eidolon",
    "release_version": "fixture",
    "package_name": "fixture.zip",
    "package_sha256": "0" * 64,
    "manifest_sha256": "1" * 64,
    "evidence_sha256": "2" * 64,
}

_SIGNATURE_FIXTURE_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA+Ck8IRvh2jR6yTyofa8g
eQIWu7y7w0eigNB9ByJrpzYvRWqM1gv5DT6+gHgvtuAtu7COxF3ScyMsbb6j5yWD
32YLVx1D9s/vXIDY6lAB8QVeHk4Gs7cGNXeR30PZkUIzBNdK2x1L5ySJ0x2+V2DZ
zIWdyqNLPgFvdvxXtiI2aKWIO6hCz71r39xw43HHQ7+080uyHMv3ePpDhjfSHwsJ
TK8XXjdMuOHVLCe602CI+JF8NQphjGq/vJaFQnMUvrzjslv5BIhQU7H8UtEfWyHC
t5JUALxdEWksX7NA3vlXDlv7PJDgdw0RZGvUR2MbBMCvR448LO4FTQdRcvpnoGCE
2wIDAQAB
-----END PUBLIC KEY-----
"""

_SIGNATURE_FIXTURE_PUBLIC_KEY_FINGERPRINT = "457c8051845c51d44e2163bc62e249babfdf0b19f00543a27ff6786460feee35"

_SIGNATURE_FIXTURE_SIGNATURE = "mlROO6asdktr6PZIYlKpg59urKgs7VJHEjwtoZcD+2ek7945TpnyxBkNQnPh/URrNb9226dLZY12fR4CUYQPSGmG3JIUnTkD/P61RchTlbajIIOkyt/Zujefqi8ziHgQO1o/c8eiIEGxxF31PzMxBLALZ1g9v8giY3T+4q54SMg6qul1sHwCmMq56gTddJ/Nh/RmVqV0H2FiIbC/qfNRQBe9EdMTfoZ3Dj+iLXMuHTqcygeHAwHk1gFeLU0/+a5YXrZam9NXyafQfLgRcybv+foITbVsO0JOolrJW2KXy5mkLy2BPdELKuzFDV+l3RcaWBZ6+Sq3RY3K6vrZsKiuzw=="

def _is_hex_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))

def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

def _source_json_sanitized(value: Any) -> Any:
    """Return package-safe source defaults with runtime timestamps stripped.

    This mirrors the release-packaging sanitizer and keeps signing inputs away from
    mutable local metadata. Human civilization has enough timestamp drift already.
    """
    volatile_keys = {"updated_at", "last_health_checked_at", "last_run_at", "last_seen_at", "last_modified", "last_opened_at"}
    if isinstance(value, dict):
        return {key: _source_json_sanitized(val) for key, val in value.items() if key not in volatile_keys}
    if isinstance(value, list):
        return [_source_json_sanitized(item) for item in value]
    return value

def _read_signature_json(signature_path: str | None) -> dict[str, Any] | None:
    if not signature_path:
        return None
    try:
        return json.loads(Path(signature_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"_read_error": str(error)}

def _pem_body_bytes(text: str) -> bytes:
    import base64
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("-----")]
    return base64.b64decode("".join(lines), validate=True)

def _der_len(data: bytes, offset: int) -> tuple[int, int]:
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    n = first & 0x7F
    if n == 0 or n > 4:
        raise ValueError("unsupported DER length")
    return int.from_bytes(data[offset:offset+n], "big"), offset + n

def _der_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
    tag = data[offset]
    length, value_offset = _der_len(data, offset + 1)
    end = value_offset + length
    if end > len(data):
        raise ValueError("truncated DER value")
    return tag, data[value_offset:end], end

def _der_integer(value: bytes) -> int:
    if not value:
        raise ValueError("empty DER integer")
    if value[0] == 0:
        value = value[1:]
    return int.from_bytes(value, "big")

def _parse_rsa_public_key_from_der(der: bytes) -> tuple[int, int]:
    tag, seq, end = _der_tlv(der, 0)
    if tag != 0x30 or end != len(der):
        raise ValueError("expected DER sequence")
    # PKCS#1 RSA PUBLIC KEY: SEQUENCE { INTEGER n, INTEGER e }
    try:
        tag_n, n_bytes, off = _der_tlv(seq, 0)
        tag_e, e_bytes, off = _der_tlv(seq, off)
        if tag_n == 0x02 and tag_e == 0x02 and off == len(seq):
            return _der_integer(n_bytes), _der_integer(e_bytes)
    except Exception:
        pass
    # SubjectPublicKeyInfo: SEQUENCE { AlgorithmIdentifier, BIT STRING RSAPublicKey }
    tag_alg, _alg, off = _der_tlv(seq, 0)
    tag_bit, bit_string, off = _der_tlv(seq, off)
    if tag_alg != 0x30 or tag_bit != 0x03 or off != len(seq) or not bit_string or bit_string[0] != 0:
        raise ValueError("unsupported public key DER format")
    return _parse_rsa_public_key_from_der(bit_string[1:])

def _load_public_rsa_key(public_key_path: str | None) -> tuple[int, int, str]:
    if not public_key_path:
        raise ValueError("public key path is required for signed verification")
    text = Path(public_key_path).read_text(encoding="utf-8")
    if "PRIVATE KEY" in text:
        raise ValueError("private key material is not accepted")
    der = _pem_body_bytes(text)
    n, e = _parse_rsa_public_key_from_der(der)
    fingerprint = hashlib.sha256(der).hexdigest()
    return n, e, fingerprint

def _mgf1(seed: bytes, length: int) -> bytes:
    output = b""
    counter = 0
    while len(output) < length:
        output += hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        counter += 1
    return output[:length]

def _rsa_pss_sha256_verify(public_key_path: str | None, message: bytes, signature_b64: str) -> tuple[bool, str, str | None]:
    import base64
    try:
        n, e, fingerprint = _load_public_rsa_key(public_key_path)
        signature = base64.b64decode(signature_b64, validate=True)
        mod_bits = n.bit_length()
        k = (mod_bits + 7) // 8
        if len(signature) != k:
            return False, "signature length does not match public key modulus", fingerprint
        s = int.from_bytes(signature, "big")
        if s >= n:
            return False, "signature representative out of range", fingerprint
        em_bits = mod_bits - 1
        em_len = (em_bits + 7) // 8
        encoded = pow(s, e, n).to_bytes(k, "big")[-em_len:]
        h_len = hashlib.sha256().digest_size
        salt_len = h_len
        if em_len < h_len + salt_len + 2:
            return False, "encoded message too short for RSA-PSS-SHA256", fingerprint
        if encoded[-1] != 0xBC:
            return False, "RSA-PSS trailer byte mismatch", fingerprint
        masked_db = encoded[:em_len - h_len - 1]
        h = encoded[em_len - h_len - 1:-1]
        leading_bits = 8 * em_len - em_bits
        if leading_bits and masked_db[0] & (0xFF << (8 - leading_bits)):
            return False, "RSA-PSS leading bits are not zero", fingerprint
        db_mask = _mgf1(h, em_len - h_len - 1)
        db = bytes(a ^ b for a, b in zip(masked_db, db_mask))
        if leading_bits:
            db = bytes([db[0] & (0xFF >> leading_bits)]) + db[1:]
        ps_len = em_len - h_len - salt_len - 2
        if db[:ps_len] != b"\x00" * ps_len or db[ps_len] != 0x01:
            return False, "RSA-PSS padding structure mismatch", fingerprint
        salt = db[-salt_len:]
        m_hash = hashlib.sha256(message).digest()
        expected_h = hashlib.sha256(b"\x00" * 8 + m_hash + salt).digest()
        if h != expected_h:
            return False, "RSA-PSS hash mismatch", fingerprint
        return True, "RSA-PSS-SHA256 signature verified with public key only", fingerprint
    except Exception as error:
        return False, str(error), None

def _load_public_trust_root_config() -> dict[str, Any]:
    default = {
        "schema_version": TRUST_ROOT_CONFIG_SCHEMA_VERSION,
        "trusted_public_keys": [],
        "private_key_material_allowed": False,
        "notes": ["Public trust roots only. Do not store private keys here, because that would be security as performance art."],
    }
    value = _read_json(TRUST_ROOT_CONFIG_PATH, default)
    if not isinstance(value, dict):
        return default
    value.setdefault("schema_version", TRUST_ROOT_CONFIG_SCHEMA_VERSION)
    value.setdefault("trusted_public_keys", [])
    value.setdefault("private_key_material_allowed", False)
    return value

def _trusted_fingerprints(trusted_fingerprint: str | None = None) -> list[str]:
    values: list[str] = []
    if trusted_fingerprint:
        values.extend([item.strip().lower() for item in trusted_fingerprint.split(",") if item.strip()])
    for source_path in (TRUST_ROOT_CONFIG_PATH, DATA_DIR / "signing_trust_policy.json"):
        policy = _read_json(source_path, {})
        for item in policy.get("trusted_public_keys", []) if isinstance(policy, dict) else []:
            if isinstance(item, dict) and _is_hex_sha256(str(item.get("fingerprint", ""))):
                values.append(str(item["fingerprint"]).lower())
    return sorted(set(values))

def _signature_sidecar_validation_rows(signature: dict[str, Any], signing_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    required = ["schema_version", "package_sha256", "manifest_sha256", "evidence_sha256", "signature_algorithm", "signature", "public_key_fingerprint", "signed_at", "signed_by"]
    missing = [key for key in required if key not in signature]
    rows.append({"name": "signature-required-fields", "status": "pass" if not missing else "blocked", "message": f"missing={', '.join(missing) or 'none'}"})
    rows.append({"name": "signature-schema", "status": "pass" if signature.get("schema_version") == SIGNATURE_SCHEMA_VERSION else "blocked", "message": str(signature.get("schema_version"))})
    rows.append({"name": "signature-algorithm", "status": "pass" if signature.get("signature_algorithm") in SIGNATURE_ALGORITHMS else "blocked", "message": str(signature.get("signature_algorithm"))})
    for key, payload_key in (("package_sha256", "package_sha256"), ("manifest_sha256", "manifest_sha256"), ("evidence_sha256", "evidence_sha256")):
        rows.append({"name": f"signature-{key}-binding", "status": "pass" if signature.get(key) == signing_payload.get(payload_key) else "blocked", "message": str(signature.get(key))})
    sig_text = signature.get("signature")
    rows.append({"name": "signature-bytes", "status": "pass" if isinstance(sig_text, str) and bool(sig_text.strip()) else "blocked", "message": "base64 signature present" if isinstance(sig_text, str) and sig_text.strip() else "missing"})
    rows.append({"name": "signature-fingerprint-format", "status": "pass" if _is_hex_sha256(signature.get("public_key_fingerprint")) else "blocked", "message": str(signature.get("public_key_fingerprint"))})
    rows.append({"name": "signature-signer-label", "status": "pass" if isinstance(signature.get("signed_by"), str) and signature.get("signed_by").strip() else "blocked", "message": str(signature.get("signed_by"))})
    rows.append({"name": "signature-timestamp", "status": "pass" if isinstance(signature.get("signed_at"), str) and signature.get("signed_at").strip() else "blocked", "message": str(signature.get("signed_at"))})
    return rows

def _signature_failure_codes(rows: list[dict[str, Any]], valid: bool, trusted: bool, supplied: bool) -> list[str]:
    if not supplied:
        return ["unsigned"]
    codes: list[str] = []
    blocked_names = {str(row.get("name", "")) for row in rows if str(row.get("status", "")).lower() in {"blocked", "failed", "fail"}}
    if "signature-file" in blocked_names:
        codes.append("malformed_signature_sidecar")
    if "signature-schema" in blocked_names or "signature-required-fields" in blocked_names:
        codes.append("invalid_signature_schema")
    if "signature-algorithm" in blocked_names:
        codes.append("unsupported_algorithm")
    if "signature-package_sha256-binding" in blocked_names:
        codes.append("package_hash_mismatch")
    if "signature-manifest_sha256-binding" in blocked_names:
        codes.append("manifest_hash_mismatch")
    if "signature-evidence_sha256-binding" in blocked_names:
        codes.append("evidence_hash_mismatch")
    if "signature-bytes" in blocked_names:
        codes.append("missing_signature_bytes")
    if "public-key-fingerprint" in blocked_names:
        codes.append("public_key_fingerprint_mismatch")
    if "cryptographic-verification" in blocked_names and not valid:
        codes.append("cryptographic_verification_failed")
    if valid and not trusted:
        codes.append("unknown_signer_fingerprint")
    return sorted(set(codes)) or ([] if trusted else ["invalid_signature"])

def _normalized_signature_trust_result(*, supplied: bool, valid: bool, trusted: bool, status: str, public_fingerprint: str | None, rows: list[dict[str, Any]]) -> dict[str, Any]:
    trust_level = "trusted" if trusted else "valid_untrusted" if valid else "invalid" if supplied else "unsigned"
    signing_status = "signed" if trusted else "signed_untrusted" if valid else "invalid" if supplied else "unsigned"
    failure_codes = _signature_failure_codes(rows, valid=valid, trusted=trusted, supplied=supplied)
    return {
        "operational_ok": status in {"pass", "warn"},
        "signed": bool(valid),
        "signing_status": signing_status,
        "signature_valid": bool(valid),
        "signature_trusted": bool(trusted),
        "safe_to_publish": bool(trusted and status == "pass"),
        "trust_level": trust_level,
        "public_key_fingerprint": public_fingerprint,
        "failure_codes": failure_codes,
    }

def _verify_signature_payload_fixture(payload: dict[str, Any], signature: dict[str, Any], public_key_pem: str, trusted_fingerprint: str | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="eidolon-signature-fixture-") as temp:
        public_key_path = Path(temp) / "fixture_public_key.pem"
        public_key_path.write_text(public_key_pem, encoding="utf-8")
        rows = _signature_sidecar_validation_rows(signature, payload)
        valid = False
        public_fingerprint = None
        verify_message = "signature not attempted"
        if _status_from(rows) in {"pass", "warn"} and isinstance(signature.get("signature"), str):
            valid, verify_message, public_fingerprint = _rsa_pss_sha256_verify(str(public_key_path), _canonical_bytes(payload), str(signature.get("signature")))
        rows.append({"name": "cryptographic-verification", "status": "pass" if valid else "blocked", "message": verify_message})
        if public_fingerprint:
            rows.append({"name": "public-key-fingerprint", "status": "pass" if signature.get("public_key_fingerprint") == public_fingerprint else "blocked", "message": public_fingerprint})
        trusted_values = [trusted_fingerprint.lower()] if trusted_fingerprint else []
        trusted = bool(valid and public_fingerprint and public_fingerprint.lower() in trusted_values)
        rows.append({"name": "trust-policy", "status": "pass" if trusted else "warn" if valid else "blocked", "message": "trusted fixture fingerprint accepted" if trusted else "fixture signature valid but not trusted" if valid else "fixture signature did not verify"})
        status = _status_from(rows)
        result = _normalized_signature_trust_result(supplied=True, valid=valid, trusted=trusted, status=status, public_fingerprint=public_fingerprint, rows=rows)
        return {**result, "status": status, "ok": _ok_from(status), "rows": rows}

__all__ = [
    'PUBLIC_KEY_POLICY_SCHEMA_VERSION',
    'PUBLISH_GATE_SCHEMA_VERSION',
    'SIGNATURE_ALGORITHMS',
    'SIGNATURE_SCHEMA_VERSION',
    'SIGNING_PAYLOAD_EXPORT_SCHEMA_VERSION',
    'SIGNING_PAYLOAD_SCHEMA_VERSION',
    'SIGNING_STATUS_VALUES',
    'TRUST_ROOT_CONFIG_PATH',
    'TRUST_ROOT_CONFIG_SCHEMA_VERSION',
    '_SIGNATURE_FIXTURE_PAYLOAD',
    '_SIGNATURE_FIXTURE_PUBLIC_KEY_FINGERPRINT',
    '_SIGNATURE_FIXTURE_PUBLIC_KEY_PEM',
    '_SIGNATURE_FIXTURE_SIGNATURE',
    '_canonical_bytes',
    '_der_integer',
    '_der_len',
    '_der_tlv',
    '_is_hex_sha256',
    '_load_public_rsa_key',
    '_load_public_trust_root_config',
    '_mgf1',
    '_normalized_signature_trust_result',
    '_parse_rsa_public_key_from_der',
    '_pem_body_bytes',
    '_read_signature_json',
    '_rsa_pss_sha256_verify',
    '_signature_failure_codes',
    '_signature_sidecar_validation_rows',
    '_source_json_sanitized',
    '_trusted_fingerprints',
    '_verify_signature_payload_fixture',
]
