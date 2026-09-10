from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path.insert(0, str(AGENT))

import memory
import post_review_development_verify as isolated_verify
import relationship_memory_curation as curation
import vector_memory


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


class FakeCollection:
    def __init__(self, ids=(), *, fail_delete: bool = False):
        self.ids = set(ids)
        self.fail_delete = fail_delete
        self.deleted: list[str] = []

    def get(self, ids, include=None):
        return {"ids": [item for item in ids if item in self.ids]}

    def delete(self, ids):
        if self.fail_delete:
            raise RuntimeError("fixture delete failure")
        for item in ids:
            self.deleted.append(item)
            self.ids.discard(item)


class isolated_memory:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eidolon-v1083-2-")
        root = Path(self.temp.name)
        self.original = (memory.MEMORY_FILE, memory.THOUGHT_LOG_FILE, vector_memory.get_collection)
        memory.MEMORY_FILE = root / "memories.json"
        memory.THOUGHT_LOG_FILE = root / "thoughts.log"
        return root

    def __exit__(self, *_args):
        memory.MEMORY_FILE, memory.THOUGHT_LOG_FILE, vector_memory.get_collection = self.original
        self.temp.cleanup()


def create_retracted(content: str = "Delete after retraction"):
    created = curation.create_relationship_memory("preference", content, source="fixture_operator")
    key = created["record"]["record_key"]
    curation.update_relationship_memory(key, "retract", source="fixture_operator")
    return created, key


def test_active_memory_cannot_be_deleted() -> None:
    with isolated_memory():
        created = curation.create_relationship_memory("preference", "Active fixture")
        before = memory.load_memories()
        try:
            curation.delete_retracted_relationship_memory(created["record"]["record_key"], "DELETE")
            raise AssertionError("active memory unexpectedly deleted")
        except curation.RelationshipMemoryCurationError:
            pass
        require(memory.load_memories() == before, "active deletion mutated memory")


def test_vector_deletion_is_verified_before_content_tombstone() -> None:
    with isolated_memory():
        created, key = create_retracted("Verified vector cleanup fixture")
        memory_id = created["record"]["id"]
        collection = FakeCollection([memory_id])
        vector_memory.get_collection = lambda: collection
        result = curation.delete_retracted_relationship_memory(key, "DELETE", source="fixture_operator")
        require(result["vector_cleanup"]["verified_absent"], "vector absence was not verified")
        require(collection.deleted == [memory_id] and memory_id not in collection.ids, "vector row not deleted exactly once")
        stored = memory.load_memories()
        serialized = json.dumps(stored)
        require("Verified vector cleanup fixture" not in serialized, "deleted content remains")
        tombstone = stored[0]
        require(tombstone["type"] == "relationship_memory_deletion_tombstone", "tombstone missing")
        require(tombstone["schema_version"] == "2", "tombstone schema missing")
        require(tombstone["vector_cleanup"]["cleanup_complete"], "cleanup evidence incomplete")
        require("content" not in tombstone and "thought" not in tombstone and "summary" not in tombstone, "tombstone retained content")


def test_delete_failure_leaves_retracted_memory_unchanged() -> None:
    with isolated_memory():
        created, key = create_retracted("Failed vector deletion fixture")
        memory_id = created["record"]["id"]
        vector_memory.get_collection = lambda: FakeCollection([memory_id], fail_delete=True)
        before = memory.MEMORY_FILE.read_bytes()
        try:
            curation.delete_retracted_relationship_memory(key, "DELETE")
            raise AssertionError("failed vector cleanup unexpectedly deleted memory")
        except curation.RelationshipMemoryCurationError:
            pass
        require(memory.MEMORY_FILE.read_bytes() == before, "memory changed after failed vector cleanup")


def test_missing_optional_semantic_store_is_recorded_honestly() -> None:
    with isolated_memory():
        _, key = create_retracted("No semantic store fixture")
        vector_memory.get_collection = lambda: None
        result = curation.delete_retracted_relationship_memory(key, "DELETE")
        cleanup = result["vector_cleanup"]
        require(cleanup["cleanup_complete"], "unconfigured semantic store blocked local deletion")
        require(cleanup["verification_status"] == "semantic_store_unavailable", "unavailable store not labeled honestly")
        require(not cleanup["verified_absent"] and not cleanup["semantic_store_available"], "unavailable store fabricated verification")
        require(not cleanup["provider_invoked"], "semantic cleanup claimed provider invocation")


def test_repeated_cleanup_survives_restart_and_is_idempotent() -> None:
    global curation
    with isolated_memory():
        created, key = create_retracted("Restart idempotency fixture")
        memory_id = created["record"]["id"]
        collection = FakeCollection([memory_id])
        vector_memory.get_collection = lambda: collection
        first = curation.delete_retracted_relationship_memory(key, "DELETE")
        before = memory.MEMORY_FILE.read_bytes()
        curation = importlib.reload(curation)
        second = curation.delete_retracted_relationship_memory(key, "DELETE")
        require(first["changed"] and not second["changed"], "repeat deletion was not idempotent")
        require(second["idempotent_replay"], "restart replay not identified")
        require(memory.MEMORY_FILE.read_bytes() == before, "idempotent replay rewrote tombstone")
        require(collection.deleted == [memory_id], "vector delete repeated after restart")


def test_deletion_integrity_summary_is_content_free_and_read_only() -> None:
    with isolated_memory():
        _, key = create_retracted("Integrity summary secret fixture")
        vector_memory.get_collection = lambda: None
        curation.delete_retracted_relationship_memory(key, "DELETE")
        before = memory.MEMORY_FILE.read_bytes()
        summary = curation.relationship_memory_deletion_integrity_summary()
        require(memory.MEMORY_FILE.read_bytes() == before, "integrity summary mutated memory")
        require(summary["tombstone_count"] == 1 and summary["incomplete_cleanup"] == 0, "integrity counts wrong")
        require(summary["content_free_tombstones"], "tombstone content boundary failed")
        require(summary["restart_recovery_supported"] and summary["repeated_cleanup_idempotent"], "restart/idempotency contract missing")
        require("secret fixture" not in json.dumps(summary).lower(), "deleted content leaked into summary")


def test_registration_privacy_and_no_model_management() -> None:
    core = [suite.name for suite in isolated_verify.select_suites("core")]
    full = [suite.name for suite in isolated_verify.select_suites("full")]
    require(core.count("v1083.2-retraction-vector-cleanup") == 1, "core registration wrong")
    require(full.count("v1083.2-retraction-vector-cleanup") == 1, "full registration wrong")
    release_source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require(release_source.count("v1083_2_retraction_vector_cleanup_tests.py") == 1, "release registration wrong")
    source = (AGENT / "relationship_memory_curation.py").read_text(encoding="utf-8")
    require("install_model" not in source and "pull_model" not in source and "switch_provider" not in source, "memory cleanup gained model authority")
    forbidden = ("data/memories.json", "data/chroma/", "data/conversation_sessions/")
    files = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    require(not [name for name in files if any(name == item or name.startswith(item) for item in forbidden)], "private runtime state present")


TESTS = [
    ("active_memory_cannot_be_deleted", test_active_memory_cannot_be_deleted),
    ("vector_deletion_is_verified_before_content_tombstone", test_vector_deletion_is_verified_before_content_tombstone),
    ("delete_failure_leaves_retracted_memory_unchanged", test_delete_failure_leaves_retracted_memory_unchanged),
    ("missing_optional_semantic_store_is_recorded_honestly", test_missing_optional_semantic_store_is_recorded_honestly),
    ("repeated_cleanup_survives_restart_and_is_idempotent", test_repeated_cleanup_survives_restart_and_is_idempotent),
    ("deletion_integrity_summary_is_content_free_and_read_only", test_deletion_integrity_summary_is_content_free_and_read_only),
    ("registration_privacy_and_no_model_management", test_registration_privacy_and_no_model_management),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            checks.append({"name": name, "status": "pass", "message": ""})
    passed = sum(check["status"] == "pass" for check in checks)
    report = {"suite": "v1083.2-retraction-vector-cleanup", "ok": passed == len(checks), "status": "pass" if passed == len(checks) else "fail", "passed": passed, "total": len(checks), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
