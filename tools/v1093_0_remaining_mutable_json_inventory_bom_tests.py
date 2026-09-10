from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bom(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(value, indent=2).encode("utf-8"))


def reload_for_data_dir(module_name: str, data_dir: Path):
    os.environ["EIDOLON_DATA_DIR"] = str(data_dir)
    for name in list(sys.modules):
        if name == module_name or name in {"paths", "settings_manager", "approval_manager", "task_queue"}:
            sys.modules.pop(name, None)
    return importlib.import_module(module_name)


def test_inventory_is_complete_and_content_free() -> None:
    inventory = importlib.import_module("metadata_store_inventory")
    rows = inventory.list_mutable_json_stores()
    ids = [row["store_id"] for row in rows]
    require(len(rows) >= 22, "mutable JSON inventory is unexpectedly narrow")
    require(len(ids) == len(set(ids)), "mutable JSON inventory contains duplicate store identifiers")
    required = {
        "settings", "projects", "memories", "tasks", "approvals", "conversations",
        "conversation_drafts", "conversation_operations", "conversation_navigation",
        "conversation_tabs", "project_switching", "project_root_recovery",
        "conversation_evaluations", "conversation_campaigns", "conversation_findings",
        "workspace_execution", "release_pipeline", "self_development",
    }
    require(required.issubset(set(ids)), "mutable JSON inventory omits required runtime families")
    project = next(row for row in rows if row["store_id"] == "projects")
    require(project["operator_registry"] is True, "operator projects registry is not explicitly protected")
    summary = inventory.inspect_mutable_json_stores(data_dir=Path(tempfile.mkdtemp()))
    require(summary["payload_returned"] is False, "inventory leaked payload content")
    require(all(row["payload_returned"] is False for row in summary["stores"]), "store inspection leaked payload content")


def test_settings_bom_load_does_not_rewrite() -> None:
    with tempfile.TemporaryDirectory() as td:
        data = Path(td)
        module = reload_for_data_dir("settings_manager", data)
        payload = dict(module.DEFAULT_SETTINGS)
        payload["dashboard_port"] = 9876
        write_bom(data / "settings.json", payload)
        before = sha(data / "settings.json")
        loaded = module.load_settings()
        require(loaded["dashboard_port"] == 9876, "settings BOM load failed")
        require(sha(data / "settings.json") == before, "settings read rewrote BOM metadata")


def test_core_mutable_stores_accept_bom_without_rewrite() -> None:
    from json_storage import load_json_file

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        samples = {
            "tasks.json": ({"version": 2, "tasks": []}, dict),
            "approval.json": ({"id": "approval_test", "status": "pending"}, dict),
            "session.json": ({"id": "session_test", "turns": []}, dict),
            "operation.json": ({"operation_id": "op_test"}, dict),
            "navigation.json": ({"revision": 1}, dict),
            "campaign.json": ({"campaign_id": "eval_campaign_20260101T000000_abcdef123456"}, dict),
            "memories.json": ([{"type": "fact", "content": "test"}], list),
        }
        for name, (payload, root_type) in samples.items():
            path = base / name
            write_bom(path, payload)
            before = sha(path)
            require(load_json_file(path, None, expected_type=root_type) == payload, f"BOM load failed for {name}")
            require(sha(path) == before, f"read rewrote {name}")


def test_selected_runtime_helpers_use_shared_storage() -> None:
    modules = [
        "settings_manager.py", "approval_manager.py", "task_queue.py",
        "conversation_sessions.py", "conversation_operations.py",
        "conversation_navigation.py", "conversation_tab_coordination.py",
        "project_root_recovery.py", "workspace_execution.py", "release_pipeline.py",
        "conversation_evaluation_campaign.py",
    ]
    for name in modules:
        source = (AGENT / name).read_text(encoding="utf-8")
        require("load_json_file" in source, f"{name} does not use BOM-aware loading")
        require("write_json_atomic" in source, f"{name} does not use canonical atomic saves")


def test_invalid_json_and_root_shape_are_preserved() -> None:
    from json_storage import load_json_file

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        invalid = base / "invalid.json"
        invalid.write_bytes(b"\xef\xbb\xbf{not-json")
        before = invalid.read_bytes()
        require(load_json_file(invalid, {"safe": True}, expected_type=dict) == {"safe": True}, "invalid JSON default failed")
        require(invalid.read_bytes() == before, "invalid JSON source was modified")
        wrong = base / "wrong.json"
        write_bom(wrong, [1, 2, 3])
        before_wrong = wrong.read_bytes()
        require(load_json_file(wrong, {"safe": True}, expected_type=dict) == {"safe": True}, "wrong root default failed")
        require(wrong.read_bytes() == before_wrong, "wrong-root source was modified")


def test_direct_and_package_imports() -> None:
    direct = importlib.import_module("metadata_store_inventory")
    require(len(direct.list_mutable_json_stores()) >= 22, "direct import failed")
    parent = str(ROOT)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    package = importlib.import_module("conscious_agent.metadata_store_inventory")
    require(len(package.list_mutable_json_stores()) >= 22, "package import failed")


def test_release_metadata_and_docs() -> None:
    release = (AGENT / "release_metadata.py").read_text(encoding="utf-8")
    require('RUNTIME_VERSION = "1093.' in release, "runtime version left the v1093 arc")
    require("v1093.0" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "release history missing v1093.0")
    require("v1093.1" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "next steps missing v1093.1")
    require("v1150" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "Codex review schedule missing")


def main() -> int:
    tests = [
        test_inventory_is_complete_and_content_free,
        test_settings_bom_load_does_not_rewrite,
        test_core_mutable_stores_accept_bom_without_rewrite,
        test_selected_runtime_helpers_use_shared_storage,
        test_invalid_json_and_root_shape_are_preserved,
        test_direct_and_package_imports,
        test_release_metadata_and_docs,
    ]
    passed = 0
    failures: list[str] = []
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as error:
            failures.append(f"{test.__name__}: {type(error).__name__}: {error}")
    report = {
        "version": "1093.0",
        "suite": "remaining-mutable-json-inventory-bom",
        "passed": passed,
        "total": len(tests),
        "ok": passed == len(tests),
        "failures": failures,
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
