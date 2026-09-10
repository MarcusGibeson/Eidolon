from __future__ import annotations

"""Attested evidence handoff for one authoritative verification graph.

The outer verifier owns expensive execution. Consumers accept its reports only
when the complete bundle and every stage receipt match the current source tree,
the expected command graph, and an invocation-scoped HMAC key.
"""

import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from release_metadata import RUNTIME_VERSION

EVIDENCE_SCHEMA = "eidolon-verification-evidence-v2"
STAGE_RECEIPT_SCHEMA = "eidolon-verification-stage-receipt-v1"
ATTESTATION_ALGORITHM = "hmac-sha256"
MAX_EVIDENCE_AGE_SECONDS = 30 * 60

ENV_EVIDENCE_FILE = "EIDOLON_VERIFICATION_EVIDENCE_FILE"
ENV_ATTESTATION_KEY = "EIDOLON_VERIFICATION_EVIDENCE_KEY"
ENV_INVOCATION_NONCE = "EIDOLON_VERIFICATION_INVOCATION_NONCE"
ENV_EXPECTED_PRODUCER = "EIDOLON_VERIFICATION_EXPECTED_PRODUCER"
ENV_SOURCE_SNAPSHOT = "EIDOLON_VERIFICATION_SOURCE_SNAPSHOT"
ENV_EVIDENCE_PURPOSE = "EIDOLON_VERIFICATION_EVIDENCE_PURPOSE"

DASHBOARD_ROUTE_TIMEOUTS: dict[str, int] = {
    "/": 60,
    "/stabilization": 90,
    "/doctor": 120,
    "/api-info": 60,
    "/stable-loop": 60,
    "/development-campaigns": 60,
}

PURPOSE_STAGE_NAMES: dict[str, tuple[str, ...]] = {
    "release": (
        "python-compile",
        "version-inventory",
        "corrective-suite",
        "import-compatibility",
        "dashboard-http-probe",
    ),
    "report-performance": (
        "version-inventory",
        "corrective-suite",
    ),
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime | None = None) -> str:
    current = value or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat()


def new_invocation_nonce() -> str:
    return secrets.token_hex(16)


def new_attestation_key() -> str:
    return secrets.token_hex(32)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")


def json_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _hmac_sha256(value: Any, key: str) -> str:
    return hmac.new(key.encode("utf-8"), _canonical_bytes(value), hashlib.sha256).hexdigest()


def _key_id(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _without_attestation(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "attestation"}


def sign_attested_object(value: dict[str, Any], key: str) -> dict[str, Any]:
    signed = dict(value)
    signed["attestation"] = {
        "algorithm": ATTESTATION_ALGORITHM,
        "key_id": _key_id(key),
        "digest": _hmac_sha256(_without_attestation(signed), key),
    }
    return signed


def _attestation_valid(value: dict[str, Any], key: str) -> bool:
    attestation = value.get("attestation")
    if not isinstance(attestation, dict):
        return False
    if attestation.get("algorithm") != ATTESTATION_ALGORITHM or attestation.get("key_id") != _key_id(key):
        return False
    expected = _hmac_sha256(_without_attestation(value), key)
    return hmac.compare_digest(str(attestation.get("digest") or ""), expected)


def source_snapshot(root: str | Path) -> dict[str, Any]:
    """Hash the authoritative source-package scope without runtime state."""
    from package_integrity import iter_source_tree_entries

    project_root = Path(root).resolve()
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for relative in iter_source_tree_entries(project_root):
        path = project_root / relative
        try:
            entries.append({
                "path": relative,
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        except OSError as exc:
            errors.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})
    return {
        "root": str(project_root),
        "file_count": len(entries),
        "entries_sha256": json_sha256(entries),
        "errors": errors,
    }


def source_snapshot_digest(root: str | Path) -> str:
    snapshot = source_snapshot(root)
    if snapshot["errors"]:
        raise OSError(f"source snapshot failed: {snapshot['errors'][:3]}")
    return str(snapshot["entries_sha256"])


def expected_stage_commands(
    root: str | Path,
    *,
    purpose: str = "release",
    python_executable: str | None = None,
) -> dict[str, list[list[str]]]:
    project_root = Path(root).resolve()
    python = str(Path(python_executable or sys.executable).resolve())
    inventory = [python, "-m", "conscious_agent.version_metadata_inventory", "--json"]
    if purpose == "release":
        inventory = [
            python,
            "-m",
            "conscious_agent.version_metadata_inventory",
            "--root",
            str(project_root),
            "--json",
        ]
    commands: dict[str, list[list[str]]] = {
        "python-compile": [[python, "tools/verification_source_compile.py"]],
        "version-inventory": [inventory],
        "corrective-suite": [[python, "tools/pre_v1078_9_corrective_tests.py", "--json"]],
        "import-compatibility": [[python, "tools/import_compatibility_quick.py"]],
        "dashboard-http-probe": [[
            python,
            str(project_root / "tools" / "dashboard_probe_worker.py"),
            "--suite-json",
            json.dumps(DASHBOARD_ROUTE_TIMEOUTS, sort_keys=True),
        ]],
    }
    required = PURPOSE_STAGE_NAMES.get(purpose, ())
    return {name: commands[name] for name in required}


def _all_true_mapping(value: Any) -> bool:
    return isinstance(value, dict) and bool(value) and all(item is True for item in value.values())


def required_stage_checks(name: str, report: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {
        "report-object": isinstance(report, dict),
        "functional-pass": report.get("ok") is True and report.get("status") == "pass",
    }
    if name == "python-compile":
        checks.update({
            "process-exited-zero": report.get("return_code") == 0 and report.get("timed_out") is False,
            "cache-cleaned": report.get("cache_cleanup_ok") is True,
            "bytecode-measured": report.get("source_tree_bytecode_measured") is True,
            "source-bytecode-unchanged": report.get("source_tree_bytecode_written") is False,
            "source-tree-unchanged": report.get("source_tree_mutation_count") == 0,
            "single-compile-process": report.get("compile_execution_count") == 1,
        })
    elif name == "version-inventory":
        digest = str(report.get("scanned_source_scope_sha256") or "")
        checks.update({
            "runtime-version-current": report.get("version") == RUNTIME_VERSION,
            "complete-source-scope-digest": len(digest) == 64,
            "inventory-files-scanned": int(report.get("scanned_source_file_count") or 0) > 0,
        })
    elif name == "corrective-suite":
        checks.update({
            "all-corrective-checks-pass": _all_true_mapping(report.get("checks")),
            "operator-evidence-untouched": report.get("real_evidence_touched") is False,
            "no-nested-full-compile": report.get("full_project_compile_execution_count") == 0,
        })
    elif name == "import-compatibility":
        results = report.get("results")
        checks.update({
            "imports-mode": report.get("mode") == "imports",
            "all-import-cases-pass": (
                isinstance(results, list)
                and bool(results)
                and all(isinstance(row, dict) and row.get("ok") is True for row in results)
            ),
            "import-counts-match": (
                int(report.get("check_count") or 0) > 0
                and report.get("check_count") == report.get("passed_count")
            ),
        })
    elif name == "dashboard-http-probe":
        routes = report.get("routes")
        checks.update({
            "all-required-routes-present": isinstance(routes, dict) and set(routes) == set(DASHBOARD_ROUTE_TIMEOUTS),
            "all-required-routes-pass": (
                isinstance(routes, dict)
                and set(routes) == set(DASHBOARD_ROUTE_TIMEOUTS)
                and all(isinstance(row, dict) and row.get("ok") is True for row in routes.values())
            ),
            "single-dashboard-stage": report.get("stage_invocation_count") == 1,
            "expected-dashboard-workers": report.get("subprocess_execution_count") == 1,
        })
    else:
        checks["known-stage"] = False
    return checks


def build_stage_receipt(
    name: str,
    *,
    producer: str,
    invocation_nonce: str,
    source_snapshot_before: str,
    source_snapshot_after: str,
    commands: Iterable[Iterable[str]],
    report: dict[str, Any],
    started_at: str,
    finished_at: str,
    elapsed_seconds: float | None,
    return_code: int | None,
    timed_out: bool,
    subprocess_execution_count: int,
    attestation_key: str,
) -> dict[str, Any]:
    normalized_commands = [[str(part) for part in command] for command in commands]
    receipt = {
        "schema": STAGE_RECEIPT_SCHEMA,
        "name": name,
        "producer": f"{producer}/{name}",
        "invocation_nonce": invocation_nonce,
        "execution_id": secrets.token_hex(16),
        "execution_count": 1,
        "subprocess_execution_count": int(subprocess_execution_count),
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": elapsed_seconds,
        "return_code": return_code,
        "timed_out": bool(timed_out),
        "commands": normalized_commands,
        "command_sha256": json_sha256(normalized_commands),
        "source_snapshot_before_sha256": source_snapshot_before,
        "source_snapshot_after_sha256": source_snapshot_after,
        "source_snapshot_unchanged": source_snapshot_before == source_snapshot_after,
        "report": report,
        "report_sha256": json_sha256(report),
        "required_checks": required_stage_checks(name, report),
    }
    return sign_attested_object(receipt, attestation_key)


def build_evidence_bundle(
    root: str | Path,
    *,
    producer: str,
    invocation_nonce: str,
    source_snapshot_sha256: str,
    attestation_key: str,
    stages: dict[str, Any],
    purpose: str = "release",
    generated_at: str | None = None,
) -> dict[str, Any]:
    required_stages = list(PURPOSE_STAGE_NAMES.get(purpose, ()))
    bundle = {
        "schema": EVIDENCE_SCHEMA,
        "purpose": purpose,
        "version": RUNTIME_VERSION,
        "root": str(Path(root).resolve()),
        "producer": producer,
        "invocation_nonce": invocation_nonce,
        "source_snapshot_sha256": source_snapshot_sha256,
        "generated_at": generated_at or isoformat_utc(),
        "required_stages": required_stages,
        "stages": dict(stages),
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_review_required": True,
    }
    bundle["bundle_sha256"] = json_sha256(bundle)
    return sign_attested_object(bundle, attestation_key)


def write_evidence_bundle(path: str | Path, bundle: dict[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(bundle, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return destination


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_stage_receipt(
    receipt: Any,
    *,
    name: str,
    producer: str,
    invocation_nonce: str,
    source_snapshot_sha256: str,
    commands: list[list[str]],
    attestation_key: str,
    generated_at: datetime,
    now: datetime,
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        return {"valid": False, "checks": {"object": False}, "errors": ["stage receipt is not an object"]}
    report = receipt.get("report")
    started = _parse_timestamp(receipt.get("started_at"))
    finished = _parse_timestamp(receipt.get("finished_at"))
    expected_checks = required_stage_checks(name, report if isinstance(report, dict) else {})
    expected_subprocesses = len(commands)
    checks = {
        "schema": receipt.get("schema") == STAGE_RECEIPT_SCHEMA,
        "name": receipt.get("name") == name,
        "producer": receipt.get("producer") == f"{producer}/{name}",
        "nonce": receipt.get("invocation_nonce") == invocation_nonce,
        "execution-id": isinstance(receipt.get("execution_id"), str) and len(receipt.get("execution_id")) >= 16,
        "single-execution": receipt.get("execution_count") == 1,
        "subprocess-count": receipt.get("subprocess_execution_count") == expected_subprocesses,
        "commands": receipt.get("commands") == commands,
        "command-digest": receipt.get("command_sha256") == json_sha256(commands),
        "source-before": receipt.get("source_snapshot_before_sha256") == source_snapshot_sha256,
        "source-after": receipt.get("source_snapshot_after_sha256") == source_snapshot_sha256,
        "source-unchanged": receipt.get("source_snapshot_unchanged") is True,
        "report-object": isinstance(report, dict),
        "report-digest": isinstance(report, dict) and receipt.get("report_sha256") == json_sha256(report),
        "required-checks-exact": receipt.get("required_checks") == expected_checks,
        "required-checks-pass": bool(expected_checks) and all(expected_checks.values()),
        "timestamps": started is not None and finished is not None,
        "timestamp-order": started is not None and finished is not None and started <= finished <= generated_at,
        "fresh": finished is not None and timedelta(seconds=-60) <= now - finished <= timedelta(seconds=MAX_EVIDENCE_AGE_SECONDS),
        "attestation": _attestation_valid(receipt, attestation_key),
    }
    errors = [label for label, ok in checks.items() if not ok]
    return {
        "valid": not errors,
        "checks": checks,
        "errors": errors,
        "execution_count": receipt.get("execution_count"),
        "subprocess_execution_count": receipt.get("subprocess_execution_count"),
        "execution_id": receipt.get("execution_id"),
        "report_sha256": receipt.get("report_sha256"),
    }


def validate_evidence_bundle(
    payload: Any,
    *,
    expected_root: str | Path,
    expected_producer: str,
    expected_invocation_nonce: str,
    expected_source_snapshot: str,
    attestation_key: str,
    expected_purpose: str = "release",
    now: datetime | None = None,
    current_source_snapshot: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"valid": False, "checks": {"object": False}, "errors": ["evidence bundle is not an object"]}
    current = (now or utc_now()).astimezone(timezone.utc)
    expected_root_text = str(Path(expected_root).resolve())
    generated = _parse_timestamp(payload.get("generated_at"))
    required_stages = list(PURPOSE_STAGE_NAMES.get(expected_purpose, ()))
    stages = payload.get("stages") if isinstance(payload.get("stages"), dict) else {}
    unsigned_for_digest = {
        key: value
        for key, value in payload.items()
        if key not in {"attestation", "bundle_sha256"}
    }
    if current_source_snapshot is not None:
        actual_source_snapshot = str(current_source_snapshot)
    else:
        try:
            actual_source_snapshot = source_snapshot_digest(expected_root)
        except OSError:
            actual_source_snapshot = "[snapshot-error]"
    checks = {
        "object": True,
        "schema": payload.get("schema") == EVIDENCE_SCHEMA,
        "purpose": expected_purpose in PURPOSE_STAGE_NAMES and payload.get("purpose") == expected_purpose,
        "version": payload.get("version") == RUNTIME_VERSION,
        "root": payload.get("root") == expected_root_text,
        "producer": bool(expected_producer) and payload.get("producer") == expected_producer,
        "nonce": bool(expected_invocation_nonce) and payload.get("invocation_nonce") == expected_invocation_nonce,
        "source-expected": bool(expected_source_snapshot) and payload.get("source_snapshot_sha256") == expected_source_snapshot,
        "source-current": actual_source_snapshot == expected_source_snapshot,
        "required-stage-list": payload.get("required_stages") == required_stages,
        "complete-stage-set": set(stages) == set(required_stages),
        "generated-at": generated is not None,
        "fresh": generated is not None and timedelta(seconds=-60) <= current - generated <= timedelta(seconds=MAX_EVIDENCE_AGE_SECONDS),
        "no-release-authority": payload.get("release_authorized") is False,
        "no-autonomy-expansion": payload.get("autonomy_expanded") is False,
        "bundle-digest": payload.get("bundle_sha256") == json_sha256(unsigned_for_digest),
        "bundle-attestation": bool(attestation_key) and _attestation_valid(payload, attestation_key),
    }

    command_map = expected_stage_commands(expected_root, purpose=expected_purpose)
    stage_validation: dict[str, Any] = {}
    if generated is not None:
        for name in required_stages:
            stage_validation[name] = _validate_stage_receipt(
                stages.get(name),
                name=name,
                producer=expected_producer,
                invocation_nonce=expected_invocation_nonce,
                source_snapshot_sha256=expected_source_snapshot,
                commands=command_map[name],
                attestation_key=attestation_key,
                generated_at=generated,
                now=current,
            )
    stage_execution_counts = {
        name: row.get("execution_count")
        for name, row in stage_validation.items()
    }
    stage_subprocess_counts = {
        name: row.get("subprocess_execution_count")
        for name, row in stage_validation.items()
    }
    execution_ids = [row.get("execution_id") for row in stage_validation.values()]
    receipts_valid = bool(stage_validation) and all(row.get("valid") is True for row in stage_validation.values())
    expensive_stage_single_execution = (
        receipts_valid
        and all(value == 1 for value in stage_execution_counts.values())
        and len(execution_ids) == len(set(execution_ids))
    )
    checks["stage-receipts"] = receipts_valid
    checks["single-execution-receipts"] = expensive_stage_single_execution
    errors = [label for label, ok in checks.items() if not ok]
    for name, row in stage_validation.items():
        errors.extend(f"{name}:{item}" for item in row.get("errors", []))
    return {
        "valid": not errors,
        "checks": checks,
        "errors": errors,
        "reason": ", ".join(errors[:8]) if errors else None,
        "producer": payload.get("producer"),
        "purpose": payload.get("purpose"),
        "source_snapshot_sha256": payload.get("source_snapshot_sha256"),
        "stage_validation": stage_validation,
        "stage_execution_counts": stage_execution_counts,
        "stage_subprocess_execution_counts": stage_subprocess_counts,
        "expensive_stage_single_execution": expensive_stage_single_execution,
    }


def load_evidence_bundle(
    path: str | Path | None,
    *,
    expected_root: str | Path,
    expected_producer: str | None = None,
    expected_invocation_nonce: str | None = None,
    expected_source_snapshot: str | None = None,
    attestation_key: str | None = None,
    expected_purpose: str | None = None,
    current_source_snapshot: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not path:
        return None, {"provided": False, "valid": False, "reason": "not provided"}
    evidence_path = Path(path)
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, {
            "provided": True,
            "valid": False,
            "path": str(evidence_path),
            "reason": f"{type(exc).__name__}: {exc}",
        }

    producer = expected_producer or os.environ.get(ENV_EXPECTED_PRODUCER, "")
    nonce = expected_invocation_nonce or os.environ.get(ENV_INVOCATION_NONCE, "")
    source_digest = expected_source_snapshot or os.environ.get(ENV_SOURCE_SNAPSHOT, "")
    key = attestation_key or os.environ.get(ENV_ATTESTATION_KEY, "")
    purpose = expected_purpose or os.environ.get(ENV_EVIDENCE_PURPOSE, "release")
    validation = validate_evidence_bundle(
        payload,
        expected_root=expected_root,
        expected_producer=producer,
        expected_invocation_nonce=nonce,
        expected_source_snapshot=source_digest,
        attestation_key=key,
        expected_purpose=purpose,
        current_source_snapshot=current_source_snapshot,
    )
    metadata = {
        "provided": True,
        "path": str(evidence_path),
        **validation,
    }
    if not validation["valid"]:
        return None, metadata
    validated_payload = dict(payload)
    validated_payload["_validated_evidence"] = True
    return validated_payload, metadata


def evidence_stage_report(bundle: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not isinstance(bundle, dict) or bundle.get("_validated_evidence") is not True:
        return None
    stage = (bundle.get("stages") or {}).get(name)
    if not isinstance(stage, dict):
        return None
    report = stage.get("report")
    return report if isinstance(report, dict) else None
