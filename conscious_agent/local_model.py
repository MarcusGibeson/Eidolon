from __future__ import annotations

"""Provider-neutral local model transport for Eidolon.

The module contains no model installation or mutation behavior. It only talks to
operator-configured local HTTP services and returns structured, bounded results.
"""

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator, Protocol, runtime_checkable
from urllib.parse import urlparse

import requests


ERROR_UNAVAILABLE = "unavailable_service"
ERROR_MISSING_MODEL = "missing_model"
ERROR_TIMEOUT = "timeout"
ERROR_MALFORMED = "malformed_response"
ERROR_EMPTY = "empty_response"
ERROR_HTTP = "http_failure"
ERROR_INTERRUPTED_STREAM = "interrupted_stream"
ERROR_INVALID_CONFIG = "invalid_configuration"
ERROR_CANCELLED = "cancelled"
ERROR_CLOSED = "closed_client"
ERROR_CONTEXT_LIMIT = "context_limit"
ERROR_UNSUPPORTED_STREAMING = "unsupported_streaming"

_THREAD_HTTP_SESSIONS = threading.local()


def _shared_http_session(config: "LocalModelConfig") -> requests.Session:
    """Reuse localhost HTTP connections per thread without sharing active responses."""
    sessions = getattr(_THREAD_HTTP_SESSIONS, "sessions", None)
    if sessions is None:
        sessions = {}
        _THREAD_HTTP_SESSIONS.sessions = sessions
    key = (config.provider, config.endpoint, config.resolved_embedding_endpoint)
    session = sessions.get(key)
    if session is None:
        session = requests.Session()
        sessions[key] = session
    return session


def _ollama_metrics(data: dict[str, Any]) -> dict[str, int]:
    mapping = {
        "total_duration": "total_duration_ns",
        "load_duration": "load_duration_ns",
        "prompt_eval_count": "prompt_eval_count",
        "prompt_eval_duration": "prompt_eval_duration_ns",
        "eval_count": "eval_count",
        "eval_duration": "eval_duration_ns",
    }
    result: dict[str, int] = {}
    for source, target in mapping.items():
        value = data.get(source)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[target] = int(value)
    return result


SAFE_ERROR_MESSAGES = {
    ERROR_UNAVAILABLE: "The configured local model service is unavailable.",
    ERROR_MISSING_MODEL: "The configured model is unavailable from the selected provider.",
    ERROR_TIMEOUT: "The configured local model request timed out.",
    ERROR_MALFORMED: "The local model service returned an invalid response.",
    ERROR_EMPTY: "The local model service returned no usable content.",
    ERROR_HTTP: "The local model HTTP request failed.",
    ERROR_INTERRUPTED_STREAM: "The local model stream ended before completion.",
    ERROR_INVALID_CONFIG: "The local model configuration is invalid.",
    ERROR_CANCELLED: "The local model request was cancelled.",
    ERROR_CLOSED: "The local model client closed before completion.",
    ERROR_CONTEXT_LIMIT: "The configured context window could not accept the request.",
    ERROR_UNSUPPORTED_STREAMING: "The configured endpoint does not support streaming.",
}


class LocalModelError(RuntimeError):
    """Structured local-model error safe for CLI, API, dashboard, and logs."""

    code = "local_model_error"

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        endpoint: str = "",
        model: str = "",
        retryable: bool = False,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.endpoint = endpoint
        self.model = model
        self.retryable = retryable
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "provider": self.provider,
            "endpoint": self.endpoint,
            "model": self.model,
            "retryable": self.retryable,
            "status_code": self.status_code,
            "details": self.details,
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a bounded representation without response bodies or raw events."""
        safe_detail_keys = {
            "failure_kind",
            "exception_type",
            "yielded_content",
            "stream_supported",
        }
        details = {
            key: value
            for key, value in self.details.items()
            if key in safe_detail_keys and isinstance(value, (str, int, float, bool, type(None)))
        }
        # Provider-controlled error strings can contain prompts, response bodies,
        # paths, or secrets. Public errors use static text and structured fields.
        message = SAFE_ERROR_MESSAGES.get(self.code, "The local model operation failed safely.")
        endpoint = self.endpoint
        try:
            parsed = urlparse(endpoint)
            host = parsed.hostname or ""
            host_text = f"[{host}]" if ":" in host and not host.startswith("[") else host
            netloc = f"{host_text}:{parsed.port}" if parsed.port is not None else host_text
            safe_endpoint = f"{parsed.scheme.lower()}://{netloc}{parsed.path.rstrip('/')}" if parsed.scheme and host else ""
        except (TypeError, ValueError):
            safe_endpoint = ""
        if endpoint and endpoint in message:
            message = message.replace(endpoint, safe_endpoint or "[redacted-endpoint]")
        return {
            "code": self.code,
            "message": message,
            "provider": str(self.provider)[:40],
            "endpoint": safe_endpoint,
            "model": str(self.model)[:160],
            "retryable": self.retryable,
            "status_code": self.status_code,
            "details": details,
            "redacted": True,
        }


class UnavailableServiceError(LocalModelError):
    code = ERROR_UNAVAILABLE


class MissingModelError(LocalModelError):
    code = ERROR_MISSING_MODEL


class LocalModelTimeoutError(LocalModelError):
    code = ERROR_TIMEOUT


class MalformedResponseError(LocalModelError):
    code = ERROR_MALFORMED


class EmptyResponseError(LocalModelError):
    code = ERROR_EMPTY


class LocalModelHttpError(LocalModelError):
    code = ERROR_HTTP


class InterruptedStreamError(LocalModelError):
    code = ERROR_INTERRUPTED_STREAM


class InvalidConfigurationError(LocalModelError):
    code = ERROR_INVALID_CONFIG


class LocalModelCancelledError(LocalModelError):
    code = ERROR_CANCELLED


class ClosedClientError(LocalModelError):
    code = ERROR_CLOSED


class ContextLimitError(LocalModelError):
    code = ERROR_CONTEXT_LIMIT


class UnsupportedStreamingError(LocalModelError):
    code = ERROR_UNSUPPORTED_STREAMING


@dataclass(frozen=True)
class GenerationSettings:
    max_tokens: int = 350
    temperature: float = 0.45
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    seed: int | None = None
    stop: tuple[str, ...] = ()

    def validated(self) -> "GenerationSettings":
        if self.max_tokens <= 0:
            raise InvalidConfigurationError("local_model_max_tokens must be greater than zero.")
        if not 0.0 <= self.temperature <= 2.0:
            raise InvalidConfigurationError("local_model_temperature must be between 0 and 2.")
        if not 0.0 < self.top_p <= 1.0:
            raise InvalidConfigurationError("local_model_top_p must be greater than 0 and at most 1.")
        if self.top_k < 0:
            raise InvalidConfigurationError("local_model_top_k cannot be negative.")
        if self.repeat_penalty <= 0:
            raise InvalidConfigurationError("local_model_repeat_penalty must be greater than zero.")
        return self


@dataclass(frozen=True)
class LocalModelConfig:
    provider: str = "ollama"
    endpoint: str = "http://localhost:11434"
    embedding_endpoint: str = ""
    model: str = "qwen2.5:7b"
    embed_model: str = "nomic-embed-text:latest"
    context_size: int = 8192
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 120.0
    ollama_keep_alive_minutes: int = 30
    retry_limit: int = 1
    retry_delay_seconds: float = 0.25
    structured_json: bool = False
    thinking_mode: str = "auto"
    generation: GenerationSettings = field(default_factory=GenerationSettings)

    @classmethod
    def from_settings(cls, settings: dict[str, Any] | None = None) -> "LocalModelConfig":
        if settings is None:
            from settings_manager import load_settings

            settings = load_settings()
        provider = str(settings.get("local_model_provider", "ollama")).strip().lower()
        legacy_endpoint = str(settings.get("ollama_base_url", "http://localhost:11434"))
        endpoint = str(settings.get("local_model_endpoint", legacy_endpoint)).strip().rstrip("/")
        embedding_endpoint = str(settings.get("local_model_embedding_endpoint", "")).strip().rstrip("/")
        seed_value = settings.get("local_model_seed", 0)
        try:
            seed_int = int(seed_value)
        except (TypeError, ValueError):
            seed_int = 0
        stop = _parse_stop_sequences(settings.get("local_model_stop_sequences", ""))
        config = cls(
            provider=provider,
            endpoint=endpoint,
            embedding_endpoint=embedding_endpoint,
            model=str(settings.get("local_model", "qwen2.5:7b")).strip(),
            embed_model=str(settings.get("embed_model", "nomic-embed-text:latest")).strip(),
            context_size=int(settings.get("local_model_context_size", 8192)),
            connect_timeout_seconds=float(settings.get("local_model_connect_timeout_seconds", 5.0)),
            read_timeout_seconds=float(
                settings.get("local_model_read_timeout_seconds", settings.get("ollama_timeout_seconds", 120))
            ),
            ollama_keep_alive_minutes=int(settings.get("local_model_ollama_keep_alive_minutes", 30)),
            retry_limit=int(settings.get("local_model_retry_limit", 1)),
            thinking_mode=str(settings.get("local_model_thinking_mode", "auto")),
            retry_delay_seconds=float(settings.get("local_model_retry_delay_seconds", 0.25)),
            generation=GenerationSettings(
                max_tokens=int(settings.get("local_model_max_tokens", 350)),
                temperature=float(settings.get("local_model_temperature", 0.45)),
                top_p=float(settings.get("local_model_top_p", 0.9)),
                top_k=int(settings.get("local_model_top_k", 40)),
                repeat_penalty=float(settings.get("local_model_repeat_penalty", 1.1)),
                seed=None if seed_int == 0 else seed_int,
                stop=stop,
            ),
        )
        return config.validated()

    def validated(self) -> "LocalModelConfig":
        if self.provider not in {"ollama", "llama_cpp"}:
            raise InvalidConfigurationError(
                f"Unsupported local model provider: {self.provider!r}. Supported providers: ollama, llama_cpp.",
                provider=self.provider,
                endpoint=self.endpoint,
                model=self.model,
            )
        parsed = urlparse(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise InvalidConfigurationError(
                "local_model_endpoint must be an absolute http:// or https:// URL.",
                provider=self.provider,
                endpoint=self.endpoint,
                model=self.model,
            )
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise InvalidConfigurationError(
                "local_model_endpoint cannot contain credentials, a query string, or a fragment.",
                provider=self.provider,
                endpoint=self.endpoint,
                model=self.model,
            )
        if self.embedding_endpoint:
            parsed_embedding = urlparse(self.embedding_endpoint)
            if parsed_embedding.scheme not in {"http", "https"} or not parsed_embedding.netloc:
                raise InvalidConfigurationError(
                    "local_model_embedding_endpoint must be empty or an absolute http:// or https:// URL.",
                    provider=self.provider,
                    endpoint=self.embedding_endpoint,
                    model=self.embed_model,
                )
            if parsed_embedding.username or parsed_embedding.password or parsed_embedding.query or parsed_embedding.fragment:
                raise InvalidConfigurationError(
                    "local_model_embedding_endpoint cannot contain credentials, a query string, or a fragment.",
                    provider=self.provider,
                    endpoint=self.embedding_endpoint,
                    model=self.embed_model,
                )
        if not self.model:
            raise InvalidConfigurationError("local_model cannot be empty.", provider=self.provider, endpoint=self.endpoint)
        if self.thinking_mode not in {"auto", "off", "on"}:
            raise InvalidConfigurationError("local_model_thinking_mode must be auto, off, or on.")
        if not self.embed_model:
            raise InvalidConfigurationError("embed_model cannot be empty.", provider=self.provider, endpoint=self.endpoint)
        if self.context_size <= 0:
            raise InvalidConfigurationError("local_model_context_size must be greater than zero.")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise InvalidConfigurationError("Local model timeouts must be greater than zero.")
        if self.ollama_keep_alive_minutes < 0 or self.ollama_keep_alive_minutes > 1440:
            raise InvalidConfigurationError("local_model_ollama_keep_alive_minutes must be between 0 and 1440.")
        if self.retry_limit < 0 or self.retry_limit > 5:
            raise InvalidConfigurationError("local_model_retry_limit must be between 0 and 5.")
        if self.retry_delay_seconds < 0 or self.retry_delay_seconds > 10:
            raise InvalidConfigurationError("local_model_retry_delay_seconds must be between 0 and 10.")
        self.generation.validated()
        return self

    @property
    def timeout(self) -> tuple[float, float]:
        return (self.connect_timeout_seconds, self.read_timeout_seconds)

    @property
    def resolved_embedding_endpoint(self) -> str:
        """Return the explicit embedding endpoint or the legacy generation endpoint fallback."""
        return self.embedding_endpoint or self.endpoint

    @property
    def uses_legacy_single_endpoint(self) -> bool:
        return not bool(self.embedding_endpoint) or self.resolved_embedding_endpoint == self.endpoint

    def with_generation(
        self,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> "LocalModelConfig":
        generation = GenerationSettings(
            max_tokens=self.generation.max_tokens if max_tokens is None else int(max_tokens),
            temperature=self.generation.temperature if temperature is None else float(temperature),
            top_p=self.generation.top_p,
            top_k=self.generation.top_k,
            repeat_penalty=self.generation.repeat_penalty,
            seed=self.generation.seed,
            stop=self.generation.stop,
        )
        return LocalModelConfig(
            provider=self.provider,
            endpoint=self.endpoint,
            embedding_endpoint=self.embedding_endpoint,
            model=self.model if model is None else str(model),
            embed_model=self.embed_model,
            context_size=self.context_size,
            connect_timeout_seconds=self.connect_timeout_seconds,
            read_timeout_seconds=self.read_timeout_seconds,
            ollama_keep_alive_minutes=self.ollama_keep_alive_minutes,
            retry_limit=self.retry_limit,
            retry_delay_seconds=self.retry_delay_seconds,
            structured_json=self.structured_json,
            thinking_mode=self.thinking_mode,
            generation=generation,
        ).validated()


@dataclass
class ProviderHealth:
    provider: str
    endpoint: str
    embedding_endpoint: str
    configured_model: str
    configured_embed_model: str
    service_available: bool = False
    embedding_service_available: bool = False
    model_available: bool | None = None
    embed_model_available: bool | None = None
    version: Any = None
    embedding_version: Any = None
    models: list[str] = field(default_factory=list)
    embedding_models: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    embedding_error: dict[str, Any] | None = None

    @property
    def status(self) -> str:
        if not self.service_available:
            return "unavailable"
        if self.model_available is False:
            return "missing_model"
        if not self.embedding_service_available or self.embed_model_available is False:
            return "degraded"
        return "healthy"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status
        return result


@runtime_checkable
class LocalModelProvider(Protocol):
    name: str

    def generate(self, prompt: str, cancel_event: threading.Event | None = None) -> str: ...

    def stream(self, prompt: str, cancel_event: threading.Event | None = None) -> Iterator[str]: ...

    def list_models(self, endpoint: str | None = None) -> list[str]: ...

    def version(self, endpoint: str | None = None) -> Any: ...

    def embed(self, text: str) -> list[float]: ...

    def close(self) -> None: ...

    def cancel(self) -> None: ...


def _parse_stop_sequences(value: Any) -> tuple[str, ...]:
    if value in {None, ""}:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item))
    text = str(value).strip()
    if not text:
        return ()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as error:
            raise InvalidConfigurationError("local_model_stop_sequences contains malformed JSON.") from error
        if not isinstance(parsed, list):
            raise InvalidConfigurationError("local_model_stop_sequences JSON must be a list of strings.")
        return tuple(str(item) for item in parsed if str(item))
    return tuple(part.strip() for part in text.split("|") if part.strip())


def _cancelled(config: LocalModelConfig, cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise LocalModelCancelledError(
            "Local model request was cancelled.",
            provider=config.provider,
            endpoint=config.endpoint,
            model=config.model,
        )


def _body_preview(response: requests.Response) -> str:
    try:
        text = response.text
    except Exception:
        text = ""
    return text[:500]


class _HttpProvider:
    name = "base"

    def __init__(self, config: LocalModelConfig, session: requests.Session | None = None) -> None:
        self.config = config.validated()
        self.session = session or requests.Session()
        self._owns_session = session is None
        self._active_responses: set[requests.Response] = set()
        self._response_lock = threading.Lock()
        self.last_metrics: dict[str, Any] = {}

    def _track_response(self, response: requests.Response) -> requests.Response:
        with self._response_lock:
            self._active_responses.add(response)
        return response

    def _close_response(self, response: requests.Response) -> None:
        with self._response_lock:
            self._active_responses.discard(response)
        response.close()

    def cancel(self) -> None:
        with self._response_lock:
            responses = list(self._active_responses)
            self._active_responses.clear()
        for response in responses:
            try:
                response.close()
            except Exception:
                pass

    def close(self) -> None:
        self.cancel()
        if self._owns_session:
            self.session.close()

    def _validate_returned_model(self, data: dict[str, Any]) -> None:
        returned_model = str(data.get("model") or "").strip()
        if returned_model and returned_model != self.config.model:
            raise MissingModelError(
                "The provider served a different model than the one explicitly configured.",
                provider=self.config.provider,
                endpoint=self.config.endpoint,
                model=self.config.model,
                retryable=False,
                details={"failure_kind": "returned_model_mismatch"},
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        endpoint: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        active_endpoint = (endpoint or self.config.endpoint).rstrip("/")
        active_model = self.config.model if model is None else model
        url = f"{active_endpoint}{path}"
        kwargs.setdefault("timeout", self.config.timeout)
        try:
            response = self.session.request(method, url, **kwargs)
        except requests.exceptions.ConnectTimeout as error:
            raise UnavailableServiceError(
                f"Local model service is unavailable at {active_endpoint}.",
                provider=self.config.provider,
                endpoint=active_endpoint,
                model=active_model,
                retryable=True,
                details={"failure_kind": "connection_failure", "exception_type": type(error).__name__},
            ) from error
        except requests.exceptions.Timeout as error:
            raise LocalModelTimeoutError(
                f"Local model request timed out at {url}.",
                provider=self.config.provider,
                endpoint=active_endpoint,
                model=active_model,
                retryable=True,
                details={"failure_kind": "read_timeout", "exception_type": type(error).__name__},
            ) from error
        except requests.exceptions.ConnectionError as error:
            raise UnavailableServiceError(
                f"Local model service is unavailable at {active_endpoint}.",
                provider=self.config.provider,
                endpoint=active_endpoint,
                model=active_model,
                retryable=True,
                details={"failure_kind": "connection_failure", "exception_type": type(error).__name__},
            ) from error
        except requests.exceptions.RequestException as error:
            raise LocalModelHttpError(
                f"Local model HTTP request failed: {error}",
                provider=self.config.provider,
                endpoint=active_endpoint,
                model=active_model,
                retryable=False,
            ) from error
        if response.status_code >= 400:
            preview = _body_preview(response)
            lowered = preview.lower()
            response.close()
            context_markers = (
                "context length",
                "context window",
                "too many tokens",
                "prompt is too long",
                "maximum context",
                "exceeds the context",
            )
            if any(token in lowered for token in context_markers) or response.status_code == 413:
                raise ContextLimitError(
                    "The configured model rejected the request because its context limit was exceeded.",
                    provider=self.config.provider,
                    endpoint=active_endpoint,
                    model=active_model,
                    status_code=response.status_code,
                    retryable=False,
                    details={"failure_kind": "provider_context_limit"},
                )
            if response.status_code == 404 and any(token in lowered for token in ("model", "not found", "does not exist")):
                raise MissingModelError(
                    f"Configured model {active_model!r} is not available from {self.config.provider}.",
                    provider=self.config.provider,
                    endpoint=active_endpoint,
                    model=active_model,
                    status_code=response.status_code,
                    details={"body": preview},
                )
            if kwargs.get("stream") and response.status_code in {404, 405, 415, 501}:
                raise UnsupportedStreamingError(
                    "The configured provider endpoint does not support the requested streaming operation.",
                    provider=self.config.provider,
                    endpoint=active_endpoint,
                    model=active_model,
                    status_code=response.status_code,
                    retryable=False,
                    details={"failure_kind": "unsupported_streaming", "stream_supported": False},
                )
            raise LocalModelHttpError(
                f"Local model HTTP request returned status {response.status_code}.",
                provider=self.config.provider,
                endpoint=active_endpoint,
                model=active_model,
                retryable=response.status_code in {429, 502, 503, 504},
                status_code=response.status_code,
                details={"body": preview},
            )
        return self._track_response(response)

    def _json(
        self,
        response: requests.Response,
        *,
        endpoint: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        active_endpoint = endpoint or self.config.endpoint
        active_model = self.config.model if model is None else model
        try:
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError) as error:
                raise MalformedResponseError(
                    "Local model service returned malformed JSON.",
                    provider=self.config.provider,
                    endpoint=active_endpoint,
                    model=active_model,
                    details={"body": _body_preview(response)},
                ) from error
            if not isinstance(data, dict):
                raise MalformedResponseError(
                    "Local model service returned a JSON value that was not an object.",
                    provider=self.config.provider,
                    endpoint=active_endpoint,
                    model=active_model,
                )
            return data
        finally:
            self._close_response(response)


class OllamaProvider(_HttpProvider):
    name = "ollama"

    def _keep_alive(self) -> str | int:
        minutes = self.config.ollama_keep_alive_minutes
        return 0 if minutes == 0 else f"{minutes}m"

    def _options(self) -> dict[str, Any]:
        generation = self.config.generation
        options: dict[str, Any] = {
            "num_ctx": self.config.context_size,
            "num_predict": generation.max_tokens,
            "temperature": generation.temperature,
            "top_p": generation.top_p,
            "top_k": generation.top_k,
            "repeat_penalty": generation.repeat_penalty,
        }
        if generation.seed is not None:
            options["seed"] = generation.seed
        if generation.stop:
            options["stop"] = list(generation.stop)
        return options

    def generate(self, prompt: str, cancel_event: threading.Event | None = None) -> str:
        _cancelled(self.config, cancel_event)
        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self._keep_alive(),
            "options": self._options(),
        }
        if self.config.structured_json:
            payload["format"] = "json"
        if self.config.thinking_mode != "auto":
            payload["think"] = self.config.thinking_mode == "on"
        response = self._request(
            "POST",
            "/api/generate",
            json=payload,
        )
        _cancelled(self.config, cancel_event)
        data = self._json(response)
        self._validate_returned_model(data)
        self.last_metrics = _ollama_metrics(data)
        text = str(data.get("response") or "").strip()
        if not text:
            error_text = str(data.get("error") or "")
            if "model" in error_text.lower() and "not found" in error_text.lower():
                raise MissingModelError(error_text, provider=self.name, endpoint=self.config.endpoint, model=self.config.model)
            raise EmptyResponseError(
                "Ollama returned an empty generation response.", provider=self.name, endpoint=self.config.endpoint, model=self.config.model
            )
        return text

    def stream(self, prompt: str, cancel_event: threading.Event | None = None) -> Iterator[str]:
        _cancelled(self.config, cancel_event)
        self.last_metrics = {}
        response = self._request(
            "POST",
            "/api/generate",
            json={"model": self.config.model, "prompt": prompt, "stream": True, "keep_alive": self._keep_alive(), "options": self._options(),
                  **({"think": self.config.thinking_mode == "on"} if self.config.thinking_mode != "auto" else {})},
            stream=True,
        )
        yielded = False
        done = False
        try:
            for raw_line in response.iter_lines(decode_unicode=True):
                _cancelled(self.config, cancel_event)
                if not raw_line:
                    continue
                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError as error:
                    raise MalformedResponseError(
                        "Ollama stream contained malformed JSON.",
                        provider=self.name,
                        endpoint=self.config.endpoint,
                        model=self.config.model,
                        details={"line": str(raw_line)[:500]},
                    ) from error
                if not isinstance(data, dict):
                    raise MalformedResponseError("Ollama stream item was not an object.", provider=self.name)
                self._validate_returned_model(data)
                if data.get("error"):
                    message = str(data["error"])
                    if "model" in message.lower() and "not found" in message.lower():
                        raise MissingModelError(message, provider=self.name, endpoint=self.config.endpoint, model=self.config.model)
                    raise LocalModelHttpError(message, provider=self.name, endpoint=self.config.endpoint, model=self.config.model)
                chunk = str(data.get("response") or "")
                if chunk:
                    yielded = True
                    yield chunk
                if data.get("done") is True:
                    self.last_metrics = _ollama_metrics(data)
                    done = True
                    break
        except requests.exceptions.Timeout as error:
            raise LocalModelTimeoutError(
                "Ollama streaming response timed out.",
                provider=self.name,
                endpoint=self.config.endpoint,
                model=self.config.model,
                retryable=False,
                details={"failure_kind": "stream_read_timeout", "exception_type": type(error).__name__, "yielded_content": yielded},
            ) from error
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as error:
            raise InterruptedStreamError(
                "Ollama disconnected before the stream completed.",
                provider=self.name,
                endpoint=self.config.endpoint,
                model=self.config.model,
                retryable=False,
                details={"failure_kind": "provider_disconnect", "exception_type": type(error).__name__, "yielded_content": yielded},
            ) from error
        finally:
            self._close_response(response)
        if not done:
            raise InterruptedStreamError(
                "Ollama stream ended before a done marker was received.",
                provider=self.name,
                endpoint=self.config.endpoint,
                model=self.config.model,
                details={"yielded_content": yielded},
            )
        if not yielded:
            raise EmptyResponseError("Ollama stream completed without content.", provider=self.name)

    def list_models(self, endpoint: str | None = None) -> list[str]:
        active_endpoint = endpoint or self.config.endpoint
        data = self._json(self._request("GET", "/api/tags", endpoint=active_endpoint), endpoint=active_endpoint)
        models = data.get("models", [])
        if not isinstance(models, list):
            raise MalformedResponseError("Ollama model list was not an array.", provider=self.name)
        names = []
        for item in models:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("model") or "").strip()
                if name:
                    names.append(name)
        return sorted(set(names))

    def version(self, endpoint: str | None = None) -> Any:
        active_endpoint = endpoint or self.config.endpoint
        return self._json(self._request("GET", "/api/version", endpoint=active_endpoint), endpoint=active_endpoint).get("version")

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            return []
        endpoint = self.config.resolved_embedding_endpoint
        response = self._request(
            "POST", "/api/embed", endpoint=endpoint, model=self.config.embed_model,
            json={"model": self.config.embed_model, "input": text},
        )
        data = self._json(response, endpoint=endpoint, model=self.config.embed_model)
        embeddings = data.get("embeddings")
        if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
            return [float(value) for value in embeddings[0]]
        embedding = data.get("embedding")
        if isinstance(embedding, list):
            return [float(value) for value in embedding]
        raise EmptyResponseError("Ollama returned no embedding vector.", provider=self.name, model=self.config.embed_model)


class LlamaCppProvider(_HttpProvider):
    name = "llama_cpp"

    def _chat_payload(self, prompt: str, stream: bool) -> dict[str, Any]:
        generation = self.config.generation
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "max_tokens": generation.max_tokens,
            "temperature": generation.temperature,
            "top_p": generation.top_p,
            "top_k": generation.top_k,
            "repeat_penalty": generation.repeat_penalty,
        }
        if generation.seed is not None:
            payload["seed"] = generation.seed
        if generation.stop:
            payload["stop"] = list(generation.stop)
        if self.config.structured_json:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def generate(self, prompt: str, cancel_event: threading.Event | None = None) -> str:
        _cancelled(self.config, cancel_event)
        data = self._json(self._request("POST", "/v1/chat/completions", json=self._chat_payload(prompt, False)))
        self._validate_returned_model(data)
        _cancelled(self.config, cancel_event)
        choices = data.get("choices")
        try:
            text = choices[0]["message"]["content"]
        except (TypeError, KeyError, IndexError) as error:
            raise MalformedResponseError(
                "llama.cpp response did not contain choices[0].message.content.",
                provider=self.name,
                endpoint=self.config.endpoint,
                model=self.config.model,
                details={"response": data},
            ) from error
        text = str(text or "").strip()
        if not text:
            raise EmptyResponseError("llama.cpp returned an empty generation response.", provider=self.name)
        return text

    def stream(self, prompt: str, cancel_event: threading.Event | None = None) -> Iterator[str]:
        _cancelled(self.config, cancel_event)
        response = self._request(
            "POST", "/v1/chat/completions", json=self._chat_payload(prompt, True), stream=True
        )
        yielded = False
        done = False
        try:
            for raw_line in response.iter_lines(decode_unicode=True):
                _cancelled(self.config, cancel_event)
                if not raw_line:
                    continue
                line = str(raw_line)
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line == "[DONE]":
                    done = True
                    break
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as error:
                    raise MalformedResponseError(
                        "llama.cpp stream contained malformed JSON.",
                        provider=self.name,
                        endpoint=self.config.endpoint,
                        model=self.config.model,
                        details={"line": line[:500]},
                    ) from error
                if not isinstance(data, dict):
                    raise MalformedResponseError("llama.cpp stream item was not an object.", provider=self.name)
                self._validate_returned_model(data)
                try:
                    chunk = data["choices"][0].get("delta", {}).get("content", "")
                except (TypeError, KeyError, IndexError) as error:
                    raise MalformedResponseError(
                        "llama.cpp stream item did not contain a valid choices delta.", provider=self.name, details={"item": data}
                    ) from error
                if chunk:
                    yielded = True
                    yield str(chunk)
        except requests.exceptions.Timeout as error:
            raise LocalModelTimeoutError(
                "llama.cpp streaming response timed out.",
                provider=self.name,
                endpoint=self.config.endpoint,
                model=self.config.model,
                retryable=False,
                details={"failure_kind": "stream_read_timeout", "exception_type": type(error).__name__, "yielded_content": yielded},
            ) from error
        except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as error:
            raise InterruptedStreamError(
                "llama.cpp disconnected before the stream completed.",
                provider=self.name,
                endpoint=self.config.endpoint,
                model=self.config.model,
                retryable=False,
                details={"failure_kind": "provider_disconnect", "exception_type": type(error).__name__, "yielded_content": yielded},
            ) from error
        finally:
            self._close_response(response)
        if not done:
            raise InterruptedStreamError(
                "llama.cpp stream ended before the [DONE] marker.",
                provider=self.name,
                endpoint=self.config.endpoint,
                model=self.config.model,
                details={"yielded_content": yielded},
            )
        if not yielded:
            raise EmptyResponseError("llama.cpp stream completed without content.", provider=self.name)

    def list_models(self, endpoint: str | None = None) -> list[str]:
        active_endpoint = endpoint or self.config.endpoint
        data = self._json(self._request("GET", "/v1/models", endpoint=active_endpoint), endpoint=active_endpoint)
        models = data.get("data", [])
        if not isinstance(models, list):
            raise MalformedResponseError("llama.cpp model list was not an array.", provider=self.name)
        return sorted({str(item.get("id") or "").strip() for item in models if isinstance(item, dict) and item.get("id")})

    def version(self, endpoint: str | None = None) -> Any:
        active_endpoint = endpoint or self.config.endpoint
        try:
            data = self._json(self._request("GET", "/health", endpoint=active_endpoint), endpoint=active_endpoint)
        except LocalModelHttpError as error:
            if error.status_code == 404:
                return None
            raise
        return data.get("version") or data.get("status")

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            return []
        endpoint = self.config.resolved_embedding_endpoint
        data = self._json(
            self._request(
                "POST", "/v1/embeddings", endpoint=endpoint, model=self.config.embed_model,
                json={"model": self.config.embed_model, "input": text},
            ),
            endpoint=endpoint,
            model=self.config.embed_model,
        )
        rows = data.get("data")
        try:
            vector = rows[0]["embedding"]
        except (TypeError, KeyError, IndexError) as error:
            raise MalformedResponseError("llama.cpp embedding response had no data[0].embedding.", provider=self.name) from error
        if not isinstance(vector, list) or not vector:
            raise EmptyResponseError("llama.cpp returned no embedding vector.", provider=self.name)
        return [float(value) for value in vector]


class LocalModelClient:
    """Provider-neutral client with bounded non-stream retry behavior."""

    def __init__(
        self,
        config: LocalModelConfig | None = None,
        *,
        session: requests.Session | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self.config = (config or LocalModelConfig.from_settings()).validated()
        self.cancel_event = cancel_event or threading.Event()
        self._closed = False
        self.last_retry_count = 0
        provider_type = OllamaProvider if self.config.provider == "ollama" else LlamaCppProvider
        resolved_session = session if session is not None else _shared_http_session(self.config)
        self.provider: LocalModelProvider = provider_type(self.config, session=resolved_session)

    @classmethod
    def from_settings(cls, settings: dict[str, Any] | None = None, **kwargs: Any) -> "LocalModelClient":
        return cls(LocalModelConfig.from_settings(settings), **kwargs)

    def __enter__(self) -> "LocalModelClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise ClosedClientError(
                "Local model client is closed.",
                provider=self.config.provider,
                endpoint=self.config.endpoint,
                model=self.config.model,
            )
        _cancelled(self.config, self.cancel_event)

    def cancel(self) -> None:
        self.cancel_event.set()
        self.provider.cancel()

    def close(self) -> None:
        if not self._closed:
            self.provider.close()
            self._closed = True

    def _call_with_retry(self, operation: Any) -> Any:
        self._ensure_open()
        self.last_retry_count = 0
        attempts = self.config.retry_limit + 1
        last_error: LocalModelError | None = None
        for attempt in range(attempts):
            self._ensure_open()
            try:
                return operation()
            except LocalModelError as error:
                last_error = error
                if not error.retryable or attempt >= attempts - 1:
                    raise
                self.last_retry_count = attempt + 1
                if self.config.retry_delay_seconds and self.cancel_event.wait(self.config.retry_delay_seconds):
                    _cancelled(self.config, self.cancel_event)
        assert last_error is not None
        raise last_error

    def generate(self, prompt: str) -> str:
        if not str(prompt).strip():
            raise InvalidConfigurationError("Local model prompt cannot be empty.")
        return str(self._call_with_retry(lambda: self.provider.generate(prompt, self.cancel_event)))

    def stream(self, prompt: str) -> Iterator[str]:
        self._ensure_open()
        self.last_retry_count = 0
        if not str(prompt).strip():
            raise InvalidConfigurationError("Local model prompt cannot be empty.")
        # Streaming requests are deliberately never replayed. Empty chunks are
        # harmless transport keep-alives; malformed yielded chunk types fail
        # closed before they can reach conversation rendering. Provider-specific
        # adapters still enforce their own JSON/schema completion markers.
        yielded_content = False
        try:
            for chunk in self.provider.stream(prompt, self.cancel_event):
                if chunk is None or chunk == "":
                    continue
                if not isinstance(chunk, str):
                    raise MalformedResponseError(
                        "The provider stream yielded a non-text chunk.",
                        provider=self.config.provider, endpoint=self.config.endpoint, model=self.config.model,
                        details={"failure_kind": "non_text_stream_chunk", "yielded_content": yielded_content},
                    )
                yielded_content = True
                yield chunk
        except Exception as error:
            if self.cancel_event.is_set() and not isinstance(error, LocalModelCancelledError):
                raise LocalModelCancelledError(
                    "Local model request was cancelled.",
                    provider=self.config.provider,
                    endpoint=self.config.endpoint,
                    model=self.config.model,
                    details={"failure_kind": "cancelled_stream_transport", "exception_type": type(error).__name__},
                ) from None
            raise

    @property
    def last_metrics(self) -> dict[str, Any]:
        value = getattr(self.provider, "last_metrics", {})
        return dict(value) if isinstance(value, dict) else {}

    def _service_endpoint(self, service: str) -> str:
        if service == "generation":
            return self.config.endpoint
        if service == "embedding":
            return self.config.resolved_embedding_endpoint
        raise InvalidConfigurationError(f"Unknown local-model service: {service!r}.")

    def list_models(self, service: str = "generation") -> list[str]:
        endpoint = self._service_endpoint(service)
        return list(self._call_with_retry(lambda: self.provider.list_models(endpoint)))

    def version(self, service: str = "generation") -> Any:
        endpoint = self._service_endpoint(service)
        return self._call_with_retry(lambda: self.provider.version(endpoint))

    def embed(self, text: str) -> list[float]:
        if not str(text).strip():
            return []
        return list(self._call_with_retry(lambda: self.provider.embed(text)))

    def health(self) -> ProviderHealth:
        self._ensure_open()
        health = ProviderHealth(
            provider=self.config.provider,
            endpoint=self.config.endpoint,
            embedding_endpoint=self.config.resolved_embedding_endpoint,
            configured_model=self.config.model,
            configured_embed_model=self.config.embed_model,
        )
        try:
            health.version = self.version("generation")
            health.models = self.list_models("generation")
            health.service_available = True
            health.model_available = self.config.model in health.models if health.models else None
        except LocalModelError as error:
            health.error = error.to_safe_dict()
            health.service_available = error.code not in {ERROR_UNAVAILABLE, ERROR_TIMEOUT}
            if error.code == ERROR_MISSING_MODEL:
                health.model_available = False

        if self.config.uses_legacy_single_endpoint and health.service_available:
            health.embedding_version = health.version
            health.embedding_models = list(health.models)
            health.embedding_service_available = True
        else:
            try:
                health.embedding_version = self.version("embedding")
                health.embedding_models = self.list_models("embedding")
                health.embedding_service_available = True
            except LocalModelError as error:
                health.embedding_error = error.to_safe_dict()
                health.embedding_service_available = error.code not in {ERROR_UNAVAILABLE, ERROR_TIMEOUT}
        if health.embedding_service_available:
            health.embed_model_available = (
                self.config.embed_model in health.embedding_models if health.embedding_models else None
            )
        return health


def provider_health(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return provider-neutral health without writing reports or runtime state."""
    try:
        with LocalModelClient.from_settings(settings) as client:
            return client.health().to_dict()
    except LocalModelError as error:
        config_provider = str((settings or {}).get("local_model_provider", "ollama"))
        config_endpoint = str((settings or {}).get("local_model_endpoint", ""))
        return ProviderHealth(
            provider=error.provider or config_provider,
            endpoint=error.endpoint or config_endpoint,
            embedding_endpoint=str((settings or {}).get("local_model_embedding_endpoint", "") or config_endpoint),
            configured_model=error.model or str((settings or {}).get("local_model", "")),
            configured_embed_model=str((settings or {}).get("embed_model", "")),
            service_available=False,
            error=error.to_safe_dict(),
        ).to_dict()
