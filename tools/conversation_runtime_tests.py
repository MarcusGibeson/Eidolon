from __future__ import annotations

"""Deterministic v1079.3 conversation runtime reliability fixtures.

All provider evidence in this suite is simulated. Runtime files are written only
to EIDOLON_DATA_DIR, which release verification places outside the source tree.
"""

import argparse
import hashlib
import json
import os
import shutil
import socket
import sys
import threading
import tempfile
import time
from copy import deepcopy
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

import requests

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _load_application_modules() -> None:
    """Import Eidolon only after the caller's runtime tree has been backed up."""
    global build_conversation_prompt
    global cancel_conversation_operation, run_conversation_turn, stream_conversation_turn
    global create_dashboard_chat_turn, render_realtime_chat_panel, stream_dashboard_chat_turn
    global ContextLimitError, LocalModelClient, LocalModelConfig
    global save_local_model_configuration, load_memories
    global DATA_DIR, DESIRES_FILE, MEMORY_FILE, SELF_FILE
    global DEFAULT_SETTINGS, load_settings, save_settings

    from conversation_context import build_conversation_prompt
    from conversation_runtime import cancel_conversation_operation, run_conversation_turn, stream_conversation_turn
    from dashboard_chat_console import create_dashboard_chat_turn, render_realtime_chat_panel, stream_dashboard_chat_turn
    from local_model import ContextLimitError, LocalModelClient, LocalModelConfig
    from local_model_configuration import save_local_model_configuration
    from memory import load_memories
    from paths import DATA_DIR, DESIRES_FILE, MEMORY_FILE, SELF_FILE
    from settings_manager import DEFAULT_SETTINGS, load_settings, save_settings

    try:
        import vector_memory

        vector_memory.add_memory_vector = lambda _memory: None
    except Exception:
        pass


@dataclass
class ProviderState:
    provider: str
    behavior: str = "success"
    generated_text: str = "SIMULATED_OK"
    requests: list[dict[str, Any]] = field(default_factory=list)
    request_count: int = 0
    first_request_failed: bool = False
    stream_started: threading.Event = field(default_factory=threading.Event)
    release_stream: threading.Event = field(default_factory=threading.Event)


class FixtureServer:
    def __init__(self, state: ProviderState) -> None:
        self.state = state
        fixture_state = state

        class QuietThreadingHTTPServer(ThreadingHTTPServer):
            def handle_error(self, request: Any, client_address: Any) -> None:
                error = sys.exc_info()[1]
                if isinstance(error, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
                    return
                super().handle_error(request, client_address)

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _json_body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    value = json.loads(raw.decode("utf-8"))
                except Exception:
                    return {}
                return value if isinstance(value, dict) else {}

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                try:
                    self.wfile.write(encoded)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

            def _send_raw(self, status: int, payload: bytes, content_type: str = "application/json") -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

            def do_POST(self) -> None:
                body = self._json_body()
                fixture_state.request_count += 1
                fixture_state.requests.append({
                    "path": self.path,
                    "stream": bool(body.get("stream")),
                    "model": body.get("model"),
                })
                if fixture_state.behavior == "retry_once" and not fixture_state.first_request_failed:
                    fixture_state.first_request_failed = True
                    self._send_json(503, {"error": "temporarily unavailable"})
                    return
                if fixture_state.behavior == "timeout":
                    time.sleep(0.35)
                if fixture_state.behavior == "context_limit":
                    self._send_json(400, {"error": "prompt exceeds maximum context length"})
                    return
                if fixture_state.behavior == "missing_model":
                    self._send_json(404, {"error": "model fixture-model not found RAW_MODEL_SECRET"})
                    return
                if fixture_state.behavior == "malformed_nonstream" and not bool(body.get("stream")):
                    self._send_raw(200, b"RAW_PROVIDER_SECRET:not-json")
                    return
                if bool(body.get("stream")):
                    self._stream_response()
                    return
                if fixture_state.provider == "ollama":
                    self._send_json(200, {
                        "model": "unexpected-loaded-model" if fixture_state.behavior == "model_mismatch" else body.get("model"),
                        "response": fixture_state.generated_text,
                        "done": True,
                    })
                else:
                    self._send_json(200, {
                        "model": "unexpected-loaded-model" if fixture_state.behavior == "model_mismatch" else body.get("model"),
                        "choices": [{"message": {"content": fixture_state.generated_text}}],
                    })

            def _stream_response(self) -> None:
                behavior = fixture_state.behavior
                if behavior == "unsupported_streaming":
                    self._send_json(405, {"error": "streaming unsupported"})
                    return
                self.send_response(200)
                content_type = "application/x-ndjson" if fixture_state.provider == "ollama" else "text/event-stream"
                self.send_header("Content-Type", content_type)
                self.send_header("Connection", "close")
                self.end_headers()
                fixture_state.stream_started.set()
                if behavior == "provider_error_secret":
                    payload = json.dumps({"error": "model unavailable RAW_STREAM_PROVIDER_SECRET"}).encode("utf-8") + b"\n"
                    self.wfile.write(payload)
                    self.wfile.flush()
                    return
                if behavior == "malformed_stream":
                    self.wfile.write(b"not-json\n")
                    self.wfile.flush()
                    return
                if fixture_state.provider == "ollama":
                    returned_model = "unexpected-loaded-model" if behavior == "model_mismatch" else "fixture-model"
                    first = json.dumps({"model": returned_model, "response": "SIMULATED_", "done": False}).encode("utf-8") + b"\n"
                    done = json.dumps({"model": returned_model, "response": "OK", "done": True}).encode("utf-8") + b"\n"
                else:
                    returned_model = "unexpected-loaded-model" if behavior == "model_mismatch" else "fixture-model"
                    first = (f'data: {{"model":"{returned_model}","choices":[{{"delta":{{"content":"SIMULATED_"}}}}]}}\n\n').encode("utf-8")
                    done = (f'data: {{"model":"{returned_model}","choices":[{{"delta":{{"content":"OK"}}}}]}}\n\ndata: [DONE]\n\n').encode("utf-8")
                self.wfile.write(first)
                self.wfile.flush()
                if behavior == "cancel_wait":
                    fixture_state.release_stream.wait(2.0)
                if behavior in {"interrupted_stream", "disconnect"}:
                    try:
                        self.connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    self.connection.close()
                    return
                self.wfile.write(done)
                self.wfile.flush()

            def log_message(self, _format: str, *_args: Any) -> None:
                return

        self.server = QuietThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def endpoint(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "FixtureServer":
        self.thread.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.state.release_stream.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


def _source_snapshot() -> dict[str, str]:
    rows: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if any(part in {"__pycache__", ".git", ".venv", "venv"} for part in path.parts):
            continue
        rows[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return rows


def _reset_runtime() -> None:
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SELF_FILE.write_text(json.dumps({"name": "Eidolon", "active_goals": ["Remain supervised"]}), encoding="utf-8")
    DESIRES_FILE.write_text(json.dumps({"helpfulness": 0.9, "safety": 1.0}), encoding="utf-8")
    MEMORY_FILE.write_text("[]", encoding="utf-8")


def _settings(provider: str, endpoint: str, **overrides: Any) -> dict[str, Any]:
    settings = deepcopy(DEFAULT_SETTINGS)
    settings.update({
        "settings_version": "1079.3",
        "last_updated_for": "v1079.3",
        "local_model_provider": provider,
        "local_model_endpoint": endpoint,
        "local_model_embedding_endpoint": "",
        "local_model": "fixture-model",
        "embed_model": "fixture-embed",
        "local_model_context_size": 2048,
        "local_model_max_tokens": 64,
        "local_model_connect_timeout_seconds": 0.2,
        "local_model_read_timeout_seconds": 0.2,
        "local_model_retry_limit": 1,
        "local_model_retry_delay_seconds": 0.01,
        "ai_chat_enabled": True,
    })
    settings.update(overrides)
    save_settings(settings)
    return settings


def _assistant_memories() -> list[dict[str, Any]]:
    return [row for row in load_memories() if row.get("type") == "conversation_eidolon"]


def _user_memories() -> list[dict[str, Any]]:
    return [row for row in load_memories() if row.get("type") == "conversation_user"]


def _latest_receipt() -> dict[str, Any]:
    receipts = sorted((DATA_DIR / "conversation_runtime" / "receipts").glob("*.json"))
    assert receipts, "conversation runtime receipt missing"
    return json.loads(receipts[-1].read_text(encoding="utf-8"))


def _assert_receipt_redacted(receipt: dict[str, Any], forbidden: tuple[str, ...] = ()) -> None:
    serialized = json.dumps(receipt, sort_keys=True)
    assert receipt["redacted"] is True
    assert receipt["contains_prompts"] is False
    assert receipt["contains_generated_responses"] is False
    assert receipt["contains_credentials"] is False
    assert receipt["contains_raw_events"] is False
    assert "LATEST USER MESSAGE" not in serialized
    assert "SIMULATED_OK" not in serialized
    for token in forbidden:
        assert token not in serialized


def _consume_runtime_stream(message: str = "hello") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events = list(stream_conversation_turn(message))
    done = next(item for item in events if item.get("event") == "done")
    return events, done["result"]


def _run_tests_destructive() -> dict[str, Any]:
    before = _source_snapshot()
    results: list[dict[str, Any]] = []

    def case(name: str, callback: Callable[[], None]) -> None:
        started = time.monotonic()
        try:
            _reset_runtime()
            callback()
            results.append({"name": name, "status": "pass", "seconds": round(time.monotonic() - started, 4)})
        except Exception as error:
            results.append({
                "name": name,
                "status": "fail",
                "seconds": round(time.monotonic() - started, 4),
                "error": f"{type(error).__name__}: {error}",
            })

    def provider_success(provider: str, streaming: bool) -> None:
        state = ProviderState(provider=provider)
        with FixtureServer(state) as server:
            _settings(provider, server.endpoint)
            if streaming:
                events, result = _consume_runtime_stream("provider success secret-user-text")
                assert any(item.get("event") == "delta" for item in events)
            else:
                result = run_conversation_turn("provider success secret-user-text").to_dict()
            assert result["success"] is True, result
            assert result["completion_state"] == "completed"
            assert result["provider"] == provider
            assert result["assistant_memory_stored"] is True
            assert len(_user_memories()) == 1
            assert len(_assistant_memories()) == 1
            receipt = _latest_receipt()
            assert receipt["provider"] == provider
            assert receipt["operation"] == ("streaming_generation" if streaming else "non_streaming_generation")
            _assert_receipt_redacted(receipt, ("secret-user-text",))

    def memory_vectorization_runs_after_provider() -> None:
        state = ProviderState(provider="ollama")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint)
            import conversation_runtime as runtime

            runtime._MEMORY_VECTOR_QUEUE.join()
            original_vector_store = runtime.store_memory_vector
            observations: list[tuple[str, int]] = []

            def record_vector_store(_memory: dict[str, Any]) -> None:
                observations.append((threading.current_thread().name, state.request_count))

            runtime.store_memory_vector = record_vector_store
            try:
                result = run_conversation_turn("vector scheduling prompt")
                runtime._MEMORY_VECTOR_QUEUE.join()
            finally:
                runtime.store_memory_vector = original_vector_store

            assert result.success is True, result
            assert len(observations) == 2, observations
            assert all(name == "eidolon-memory-vector-worker" for name, _count in observations), observations
            assert all(request_count == 1 for _name, request_count in observations), observations
            assert int(result.timings_ms.get("pre_provider") or 0) < int(result.timings_ms.get("total") or 0)

    def safe_retry_no_duplicates() -> None:
        state = ProviderState(provider="ollama", behavior="retry_once")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_retry_limit=1)
            result = run_conversation_turn("retry exactly once")
            assert result.success is True, result
            assert result.retry_count == 1
            assert state.request_count == 2
            assert len(_user_memories()) == 1
            assert len(_assistant_memories()) == 1
            assert _assistant_memories()[0]["content"].count("SIMULATED_OK") == 1
            receipt = _latest_receipt()
            assert receipt["retry_count"] == 1

    def streaming_never_retries() -> None:
        state = ProviderState(provider="ollama", behavior="retry_once")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_retry_limit=3)
            events, result = _consume_runtime_stream("do not replay stream")
            assert result["success"] is False
            assert result["retry_count"] == 0
            assert state.request_count == 1
            assert len(_assistant_memories()) == 0
            assert any(item.get("event") == "replace" for item in events)

    def stream_failure(behavior: str, expected: str) -> None:
        state = ProviderState(provider="ollama", behavior=behavior)
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_retry_limit=3)
            events, result = _consume_runtime_stream("stream failure raw-secret")
            assert result["success"] is False, result
            assert result["failure_category"] == expected, result
            assert result["assistant_memory_stored"] is False
            assert len(_assistant_memories()) == 0
            error_event = next(item for item in events if item.get("event") == "error")
            serialized = json.dumps(error_event)
            assert "raw-secret" not in serialized
            assert "not-json" not in serialized
            assert any(item.get("event") == "replace" for item in events)
            receipt = _latest_receipt()
            assert receipt["failure_category"] == expected
            _assert_receipt_redacted(receipt, ("raw-secret", "not-json"))

    def timeout_nonstream() -> None:
        state = ProviderState(provider="ollama", behavior="timeout")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_read_timeout_seconds=0.05, local_model_retry_limit=0)
            result = run_conversation_turn("timeout prompt secret")
            assert result.success is False
            assert result.failure_category == "timeout"
            assert len(_assistant_memories()) == 0
            assert "No fallback provider was used" in result.display_message
            receipt = _latest_receipt()
            _assert_receipt_redacted(receipt, ("timeout prompt secret",))

    def missing_model_is_visible_and_redacted(streaming: bool) -> None:
        state = ProviderState(provider="ollama", behavior="missing_model")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_retry_limit=0)
            if streaming:
                events, result = _consume_runtime_stream("missing model prompt secret")
                assert any(item.get("event") == "replace" for item in events)
            else:
                result = run_conversation_turn("missing model prompt secret").to_dict()
            assert result["success"] is False, result
            assert result["failure_category"] == "missing_model", result
            assert result["fallback_used"] is False
            assert len(_assistant_memories()) == 0
            serialized = json.dumps(result)
            assert "RAW_MODEL_SECRET" not in serialized
            receipt = _latest_receipt()
            assert receipt["failure_category"] == "missing_model"
            _assert_receipt_redacted(receipt, ("missing model prompt secret", "RAW_MODEL_SECRET"))

    def malformed_nonstream_is_redacted() -> None:
        state = ProviderState(provider="llama_cpp", behavior="malformed_nonstream")
        with FixtureServer(state) as server:
            _settings("llama_cpp", server.endpoint, local_model_retry_limit=0)
            result = run_conversation_turn("nonstream malformed prompt secret")
            assert result.success is False, result
            assert result.failure_category == "malformed_response"
            assert len(_assistant_memories()) == 0
            assert "RAW_PROVIDER_SECRET" not in json.dumps(result.to_dict())
            receipt = _latest_receipt()
            _assert_receipt_redacted(receipt, ("nonstream malformed prompt secret", "RAW_PROVIDER_SECRET"))

    def invalid_configuration_is_structured() -> None:
        settings = deepcopy(DEFAULT_SETTINGS)
        settings.update({
            "local_model_provider": "ollama",
            "local_model_endpoint": "not-an-http-endpoint",
            "local_model": "fixture-model",
            "embed_model": "fixture-embed",
        })
        save_settings(settings)
        result = run_conversation_turn("configuration prompt secret")
        assert result.success is False
        assert result.failure_category == "invalid_configuration", result
        assert result.user_memory_stored is False
        assert len(_assistant_memories()) == 0
        stream_events, stream_result = _consume_runtime_stream("configuration stream secret")
        assert stream_result["failure_category"] == "invalid_configuration"
        assert any(item.get("event") == "error" for item in stream_events)
        receipt = _latest_receipt()
        _assert_receipt_redacted(receipt, ("configuration prompt secret", "configuration stream secret"))

    def assistant_memory_failure_marks_turn_incomplete() -> None:
        state = ProviderState(provider="ollama")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_retry_limit=0)
            import conversation_runtime as runtime

            original_store = runtime.store_memory

            def fail_assistant(memory: dict[str, Any], **kwargs: Any) -> None:
                if memory.get("type") == "conversation_eidolon":
                    raise OSError("RAW_MEMORY_FAILURE_SECRET")
                original_store(memory, **kwargs)

            runtime.store_memory = fail_assistant
            try:
                result = run_conversation_turn("memory failure prompt secret")
            finally:
                runtime.store_memory = original_store
            assert result.success is False
            assert result.completion_state == "response_generated_memory_failed"
            assert result.failure_category == "memory_write_failure"
            assert result.assistant_memory_stored is False
            assert len(_user_memories()) == 1
            assert len(_assistant_memories()) == 0
            assert "RAW_MEMORY_FAILURE_SECRET" not in json.dumps(result.to_dict())
            receipt = _latest_receipt()
            assert receipt["memory_commit"]["assistant_response"] is False
            _assert_receipt_redacted(receipt, ("memory failure prompt secret", "RAW_MEMORY_FAILURE_SECRET"))

    def explicit_cancellation() -> None:
        state = ProviderState(provider="ollama", behavior="cancel_wait")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_read_timeout_seconds=2.0)
            events: list[dict[str, Any]] = []

            def consume() -> None:
                events.extend(stream_conversation_turn("cancel this safely"))

            thread = threading.Thread(target=consume)
            thread.start()
            deadline = time.monotonic() + 2
            operation_id = ""
            while time.monotonic() < deadline:
                for item in events:
                    if item.get("event") == "meta":
                        operation_id = str(item.get("operation_id") or "")
                if operation_id:
                    break
                time.sleep(0.01)
            assert operation_id
            cancellation = cancel_conversation_operation(operation_id)
            assert cancellation["ok"] is True
            state.release_stream.set()
            thread.join(timeout=3)
            assert not thread.is_alive()
            done = next(item for item in events if item.get("event") == "done")
            assert done["result"]["completion_state"] == "cancelled", done
            assert len(_assistant_memories()) == 0

    def provider_controlled_error_is_redacted() -> None:
        state = ProviderState(provider="ollama", behavior="provider_error_secret")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint, local_model_retry_limit=0)
            events, result = _consume_runtime_stream("redaction boundary prompt")
            serialized = json.dumps(events, sort_keys=True)
            assert result["success"] is False
            assert "RAW_STREAM_PROVIDER_SECRET" not in serialized
            assert "redaction boundary prompt" not in serialized
            _assert_receipt_redacted(
                _latest_receipt(),
                ("RAW_STREAM_PROVIDER_SECRET", "redaction boundary prompt"),
            )

    def returned_model_mismatch_is_blocked(provider: str, streaming: bool) -> None:
        state = ProviderState(provider=provider, behavior="model_mismatch")
        with FixtureServer(state) as server:
            _settings(provider, server.endpoint, local_model_retry_limit=0)
            if streaming:
                events, result = _consume_runtime_stream("model mismatch stream secret")
                assert not any(item.get("event") == "delta" for item in events), events
            else:
                result = run_conversation_turn("model mismatch nonstream secret").to_dict()
            assert result["success"] is False
            assert result["failure_category"] == "missing_model"
            assert result["assistant_memory_stored"] is False
            assert len(_assistant_memories()) == 0
            _assert_receipt_redacted(
                _latest_receipt(),
                ("unexpected-loaded-model", "model mismatch"),
            )

    def completed_responses_are_closed() -> None:
        class FakeResponse:
            status_code = 200
            text = ""

            def __init__(self) -> None:
                self.closed = False

            def json(self) -> dict[str, Any]:
                return {"response": "closed cleanly", "done": True}

            def close(self) -> None:
                self.closed = True

        class FakeSession:
            def __init__(self, response: FakeResponse) -> None:
                self.response = response
                self.closed = False

            def request(self, *_args: Any, **_kwargs: Any) -> FakeResponse:
                return self.response

            def close(self) -> None:
                self.closed = True

        response = FakeResponse()
        session = FakeSession(response)
        config = LocalModelConfig(
            provider="ollama",
            endpoint="http://127.0.0.1:11434",
            model="fixture-model",
            embed_model="fixture-embed",
            retry_limit=0,
        )
        client = LocalModelClient(config, session=session)
        assert client.generate("close this response") == "closed cleanly"
        assert response.closed is True
        client.close()

    def cancellation_wins_before_memory_commit() -> None:
        import conversation_runtime as runtime

        _settings("ollama", "http://127.0.0.1:11434", local_model_retry_limit=0)
        active_cancel = threading.Event()
        original_client = runtime.LocalModelClient

        class CommitRaceClient:
            last_retry_count = 0

            def __init__(self, _config: Any, *, cancel_event: threading.Event) -> None:
                self.cancel_event = cancel_event

            def generate(self, _prompt: str) -> str:
                self.cancel_event.set()
                return "MUST_NOT_BE_COMMITTED"

            def cancel(self) -> None:
                self.cancel_event.set()

            def close(self) -> None:
                return

        runtime.LocalModelClient = CommitRaceClient
        try:
            result = runtime.run_conversation_turn("cancel at commit", cancel_event=active_cancel)
        finally:
            runtime.LocalModelClient = original_client
        assert result.completion_state == "cancelled", result
        assert result.assistant_memory_stored is False
        assert len(_assistant_memories()) == 0
        assert "MUST_NOT_BE_COMMITTED" not in json.dumps(_latest_receipt())

    def closed_consumer_has_truthful_receipt() -> None:
        state = ProviderState(provider="ollama")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint)
            stream = stream_conversation_turn("consumer disconnect")
            operation_id = ""
            for item in stream:
                operation_id = operation_id or str(item.get("operation_id") or "")
                if item.get("event") == "delta":
                    break
            assert operation_id
            stream.close()
            receipt = _latest_receipt()
            assert receipt["completion_state"] == "consumer_disconnected", receipt
            assert receipt["failure_category"] == "consumer_disconnected"
            assert len(_assistant_memories()) == 0
            assert cancel_conversation_operation(operation_id)["status"] == "not_active"

    def disabled_stream_still_completes_protocol() -> None:
        _settings("ollama", "http://127.0.0.1:11434", ai_chat_enabled=False)
        events, result = _consume_runtime_stream("no provider call")
        assert result["completion_state"] == "ai_disabled", events
        assert any(item.get("event") == "done" for item in events)
        assert len(_assistant_memories()) == 0

    def context_reduction() -> None:
        memories = [
            {"type": "core_memory", "importance": "critical", "content": "KEEP_IMPORTANT_MEMORY_WHOLE"},
            *[
                {"type": "memory", "content": f"regular memory {index} " + ("x" * 180)}
                for index in range(20)
            ],
        ]
        packet = build_conversation_prompt(
            user_message="latest message must survive",
            self_model={"name": "Eidolon", "active_goals": ["supervised"]},
            desires={"safety": 1.0},
            memories=memories,
            project_context="project context " + ("p" * 600),
            goal_context="goal context " + ("g" * 600),
            task_context="task context " + ("t" * 600),
            context_size=900,
            max_tokens=100,
        )
        assert "SYSTEM CONTRACT" in packet.prompt
        assert "latest message must survive" in packet.prompt
        assert "KEEP_IMPORTANT_MEMORY_WHOLE" in packet.prompt
        assert packet.metrics.memories_omitted > 0
        assert packet.metrics.estimated_prompt_tokens <= packet.metrics.input_budget_tokens
        try:
            build_conversation_prompt(
                user_message="z" * 5000,
                self_model={"name": "Eidolon"},
                desires={},
                memories=[],
                project_context="",
                goal_context="",
                task_context="",
                context_size=256,
                max_tokens=64,
            )
        except ContextLimitError as error:
            assert error.code == "context_limit"
        else:
            raise AssertionError("oversized protected context was not rejected")

    def provider_context_limit() -> None:
        state = ProviderState(provider="llama_cpp", behavior="context_limit")
        with FixtureServer(state) as server:
            _settings("llama_cpp", server.endpoint, local_model_retry_limit=0)
            result = run_conversation_turn("provider should reject context")
            assert result.failure_category == "context_limit", result
            assert len(_assistant_memories()) == 0

    def dashboard_paths() -> None:
        state = ProviderState(provider="ollama")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint)
            import dashboard_chat_console as console

            original_side_effects = console._save_post_response_side_effects
            console._save_post_response_side_effects = lambda *_args, **_kwargs: ""
            try:
                events = list(stream_dashboard_chat_turn("dashboard streaming path"))
                done = next(item for item in events if item.get("event") == "done")
                assert done["turn"]["completion_state"] == "completed"
                assert done["turn"]["conversation_runtime"]["assistant_memory_stored"] is True
                nonstream = create_dashboard_chat_turn("dashboard nonstream path")
                assert nonstream["completion_state"] == "completed"
                assert nonstream["conversation_runtime"]["assistant_memory_stored"] is True
            finally:
                console._save_post_response_side_effects = original_side_effects

    def dashboard_error_redaction() -> None:
        state = ProviderState(provider="ollama", behavior="malformed_stream")
        with FixtureServer(state) as server:
            _settings("ollama", server.endpoint)
            import dashboard_chat_console as console

            original_side_effects = console._save_post_response_side_effects
            console._save_post_response_side_effects = lambda *_args, **_kwargs: ""
            try:
                events = list(stream_dashboard_chat_turn("dashboard-secret"))
            finally:
                console._save_post_response_side_effects = original_side_effects
            done = next(item for item in events if item.get("event") == "done")
            assert done["turn"]["completion_state"] == "failed"
            serialized = json.dumps(events)
            assert "not-json" not in serialized
            assert "dashboard-secret" not in json.dumps(done["turn"]["conversation_runtime"])
            assert len(_assistant_memories()) == 0

    def dashboard_sse_reaches_eof_and_closes() -> None:
        rendered = render_realtime_chat_panel(None)
        assert "if (activeController) activeController.abort();" not in rendered
        assert "const turnController = new AbortController();" in rendered
        assert "signal: turnController.signal" in rendered
        assert "if (activeController === turnController) activeController = null;" in rendered
        state = ProviderState(provider="ollama")
        with FixtureServer(state) as provider_server:
            _settings("ollama", provider_server.endpoint)
            from api_server import EidolonApiHandler

            dashboard_server = ThreadingHTTPServer(("127.0.0.1", 0), EidolonApiHandler)
            dashboard_thread = threading.Thread(target=dashboard_server.serve_forever, daemon=True)
            dashboard_thread.start()
            try:
                host, port = dashboard_server.server_address
                response = requests.post(
                    f"http://{host}:{port}/api/dashboard-chat/stream",
                    json={"message": "dashboard eof contract", "use_ai": True},
                    timeout=(1.0, 15.0),
                )
                assert response.status_code == 200
                assert response.headers.get("Connection", "").lower() == "close"
                assert "event: done" in response.text
                assert response.raw.closed is True
            finally:
                dashboard_server.shutdown()
                dashboard_server.server_close()
                dashboard_thread.join(timeout=3)

    def provider_profile_isolation_and_state() -> None:
        initial = deepcopy(DEFAULT_SETTINGS)
        initial.update({
            "local_model_provider": "ollama",
            "local_model_endpoint": "http://127.0.0.1:11434",
            "local_model": "ollama-model",
            "embed_model": "ollama-embed",
        })
        save_settings(initial)
        MEMORY_FILE.write_text(json.dumps([{"type": "conversation_user", "content": "state survives switches"}]), encoding="utf-8")
        save_local_model_configuration({
            "local_model_provider": "llama_cpp",
            "local_model_endpoint": "http://127.0.0.1:8080",
            "local_model_embedding_endpoint": "http://127.0.0.1:8081",
            "local_model": "llama-model",
            "embed_model": "llama-embed",
            "local_model_context_size": 4096,
            "local_model_connect_timeout_seconds": 5.0,
            "local_model_read_timeout_seconds": 90.0,
            "local_model_max_tokens": 200,
            "local_model_temperature": 0.4,
            "local_model_top_p": 0.8,
            "local_model_top_k": 30,
            "local_model_repeat_penalty": 1.05,
        })
        llama_settings = load_settings()
        assert llama_settings["local_model_provider"] == "llama_cpp"
        assert llama_settings["local_model_endpoint"].endswith(":8080")
        save_local_model_configuration({
            "local_model_provider": "ollama",
            **{key: llama_settings.get(key) for key in (
                "local_model_endpoint", "local_model_embedding_endpoint", "local_model", "embed_model",
                "local_model_context_size", "local_model_connect_timeout_seconds", "local_model_read_timeout_seconds",
                "local_model_max_tokens", "local_model_temperature", "local_model_top_p", "local_model_top_k",
                "local_model_repeat_penalty",
            )},
        })
        restored = load_settings()
        assert restored["local_model_provider"] == "ollama"
        assert restored["local_model_endpoint"] == "http://127.0.0.1:11434"
        assert restored["local_model"] == "ollama-model"
        assert restored["local_model_provider_profiles"]["llama_cpp"]["local_model"] == "llama-model"
        assert load_memories()[0]["content"] == "state survives switches"

    def partial_provider_switch_preserves_target_profile() -> None:
        initial = deepcopy(DEFAULT_SETTINGS)
        initial.update({
            "local_model_provider": "ollama",
            "local_model_endpoint": "http://127.0.0.1:11434",
            "local_model": "ollama-current",
            "embed_model": "ollama-embed-current",
        })
        profiles = deepcopy(initial["local_model_provider_profiles"])
        profiles["ollama"].update({
            "local_model_endpoint": "http://127.0.0.1:11434",
            "local_model": "ollama-current",
            "embed_model": "ollama-embed-current",
        })
        profiles["llama_cpp"].update({
            "local_model_endpoint": "http://127.0.0.1:8080",
            "local_model_embedding_endpoint": "http://127.0.0.1:8081",
            "local_model": "llama-saved",
            "embed_model": "llama-embed-saved",
            "local_model_context_size": 4096,
        })
        initial["local_model_provider_profiles"] = profiles
        save_settings(initial)
        save_local_model_configuration({
            "local_model_provider": "llama_cpp",
            "local_model_endpoint": "http://127.0.0.1:18080",
        })
        switched = load_settings()
        assert switched["local_model_provider"] == "llama_cpp"
        assert switched["local_model_endpoint"] == "http://127.0.0.1:18080"
        assert switched["local_model_embedding_endpoint"] == "http://127.0.0.1:8081"
        assert switched["local_model"] == "llama-saved"
        assert switched["embed_model"] == "llama-embed-saved"
        assert switched["local_model_context_size"] == 4096

    for provider in ("ollama", "llama_cpp"):
        case(f"{provider}_non_streaming_end_to_end", lambda provider=provider: provider_success(provider, False))
        case(f"{provider}_streaming_end_to_end", lambda provider=provider: provider_success(provider, True))
    case("memory_vectorization_runs_after_provider", memory_vectorization_runs_after_provider)
    case("bounded_non_stream_retry_has_single_memory_and_reply", safe_retry_no_duplicates)
    case("streaming_requests_are_never_replayed", streaming_never_retries)
    case("malformed_stream_is_redacted_and_not_committed", lambda: stream_failure("malformed_stream", "malformed_response"))
    case("interrupted_stream_is_not_committed", lambda: stream_failure("interrupted_stream", "interrupted_stream"))
    case("provider_disconnect_is_not_committed", lambda: stream_failure("disconnect", "interrupted_stream"))
    case("unsupported_streaming_is_visible_and_not_retried", lambda: stream_failure("unsupported_streaming", "unsupported_streaming"))
    case("non_stream_timeout_is_visible_and_has_no_fallback", timeout_nonstream)
    case("missing_model_non_stream_is_visible_and_redacted", lambda: missing_model_is_visible_and_redacted(False))
    case("missing_model_stream_is_visible_and_redacted", lambda: missing_model_is_visible_and_redacted(True))
    case("malformed_non_stream_is_redacted_and_not_committed", malformed_nonstream_is_redacted)
    case("invalid_configuration_is_structured_for_stream_and_nonstream", invalid_configuration_is_structured)
    case("assistant_memory_failure_marks_turn_incomplete", assistant_memory_failure_marks_turn_incomplete)
    case("explicit_stream_cancellation_is_clean", explicit_cancellation)
    case("provider_controlled_stream_errors_are_redacted", provider_controlled_error_is_redacted)
    for provider in ("ollama", "llama_cpp"):
        case(f"{provider}_nonstream_returned_model_mismatch_is_blocked", lambda provider=provider: returned_model_mismatch_is_blocked(provider, False))
        case(f"{provider}_stream_returned_model_mismatch_is_blocked", lambda provider=provider: returned_model_mismatch_is_blocked(provider, True))
    case("completed_nonstream_responses_are_closed", completed_responses_are_closed)
    case("cancellation_wins_before_assistant_memory_commit", cancellation_wins_before_memory_commit)
    case("closed_stream_consumer_has_truthful_receipt", closed_consumer_has_truthful_receipt)
    case("ai_disabled_stream_still_emits_done", disabled_stream_still_completes_protocol)
    case("context_budget_reduces_history_predictably", context_reduction)
    case("provider_context_limit_is_classified", provider_context_limit)
    case("dashboard_stream_and_nonstream_complete_path", dashboard_paths)
    case("dashboard_failure_payload_is_redacted", dashboard_error_redaction)
    case("dashboard_sse_reaches_eof_and_closes", dashboard_sse_reaches_eof_and_closes)
    case("provider_profiles_and_conversation_state_are_isolated", provider_profile_isolation_and_state)
    case("partial_provider_switch_preserves_target_profile", partial_provider_switch_preserves_target_profile)

    after = _source_snapshot()
    unchanged = before == after
    if not unchanged:
        results.append({"name": "source_tree_immutability", "status": "fail", "error": "Source tree changed during v1079.3 fixtures."})
    passed = sum(item["status"] == "pass" for item in results)
    ok = unchanged and passed == len(results)
    return {
        "suite": "v1079.3 conversational runtime reliability and recovery fixtures",
        "evidence_type": "fixture_simulation",
        "native_provider_evidence": False,
        "ok": ok,
        "status": "pass" if ok else "fail",
        "passed": passed,
        "total": len(results),
        "source_tree_unchanged": unchanged,
        "results": results,
    }


def _runtime_tree_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "files": {}, "directories": []}
    files: dict[str, str] = {}
    directories: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(relative)
        elif path.is_file():
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"exists": True, "files": files, "directories": directories}


def run_tests() -> dict[str, Any]:
    """Run destructive fixtures while restoring the caller's external runtime exactly."""
    runtime_before = _runtime_tree_snapshot(EXTERNAL_DATA_DIR)
    original_exists = EXTERNAL_DATA_DIR.exists()
    backup_root = Path(tempfile.mkdtemp(prefix="eidolon-conversation-runtime-fixture-backup-"))
    backup_data = backup_root / "data"
    if original_exists:
        shutil.copytree(EXTERNAL_DATA_DIR, backup_data)

    report: dict[str, Any]
    restore_error: str | None = None
    try:
        _load_application_modules()
        report = _run_tests_destructive()
    except Exception as error:
        report = {
            "suite": "v1079.3 conversational runtime reliability and recovery fixtures",
            "evidence_type": "fixture_simulation",
            "native_provider_evidence": False,
            "ok": False,
            "status": "fail",
            "passed": 0,
            "total": 0,
            "source_tree_unchanged": False,
            "results": [{
                "name": "fixture_suite_execution",
                "status": "fail",
                "error": f"{type(error).__name__}: {error}",
            }],
        }
    finally:
        try:
            shutil.rmtree(EXTERNAL_DATA_DIR, ignore_errors=True)
            if original_exists:
                shutil.copytree(backup_data, EXTERNAL_DATA_DIR)
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"
        finally:
            shutil.rmtree(backup_root, ignore_errors=True)

    runtime_after = _runtime_tree_snapshot(EXTERNAL_DATA_DIR)
    runtime_restored = restore_error is None and runtime_before == runtime_after
    results = list(report.get("results") or [])
    results.append({
        "name": "external_runtime_seed_restored_after_fixture_suite",
        "status": "pass" if runtime_restored else "fail",
        **({} if runtime_restored else {"error": restore_error or "external runtime data changed"}),
    })
    passed = sum(item.get("status") == "pass" for item in results)
    report.update({
        "results": results,
        "passed": passed,
        "total": len(results),
        "runtime_data_restored": runtime_restored,
        "runtime_data_restore_error": restore_error,
    })
    report["ok"] = bool(report.get("source_tree_unchanged")) and passed == len(results)
    report["status"] = "pass" if report["ok"] else "fail"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic v1079.3 conversation runtime fixtures.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_tests()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"{report['status'].upper()}: {report['passed']}/{report['total']} v1079.3 checks")
        for item in report["results"]:
            print(f"- {item['status']}: {item['name']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
