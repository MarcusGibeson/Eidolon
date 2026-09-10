from __future__ import annotations

"""Deterministic fixture tests for the v1078.9 provider-neutral local-model path.

These fixtures never claim native Ollama or llama.cpp evidence. They run a local
HTTP stub, write runtime settings only under a temporary EIDOLON_DATA_DIR, and
verify that the source tree is unchanged.
"""

import argparse
import hashlib
import json
import os
import socket
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


class FixtureState:
    def __init__(self) -> None:
        self.scenario = "healthy"
        self.request_count = 0
        self.requests: list[dict[str, Any]] = []


STATE = FixtureState()


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


class FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

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

    def do_GET(self) -> None:
        STATE.request_count += 1
        STATE.requests.append({"method": "GET", "path": self.path})
        if STATE.scenario == "timeout":
            time.sleep(0.2)
        if STATE.scenario == "malformed_json":
            self._send(200, b"{not-json", "application/json")
            return
        if STATE.scenario == "http_error":
            self._send(500, {"error": "fixture failure"})
            return
        if STATE.scenario == "retry_then_success" and STATE.request_count == 1:
            self._send(503, {"error": "temporarily unavailable"})
            return
        if self.path == "/api/version":
            self._send(200, {"version": "fixture-ollama-1"})
        elif self.path == "/api/tags":
            self._send(200, {"models": [{"name": "fixture-ollama"}, {"name": "fixture-embed"}]})
        elif self.path == "/health":
            self._send(200, {"status": "ok", "version": "fixture-llama-1"})
        elif self.path == "/v1/models":
            self._send(200, {"object": "list", "data": [{"id": "fixture-llama"}, {"id": "fixture-embed"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        STATE.request_count += 1
        body = _read_json(self)
        STATE.requests.append({"method": "POST", "path": self.path, "body": body})

        if STATE.scenario == "timeout":
            time.sleep(0.2)
        if STATE.scenario == "retry_then_success" and STATE.request_count == 1:
            self._send(503, {"error": "temporarily unavailable"})
            return
        if STATE.scenario == "missing_model":
            self._send(404, {"error": "model not found"})
            return
        if STATE.scenario == "http_error":
            self._send(500, {"error": "fixture failure"})
            return
        if STATE.scenario == "malformed_json":
            self._send(200, b"{not-json", "application/json")
            return

        if self.path == "/api/generate":
            if body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Connection", "close")
                self.end_headers()
                rows = [b'{"response":"Hello ","done":false}\n']
                if STATE.scenario == "malformed_stream":
                    rows.append(b"not-json\n")
                elif STATE.scenario != "interrupted_stream":
                    rows.extend([b'{"response":"Ollama","done":false}\n', b'{"done":true}\n'])
                for row in rows:
                    self.wfile.write(row)
                    self.wfile.flush()
                self.close_connection = True
                return
            if STATE.scenario == "empty_response":
                self._send(200, {"response": "", "done": True})
            else:
                self._send(200, {"response": "Hello Ollama", "done": True})
            return

        if self.path == "/api/embed":
            if STATE.scenario == "unsupported_embedding":
                self._send(404, {"error": "embedding endpoint disabled"})
            else:
                self._send(200, {"embeddings": [[0.1, 0.2, 0.3]]})
            return

        if self.path == "/v1/chat/completions":
            if body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "close")
                self.end_headers()
                rows = [b'data: {"choices":[{"delta":{"content":"Hello "}}]}\n\n']
                if STATE.scenario == "malformed_stream":
                    rows.append(b"data: nope\n\n")
                elif STATE.scenario != "interrupted_stream":
                    rows.extend([
                        b'data: {"choices":[{"delta":{"content":"llama.cpp"}}]}\n\n',
                        b"data: [DONE]\n\n",
                    ])
                for row in rows:
                    self.wfile.write(row)
                    self.wfile.flush()
                self.close_connection = True
                return
            if STATE.scenario == "empty_response":
                content = ""
            else:
                content = "Hello llama.cpp"
            self._send(200, {"choices": [{"message": {"role": "assistant", "content": content}}]})
            return

        if self.path == "/v1/embeddings":
            if STATE.scenario == "unsupported_embedding":
                self._send(404, {"error": "embedding endpoint disabled"})
            else:
                self._send(200, {"data": [{"embedding": [0.4, 0.5, 0.6]}]})
            return

        self._send(404, {"error": "not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def _snapshot_source() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(part in {"__pycache__", ".git", ".venv", "venv"} for part in path.parts):
            continue
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _config(provider: str, endpoint: str, **overrides: Any):
    from local_model import GenerationSettings, LocalModelConfig

    generation = GenerationSettings(
        max_tokens=overrides.pop("max_tokens", 77),
        temperature=overrides.pop("temperature", 0.33),
        top_p=0.88,
        top_k=31,
        repeat_penalty=1.07,
        seed=42,
        stop=("STOP",),
    )
    return LocalModelConfig(
        provider=provider,
        endpoint=endpoint,
        model="fixture-ollama" if provider == "ollama" else "fixture-llama",
        embed_model="fixture-embed",
        context_size=4096,
        connect_timeout_seconds=overrides.pop("connect_timeout_seconds", 0.2),
        read_timeout_seconds=overrides.pop("read_timeout_seconds", 0.5),
        retry_limit=overrides.pop("retry_limit", 0),
        retry_delay_seconds=0.01,
        generation=generation,
    ).validated()


def _expect_error(code: str, callback: Callable[[], Any]) -> None:
    from local_model import LocalModelError

    try:
        callback()
    except LocalModelError as error:
        assert error.code == code, (error.code, error)
        return
    raise AssertionError(f"Expected LocalModelError code {code}")


def run_tests() -> dict[str, Any]:
    before = _snapshot_source()
    results: list[dict[str, Any]] = []
    temp_data = tempfile.TemporaryDirectory(prefix="eidolon-local-model-fixture-")
    os.environ["EIDOLON_DATA_DIR"] = temp_data.name

    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{port}"

    from local_model import LocalModelClient

    def case(name: str, callback: Callable[[], None]) -> None:
        STATE.scenario = "healthy"
        STATE.request_count = 0
        STATE.requests.clear()
        started = time.monotonic()
        try:
            callback()
        except Exception as error:
            results.append({"name": name, "status": "fail", "seconds": round(time.monotonic() - started, 4), "error": repr(error)})
        else:
            results.append({"name": name, "status": "pass", "seconds": round(time.monotonic() - started, 4)})

    def healthy_ollama() -> None:
        with LocalModelClient(_config("ollama", endpoint)) as client:
            assert client.generate("hello") == "Hello Ollama"
            assert "".join(client.stream("hello")) == "Hello Ollama"

    def healthy_llama() -> None:
        with LocalModelClient(_config("llama_cpp", endpoint)) as client:
            assert client.generate("hello") == "Hello llama.cpp"
            assert "".join(client.stream("hello")) == "Hello llama.cpp"

    def ollama_inventory() -> None:
        with LocalModelClient(_config("ollama", endpoint)) as client:
            assert client.version() == "fixture-ollama-1"
            assert "fixture-ollama" in client.list_models()
            assert client.embed("hello") == [0.1, 0.2, 0.3]
            health = client.health().to_dict()
            assert health["status"] == "healthy" and health["model_available"] is True

    def llama_inventory() -> None:
        with LocalModelClient(_config("llama_cpp", endpoint)) as client:
            assert client.version() == "fixture-llama-1"
            assert "fixture-llama" in client.list_models()
            assert client.embed("hello") == [0.4, 0.5, 0.6]

    def unavailable() -> None:
        closed_endpoint = f"http://127.0.0.1:{_free_port()}"
        with LocalModelClient(_config("ollama", closed_endpoint)) as client:
            _expect_error("unavailable_service", lambda: client.generate("hello"))

    def missing_model() -> None:
        STATE.scenario = "missing_model"
        with LocalModelClient(_config("ollama", endpoint)) as client:
            _expect_error("missing_model", lambda: client.generate("hello"))

    def timeout() -> None:
        STATE.scenario = "timeout"
        with LocalModelClient(_config("ollama", endpoint, read_timeout_seconds=0.03)) as client:
            _expect_error("timeout", lambda: client.generate("hello"))

    def malformed_json() -> None:
        STATE.scenario = "malformed_json"
        with LocalModelClient(_config("ollama", endpoint)) as client:
            _expect_error("malformed_response", lambda: client.generate("hello"))

    def empty_response() -> None:
        STATE.scenario = "empty_response"
        with LocalModelClient(_config("llama_cpp", endpoint)) as client:
            _expect_error("empty_response", lambda: client.generate("hello"))

    def http_error() -> None:
        STATE.scenario = "http_error"
        with LocalModelClient(_config("llama_cpp", endpoint)) as client:
            _expect_error("http_failure", lambda: client.generate("hello"))

    def interrupted_stream() -> None:
        STATE.scenario = "interrupted_stream"
        with LocalModelClient(_config("ollama", endpoint)) as client:
            _expect_error("interrupted_stream", lambda: list(client.stream("hello")))

    def malformed_stream() -> None:
        STATE.scenario = "malformed_stream"
        with LocalModelClient(_config("llama_cpp", endpoint)) as client:
            _expect_error("malformed_response", lambda: list(client.stream("hello")))

    def recovery() -> None:
        config = _config("ollama", endpoint)
        with LocalModelClient(config) as client:
            STATE.scenario = "http_error"
            _expect_error("http_failure", lambda: client.generate("hello"))
            STATE.scenario = "healthy"
            assert client.generate("hello") == "Hello Ollama"

    def bounded_retry() -> None:
        STATE.scenario = "retry_then_success"
        with LocalModelClient(_config("ollama", endpoint, retry_limit=1)) as client:
            assert client.generate("hello") == "Hello Ollama"
        assert STATE.request_count == 2

    def provider_switching_real_conversation_path() -> None:
        from settings_manager import DEFAULT_SETTINGS

        settings_path = Path(temp_data.name) / "settings.json"
        settings = dict(DEFAULT_SETTINGS)
        settings.update({
            "local_model_provider": "ollama",
            "local_model_endpoint": endpoint,
            "local_model": "fixture-ollama",
            "embed_model": "fixture-embed",
            "local_model_retry_limit": 0,
        })
        settings_path.write_text(json.dumps(settings), encoding="utf-8")
        import local_brain

        assert local_brain.local_generate("shared prompt") == "Hello Ollama"
        ollama_request = STATE.requests[-1]
        settings.update({"local_model_provider": "llama_cpp", "local_model": "fixture-llama"})
        settings_path.write_text(json.dumps(settings), encoding="utf-8")
        assert local_brain.local_generate("shared prompt") == "Hello llama.cpp"
        llama_request = STATE.requests[-1]
        assert ollama_request["path"] == "/api/generate"
        assert llama_request["path"] == "/v1/chat/completions"
        assert ollama_request["body"]["prompt"] == "shared prompt"
        assert ollama_request["body"]["keep_alive"] == "30m"
        assert llama_request["body"]["messages"][0]["content"] == "shared prompt"
        assert "keep_alive" not in llama_request["body"]
        assert ollama_request["body"]["options"]["top_k"] == settings["local_model_top_k"]
        assert llama_request["body"]["top_k"] == settings["local_model_top_k"]

    def cancellation_closed_and_invalid_config() -> None:
        from local_model import LocalModelConfig

        client = LocalModelClient(_config("ollama", endpoint))
        client.cancel()
        _expect_error("cancelled", lambda: client.generate("hello"))
        client.close()
        _expect_error("closed_client", lambda: client.generate("hello"))
        _expect_error(
            "invalid_configuration",
            lambda: LocalModelConfig(provider="mystery", endpoint=endpoint, model="x", embed_model="y").validated(),
        )

    for name, callback in [
        ("healthy_ollama_generation_and_stream", healthy_ollama),
        ("healthy_llama_cpp_generation_and_stream", healthy_llama),
        ("ollama_listing_version_embedding_health", ollama_inventory),
        ("llama_cpp_listing_version_embedding", llama_inventory),
        ("service_unavailable_connection_refused", unavailable),
        ("missing_model", missing_model),
        ("request_timeout", timeout),
        ("malformed_json", malformed_json),
        ("empty_response", empty_response),
        ("http_error", http_error),
        ("interrupted_stream", interrupted_stream),
        ("malformed_stream", malformed_stream),
        ("recovery_after_failure", recovery),
        ("bounded_transient_retry", bounded_retry),
        ("provider_switching_real_conversation_path", provider_switching_real_conversation_path),
        ("cancellation_closed_client_invalid_config", cancellation_closed_and_invalid_config),
    ]:
        case(name, callback)

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    temp_data.cleanup()

    after = _snapshot_source()
    source_unchanged = before == after
    if not source_unchanged:
        results.append({
            "name": "source_tree_immutability",
            "status": "fail",
            "error": "Source tree changed during fixture execution.",
            "added": sorted(set(after) - set(before)),
            "removed": sorted(set(before) - set(after)),
            "changed": sorted(path for path in set(before) & set(after) if before[path] != after[path]),
        })
    passed = sum(item["status"] == "pass" for item in results)
    return {
        "suite": "v1078.9 local-model deterministic fixtures",
        "evidence_type": "fixture_simulation",
        "native_model_evidence": False,
        "status": "pass" if passed == len(results) and source_unchanged else "fail",
        "passed": passed,
        "total": len(results),
        "source_tree_unchanged": source_unchanged,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic local-model provider fixtures.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_tests()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"{report['status'].upper()}: {report['passed']}/{report['total']} fixture checks")
        for item in report["results"]:
            print(f"- {item['status']}: {item['name']}{' - ' + item.get('error', '') if item.get('error') else ''}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
