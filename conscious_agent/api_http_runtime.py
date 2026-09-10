from __future__ import annotations

"""HTTP transport runtime extracted from ``api_server.py`` in v1250.8.

This module owns HTTP serialization and transport only. Route interpretation and
all mutation authority remain in the manually reviewed ``api_server`` dispatch.
"""

import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

CONTRACT_VERSION = "v1250.8"

@dataclass(frozen=True)
class ApiRuntimeDependencies:
    to_jsonable: Callable[[Any], Any]
    ok: Callable[..., dict[str, Any]]
    error: Callable[..., dict[str, Any]]
    dispatch_api: Callable[..., tuple[int, dict[str, Any]]]
    parse_request_body: Callable[[bytes, str], dict[str, Any]]
    api_error_type: type[Exception]
    cancel_conversation_operation: Callable[[str], dict[str, Any]]
    stream_dashboard_chat_turn: Callable[..., Any]


def build_api_handler_class(dependencies: ApiRuntimeDependencies) -> type[BaseHTTPRequestHandler]:
    class EidolonApiHandler(BaseHTTPRequestHandler):
        server_version = "EidolonAPI/10.0"

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            encoded = json.dumps(dependencies.to_jsonable(payload), indent=2, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(encoded)

        def _send_sse_event(self, event: str, payload: dict[str, Any]) -> None:
            encoded = f"event: {event}\ndata: {json.dumps(dependencies.to_jsonable(payload), default=str)}\n\n".encode("utf-8")
            self.wfile.write(encoded)
            self.wfile.flush()

        def do_OPTIONS(self) -> None:
            self._send_json(dependencies.ok({"methods": ["GET", "POST", "OPTIONS"]}))

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in {"/api"} and not parsed.path.startswith("/api/"):
                self._send_json(dependencies.error(404, "This server exposes only /api routes."), status=404)
                return
            status, payload = dependencies.dispatch_api("GET", parsed.path, query=parse_qs(parsed.query))
            self._send_json(payload, status=status)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in {"/api"} and not parsed.path.startswith("/api/"):
                self._send_json(dependencies.error(404, "This server exposes only /api routes."), status=404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) if length else b""
            try:
                body = dependencies.parse_request_body(raw_body, self.headers.get("Content-Type", ""))
            except dependencies.api_error_type as error:
                self._send_json(dependencies.error(error.status, error.message, error.details), status=error.status)
                return
            if parsed.path == "/api/dashboard-chat/cancel":
                result = dependencies.cancel_conversation_operation(str(body.get("operation_id") or ""))
                self._send_json(result, status=200 if result.get("ok") else 404)
                return
            if parsed.path == "/api/dashboard-chat/stream":
                message = str(body.get("message") or "").strip()
                use_ai_raw = body.get("use_ai", True)
                use_ai = bool(use_ai_raw) if not isinstance(use_ai_raw, str) else use_ai_raw.lower() in {"1", "true", "yes", "on"}
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.send_header("Connection", "close")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                cancel_event = threading.Event()
                stream = dependencies.stream_dashboard_chat_turn(message, use_ai=use_ai, cancel_event=cancel_event)
                try:
                    for item in stream:
                        event_name = str(item.get("event") or "message")
                        self._send_sse_event(event_name, item)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    cancel_event.set()
                    stream.close()
                except Exception as error:
                    cancel_event.set()
                    try:
                        self._send_sse_event(
                            "error",
                            {
                                "event": "error",
                                "failure_category": "sse_transport_failure",
                                "message": "The dashboard stream transport failed safely.",
                                "error_type": type(error).__name__,
                            },
                        )
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        pass
                finally:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    self.close_connection = True
                return
            status, payload = dependencies.dispatch_api("POST", parsed.path, query=parse_qs(parsed.query), body=body)
            self._send_json(payload, status=status)

        def log_message(self, format: str, *args: Any) -> None:
            return
    return EidolonApiHandler


def serve_api(*, host: str | None, port: int | None, handler_class: type[BaseHTTPRequestHandler], load_settings: Callable[[], dict[str, Any]]) -> None:
    settings = load_settings()
    host = str(settings.get("api_host", "127.0.0.1")) if host is None else host
    port = int(settings.get("api_port", 8766)) if port is None else int(port)
    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"Eidolon local API running at http://{host}:{port}/api")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAPI server stopped.")
    finally:
        server.server_close()


__all__ = [
    "CONTRACT_VERSION",
    "ApiRuntimeDependencies",
    "build_api_handler_class",
    "serve_api",
]
