from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

STARTUP_TARGET_SECONDS = 15.0
DEFAULT_READY_ROUTE = "/api/dashboard-health"


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _terminate_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    if process.poll() is None:
        process.terminate()
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.communicate(timeout=5)


def _startup_environment(project_root: Path, runtime_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    agent_root = project_root / "conscious_agent"
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment.update(
        {
            "EIDOLON_DATA_DIR": str(runtime_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": os.pathsep.join(part for part in (str(agent_root), existing_pythonpath) if part),
        }
    )
    return environment


def measure_dashboard_import(project_root: str | Path, *, timeout_seconds: float = 30.0) -> dict[str, Any]:
    root = Path(project_root).resolve()
    runtime_root = Path(tempfile.mkdtemp(prefix="eidolon-dashboard-import-"))
    environment = _startup_environment(root, runtime_root)
    script = (
        "import json,time; start=time.perf_counter(); import dashboard; "
        "print(json.dumps({'import_seconds':time.perf_counter()-start,'module':'dashboard'}))"
    )
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        elapsed = time.perf_counter() - started
        payload: dict[str, Any] = {}
        try:
            payload = json.loads(completed.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            pass
        return {
            "ok": completed.returncode == 0 and isinstance(payload.get("import_seconds"), (int, float)),
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
            "import_seconds": payload.get("import_seconds"),
            "stderr_tail": completed.stderr[-2000:],
        }
    except subprocess.TimeoutExpired as error:
        return {
            "ok": False,
            "returncode": None,
            "elapsed_seconds": time.perf_counter() - started,
            "import_seconds": None,
            "error": "timeout",
            "stderr_tail": str(error.stderr or "")[-2000:],
        }
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)


def measure_dashboard_server(
    project_root: str | Path,
    *,
    route: str = DEFAULT_READY_ROUTE,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    if not route.startswith("/"):
        raise ValueError("The dashboard startup route must begin with '/'.")
    runtime_root = Path(tempfile.mkdtemp(prefix="eidolon-dashboard-runtime-"))
    port = _free_tcp_port()
    environment = _startup_environment(root, runtime_root)
    command = [
        sys.executable,
        str(root / "conscious_agent" / "main.py"),
        "--dashboard",
        "--dashboard-host",
        "127.0.0.1",
        "--dashboard-port",
        str(port),
    ]
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    tcp_ready_seconds: float | None = None
    first_response_seconds: float | None = None
    status_code: int | None = None
    response_body = ""
    error = ""
    deadline = started + timeout_seconds
    try:
        while time.perf_counter() < deadline:
            if process.poll() is not None:
                error = f"dashboard_exited_{process.returncode}"
                break
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                    tcp_ready_seconds = time.perf_counter() - started
                    break
            except OSError:
                time.sleep(0.03)
        if tcp_ready_seconds is None and not error:
            error = "tcp_readiness_timeout"
        if tcp_ready_seconds is not None:
            request = urllib.request.Request(f"http://127.0.0.1:{port}{route}")
            try:
                with urllib.request.urlopen(request, timeout=max(1.0, deadline - time.perf_counter())) as response:
                    status_code = int(response.status)
                    response_body = response.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as response:
                status_code = int(response.code)
                response_body = response.read().decode("utf-8", "replace")
                error = f"http_status_{status_code}"
            first_response_seconds = time.perf_counter() - started
    except Exception as exception:
        error = f"{type(exception).__name__}: {exception}"
    finally:
        stdout, stderr = _terminate_process(process)
        shutil.rmtree(runtime_root, ignore_errors=True)
    return {
        "ok": bool(status_code == 200 and first_response_seconds is not None),
        "target_seconds": STARTUP_TARGET_SECONDS,
        "below_target": bool(first_response_seconds is not None and first_response_seconds < STARTUP_TARGET_SECONDS),
        "route": route,
        "tcp_ready_seconds": tcp_ready_seconds,
        "first_response_seconds": first_response_seconds,
        "status_code": status_code,
        "response_json": _safe_json_object(response_body),
        "error": error,
        "returncode": process.returncode,
        "stdout_tail": stdout[-1000:],
        "stderr_tail": stderr[-2000:],
    }



def probe_dashboard_routes(
    project_root: str | Path,
    routes: list[str] | tuple[str, ...],
    *,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    normalized = [str(route) for route in routes]
    if not normalized or any(not route.startswith("/") for route in normalized):
        raise ValueError("Dashboard route probes require one or more absolute routes.")
    runtime_root = Path(tempfile.mkdtemp(prefix="eidolon-dashboard-routes-"))
    port = _free_tcp_port()
    environment = _startup_environment(root, runtime_root)
    command = [sys.executable, str(root / "conscious_agent" / "main.py"), "--dashboard", "--dashboard-host", "127.0.0.1", "--dashboard-port", str(port)]
    started = time.perf_counter()
    process = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    results: list[dict[str, Any]] = []
    error = ""
    deadline = started + timeout_seconds
    try:
        while time.perf_counter() < deadline:
            if process.poll() is not None:
                error = f"dashboard_exited_{process.returncode}"
                break
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                    break
            except OSError:
                time.sleep(0.03)
        else:
            error = "tcp_readiness_timeout"
        if not error:
            for route in normalized:
                route_started = time.perf_counter()
                status_code: int | None = None
                body = ""
                route_error = ""
                request = urllib.request.Request(f"http://127.0.0.1:{port}{route}")
                try:
                    with urllib.request.urlopen(request, timeout=max(1.0, deadline-time.perf_counter())) as response:
                        status_code = int(response.status); body = response.read().decode("utf-8", "replace")
                except urllib.error.HTTPError as response:
                    status_code = int(response.code); body = response.read().decode("utf-8", "replace"); route_error = f"http_status_{status_code}"
                results.append({"route":route,"status_code":status_code,"seconds":time.perf_counter()-route_started,"elapsed_from_process_start_seconds":time.perf_counter()-started,"ok":status_code==200,"response_json":_safe_json_object(body),"body_prefix":body[:240],"error":route_error})
    except Exception as exception:
        error = f"{type(exception).__name__}: {exception}"
    finally:
        stdout, stderr = _terminate_process(process)
        shutil.rmtree(runtime_root, ignore_errors=True)
    return {"ok":not error and len(results)==len(normalized) and all(row["ok"] for row in results),"target_seconds":STARTUP_TARGET_SECONDS,"routes":results,"error":error,"returncode":process.returncode,"stdout_tail":stdout[-1000:],"stderr_tail":stderr[-2000:]}

def _safe_json_object(value: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def parse_importtime_output(output: str, *, limit: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        if not raw_line.startswith("import time:") or "self [us]" in raw_line:
            continue
        parts = raw_line[len("import time:") :].split("|")
        if len(parts) != 3:
            continue
        try:
            self_us = int(parts[0].strip())
            cumulative_us = int(parts[1].strip())
        except ValueError:
            continue
        rows.append(
            {
                "module": parts[2].strip(),
                "self_seconds": self_us / 1_000_000,
                "cumulative_seconds": cumulative_us / 1_000_000,
            }
        )
    rows.sort(key=lambda row: (row["cumulative_seconds"], row["self_seconds"]), reverse=True)
    return rows[: max(0, int(limit))]


def profile_dashboard_imports(
    project_root: str | Path,
    *,
    limit: int = 20,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    runtime_root = Path(tempfile.mkdtemp(prefix="eidolon-dashboard-profile-"))
    environment = _startup_environment(root, runtime_root)
    try:
        completed = subprocess.run(
            [sys.executable, "-X", "importtime", "-c", "import dashboard"],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "rows": parse_importtime_output(completed.stderr, limit=limit),
            "stderr_tail": completed.stderr[-2000:] if completed.returncode else "",
        }
    except subprocess.TimeoutExpired as error:
        return {"ok": False, "error": "timeout", "rows": [], "stderr_tail": str(error.stderr or "")[-2000:]}
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)


def build_dashboard_startup_report(
    project_root: str | Path,
    *,
    runs: int = 3,
    route: str = DEFAULT_READY_ROUTE,
    profile_imports: bool = True,
) -> dict[str, Any]:
    run_count = max(1, min(int(runs), 10))
    imports = [measure_dashboard_import(project_root) for _ in range(run_count)]
    servers = [measure_dashboard_server(project_root, route=route) for _ in range(run_count)]
    response_values = [row["first_response_seconds"] for row in servers if row.get("first_response_seconds") is not None]
    report: dict[str, Any] = {
        "ok": all(row.get("ok") for row in imports + servers),
        "target_seconds": STARTUP_TARGET_SECONDS,
        "route": route,
        "import_runs": imports,
        "server_runs": servers,
        "maximum_first_response_seconds": max(response_values) if response_values else None,
        "average_first_response_seconds": sum(response_values) / len(response_values) if response_values else None,
        "all_server_runs_below_target": len(response_values) == run_count and all(value < STARTUP_TARGET_SECONDS for value in response_values),
    }
    if profile_imports:
        report["import_profile"] = profile_dashboard_imports(project_root)
    return report


def _request_route(port: int, route: str, *, timeout_seconds: float) -> tuple[int | None, str, str]:
    request = urllib.request.Request(f"http://127.0.0.1:{port}{route}", headers={"Cache-Control": "no-store"})
    try:
        with urllib.request.urlopen(request, timeout=max(0.25, timeout_seconds)) as response:
            return int(response.status), response.read().decode("utf-8", "replace"), ""
    except urllib.error.HTTPError as response:
        return int(response.code), response.read().decode("utf-8", "replace"), f"http_status_{response.code}"
    except Exception as error:
        return None, "", type(error).__name__


def _seed_first_use_runtime(project_root: Path, runtime_root: Path) -> None:
    source_data = project_root / "data"
    if source_data.exists():
        shutil.copytree(source_data, runtime_root, dirs_exist_ok=True)
    else:
        runtime_root.mkdir(parents=True, exist_ok=True)


def measure_first_use_sequence(
    project_root: str | Path,
    *,
    runtime_root: str | Path | None = None,
    seed_runtime: bool = True,
    timeout_seconds: float = 45.0,
    include_provider_probe: bool = True,
) -> dict[str, Any]:
    """Measure the real local first-use route sequence with content-free output.

    The provider phase is informative. An unavailable provider does not make the
    chat shell unusable and is never represented as ready without direct evidence.
    """

    root = Path(project_root).resolve()
    owns_runtime = runtime_root is None
    runtime = Path(runtime_root).resolve() if runtime_root is not None else Path(tempfile.mkdtemp(prefix="eidolon-first-use-runtime-"))
    runtime.mkdir(parents=True, exist_ok=True)
    if seed_runtime:
        _seed_first_use_runtime(root, runtime)
    port = _free_tcp_port()
    environment = _startup_environment(root, runtime)
    command = [
        sys.executable,
        str(root / "conscious_agent" / "main.py"),
        "--dashboard",
        "--dashboard-host",
        "127.0.0.1",
        "--dashboard-port",
        str(port),
    ]
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    phases: list[dict[str, Any]] = []
    deadline = started + max(5.0, float(timeout_seconds))
    tcp_ready: float | None = None
    process_error = ""

    def record(name: str, status: str, *, required: bool, status_code: int | None = None, detail: str = "") -> None:
        phases.append({
            "name": name,
            "status": status,
            "required": required,
            "elapsed_from_process_start_seconds": round(max(0.0, time.perf_counter() - started), 6),
            "status_code": status_code,
            "detail": str(detail or "")[:120],
        })

    try:
        while time.perf_counter() < deadline:
            if process.poll() is not None:
                process_error = f"dashboard_exited_{process.returncode}"
                break
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                    tcp_ready = time.perf_counter() - started
                    record("tcp_readiness", "ready", required=True)
                    break
            except OSError:
                time.sleep(0.03)
        if tcp_ready is None:
            record("tcp_readiness", "failed", required=True, detail=process_error or "timeout")
            return {
                "ok": False,
                "status": "failed",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "python_311_or_newer": sys.version_info >= (3, 11),
                "target_cold_health_seconds": STARTUP_TARGET_SECONDS,
                "target_chat_interactive_seconds": 5.0,
                "phases": phases,
                "provider_ready": False,
                "provider_status": "not_checked",
                "content_free": True,
                "private_values_included": False,
            }

        route_budget = max(1.0, deadline - time.perf_counter())
        status_code, body, error = _request_route(port, "/api/dashboard-health", timeout_seconds=route_budget)
        health_ok = status_code == 200
        record("first_health_response", "ready" if health_ok else "failed", required=True, status_code=status_code, detail=error)

        status_code, body, error = _request_route(port, "/", timeout_seconds=max(1.0, deadline - time.perf_counter()))
        shell_ok = status_code == 200 and "data-first-use-shell='v1101'" in body and "id='message'" in body
        record("overview_shell_available", "ready" if shell_ok else "failed", required=True, status_code=status_code, detail=error)
        interactive_seconds = time.perf_counter() - started if shell_ok else None
        record("chat_input_interactive", "ready" if shell_ok else "failed", required=True, status_code=status_code)

        status_code, body, error = _request_route(port, "/api/first-use/bootstrap", timeout_seconds=max(1.0, deadline - time.perf_counter()))
        bootstrap = _safe_json_object(body) or {}
        bootstrap_ok = status_code == 200 and bootstrap.get("ok") is True and bootstrap.get("chat_interactive") is True
        selected_session = bootstrap.get("selected_session") if isinstance(bootstrap.get("selected_session"), dict) else {}
        active_project = bootstrap.get("active_project") if isinstance(bootstrap.get("active_project"), dict) else {}
        progress = bootstrap.get("progress") if isinstance(bootstrap.get("progress"), dict) else {}
        restart = bootstrap.get("restart") if isinstance(bootstrap.get("restart"), dict) else {}
        active_session_present = bool(selected_session.get("id"))
        restoration_detail = "restored" if active_session_present else "empty_ready" if bootstrap_ok else (error or str(bootstrap.get("status") or "degraded"))
        record("active_conversation_restoration", "ready" if bootstrap_ok else "degraded", required=False, status_code=status_code, detail=restoration_detail)

        status_code, body, error = _request_route(port, "/api/dashboard-chat/active-session", timeout_seconds=max(1.0, deadline - time.perf_counter()))
        active = _safe_json_object(body) or {}
        active_ok = status_code == 200 and active.get("ok") is True
        record("conversation_surface_available", "ready" if active_ok else "degraded", required=False, status_code=status_code, detail=error)

        provider_ready = False
        provider_status = "not_checked"
        if include_provider_probe:
            status_code, body, error = _request_route(port, "/api/local-model/readiness", timeout_seconds=min(12.0, max(1.0, deadline - time.perf_counter())))
            provider_payload = _safe_json_object(body) or {}
            provider_data = provider_payload.get("data") if isinstance(provider_payload.get("data"), dict) else provider_payload
            provider_ready = bool(
                status_code == 200
                and provider_data.get("service_available")
                and provider_data.get("generation_model_available") is not False
            )
            provider_status = "ready" if provider_ready else str(
                provider_data.get("availability_state") or provider_data.get("status") or error or "unavailable"
            )[:60]
            record("first_provider_ready_state", "ready" if provider_ready else "unavailable", required=False, status_code=status_code, detail=provider_status)

        health_seconds = next((row["elapsed_from_process_start_seconds"] for row in phases if row["name"] == "first_health_response"), None)
        required_ok = all(row["status"] == "ready" for row in phases if row.get("required"))
        return {
            "ok": bool(required_ok),
            "status": "ready" if required_ok else "failed",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "python_311_or_newer": sys.version_info >= (3, 11),
            "target_cold_health_seconds": STARTUP_TARGET_SECONDS,
            "target_chat_interactive_seconds": 5.0,
            "tcp_ready_seconds": round(tcp_ready, 6) if tcp_ready is not None else None,
            "first_health_response_seconds": health_seconds,
            "chat_input_interactive_seconds": round(interactive_seconds, 6) if interactive_seconds is not None else None,
            "cold_health_below_target": bool(health_seconds is not None and health_seconds < STARTUP_TARGET_SECONDS),
            "chat_interactive_below_target": bool(interactive_seconds is not None and interactive_seconds < 5.0),
            "active_conversation_restoration_completed": bool(bootstrap_ok),
            "active_conversation_present": bool(active_session_present),
            "active_conversation_restored": bool(bootstrap_ok and active_session_present),
            "active_project_present": bool(active_project.get("id")),
            "active_project_truth_status": str(active_project.get("truth_status") or active_project.get("status") or "unknown")[:64],
            "startup_progress_status": str(progress.get("status") or "unknown")[:32],
            "startup_progress_completed_phases": max(0, int(progress.get("completed_phase_count") or 0)),
            "startup_progress_total_phases": max(0, int(progress.get("total_phase_count") or 0)),
            "continuity_digest": str(restart.get("continuity_digest") or "")[:64],
            "conversation_surface_available": bool(active_ok),
            "provider_ready": provider_ready,
            "provider_status": provider_status,
            "phases": phases,
            "accepted_message_replayed": False,
            "provider_request_repeated": False,
            "content_free": True,
            "private_values_included": False,
        }
    finally:
        _terminate_process(process)
        if owns_runtime:
            shutil.rmtree(runtime, ignore_errors=True)


def measure_cold_warm_and_fresh_first_use(
    project_root: str | Path,
    *,
    timeout_seconds: float = 45.0,
    include_provider_probe: bool = True,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    shared_runtime = Path(tempfile.mkdtemp(prefix="eidolon-first-use-shared-"))
    fresh_runtime = Path(tempfile.mkdtemp(prefix="eidolon-first-use-fresh-"))
    try:
        cold = measure_first_use_sequence(
            root, runtime_root=shared_runtime, seed_runtime=True,
            timeout_seconds=timeout_seconds, include_provider_probe=include_provider_probe,
        )
        warm = measure_first_use_sequence(
            root, runtime_root=shared_runtime, seed_runtime=False,
            timeout_seconds=timeout_seconds, include_provider_probe=include_provider_probe,
        )
        fresh = measure_first_use_sequence(
            root, runtime_root=fresh_runtime, seed_runtime=False,
            timeout_seconds=timeout_seconds, include_provider_probe=include_provider_probe,
        )
        cold_digest = str(cold.get("continuity_digest") or "")
        warm_digest = str(warm.get("continuity_digest") or "")
        cold_warm_parity = bool(cold_digest and warm_digest and cold_digest == warm_digest)
        return {
            "ok": all(row.get("ok") for row in (cold, warm, fresh)) and cold_warm_parity,
            "cold": cold,
            "warm": warm,
            "fresh_external_runtime": fresh,
            "cold_warm_continuity_parity": cold_warm_parity,
            "accepted_message_replayed": False,
            "provider_request_repeated": False,
            "content_free": True,
            "private_values_included": False,
        }
    finally:
        shutil.rmtree(shared_runtime, ignore_errors=True)
        shutil.rmtree(fresh_runtime, ignore_errors=True)
