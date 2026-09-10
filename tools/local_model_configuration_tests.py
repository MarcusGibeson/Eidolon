from __future__ import annotations

"""Deterministic v1079.1 separate-endpoint and dashboard configuration fixtures.

These tests use local HTTP fixtures only. They never claim native Ollama,
llama.cpp, Windows, model-installation, or model-file evidence.
"""

import argparse
import hashlib
import html
import json
import os
import socket
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for item in (str(AGENT), str(ROOT)):
    if item not in sys.path:
        sys.path.insert(0, item)

from local_model import GenerationSettings, LocalModelClient, LocalModelConfig
from local_model_integration_tests import _snapshot_source
from local_model_evidence import EVIDENCE_SOURCE_FIXTURE
from local_model_readiness import native_model_smoke as _native_model_smoke, provider_readiness as _provider_readiness


def provider_readiness(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("evidence_source", EVIDENCE_SOURCE_FIXTURE)
    return _provider_readiness(*args, **kwargs)


def native_model_smoke(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("evidence_source", EVIDENCE_SOURCE_FIXTURE)
    return _native_model_smoke(*args, **kwargs)


@dataclass
class EndpointState:
    scenario: str = "healthy"
    provider: str = "ollama"
    models: list[str] = field(default_factory=list)
    requests: list[dict[str, Any]] = field(default_factory=list)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        value = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


class EndpointHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> EndpointState:
        return self.server.state  # type: ignore[attr-defined]

    def _send(self, status: int, payload: Any, content_type: str = "application/json") -> None:
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _scenario(self) -> bool:
        if self.state.scenario == "timeout":
            # Keep the artificial delay well above the client deadline so a
            # busy Windows scheduler cannot also time out the healthy fixture.
            time.sleep(1.0)
        if self.state.scenario == "malformed":
            self._send(200, b"{bad-json", "application/json")
            return True
        if self.state.scenario == "http_error":
            self._send(503, {"error": "fixture service unavailable"})
            return True
        return False

    def do_GET(self) -> None:
        self.state.requests.append({"method": "GET", "path": self.path})
        if self._scenario():
            return
        if self.path == "/api/version":
            self._send(200, {"version": "fixture-ollama-v1079.1"})
        elif self.path == "/api/tags":
            self._send(200, {"models": [{"name": name} for name in self.state.models]})
        elif self.path == "/health":
            self._send(200, {"status": "ok", "version": "fixture-llama-v1079.1"})
        elif self.path == "/v1/models":
            self._send(200, {"object": "list", "data": [{"id": name} for name in self.state.models]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        body = _read_json(self)
        self.state.requests.append({"method": "POST", "path": self.path, "body": body})
        if self._scenario():
            return
        if self.path == "/api/generate":
            if body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Connection", "close")
                self.end_headers()
                for row in (b'{"response":"SEPARATE_","done":false}\n', b'{"response":"OK","done":false}\n', b'{"done":true}\n'):
                    self.wfile.write(row)
                    self.wfile.flush()
                self.close_connection = True
            else:
                self._send(200, {"response": "SEPARATE_OK", "done": True})
            return
        if self.path == "/api/embed":
            self._send(200, {"embeddings": [[0.11, 0.22, 0.33, 0.44]]})
            return
        if self.path == "/v1/chat/completions":
            if body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "close")
                self.end_headers()
                for row in (
                    b'data: {"choices":[{"delta":{"content":"SEPARATE_"}}]}\n\n',
                    b'data: {"choices":[{"delta":{"content":"OK"}}]}\n\n',
                    b'data: [DONE]\n\n',
                ):
                    self.wfile.write(row)
                    self.wfile.flush()
                self.close_connection = True
            else:
                self._send(200, {"choices": [{"message": {"role": "assistant", "content": "SEPARATE_OK"}}]})
            return
        if self.path == "/v1/embeddings":
            self._send(200, {"data": [{"embedding": [0.55, 0.66, 0.77]}]})
            return
        self._send(404, {"error": "not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


class FixtureServer:
    def __init__(self, state: EndpointState) -> None:
        self.state = state
        self.server = ThreadingHTTPServer(("127.0.0.1", _free_port()), EndpointHandler)
        self.server.state = state  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.endpoint = f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> "FixtureServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _config(provider: str, generation_endpoint: str, embedding_endpoint: str = "", **overrides: Any) -> LocalModelConfig:
    return LocalModelConfig(
        provider=provider,
        endpoint=generation_endpoint,
        embedding_endpoint=embedding_endpoint,
        model="gen-model",
        embed_model="embed-model",
        context_size=4096,
        connect_timeout_seconds=overrides.pop("connect_timeout_seconds", 1.0),
        read_timeout_seconds=overrides.pop("read_timeout_seconds", 3.0),
        retry_limit=0,
        retry_delay_seconds=0.0,
        generation=GenerationSettings(max_tokens=24, temperature=0.0, top_p=0.9, top_k=20, repeat_penalty=1.05),
    ).validated()


def run_tests() -> dict[str, Any]:
    before = _snapshot_source()
    results: list[dict[str, Any]] = []
    previous_data = os.environ.get("EIDOLON_DATA_DIR")
    temp_data = tempfile.TemporaryDirectory(prefix="eidolon-v1079-1-config-")
    os.environ["EIDOLON_DATA_DIR"] = temp_data.name

    from local_model_configuration import (
        LocalModelConfigurationValidationError,
        configuration_payload,
        save_local_model_configuration,
        validate_local_model_configuration,
    )

    def case(name: str, callback: Callable[[], None]) -> None:
        started = time.monotonic()
        try:
            callback()
        except Exception as error:
            results.append({"name": name, "status": "fail", "seconds": round(time.monotonic() - started, 4), "error": repr(error)})
        else:
            results.append({"name": name, "status": "pass", "seconds": round(time.monotonic() - started, 4)})

    def legacy_single_endpoint_fallback() -> None:
        state = EndpointState(provider="ollama", models=["gen-model", "embed-model"])
        with FixtureServer(state) as server:
            config = _config("ollama", server.endpoint)
            assert config.embedding_endpoint == ""
            assert config.resolved_embedding_endpoint == server.endpoint
            assert config.uses_legacy_single_endpoint is True
            with LocalModelClient(config) as client:
                assert client.generate("hello") == "SEPARATE_OK"
                assert client.embed("hello") == [0.11, 0.22, 0.33, 0.44]
            paths = [item["path"] for item in state.requests]
            assert "/api/generate" in paths and "/api/embed" in paths

    def separate_healthy(provider: str) -> None:
        generation = EndpointState(provider=provider, models=["gen-model"])
        embedding = EndpointState(provider=provider, models=["embed-model"])
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            config = _config(provider, gen_server.endpoint, embed_server.endpoint)
            readiness = provider_readiness(config=config)
            assert readiness["status"] == "ready", readiness
            assert readiness["generation_endpoint"] == gen_server.endpoint
            assert readiness["embedding_endpoint"] == embed_server.endpoint
            assert readiness["generation_service_available"] is True
            assert readiness["embedding_service_available"] is True
            smoke = native_model_smoke(config=config, confirmed=True, timeout_seconds=1.0)
            assert smoke["status"] == "pass", smoke
            assert [item["status"] for item in smoke["checks"]] == ["pass", "pass", "pass", "pass"]
            assert any(item["path"] in {"/api/generate", "/v1/chat/completions"} for item in generation.requests)
            assert any(item["path"] in {"/api/embed", "/v1/embeddings"} for item in embedding.requests)
            assert not any(item["path"] in {"/api/embed", "/v1/embeddings"} for item in generation.requests)

    def generation_unavailable() -> None:
        embedding = EndpointState(provider="llama_cpp", models=["embed-model"])
        with FixtureServer(embedding) as embed_server:
            config = _config("llama_cpp", f"http://127.0.0.1:{_free_port()}", embed_server.endpoint)
            report = provider_readiness(config=config)
            assert report["status"] == "blocked", report
            assert report["generation_service_available"] is False
            assert report["embedding_service_available"] is True
            assert any(item.get("service") == "generation" and item.get("classification") == "connection_failure" for item in report["issues"])

    def embedding_unavailable() -> None:
        generation = EndpointState(provider="ollama", models=["gen-model"])
        with FixtureServer(generation) as gen_server:
            config = _config("ollama", gen_server.endpoint, f"http://127.0.0.1:{_free_port()}")
            report = provider_readiness(config=config)
            assert report["status"] == "degraded", report
            assert report["generation_service_available"] is True
            assert report["embedding_service_available"] is False
            assert any(item.get("service") == "embedding" and item.get("classification") == "connection_failure" for item in report["issues"])

    def missing_generation_model() -> None:
        generation = EndpointState(provider="llama_cpp", models=["other-model"])
        embedding = EndpointState(provider="llama_cpp", models=["embed-model"])
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            report = provider_readiness(config=_config("llama_cpp", gen_server.endpoint, embed_server.endpoint))
            assert report["status"] == "blocked", report
            assert report["generation_model_available"] is False
            assert any(item.get("classification") == "missing_model" and item.get("service") == "generation" for item in report["issues"])

    def missing_embedding_model() -> None:
        generation = EndpointState(provider="ollama", models=["gen-model"])
        embedding = EndpointState(provider="ollama", models=["other-embed"])
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            report = provider_readiness(config=_config("ollama", gen_server.endpoint, embed_server.endpoint))
            assert report["status"] == "degraded", report
            assert report["embedding_model_available"] is False
            assert any(item.get("classification") == "missing_embedding_model" and item.get("service") == "embedding" for item in report["issues"])

    def malformed_generation_response() -> None:
        generation = EndpointState(provider="ollama", models=["gen-model"], scenario="malformed")
        embedding = EndpointState(provider="ollama", models=["embed-model"])
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            report = provider_readiness(config=_config("ollama", gen_server.endpoint, embed_server.endpoint))
            assert report["status"] == "blocked", report
            assert any(item.get("classification") == "malformed_response" and item.get("service") == "generation" for item in report["issues"])

    def embedding_timeout() -> None:
        generation = EndpointState(provider="llama_cpp", models=["gen-model"])
        embedding = EndpointState(provider="llama_cpp", models=["embed-model"], scenario="timeout")
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            config = _config("llama_cpp", gen_server.endpoint, embed_server.endpoint, read_timeout_seconds=0.35)
            report = provider_readiness(config=config)
            assert report["status"] == "degraded", report
            assert any(item.get("classification") == "read_timeout" and item.get("service") == "embedding" for item in report["issues"])

    def dashboard_save_validation() -> None:
        invalid = {
            "local_model_provider": "llama_cpp",
            "local_model_endpoint": "not-a-url",
            "local_model_embedding_endpoint": "http://127.0.0.1:8081",
            "local_model": "gen-model",
            "embed_model": "embed-model",
        }
        try:
            save_local_model_configuration(invalid)
        except LocalModelConfigurationValidationError as error:
            assert any(item["field"] == "local_model_endpoint" for item in error.errors), error.errors
        else:
            raise AssertionError("Invalid dashboard endpoint was saved")

        valid = {
            "local_model_provider": "llama_cpp",
            "local_model_endpoint": "http://127.0.0.1:8080/",
            "local_model_embedding_endpoint": "http://127.0.0.1:8081/",
            "local_model": "gen-model",
            "embed_model": "embed-model",
            "local_model_context_size": 8192,
            "local_model_connect_timeout_seconds": 3.0,
            "local_model_read_timeout_seconds": 60.0,
            "local_model_max_tokens": 256,
            "local_model_temperature": 0.4,
            "local_model_top_p": 0.9,
            "local_model_top_k": 40,
            "local_model_repeat_penalty": 1.1,
        }
        saved = save_local_model_configuration(valid)
        assert saved["values"]["local_model_endpoint"] == "http://127.0.0.1:8080"
        assert saved["values"]["local_model_embedding_endpoint"] == "http://127.0.0.1:8081"
        assert saved["embedding_endpoint_uses_generation_fallback"] is False
        assert saved["validation"]["status"] == "valid"

    def dashboard_and_api_controls() -> None:
        generation = EndpointState(provider="ollama", models=["gen-model"])
        embedding = EndpointState(provider="ollama", models=["embed-model"])
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            values = {
                "local_model_provider": "ollama",
                "local_model_endpoint": gen_server.endpoint,
                "local_model_embedding_endpoint": embed_server.endpoint,
                "local_model": "gen-model",
                "embed_model": "embed-model",
                "local_model_context_size": 4096,
                "local_model_connect_timeout_seconds": 0.2,
                "local_model_read_timeout_seconds": 1.0,
                "local_model_max_tokens": 32,
                "local_model_temperature": 0.0,
                "local_model_top_p": 0.9,
                "local_model_top_k": 20,
                "local_model_repeat_penalty": 1.05,
            }
            save_local_model_configuration(values)
            from api_server import ApiError, handle_api_get, handle_api_post
            status, payload = handle_api_get("/api/local-model/configuration")
            assert status == 200 and payload["data"]["validation"]["status"] == "valid"
            status, payload = handle_api_post("/api/local-model/readiness", {"settings": values})
            assert status == 200 and payload["data"]["status"] == "ready", payload
            try:
                handle_api_post("/api/local-model/native-smoke", {"settings": values})
            except ApiError as error:
                assert error.status == 400
            else:
                raise AssertionError("Native smoke ran without exact confirmation")
            status, payload = handle_api_post("/api/local-model/native-smoke", {
                "settings": values, "confirm": "RUN_NATIVE_MODEL_SMOKE", "timeout_seconds": 1,
            })
            assert status == 200 and payload["data"]["status"] == "pass", payload
            serialized = json.dumps(payload)
            assert "nativeEvent" not in serialized and "currentTarget" not in serialized

            from dashboard_local_model import render_local_model_status
            page = render_local_model_status(
                safe=lambda value: html.escape(str(value if value is not None else ""), quote=True),
                card=lambda title, body: f"<section><h3>{title}</h3>{body}</section>",
                layout=lambda route, body: body,
            )
            assert "local_model_embedding_endpoint" in page
            assert "Check readiness" in page and "Run native smoke" in page
            assert "/api/local-model/configuration" in page
            assert page.count("join('\\n')") == 2
            assert "join('\n')" not in page
            assert "title=" not in page.lower()

    def fallback_configuration_payload() -> None:
        merged, config = validate_local_model_configuration({"local_model_embedding_endpoint": ""})
        payload = configuration_payload(merged)
        assert config.resolved_embedding_endpoint == config.endpoint
        assert payload["embedding_endpoint_uses_generation_fallback"] is True
        assert payload["effective_embedding_endpoint"] == config.endpoint

    for name, callback in [
        ("legacy_single_endpoint_fallback", legacy_single_endpoint_fallback),
        ("separate_healthy_ollama_endpoints", lambda: separate_healthy("ollama")),
        ("separate_healthy_llama_cpp_endpoints", lambda: separate_healthy("llama_cpp")),
        ("generation_service_unavailable", generation_unavailable),
        ("embedding_service_unavailable", embedding_unavailable),
        ("missing_generation_model", missing_generation_model),
        ("missing_embedding_model", missing_embedding_model),
        ("malformed_generation_response", malformed_generation_response),
        ("embedding_timeout_behavior", embedding_timeout),
        ("dashboard_save_validation", dashboard_save_validation),
        ("dashboard_api_readiness_and_smoke_controls", dashboard_and_api_controls),
        ("configuration_payload_legacy_fallback", fallback_configuration_payload),
    ]:
        case(name, callback)

    temp_data.cleanup()
    if previous_data is None:
        os.environ.pop("EIDOLON_DATA_DIR", None)
    else:
        os.environ["EIDOLON_DATA_DIR"] = previous_data

    after = _snapshot_source()
    unchanged = before == after
    if not unchanged:
        results.append({
            "name": "source_tree_immutability",
            "status": "fail",
            "error": "Source tree changed during v1079.1 configuration fixtures.",
            "added": sorted(set(after) - set(before)),
            "removed": sorted(set(before) - set(after)),
            "changed": sorted(path for path in set(before) & set(after) if before[path] != after[path]),
        })
    passed = sum(item["status"] == "pass" for item in results)
    ok = passed == len(results) and unchanged
    return {
        "suite": "v1079.1 local-model configuration and separate-endpoint fixtures",
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
    parser = argparse.ArgumentParser(description="Run deterministic v1079.1 separate-endpoint and dashboard configuration fixtures.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_tests()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"{report['status'].upper()}: {report['passed']}/{report['total']} v1079.1 checks")
        for item in report["results"]:
            print(f"- {item['status']}: {item['name']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
