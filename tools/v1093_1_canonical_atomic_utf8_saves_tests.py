from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_canonical_write_is_bom_free_and_atomic() -> None:
    from json_storage import write_json_atomic
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "state.json"
        write_json_atomic(path, {"snowman": "☃", "value": 2}, expected_type=dict, sort_keys=True)
        raw = path.read_bytes()
        require(not raw.startswith(b"\xef\xbb\xbf"), "canonical save retained a BOM")
        require(raw.endswith(b"\n"), "canonical save omitted final newline")
        require(json.loads(raw.decode("utf-8"))["snowman"] == "☃", "UTF-8 content changed")
        require(not list(path.parent.glob(f".{path.name}.transaction-*.tmp")), "temporary file remained")


def test_invalid_root_shape_never_replaces_prior_file() -> None:
    from json_storage import JsonStorageError, write_json_atomic
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "state.json"
        path.write_text('{"kept": true}\n', encoding="utf-8")
        before = path.read_bytes()
        try:
            write_json_atomic(path, [1, 2, 3], expected_type=dict)
        except JsonStorageError:
            pass
        else:
            raise AssertionError("wrong-root write was accepted")
        require(path.read_bytes() == before, "wrong-root write replaced prior file")


def test_serialization_failure_never_replaces_prior_file() -> None:
    from json_storage import write_json_atomic
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "state.json"
        path.write_text('{"kept": true}\n', encoding="utf-8")
        before = path.read_bytes()
        try:
            write_json_atomic(path, {"bad": object()}, expected_type=dict)
        except TypeError:
            pass
        else:
            raise AssertionError("unserializable value was accepted")
        require(path.read_bytes() == before, "serialization failure replaced prior file")
        require(not list(path.parent.glob("*.tmp")), "serialization failure left a temporary file")


def test_permission_retry_is_bounded_and_preserves_result() -> None:
    storage = importlib.import_module("json_storage")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "state.json"
        original_replace = storage.os.replace
        calls = {"count": 0}
        def flaky(source, target):
            calls["count"] += 1
            if calls["count"] < 3:
                raise PermissionError("simulated Windows sharing")
            return original_replace(source, target)
        storage.os.replace = flaky
        try:
            storage.write_json_atomic(path, {"ok": True}, expected_type=dict, retry_delay_seconds=0)
        finally:
            storage.os.replace = original_replace
        require(calls["count"] == 3, "permission retry count was not bounded")
        require(json.loads(path.read_text(encoding="utf-8"))["ok"] is True, "retry did not commit valid result")


def test_concurrent_writers_use_unique_temporary_files() -> None:
    from json_storage import load_json_file, write_json_atomic
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "state.json"
        errors: list[str] = []
        def writer(index: int) -> None:
            try:
                for sequence in range(20):
                    write_json_atomic(path, {"writer": index, "sequence": sequence}, expected_type=dict)
            except Exception as error:
                errors.append(f"{type(error).__name__}: {error}")
        threads = [threading.Thread(target=writer, args=(index,)) for index in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        require(not errors, f"concurrent writers failed: {errors}")
        require(all(not thread.is_alive() for thread in threads), "concurrent writer did not finish")
        value = load_json_file(path, None, expected_type=dict)
        require(isinstance(value, dict) and set(value) == {"writer", "sequence"}, "final concurrent result is invalid")
        require(not list(path.parent.glob(f".{path.name}.transaction-*.tmp")), "concurrent writes left temp files")


def test_runtime_saves_are_routed_through_shared_atomic_helper() -> None:
    modules = [
        "memory.py", "settings_manager.py", "approval_manager.py", "task_queue.py",
        "conversation_sessions.py", "conversation_operations.py", "conversation_navigation.py",
        "conversation_tab_coordination.py", "project_root_recovery.py",
        "workspace_execution.py", "release_pipeline.py", "conversation_evaluation_campaign.py",
    ]
    for name in modules:
        source = (AGENT / name).read_text(encoding="utf-8")
        require("write_json_atomic" in source, f"{name} still bypasses shared atomic saves")


def test_settings_invalid_original_is_preserved() -> None:
    with tempfile.TemporaryDirectory() as td:
        data = Path(td)
        os.environ["EIDOLON_DATA_DIR"] = str(data)
        for name in ["paths", "settings_manager"]:
            sys.modules.pop(name, None)
        module = importlib.import_module("settings_manager")
        target = data / "settings.json"
        target.write_bytes(b"\xef\xbb\xbf{broken")
        before = target.read_bytes()
        loaded = module.load_settings()
        require(isinstance(loaded, dict) and loaded["safe_mode"] == "strict", "safe defaults not returned")
        require(target.read_bytes() == before, "invalid settings original was overwritten")


def test_release_metadata_and_docs() -> None:
    source = (AGENT / "release_metadata.py").read_text(encoding="utf-8")
    require('RUNTIME_VERSION = "1093.' in source, "runtime version left the v1093 arc")
    require("v1093.1" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "history missing v1093.1")
    require("v1093.2" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "next step missing v1093.2")


def main() -> int:
    tests = [
        test_canonical_write_is_bom_free_and_atomic,
        test_invalid_root_shape_never_replaces_prior_file,
        test_serialization_failure_never_replaces_prior_file,
        test_permission_retry_is_bounded_and_preserves_result,
        test_concurrent_writers_use_unique_temporary_files,
        test_runtime_saves_are_routed_through_shared_atomic_helper,
        test_settings_invalid_original_is_preserved,
        test_release_metadata_and_docs,
    ]
    failures: list[str] = []
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as error:
            failures.append(f"{test.__name__}: {type(error).__name__}: {error}")
    report = {"version": "1093.1", "suite": "canonical-atomic-utf8-saves", "passed": passed, "total": len(tests), "ok": passed == len(tests), "failures": failures}
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
