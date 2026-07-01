from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from paths import ROOT_DIR

GENERATED_PROBE_HARNESS_VERSION = "1032.0"
GENERATED_PROBE_TIMEOUT_SECONDS = 5
_RESULT_PREFIX = "__EIDOLON_GENERATED_PROBE_RESULT__"
PROTECTED_SNAPSHOT_PATHS = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent",
    "tools",
    "sandbox/generated_validation_probes",
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/active_project.json",
    "data/workspaces/projects.json",
)

_CHILD_CODE = r'''
import importlib.util
import json
import pathlib
import sys
import traceback

probe_path = pathlib.Path(sys.argv[1])
marker = sys.argv[2]
try:
    spec = importlib.util.spec_from_file_location("eidolon_subprocess_generated_probe", probe_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("probe module spec could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    preview = module.probe_preview()
    payload = {"ok": True, "preview": preview, "error": "", "exception_type": ""}
except BaseException as exc:
    payload = {"ok": False, "preview": {}, "error": str(exc), "exception_type": type(exc).__name__, "traceback": traceback.format_exc(limit=5)}
print(marker + " " + json.dumps(payload, sort_keys=True, default=str))
'''


def _normalized_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_ignored_snapshot_path(path: Path) -> bool:
    parts = set(path.parts)
    return (
        "__pycache__" in parts
        or ".git" in parts
        or ".pytest_cache" in parts
        or path.name.endswith(".pyc")
        or path.name.endswith(".pyo")
    )


def _snapshot_project(root: Path) -> dict[str, tuple[int, int]]:
    """Snapshot protected project surfaces only.

    The harness detects project-side effects for source, probe, README, and
    source-metadata surfaces without walking runtime/private/package archives. It
    is intentionally not a complete filesystem sandbox and does not claim to
    observe writes outside the project root.
    """
    snapshot: dict[str, tuple[int, int]] = {}
    if not root.exists():
        return snapshot
    candidates: list[Path] = []
    for rel in PROTECTED_SNAPSHOT_PATHS:
        base = root / rel
        if not base.exists():
            continue
        if base.is_file():
            candidates.append(base)
        else:
            candidates.extend(path for path in base.rglob("*") if path.is_file())
    for path in candidates:
        if _is_ignored_snapshot_path(path):
            continue
        try:
            stat = path.stat()
            snapshot[_normalized_rel(path, root)] = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            continue
    return snapshot


def _diff_snapshots(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> list[str]:
    changed: list[str] = []
    for rel, state in after.items():
        if before.get(rel) != state:
            changed.append(rel)
    for rel in before:
        if rel not in after:
            changed.append(rel)
    return sorted(set(changed))


def _classify_side_effects(changed: list[str]) -> dict[str, bool | None]:
    return {
        "network_access_detected": None,
        "network_access_detection_supported": False,
        "network_access_blocked": False,
        "network_access_not_measured": True,
        "external_filesystem_write_detection_supported": False,
        "external_filesystem_writes_not_measured": True,
        "project_side_effect_snapshot_scope_limited": True,
        "scheduler_access_detected": any(rel.startswith("data/scheduler") or rel.startswith("data/schedules") for rel in changed),
        "memory_write_detected": any(rel.startswith("data/memories") or rel.startswith("data/memory") for rel in changed),
        "approval_write_detected": any(rel.startswith("data/approvals/") or rel.startswith("data/approvals") for rel in changed),
        "release_write_detected": any(rel.startswith("data/releases/") or rel.startswith("data/release_package/") for rel in changed),
        "source_write_detected": any(rel.startswith("conscious_agent/") or rel.startswith("tools/") or rel.startswith("sandbox/generated_validation_probes/") for rel in changed),
        "live_wiring_detected": any(rel in {"conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py"} for rel in changed),
    }


def _parse_child_payload(stdout: str, marker: str) -> tuple[dict[str, Any], str]:
    payloads: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if line.startswith(marker + " "):
            raw = line[len(marker) + 1 :]
            try:
                payloads.append(json.loads(raw))
            except Exception as exc:
                return {}, f"invalid probe result json: {exc}"
    if not payloads:
        return {}, "probe result marker missing"
    return payloads[-1], ""


def execute_generated_probe(root: Path = ROOT_DIR, surface_id: str = "", expected_source_smoke: str = "", timeout_seconds: int = GENERATED_PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    sandbox_relative_path = f"sandbox/generated_validation_probes/{surface_id}_probe.py"
    return execute_generated_probe_path(
        root=root,
        probe_path=root / sandbox_relative_path,
        surface_id=surface_id,
        expected_source_smoke=expected_source_smoke,
        sandbox_relative_path=sandbox_relative_path,
        timeout_seconds=timeout_seconds,
    )


def execute_generated_probe_path(root: Path, probe_path: Path, surface_id: str, expected_source_smoke: str, sandbox_relative_path: str | None = None, timeout_seconds: int = GENERATED_PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    root = Path(root).resolve()
    path = Path(probe_path)
    if not path.is_absolute():
        path = root / path
    sandbox_root = (root / "sandbox" / "generated_validation_probes").resolve()
    resolved_path = path.resolve()
    if sandbox_relative_path is None:
        try:
            sandbox_relative_path = resolved_path.relative_to(root).as_posix()
        except Exception:
            sandbox_relative_path = str(path).replace("\\", "/")
    inside_sandbox = False
    try:
        resolved_path.relative_to(sandbox_root)
        inside_sandbox = True
    except Exception:
        inside_sandbox = False

    file_exists = resolved_path.exists()
    stdout = ""
    stderr = ""
    timed_out = False
    return_code = 1
    elapsed_seconds = 0.0
    error = ""
    payload: dict[str, Any] = {}
    preview: dict[str, Any] = {}
    before = _snapshot_project(root)
    marker = f"{_RESULT_PREFIX}_{uuid.uuid4().hex}"

    if not file_exists or not inside_sandbox:
        error = "probe file missing or outside sandbox"
    else:
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="eidolon_probe_cwd_") as tmpdir:
            env = {
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", "-B", "-c", _CHILD_CODE, str(resolved_path), marker],
                    cwd=tmpdir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                return_code = int(completed.returncode)
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
                payload, parse_error = _parse_child_payload(stdout, marker)
                if parse_error:
                    error = parse_error
                elif payload.get("ok") is not True:
                    error = str(payload.get("error") or "probe execution failed")
                preview_value = payload.get("preview", {}) if isinstance(payload, dict) else {}
                preview = preview_value if isinstance(preview_value, dict) else {}
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                return_code = -9
                stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace") if exc.stdout else ""
                stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace") if exc.stderr else ""
                error = f"probe timed out after {timeout_seconds}s"
            except Exception as exc:
                error = str(exc)
            elapsed_seconds = round(time.monotonic() - started, 4)

    after = _snapshot_project(root)
    changed_files = _diff_snapshots(before, after)
    side_effects = _classify_side_effects(changed_files)
    metadata = preview.get("metadata", {}) if isinstance(preview, dict) else {}
    project_side_effect_detected = bool(changed_files)
    passed = (
        error == ""
        and return_code == 0
        and timed_out is False
        and project_side_effect_detected is False
        and preview.get("ok") is True
        and preview.get("review_only") is True
        and preview.get("writes_files") is False
        and preview.get("activates_generated_wiring") is False
        and preview.get("expands_autonomy") is False
        and metadata.get("surface_id") == surface_id
        and metadata.get("smoke_check") == expected_source_smoke
        and metadata.get("sandbox_relative_path") == sandbox_relative_path
    )
    return {
        "harness_version": GENERATED_PROBE_HARNESS_VERSION,
        "execution_mode": "subprocess_isolated_python_child",
        "surface_id": surface_id,
        "source_smoke_check": expected_source_smoke,
        "sandbox_relative_path": sandbox_relative_path,
        "file_exists": file_exists,
        "inside_sandbox_root": inside_sandbox,
        "passed": passed,
        "error": error,
        "return_code": return_code,
        "stdout_captured": stdout is not None,
        "stderr_captured": stderr is not None,
        "stdout_text": stdout,
        "stderr_text": stderr,
        "stdout_line_count": len(stdout.splitlines()),
        "stderr_line_count": len(stderr.splitlines()),
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "elapsed_seconds": elapsed_seconds,
        "metadata_surface_id": metadata.get("surface_id"),
        "metadata_smoke_check": metadata.get("smoke_check"),
        "metadata_path": metadata.get("sandbox_relative_path"),
        "project_side_effect_detected": project_side_effect_detected,
        "changed_project_file_count": len(changed_files),
        "changed_project_files": changed_files[:25],
        "protected_snapshot_paths": list(PROTECTED_SNAPSHOT_PATHS),
        "containment_warning": "subprocess containment does not measure network access or writes outside the project root",
        **side_effects,
    }
