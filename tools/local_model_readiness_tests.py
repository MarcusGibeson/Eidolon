from __future__ import annotations

"""Deterministic v1079.0 provider readiness and native-smoke fixtures."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
for path in (str(AGENT), str(TOOLS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from local_model import LocalModelConfig
from local_model_integration_tests import FixtureHandler, STATE, _config, _free_port, _snapshot_source
from local_model_evidence import EVIDENCE_SOURCE_FIXTURE
from local_model_readiness import native_model_smoke as _native_model_smoke, provider_readiness as _provider_readiness


def provider_readiness(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("evidence_source", EVIDENCE_SOURCE_FIXTURE)
    return _provider_readiness(*args, **kwargs)


def native_model_smoke(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("evidence_source", EVIDENCE_SOURCE_FIXTURE)
    return _native_model_smoke(*args, **kwargs)


def run_tests() -> dict[str, Any]:
    before = _snapshot_source()
    results: list[dict[str, Any]] = []
    temp_data = tempfile.TemporaryDirectory(prefix="eidolon-readiness-fixture-")
    previous_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = temp_data.name

    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{port}"

    def case(name: str, callback: Callable[[], None]) -> None:
        STATE.scenario = "healthy"
        STATE.request_count = 0
        STATE.requests.clear()
        started = time.monotonic()
        try:
            callback()
        except Exception as error:
            results.append({"name": name, "status": "fail", "seconds": round(time.monotonic()-started, 4), "error": repr(error)})
        else:
            results.append({"name": name, "status": "pass", "seconds": round(time.monotonic()-started, 4)})

    def healthy(provider: str) -> None:
        report = provider_readiness(config=_config(provider, endpoint))
        assert report["status"] == "ready", report
        assert report["service_available"] is True
        assert report["generation_model_available"] is True
        assert report["embedding_model_available"] is True
        assert report["capabilities"]["generation"]["available"] is True

    def missing_generation() -> None:
        report = provider_readiness(config=replace(_config("ollama", endpoint), model="absent-model"))
        assert report["status"] == "blocked", report
        assert report["generation_model_available"] is False
        assert "missing_model" in {row["classification"] for row in report["issues"]}

    def missing_embedding() -> None:
        report = provider_readiness(config=replace(_config("llama_cpp", endpoint), embed_model="absent-embed"))
        assert report["status"] == "degraded", report
        assert report["embedding_model_available"] is False
        assert "missing_embedding_model" in {row["classification"] for row in report["issues"]}

    def connection_failure() -> None:
        closed = f"http://127.0.0.1:{_free_port()}"
        report = provider_readiness(config=_config("ollama", closed))
        assert report["status"] == "blocked", report
        assert "connection_failure" in {row["classification"] for row in report["issues"]}

    def read_timeout() -> None:
        STATE.scenario = "timeout"
        report = provider_readiness(config=_config("ollama", endpoint, read_timeout_seconds=0.03))
        assert report["status"] == "blocked", report
        assert "read_timeout" in {row["classification"] for row in report["issues"]}

    def malformed() -> None:
        STATE.scenario = "malformed_json"
        report = provider_readiness(config=_config("ollama", endpoint))
        assert report["status"] == "blocked", report
        assert "malformed_response" in {row["classification"] for row in report["issues"]}

    def invalid_configuration() -> None:
        report = provider_readiness(config=LocalModelConfig(provider="mystery", endpoint=endpoint, model="x", embed_model="y"))
        assert report["status"] == "blocked", report
        assert report["issues"][0]["classification"] == "configuration_error"

    def opt_in_required() -> None:
        report = native_model_smoke(config=_config("ollama", endpoint), confirmed=False)
        assert report["status"] == "blocked"
        assert report["confirmation_required"] is True
        assert STATE.request_count == 0

    def healthy_native(provider: str) -> None:
        report = native_model_smoke(config=_config(provider, endpoint), confirmed=True, timeout_seconds=1.0)
        assert report["status"] == "pass", report
        assert [row["status"] for row in report["checks"]] == ["pass", "pass", "pass", "pass"]
        assert report["native_evidence"] is False
        assert report["evidence_receipt"]["evidence_source"] == "fixture_simulation"
        assert report["evidence_receipt"]["native_provider_evidence"] is False

    def unsupported_embedding() -> None:
        STATE.scenario = "unsupported_embedding"
        report = native_model_smoke(config=_config("llama_cpp", endpoint), confirmed=True, timeout_seconds=1.0)
        assert report["status"] == "partial", report
        embedding = next(row for row in report["checks"] if row["name"] == "bounded_embedding")
        assert embedding["status"] == "unsupported", embedding
        assert embedding["error"]["classification"] == "unsupported_capability"

    def api_readiness_route() -> None:
        from settings_manager import DEFAULT_SETTINGS

        settings = dict(DEFAULT_SETTINGS)
        settings.update({
            "local_model_provider": "ollama",
            "local_model_endpoint": endpoint,
            "local_model": "fixture-ollama",
            "embed_model": "fixture-embed",
            "local_model_retry_limit": 0,
        })
        (Path(temp_data.name) / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
        from api_server import handle_api_get

        status_code, payload = handle_api_get("/api/local-model/readiness")
        assert status_code == 200, (status_code, payload)
        assert payload.get("ok") is True
        assert payload["data"]["status"] == "ready", payload
        assert payload["data"]["capabilities"]["streaming"]["available"] is True

    def cli_smoke_requires_confirmation() -> None:
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, "eidolon.py", "model-smoke", "--json"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert completed.returncode == 2, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["confirmation_required"] is True
        assert payload["native_evidence"] is False

    for name, callback in [
        ("healthy_ollama_readiness", lambda: healthy("ollama")),
        ("healthy_llama_cpp_readiness", lambda: healthy("llama_cpp")),
        ("missing_generation_model", missing_generation),
        ("missing_embedding_model", missing_embedding),
        ("connection_failure_classification", connection_failure),
        ("read_timeout_classification", read_timeout),
        ("malformed_response_classification", malformed),
        ("invalid_configuration_classification", invalid_configuration),
        ("native_smoke_requires_explicit_opt_in", opt_in_required),
        ("healthy_ollama_native_smoke", lambda: healthy_native("ollama")),
        ("healthy_llama_cpp_native_smoke", lambda: healthy_native("llama_cpp")),
        ("unsupported_embedding_capability", unsupported_embedding),
        ("api_readiness_route", api_readiness_route),
        ("cli_native_smoke_requires_confirmation", cli_smoke_requires_confirmation),
    ]:
        case(name, callback)

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    temp_data.cleanup()
    if previous_data_dir is None:
        os.environ.pop("EIDOLON_DATA_DIR", None)
    else:
        os.environ["EIDOLON_DATA_DIR"] = previous_data_dir

    after = _snapshot_source()
    unchanged = before == after
    if not unchanged:
        results.append({"name": "source_tree_immutability", "status": "fail", "error": "Source tree changed during readiness fixtures."})
    passed = sum(row["status"] == "pass" for row in results)
    ok = passed == len(results) and unchanged
    return {
        "suite": "v1079.0 provider readiness and native smoke fixtures",
        "evidence_type": "fixture_simulation",
        "native_model_evidence": False,
        "ok": ok,
        "status": "pass" if ok else "fail",
        "passed": passed,
        "total": len(results),
        "source_tree_unchanged": unchanged,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic provider readiness and native-smoke fixtures.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_tests()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"{report['status'].upper()}: {report['passed']}/{report['total']} readiness checks")
        for row in report["results"]:
            print(f"- {row['status']}: {row['name']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
