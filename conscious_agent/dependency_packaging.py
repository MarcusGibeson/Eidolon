from __future__ import annotations

"""v1275.3-v1275.5 dependency/package integration with v1274 environment evidence."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from dependency_packaging_foundations import *
from environment_awareness_foundations import load_environment_awareness, validate_environment_awareness
from environment_awareness_reliability import evaluate_environment_preflight
from isolated_self_modification_foundations import source_only_manifest

CONTRACT_VERSION = "v1275.5"
INSTALL_AUTH_PREFIX = "Authorize disposable dependency install"


def inspect_dependency_packaging(source_root: str | Path, *, environment_id: str = "", runtime_root: str | Path | None = None, now: float | None = None) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    intent = inventory_dependency_intent(root)
    conflicts = detect_dependency_conflicts(intent["declarations"])
    package = build_reproducible_source_package_manifest(root)
    env_valid = False; env_source_match = False; environment_status = "not_bound"
    if environment_id:
        env = load_environment_awareness(environment_id, runtime_root=runtime_root)
        env_valid = validate_environment_awareness(env).get("ok") is True
        env_source_match = env_valid and str(env.get("source_manifest_digest") or "") == str(source_only_manifest(root).get("source_manifest_digest") or "")
        environment_status = "current_lineage" if env_source_match else "invalid_or_stale_lineage"
    report = {
        "ok": conflicts["conflict_count"] == 0 and (not environment_id or env_source_match),
        "status": "dependency_packaging_assessment_ready" if conflicts["conflict_count"] == 0 and (not environment_id or env_source_match) else "dependency_packaging_assessment_blocked",
        "contract_version": CONTRACT_VERSION, "dependency_intent_digest": intent["dependency_intent_digest"],
        "dependency_file_count": intent["dependency_file_count"], "declaration_count": intent["declaration_count"],
        "lock_file_count": intent["lock_file_count"], "conflict_count": conflicts["conflict_count"],
        "uncertain_relationship_count": conflicts["uncertain_relationship_count"],
        "package_manifest_digest": package["package_manifest_digest"], "package_file_count": package["package_file_count"],
        "environment_id_bound": bool(environment_id), "environment_record_valid": env_valid, "environment_source_lineage_match": env_source_match,
        "environment_status": environment_status, "operator_review_required": True,
        **AUTHORITY_FLAGS,
    }
    report["assessment_digest"] = _digest(report)
    return report


def prepare_clean_install_request(source_root: str | Path, *, environment_id: str, runtime_root: str | Path | None, requirement_files: Iterable[str] = ("requirements.txt",), now: float | None = None) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    assessment = inspect_dependency_packaging(root, environment_id=environment_id, runtime_root=runtime_root, now=now)
    files = [str(x).replace("\\", "/") for x in list(requirement_files)[:16]]
    if not files:
        raise ValueError("clean_install_requires_requirement_file")
    for rel in files:
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts or not (root / rel).is_file():
            raise ValueError("clean_install_requirement_file_invalid")
    preflight = evaluate_environment_preflight(environment_id, runtime_root=runtime_root, requirements={"python:implementation": "cpython", "path:source_exists": True}, now=now)
    request = {
        "ok": assessment["ok"] and preflight.get("preflight_passed") is True,
        "status": "clean_install_authorization_required" if assessment["ok"] and preflight.get("preflight_passed") is True else "clean_install_preflight_blocked",
        "contract_version": CONTRACT_VERSION, "assessment_digest": assessment["assessment_digest"],
        "dependency_intent_digest": assessment["dependency_intent_digest"], "package_manifest_digest": assessment["package_manifest_digest"],
        "environment_id": environment_id, "environment_preflight_passed": preflight.get("preflight_passed") is True,
        "requirement_files": files, "disposable_environment_required": True, "network_default_allowed": False,
        "active_source_modified": False, "install_executed": False, "authorization_consumed": False,
        **AUTHORITY_FLAGS,
    }
    request["request_digest"] = _digest(request)
    request["authorization_phrase"] = f"{INSTALL_AUTH_PREFIX} digest {request['request_digest']}."
    return request


def execute_clean_install_request(request: Mapping[str, Any], *, exact_authorization: str, source_root: str | Path, runner: Callable[[list[str], Path, Mapping[str, str]], Mapping[str, Any]] | None = None) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve(strict=True)
    expected = str(request.get("authorization_phrase") or "")
    if not request.get("ok") or request.get("status") != "clean_install_authorization_required":
        raise ValueError("clean_install_request_not_ready")
    if str(exact_authorization or "") != expected:
        return {"ok": False, "status": "clean_install_exact_authorization_required", "install_executed": False, "authorization_consumed": False, **AUTHORITY_FLAGS}
    current_intent = inventory_dependency_intent(root)
    if current_intent["dependency_intent_digest"] != request.get("dependency_intent_digest"):
        return {"ok": False, "status": "clean_install_stale_dependency_intent", "install_executed": False, "authorization_consumed": False, **AUTHORITY_FLAGS}
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INDEX": "1"}
    started = time.monotonic()
    if runner is None:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1275-clean-") as td:
            env_root = Path(td) / "venv"
            venv.EnvBuilder(with_pip=True, clear=True).create(env_root)
            python = env_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            command = [str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--no-index"]
            for rel in request.get("requirement_files") or []:
                command.extend(["-r", str(rel)])
            proc = subprocess.run(command, cwd=root, env={**os.environ, **env}, capture_output=True, text=True, timeout=120)
            result = {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    else:
        command = ["<disposable-python>", "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--no-index"]
        for rel in request.get("requirement_files") or []:
            command.extend(["-r", str(rel)])
        result = dict(runner(command, root, env))
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    rc = int(result.get("returncode", 1))
    receipt = {
        "ok": rc == 0, "status": "clean_install_verified" if rc == 0 else "clean_install_failed",
        "contract_version": CONTRACT_VERSION, "request_digest": request.get("request_digest"),
        "authorization_consumed": True, "install_executed": True, "disposable_environment_required": True,
        "returncode": rc, "elapsed_ms": elapsed_ms,
        "stdout_digest": hashlib.sha256(str(result.get("stdout") or "").encode()).hexdigest(),
        "stderr_digest": hashlib.sha256(str(result.get("stderr") or "").encode()).hexdigest(),
        "raw_installer_output_persisted": False, "network_used": False, "active_source_modified": False,
        **{**AUTHORITY_FLAGS, "dependency_install_authorized": False},
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


def verify_reproducible_package_manifest(source_root: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    current = build_reproducible_source_package_manifest(source_root)
    same = current.get("package_manifest_digest") == manifest.get("package_manifest_digest") and current.get("package_file_count") == manifest.get("package_file_count")
    return {
        "ok": same, "status": "package_manifest_reproducible" if same else "package_manifest_drift_detected",
        "expected_package_manifest_digest": manifest.get("package_manifest_digest"), "current_package_manifest_digest": current.get("package_manifest_digest"),
        "package_file_count": current.get("package_file_count"), "package_published": False, **AUTHORITY_FLAGS,
    }


__all__ = ["CONTRACT_VERSION", "inspect_dependency_packaging", "prepare_clean_install_request", "execute_clean_install_request", "verify_reproducible_package_manifest"]
