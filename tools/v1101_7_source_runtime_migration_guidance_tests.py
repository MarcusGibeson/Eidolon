from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

import launch_environment
from package_integrity import SOURCE_DATA_ALLOWLIST


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def _source_snapshot() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def test_windows_default_runtime_uses_local_app_data() -> None:
    env = {"LOCALAPPDATA": r"C:\Users\FixtureUserUser\AppData\Local", "USERPROFILE": r"C:\Users\FixtureUser"}
    root = launch_environment.default_external_runtime_root(environment=env, platform_name="Windows")
    normalized = str(root).replace("/", "\\").lower()
    require(normalized.endswith(r"eidolon\runtime"), root)
    require("appdata" in normalized and "local" in normalized, root)


def test_ordinary_runtime_guidance_defaults_external_without_mutation() -> None:
    guidance = launch_environment.build_runtime_migration_guidance(
        ROOT,
        environment={},
        platform_name="Windows",
    )
    require(guidance["status"] == "external_runtime_active", guidance)
    require(guidance["runtime_external"] is True, guidance)
    require(guidance["automatic_migration"] is False and guidance["runtime_mutation_performed"] is False, guidance)
    require(guidance["private_paths_included"] is False, guidance)


def test_explicit_external_runtime_is_preserved() -> None:
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1101-7-explicit-"))
    env = {"EIDOLON_DATA_DIR": str(runtime), "HOME": str(runtime.parent)}
    status = launch_environment.prepare_ordinary_launch_environment(ROOT, environment=env, create_runtime=True)
    require(env["EIDOLON_DATA_DIR"] == str(runtime), env)
    require(status["explicit_override_preserved"] is True and status["runtime_external"] is True, status)


def test_new_external_runtime_seeds_only_source_safe_defaults() -> None:
    parent = Path(tempfile.mkdtemp(prefix="eidolon-v1101-7-home-"))
    env = {"HOME": str(parent), "XDG_DATA_HOME": str(parent / "xdg")}
    before = _source_snapshot()
    status = launch_environment.prepare_ordinary_launch_environment(ROOT, environment=env, platform_name="Linux")
    after = _source_snapshot()
    runtime = Path(env["EIDOLON_DATA_DIR"])
    files = sorted(path.relative_to(runtime).as_posix() for path in runtime.rglob("*") if path.is_file())
    expected = sorted(Path(item).relative_to("data").as_posix() for item in SOURCE_DATA_ALLOWLIST)
    require(files == expected, {"files": files, "expected": expected})
    require(status["source_safe_defaults_seeded"] == len(expected), status)
    require(before == after, "source changed")


def test_runtime_guide_is_redacted_unless_paths_are_explicitly_requested() -> None:
    env = os.environ.copy()
    env.pop("EIDOLON_DATA_DIR", None)
    redacted = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "runtime-guide", "--json"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    require(redacted.returncode == 0, redacted.stderr)
    payload = json.loads(redacted.stdout)
    require(payload["private_paths_included"] is False, payload)
    encoded = redacted.stdout.lower()
    require("active_runtime_root" not in encoded and "source_root" not in encoded, encoded)
    local = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "runtime-guide", "--show-paths"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    require(local.returncode == 0 and "active_runtime_root" in local.stdout, local.stderr)


def test_route_and_shell_expose_non_mutating_runtime_guidance() -> None:
    shell = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    dashboard = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
    verifier = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
    for token in ("Runtime home", "runtime-state", "No data is moved automatically"):
        require(token in shell, token)
    require('/api/first-use/runtime-guidance' in dashboard, "guidance route")
    require(verifier.count('"tools/v1101_7_source_runtime_migration_guidance_tests.py"') == 1, "focused registration")


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
    report = {"suite": "v1101.7-source-runtime-migration-guidance", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
