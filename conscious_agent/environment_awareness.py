from __future__ import annotations

"""v1274.3-v1274.5 real environment observation and development integration."""

import os
import platform
import shutil
import socket
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from ownership_concurrency import ownership_concurrency_operator_status
from ownership_concurrency_foundations import load_ownership_concurrency
from environment_awareness_foundations import *

CONTRACT_VERSION = "v1274.5"


def _observed(domain: str, key: str, kind: str, value: Any, source: str, now: float, ttl: int = 300) -> dict[str, Any]:
    return build_environment_fact(domain=domain, key=key, evidence_class="observed", value_kind=kind, value=value, source_code=source, observed_at=now, stale_after_seconds=ttl)


def _unknown(domain: str, key: str, source: str, now: float, ttl: int = 60) -> dict[str, Any]:
    return build_environment_fact(domain=domain, key=key, evidence_class="unknown", value_kind="state", value="unknown", source_code=source, observed_at=now, stale_after_seconds=ttl)


def _safe_system_code(value: str) -> str:
    text = str(value or "unknown").strip().lower().replace(" ", "_")
    return text if text in {"windows", "linux", "darwin", "freebsd", "unknown"} else "other"


def observe_platform_facts(*, probes: Mapping[str, Callable[[], Any]] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    probes = dict(probes or {})
    clock = float(time.time() if now is None else now)
    system_probe = probes.get("platform_system", platform.system)
    os_name_probe = probes.get("os_name", lambda: os.name)
    machine_probe = probes.get("machine", platform.machine)
    facts: list[dict[str, Any]] = []
    try:
        system = _safe_system_code(str(system_probe()))
        facts.append(_observed("platform", "operating_system", "code", system, "platform_system_probe", clock, 3600))
    except Exception:
        facts.append(_unknown("platform", "operating_system", "platform_system_probe", clock))
    try:
        name = str(os_name_probe() or "unknown").lower()
        name = name if name in {"nt", "posix", "java"} else "other"
        facts.append(_observed("platform", "os_api_family", "code", name, "os_name_probe", clock, 3600))
    except Exception:
        facts.append(_unknown("platform", "os_api_family", "os_name_probe", clock))
    try:
        machine = str(machine_probe() or "unknown").lower()
        arch = "x86_64" if machine in {"amd64", "x86_64"} else "arm64" if machine in {"arm64", "aarch64"} else "other"
        facts.append(_observed("platform", "machine_architecture", "code", arch, "machine_probe", clock, 3600))
    except Exception:
        facts.append(_unknown("platform", "machine_architecture", "machine_probe", clock))
    return facts


def observe_path_facts(source_root: str | Path, runtime_root: str | Path, *, probes: Mapping[str, Callable[..., Any]] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    probes = dict(probes or {})
    clock = float(time.time() if now is None else now)
    source = Path(source_root).resolve()
    runtime = Path(runtime_root).resolve()
    exists_probe = probes.get("path_exists", lambda p: Path(p).exists())
    is_dir_probe = probes.get("path_is_dir", lambda p: Path(p).is_dir())
    facts: list[dict[str, Any]] = []
    for label, path in (("source", source), ("runtime", runtime)):
        try:
            facts.append(_observed("path", f"{label}_exists", "boolean", bool(exists_probe(path)), "filesystem_metadata_probe", clock))
            facts.append(_observed("path", f"{label}_is_directory", "boolean", bool(is_dir_probe(path)), "filesystem_metadata_probe", clock))
            facts.append(_observed("path", f"{label}_absolute", "boolean", path.is_absolute(), "path_parser", clock, 3600))
            facts.append(_observed("path", f"{label}_length", "integer", len(str(path)), "path_parser", clock, 3600))
            facts.append(_observed("path", f"{label}_digest", "digest", digest_sensitive_text(str(path)), "path_digest", clock, 3600))
        except Exception:
            facts.append(_unknown("path", f"{label}_exists", "filesystem_metadata_probe", clock))
    # This is an inference from the parsed path shape, deliberately not an OS observation.
    source_text = str(source)
    if len(source_text) >= 2 and source_text[1:2] == ":":
        basis = next((x for x in facts if x.get("key") == "source_absolute"), None)
        if basis:
            facts.append(build_environment_fact(domain="path", key="source_path_windows_drive_shape", evidence_class="inferred", value_kind="boolean", value=True, source_code="path_shape_inference", basis_fact_digests=[basis["fact_digest"]], observed_at=clock, stale_after_seconds=3600))
    return facts


def observe_python_facts(*, probes: Mapping[str, Callable[[], Any]] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    probes = dict(probes or {})
    clock = float(time.time() if now is None else now)
    version_probe = probes.get("python_version", lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    impl_probe = probes.get("python_implementation", platform.python_implementation)
    executable_probe = probes.get("python_executable", lambda: sys.executable)
    venv_probe = probes.get("python_venv", lambda: sys.prefix != getattr(sys, "base_prefix", sys.prefix))
    facts: list[dict[str, Any]] = []
    for key, kind, probe, source in (
        ("version", "version", version_probe, "python_runtime_probe"),
        ("implementation", "code", lambda: str(impl_probe()).lower(), "python_runtime_probe"),
        ("virtual_environment_active", "boolean", venv_probe, "python_prefix_probe"),
    ):
        try:
            value = probe()
            if key == "implementation" and value not in {"cpython", "pypy", "graalpython", "jython"}:
                value = "other"
            facts.append(_observed("python", key, kind, value, source, clock, 3600))
        except Exception:
            facts.append(_unknown("python", key, source, clock))
    try:
        facts.append(_observed("python", "executable_digest", "digest", digest_sensitive_text(str(executable_probe())), "python_executable_digest", clock, 3600))
    except Exception:
        facts.append(_unknown("python", "executable_digest_state", "python_executable_digest", clock))
    return facts


def observe_permission_facts(source_root: str | Path, runtime_root: str | Path, *, probes: Mapping[str, Callable[..., Any]] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    probes = dict(probes or {})
    clock = float(time.time() if now is None else now)
    access_probe = probes.get("access", os.access)
    facts: list[dict[str, Any]] = []
    for label, path in (("source", Path(source_root)), ("runtime", Path(runtime_root))):
        for mode_name, mode in (("readable", os.R_OK), ("writable", os.W_OK)):
            try:
                facts.append(_observed("permission", f"{label}_{mode_name}", "boolean", bool(access_probe(path, mode)), "filesystem_access_probe", clock, 60))
            except Exception:
                facts.append(_unknown("permission", f"{label}_{mode_name}", "filesystem_access_probe", clock))
    return facts


def observe_configuration_facts(names: Iterable[str], *, environ: Mapping[str, str] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    env = os.environ if environ is None else environ
    clock = float(time.time() if now is None else now)
    facts: list[dict[str, Any]] = []
    for raw in list(names)[:32]:
        name = str(raw or "").strip()
        key = name.lower().replace("_", "-")
        key = "config-" + "".join(ch for ch in key if ch.isalnum() or ch == "-")[:80]
        if not key or key == "config-":
            continue
        # Presence only.  The value itself never enters the fact model.
        facts.append(_observed("configuration", key, "boolean", name in env, "environment_presence_probe", clock, 60))
    return facts


def observe_provider_facts(provider_codes: Iterable[str], *, availability_probe: Callable[[str], bool | None] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    clock = float(time.time() if now is None else now)
    facts: list[dict[str, Any]] = []
    for raw in list(provider_codes)[:16]:
        code = str(raw or "").strip().lower()
        if not code or not all(ch.isalnum() or ch in "_.:-" for ch in code) or len(code) > 48:
            continue
        key = f"provider_{code}_available"
        if availability_probe is None:
            facts.append(_unknown("provider", key, "provider_availability_not_probed", clock))
            continue
        try:
            value = availability_probe(code)
            if value is None:
                facts.append(_unknown("provider", key, "provider_availability_probe", clock))
            else:
                facts.append(_observed("provider", key, "boolean", bool(value), "provider_availability_probe", clock, 30))
        except Exception:
            facts.append(_unknown("provider", key, "provider_availability_probe", clock))
    return facts


def observe_port_facts(ports: Iterable[int], *, port_probe: Callable[[int], str | bool | None] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    clock = float(time.time() if now is None else now)
    facts: list[dict[str, Any]] = []
    for raw in list(ports)[:16]:
        port = int(raw)
        if port < 1 or port > 65535:
            raise ValueError("environment_port_out_of_range")
        key = f"tcp_port_{port}_state"
        if port_probe is None:
            facts.append(_unknown("port", key, "port_probe_not_requested", clock))
            continue
        try:
            result = port_probe(port)
            if result is None:
                facts.append(_unknown("port", key, "port_availability_probe", clock))
            else:
                state = result if isinstance(result, str) else ("available" if result else "unavailable")
                if state not in {"available", "in_use", "unavailable", "blocked", "unknown"}:
                    state = "unknown"
                facts.append(_observed("port", key, "state", state, "port_availability_probe", clock, 15))
        except Exception:
            facts.append(_unknown("port", key, "port_availability_probe", clock))
    return facts


def observe_process_facts(*, process_probe: Callable[[], Mapping[str, Any]] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    clock = float(time.time() if now is None else now)
    if process_probe is None:
        # Current-process liveness is directly observed; arbitrary process lists
        # are not guessed from names or stale PID files.
        return [_observed("process", "current_process_alive", "boolean", True, "current_process_probe", clock, 10)]
    try:
        row = dict(process_probe() or {})
        return [
            _observed("process", "current_process_alive", "boolean", bool(row.get("current_process_alive", True)), "process_probe", clock, 10),
            _observed("process", "worker_count", "integer", max(0, int(row.get("worker_count", 0))), "process_probe", clock, 10),
        ]
    except Exception:
        return [_unknown("process", "current_process_alive", "process_probe", clock)]


def observe_resource_facts(source_root: str | Path, *, resource_probe: Callable[[], Mapping[str, Any]] | None = None, now: float | None = None) -> list[dict[str, Any]]:
    clock = float(time.time() if now is None else now)
    facts: list[dict[str, Any]] = []
    try:
        row = dict(resource_probe() if resource_probe else {})
        cpu = row.get("cpu_count", os.cpu_count())
        if cpu is not None:
            facts.append(_observed("resource", "logical_cpu_count", "integer", max(1, int(cpu)), "resource_probe", clock, 60))
        disk_free = row.get("disk_free_bytes")
        if disk_free is None:
            disk_free = shutil.disk_usage(Path(source_root)).free
        facts.append(_observed("resource", "source_volume_free_bytes", "integer", max(0, int(disk_free)), "resource_probe", clock, 30))
        memory = row.get("memory_total_bytes")
        if memory is not None:
            facts.append(_observed("resource", "memory_total_bytes", "integer", max(0, int(memory)), "resource_probe", clock, 60))
        else:
            facts.append(_unknown("resource", "memory_total_bytes_state", "resource_probe", clock))
    except Exception:
        facts.append(_unknown("resource", "resource_probe_state", "resource_probe", clock))
    return facts


def collect_development_environment_facts(
    source_root: str | Path,
    runtime_root: str | Path,
    *,
    requested_ports: Iterable[int] = (),
    configuration_names: Iterable[str] = (),
    provider_codes: Iterable[str] = (),
    provider_availability_probe: Callable[[str], bool | None] | None = None,
    port_probe: Callable[[int], str | bool | None] | None = None,
    process_probe: Callable[[], Mapping[str, Any]] | None = None,
    resource_probe: Callable[[], Mapping[str, Any]] | None = None,
    probes: Mapping[str, Callable[..., Any]] | None = None,
    environ: Mapping[str, str] | None = None,
    now: float | None = None,
) -> list[dict[str, Any]]:
    clock = float(time.time() if now is None else now)
    facts: list[dict[str, Any]] = []
    facts.extend(observe_platform_facts(probes=probes, now=clock))
    facts.extend(observe_path_facts(source_root, runtime_root, probes=probes, now=clock))
    facts.extend(observe_python_facts(probes=probes, now=clock))
    facts.extend(observe_permission_facts(source_root, runtime_root, probes=probes, now=clock))
    facts.extend(observe_configuration_facts(configuration_names, environ=environ, now=clock))
    facts.extend(observe_provider_facts(provider_codes, availability_probe=provider_availability_probe, now=clock))
    facts.extend(observe_port_facts(requested_ports, port_probe=port_probe, now=clock))
    facts.extend(observe_process_facts(process_probe=process_probe, now=clock))
    facts.extend(observe_resource_facts(source_root, resource_probe=resource_probe, now=clock))
    return facts[:MAX_FACTS]


def refresh_development_environment(
    environment_id: str,
    source_root: str | Path,
    *,
    runtime_root: str | Path | None,
    requested_ports: Iterable[int] = (),
    configuration_names: Iterable[str] = (),
    provider_codes: Iterable[str] = (),
    provider_availability_probe: Callable[[str], bool | None] | None = None,
    port_probe: Callable[[int], str | bool | None] | None = None,
    process_probe: Callable[[], Mapping[str, Any]] | None = None,
    resource_probe: Callable[[], Mapping[str, Any]] | None = None,
    probes: Mapping[str, Callable[..., Any]] | None = None,
    environ: Mapping[str, str] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    record = load_environment_awareness(environment_id, runtime_root=runtime_root)
    if not validate_environment_awareness(record).get("ok"):
        raise ValueError("valid_environment_awareness_required")
    ownership = load_ownership_concurrency(str(record.get("ownership_id") or ""), runtime_root=runtime_root)
    if str(ownership.get("source_manifest_digest") or "") != str(record.get("source_manifest_digest") or ""):
        raise ValueError("environment_awareness_source_lineage_changed")
    facts = collect_development_environment_facts(
        source_root, runtime_root or source_root, requested_ports=requested_ports, configuration_names=configuration_names,
        provider_codes=provider_codes, provider_availability_probe=provider_availability_probe, port_probe=port_probe,
        process_probe=process_probe, resource_probe=resource_probe, probes=probes, environ=environ, now=now,
    )
    updated = record_environment_facts(environment_id, facts, runtime_root=runtime_root, now=now)
    return {**public_environment_awareness(updated, now=now), "operation_status": "development_environment_refreshed", "facts": list(updated.get("facts") or [])}


def environment_aware_operator_status(environment_id: str, *, runtime_root: str | Path | None, now: float | None = None) -> dict[str, Any]:
    row = load_environment_awareness(environment_id, runtime_root=runtime_root)
    public = public_environment_awareness(row, now=now)
    ownership = ownership_concurrency_operator_status(str(row.get("ownership_id") or ""), runtime_root=runtime_root, now=now)
    public.update({
        "ownership_status": ownership.get("status"),
        "ownership_active_claim_count": ownership.get("active_claim_count", 0),
        "ownership_expired_or_unreconciled_claim_count": ownership.get("expired_or_unreconciled_claim_count", 0),
        "next_required_authorization": ownership.get("next_required_authorization", "none"),
        "environment_observation_grants_authority": False,
    })
    return public


__all__ = [
    "CONTRACT_VERSION", "observe_platform_facts", "observe_path_facts", "observe_python_facts", "observe_permission_facts",
    "observe_configuration_facts", "observe_provider_facts", "observe_port_facts", "observe_process_facts", "observe_resource_facts",
    "collect_development_environment_facts", "refresh_development_environment", "environment_aware_operator_status",
]
