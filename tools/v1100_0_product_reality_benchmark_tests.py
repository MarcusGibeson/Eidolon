from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1100-benchmark-runtime-")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
sys.path[:0] = [str(AGENT), str(TOOLS)]

import api_server
import post_review_development_verify as verify
import product_reality_benchmark as benchmark
import release_metadata
from version_metadata_inventory import build_version_metadata_inventory


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def report() -> dict[str, object]:
    return benchmark.build_product_reality_benchmark()


def test_exact_benchmark_identity() -> None:
    value = report()
    require(value["version"] == "1100.0", value)
    require(value["status"] == "benchmark_complete", value)
    require(value["product_stage"] == "desktop_alpha_development", value)


def test_roadmap_contains_exactly_fifty_releases() -> None:
    value = report()
    releases = value["roadmap"]
    require(isinstance(releases, list) and len(releases) == 50, len(releases))
    require(releases[0]["version"] == "1101.0", releases[0])
    require(releases[-1]["version"] == "1105.9", releases[-1])
    require(len({item["version"] for item in releases}) == 50, "duplicate version")


def test_three_version_bundle_cadence_and_checkpoint() -> None:
    for item in report()["roadmap"]:
        patch = int(item["version"].split(".")[-1])
        expected = "A" if patch <= 2 else "B" if patch <= 5 else "C" if patch <= 8 else "checkpoint"
        require(item["bundle"] == expected, item)


def test_benchmark_is_honest_about_incomplete_product_areas() -> None:
    areas = {area["id"]: area for area in report()["areas"]}
    require(areas["natural_conversation_quality"]["status"] == "requires_native_evidence", areas)
    require(areas["conversational_action_portal"]["status"] == "partially_established", areas)
    require(areas["self_development"]["status"] == "supervised_only", areas)
    require(areas["native_desktop_product"]["status"] == "not_established", areas)


def test_established_foundations_are_preserved() -> None:
    areas = {area["id"]: area for area in report()["areas"]}
    require(areas["release_and_metadata_integrity"]["status"] == "established", areas)
    require(areas["source_runtime_separation"]["status"] == "established", areas)
    require(areas["windows_startup_and_process_reliability"]["status"] == "established_after_review_repair", areas)


def test_benchmark_is_deterministic() -> None:
    first = report()
    second = report()
    require(first == second, "benchmark changed between reads")
    for key in ("areas_digest", "roadmap_digest", "benchmark_digest"):
        require(len(first[key]) == 64, key)


def test_read_only_content_free_boundaries() -> None:
    value = report()
    for key in (
        "provider_invoked",
        "runtime_state_read",
        "runtime_state_written",
        "source_modified",
        "installation_performed",
        "promotion_performed",
        "certification_performed",
        "autonomy_claimed",
    ):
        require(value[key] is False, key)
    require(value["content_free"] is True, value)
    require(not benchmark.product_reality_benchmark_contains_private_fields(value), "private field")


def test_private_field_detector() -> None:
    require(benchmark.product_reality_benchmark_contains_private_fields({"private_note": "x"}), "note")
    require(benchmark.product_reality_benchmark_contains_private_fields({"provider_payload": "x"}), "payload")
    require(not benchmark.product_reality_benchmark_contains_private_fields(report()), "false positive")


def test_api_get_route_and_index() -> None:
    status, payload = api_server.handle_api_get("/api/product-reality-benchmark", {})
    require(status == 200, status)
    require(payload["data"]["version"] == "1100.0", payload)
    _, index = api_server.handle_api_get("/api", {})
    require("GET /api/product-reality-benchmark" in index["data"]["endpoints"], index)


def test_no_mutating_api_route() -> None:
    source = (AGENT / "api_server.py").read_text(encoding="utf-8")
    post = source[source.index("def handle_api_post") :]
    require('parts == ["product-reality-benchmark"]' not in post, "POST route exists")


def test_v1100_benchmark_remains_the_successor_baseline() -> None:
    version = tuple(int(part) for part in release_metadata.WORKING_SOURCE_VERSION.split("."))
    require(version >= (1101, 2), release_metadata.WORKING_SOURCE_VERSION)
    require(release_metadata.PREVIOUS_WORKING_SOURCE_VERSION == "1100.0", release_metadata.PREVIOUS_WORKING_SOURCE_VERSION)
    require(benchmark.BENCHMARK_VERSION == "1100.0", benchmark.BENCHMARK_VERSION)


def test_docs_contain_benchmark_and_roadmap() -> None:
    for name in ("README.md", "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        require("v1100.0" in text, name)
    roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
    entries = re.findall(r"^- \*\*v\d+\.\d+\*\*", roadmap, flags=re.MULTILINE)
    require(len(entries) == 50, f"roadmap entry count {len(entries)}")
    require("v1101.0" in roadmap and "v1105.9" in roadmap, "roadmap bounds")


def test_registration_is_exactly_once() -> None:
    names = [suite.name for suite in verify.SUITES]
    name = "v1100.0-product-reality-benchmark"
    require(names.count(name) == 1, names.count(name))
    benchmark_index = names.index(name)
    require("v1101.0-cold-start-budget-truth" in names[:benchmark_index], names[: benchmark_index + 1])
    require("v1099.9-consumer-use-lifecycle-consolidation" in names[benchmark_index + 1 :], names[benchmark_index: benchmark_index + 3])


def test_version_inventory_uses_working_source_authority() -> None:
    value = build_version_metadata_inventory(ROOT)
    require(value["ok"] is True, value)
    require(value["runtime_authority"] == "conscious_agent/release_metadata.py:WORKING_SOURCE_VERSION", value)


def test_release_verifier_defaults_stages_to_external_runtime() -> None:
    source = (TOOLS / "release_verify.py").read_text(encoding="utf-8")
    require("runtime_env: dict[str, str] = {}" in source, "runtime environment is not initialized")
    require("stage_env = env_overrides if env_overrides is not None else runtime_env" in source, "fixture stages can write into source")


def test_version_history_does_not_invent_v1099_0() -> None:
    history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    require("## v1099.0 " not in history, "invented skipped release")


def test_source_only_contract() -> None:
    forbidden = {
        "data/projects.json",
        "data/tasks.json",
        "data/memories.json",
        "data/conversations.json",
        ".git",
        ".venv",
        "venv",
    }
    relative = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")}
    require(not (forbidden & relative), forbidden & relative)
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        require("__pycache__" not in rel.parts, rel)
        require(path.suffix not in {".pyc", ".pyo", ".zip"}, rel)


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks: list[dict[str, str]] = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as exc:
            checks.append({"name": name, "status": "fail", "message": f"{type(exc).__name__}: {exc}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    value = {
        "suite": "v1100.0-product-reality-benchmark",
        "ok": passed == len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "passed": passed,
        "total": len(TESTS),
        "checks": checks,
    }
    print(json.dumps(value, indent=2))
    return 0 if value["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
