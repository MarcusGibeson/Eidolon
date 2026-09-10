from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-6-"))

import release_signature_primitives as primitives  # noqa: E402
import self_maintenance as parent  # noqa: E402
from checkpoint_registry import lookup_checkpoint, validate_checkpoint_report  # noqa: E402
from self_maintenance_decomposition import (  # noqa: E402
    AUTHORITY_FLAGS,
    BASELINE_PARENT_LINE_COUNT,
    CONTRACT_VERSION,
    EXTRACTED_NAMES,
    validate_self_maintenance_decomposition,
)
from self_maintenance_decomposition_checkpoint import build_self_maintenance_decomposition_checkpoint  # noqa: E402

from release_authority import WORKING_SOURCE_VERSION, PREVIOUS_WORKING_SOURCE_VERSION
checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


validation = validate_self_maintenance_decomposition(source_root=ROOT)
checkpoint = build_self_maintenance_decomposition_checkpoint(source_root=ROOT)
checkpoint_validation = validate_checkpoint_report(checkpoint, source_root=ROOT)
parent_source = (ROOT / "conscious_agent/self_maintenance.py").read_text(encoding="utf-8")
child_source = (ROOT / "conscious_agent/release_signature_primitives.py").read_text(encoding="utf-8")
parent_tree = ast.parse(parent_source)
child_tree = ast.parse(child_source)
parent_defs = {node.name for node in parent_tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
child_defs = {node.name for node in child_tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}

require(CONTRACT_VERSION == "v1250.6")
require(primitives.CONTRACT_VERSION == "v1250.6")
require(BASELINE_PARENT_LINE_COUNT == 46910)
require(len(EXTRACTED_NAMES) == 18)
require(validation["ok"] is True)
require(validation["status"] == "self_maintenance_decomposed")
require(validation["passed"] == validation["total"] == 11)
require(all(validation["checks"].values()))
require(validation["parent_line_count"] < 46760)
require(300 <= validation["extracted_line_count"] <= 500)
require(validation["extracted_name_count"] == 18)
require(len(validation["validation_digest"]) == 64)
require(set(EXTRACTED_NAMES).isdisjoint(parent_defs))
require(set(EXTRACTED_NAMES).issubset(child_defs))
require("from release_signature_primitives import (" in parent_source)
require("BEGIN PRIVATE KEY" not in child_source)
require("BEGIN PUBLIC KEY" in child_source)
require("subprocess" not in child_source)
require("requests" not in child_source)
require("urllib" not in child_source)
require("shell=True" not in child_source)
require(primitives._is_hex_sha256("a" * 64) is True)
require(primitives._is_hex_sha256("A" * 64) is False)
require(primitives._is_hex_sha256("a" * 63) is False)
require(primitives._canonical_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}')
require(primitives._source_json_sanitized({"updated_at": "x", "value": 1}) == {"value": 1})
require(primitives._source_json_sanitized([{"last_run_at": "x", "value": 2}]) == [{"value": 2}])
require(primitives._pem_body_bytes(primitives._SIGNATURE_FIXTURE_PUBLIC_KEY_PEM))
require(primitives._SIGNATURE_FIXTURE_PUBLIC_KEY_FINGERPRINT == hashlib.sha256(primitives._pem_body_bytes(primitives._SIGNATURE_FIXTURE_PUBLIC_KEY_PEM)).hexdigest())
try:
    primitives._load_public_rsa_key(None)
except ValueError as error:
    require("public key path is required" in str(error))
else:
    require(False)
require(primitives._mgf1(b"seed", 33) == parent._mgf1(b"seed", 33))
require(parent._canonical_bytes({"x": 1}) == primitives._canonical_bytes({"x": 1}))
require(parent._source_json_sanitized({"updated_at": "x", "x": 1}) == {"x": 1})
require(parent.SIGNATURE_SCHEMA_VERSION == primitives.SIGNATURE_SCHEMA_VERSION == "1032.0")
require(parent.SIGNING_PAYLOAD_SCHEMA_VERSION == primitives.SIGNING_PAYLOAD_SCHEMA_VERSION == "1032.0")
require(parent.TRUST_ROOT_CONFIG_PATH == primitives.TRUST_ROOT_CONFIG_PATH)
require(parent._SIGNATURE_FIXTURE_SIGNATURE == primitives._SIGNATURE_FIXTURE_SIGNATURE)
require(parent._rsa_pss_sha256_verify is primitives._rsa_pss_sha256_verify)
require(parent._trusted_fingerprints is primitives._trusted_fingerprints)
require(parent._signature_failure_codes([], valid=False, trusted=False, supplied=False) == ["unsigned"])
require(parent._normalized_signature_trust_result(supplied=False, valid=False, trusted=False, status="warn", public_fingerprint=None, rows=[])["trust_level"] == "unsigned")
require(parent.build_signature_fixture_verification(save=False)["status"] == "pass")
require(lookup_checkpoint("1250.6") is not None)
require(lookup_checkpoint("1250.6").title == "Self-Maintenance Signature Primitive Decomposition")
require(checkpoint["ok"] is True)
require(checkpoint["checkpoint_version"] == "1250.6")
require(checkpoint["status"] == "self_maintenance_decomposition_ready")
require(checkpoint["passed"] == checkpoint["total"] == 3)
require(checkpoint["details"]["parent_line_count"] == validation["parent_line_count"])
require(checkpoint["details"]["extracted_line_count"] == validation["extracted_line_count"])
require(checkpoint_validation["ok"] is True)
require(checkpoint_validation["passed"] == checkpoint_validation["total"])
require(f'WORKING_SOURCE_VERSION = "{WORKING_SOURCE_VERSION}"' in (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8"))
require(f'PREVIOUS_WORKING_SOURCE_VERSION = "{PREVIOUS_WORKING_SOURCE_VERSION}"' in (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8"))
for key, expected in AUTHORITY_FLAGS.items():
    require(expected is False)
    require(validation[key] is False)
    require(checkpoint.get(key, False) is False)

result = {"suite": "v1250.6-self-maintenance-signature-primitive-decomposition", "ok": all(checks), "passed": sum(checks), "total": len(checks)}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
