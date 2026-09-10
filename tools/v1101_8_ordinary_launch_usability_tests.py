from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

import dashboard_launcher


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _source_snapshot() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def _wait_health(port: int, timeout: float = 25.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/dashboard-health", timeout=0.5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("service") == "eidolon-dashboard":
                    return payload
        except Exception:
            time.sleep(0.1)
    raise AssertionError("dashboard health timeout")


def test_human_launcher_defaults_to_start() -> None:
    launcher = (ROOT / "eidolon.py").read_text(encoding="utf-8")
    ps1 = (ROOT / "run_eidolon.ps1").read_text(encoding="utf-8")
    shell = (ROOT / "run_eidolon.sh").read_text(encoding="utf-8")
    require('command = args.command or "start"' in launcher, "root launcher")
    require('getattr(args, "no_browser", False)' in launcher, "implicit start arguments")
    require('"startup-soak"' in launcher.split('if command not in', 1)[1].split('}:', 1)[0], "soak isolation")
    require('@("start")' in ps1, "PowerShell default")
    require("set -- start" in shell, "shell default")


def test_dashboard_launcher_reuses_existing_eidolon_service() -> None:
    original_probe = dashboard_launcher.probe_existing_dashboard
    original_open = dashboard_launcher.webbrowser.open
    opened: list[str] = []
    dashboard_launcher.probe_existing_dashboard = lambda *_args, **_kwargs: {"reachable": True, "eidolon_dashboard": True, "status_code": 200, "service": "eidolon-dashboard"}
    dashboard_launcher.webbrowser.open = lambda url, **_kwargs: opened.append(url) or True
    try:
        code = dashboard_launcher.launch_dashboard_from_argv(["--dashboard", "--dashboard-port", "9876", "--open-browser"])
    finally:
        dashboard_launcher.probe_existing_dashboard = original_probe
        dashboard_launcher.webbrowser.open = original_open
    require(code == 0 and opened == ["http://127.0.0.1:9876/"], opened)


def test_ordinary_start_uses_external_runtime_and_serves_first_use_shell() -> None:
    parent = Path(tempfile.mkdtemp(prefix="eidolon-v1101-8-home-"))
    port = _free_port()
    env = os.environ.copy()
    env.pop("EIDOLON_DATA_DIR", None)
    env.update({"HOME": str(parent), "USERPROFILE": str(parent), "XDG_DATA_HOME": str(parent / "xdg"), "LOCALAPPDATA": str(parent / "local"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"})
    before = _source_snapshot()
    process = subprocess.Popen([sys.executable, str(ROOT / "eidolon.py"), "start", "--no-browser", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        health = _wait_health(port)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as response:
            html = response.read().decode("utf-8")
        require(health.get("service") == "eidolon-dashboard", health)
        require("data-first-use-shell='v1101'" in html and "Runtime home" in html, "first-use shell")
        runtime = parent / "xdg" / "eidolon" / "runtime"
        require(runtime.exists() and (runtime / "workspaces" / "active_project.json").is_file(), runtime)
    finally:
        process.terminate()
        try:
            process.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill(); process.communicate(timeout=5)
    after = _source_snapshot()
    require(before == after, "ordinary launch changed source")


def test_second_start_reuses_running_dashboard_without_duplicate_process() -> None:
    parent = Path(tempfile.mkdtemp(prefix="eidolon-v1101-8-reuse-"))
    runtime = parent / "runtime"
    port = _free_port()
    env = os.environ.copy()
    env.update({"EIDOLON_DATA_DIR": str(runtime), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"})
    first = subprocess.Popen([sys.executable, str(ROOT / "eidolon.py"), "start", "--no-browser", "--port", str(port)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        _wait_health(port)
        second = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "start", "--no-browser", "--port", str(port)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=12)
        require(second.returncode == 0, second.stderr)
        require("already running" in second.stdout.lower(), second.stdout)
        require(first.poll() is None, "first dashboard stopped")
    finally:
        first.terminate()
        try:
            first.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            first.kill(); first.communicate(timeout=5)


def test_startup_path_remains_lightweight_and_no_replay_contract_is_visible() -> None:
    main_text = (ROOT / "conscious_agent" / "main.py").read_text(encoding="utf-8")
    launcher = (ROOT / "conscious_agent" / "dashboard_launcher.py").read_text(encoding="utf-8")
    shell = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require(main_text.index('if __name__ == "__main__" and "--dashboard"') < main_text.index("import argparse"), "early dispatch")
    require("from .dashboard import run_dashboard" in launcher and "probe_existing_dashboard" in launcher, "lightweight launcher")
    for token in ("no automatic resend", "Startup did not replay", "No data is moved automatically"):
        require(token.lower() in shell.lower(), token)


def test_focused_registration_and_setup_guidance_exist_once() -> None:
    verifier = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
    setup = (ROOT / "setup.ps1").read_text(encoding="utf-8")
    require(verifier.count('"tools/v1101_8_ordinary_launch_usability_tests.py"') == 1, "focused registration")
    for token in ("run_eidolon.ps1", "runtime-guide", "startup-soak"):
        require(token in setup, token)


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1101.8-ordinary-launch-usability", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
