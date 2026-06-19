from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN = PROJECT_ROOT / "conscious_agent" / "main.py"
SETTINGS = PROJECT_ROOT / "data" / "settings.json"
sys.path.insert(0, str(PROJECT_ROOT / "conscious_agent"))


def check_import(module: str) -> bool:
    try:
        importlib.import_module(module)
    except Exception as error:
        print(f"[fail] import {module}: {error}")
        return False
    print(f"[ok] import {module}")
    return True


def run_main(*args: str) -> bool:
    command = [sys.executable, str(MAIN), *args]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    label = " ".join(args)
    if result.returncode != 0:
        print(f"[fail] main.py {label}")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return False
    print(f"[ok] main.py {label}")
    return True


def check_settings() -> bool:
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"[fail] settings.json: {error}")
        return False

    model = data.get("local_model")
    embed_model = data.get("embed_model")
    safe_mode = data.get("safe_mode")
    print(f"[ok] settings.json local_model={model} embed_model={embed_model} safe_mode={safe_mode}")
    return True



def check_compile() -> bool:
    command = [sys.executable, "-m", "py_compile", *[str(path) for path in sorted((PROJECT_ROOT / "conscious_agent").glob("*.py"))]]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        print("[fail] py_compile conscious_agent/*.py")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return False
    print("[ok] py_compile conscious_agent/*.py")
    return True


def check_lifecycle_filters() -> bool:
    try:
        from task_lifecycle import normalize_lifecycle_stage_filter, task_lifecycle_summary

        if normalize_lifecycle_stage_filter("needs attention") != "needs_attention":
            print("[fail] lifecycle filter alias normalization")
            return False
        summary = task_lifecycle_summary(stage_filter="needs_attention")
        if "filtered_total" not in summary or "filters" not in summary:
            print("[fail] lifecycle filter summary shape")
            return False
    except Exception as error:
        print(f"[fail] lifecycle filters: {error}")
        return False
    print("[ok] lifecycle filters")
    return True


def main() -> int:
    checks = [
        check_import("requests"),
        check_import("chromadb"),
        check_settings(),
        check_compile(),
        run_main("--status"),
        run_main("--settings-health"),
        run_main("--task-work", "summary"),
        check_import("task_lifecycle"),
        check_lifecycle_filters(),
        run_main("--request-next-task-approval", "--dry-run"),
    ]
    if all(checks):
        print("Smoke check passed.")
        return 0
    print("Smoke check failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
