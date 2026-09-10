from __future__ import annotations

import json
from typing import Any, Iterator

from local_model import (
    LocalModelClient,
    LocalModelConfig,
    LocalModelError,
    provider_health,
)
from settings_manager import DEFAULT_SETTINGS, get_setting, load_settings


# Compatibility exports for older modules. Importing this module must remain
# read-only; runtime requests still reload operator settings at call time.
DEFAULT_LOCAL_MODEL = str(DEFAULT_SETTINGS.get("local_model") or "qwen2.5:7b")
DEFAULT_EMBED_MODEL = str(DEFAULT_SETTINGS.get("embed_model") or "nomic-embed-text:latest")


def _friendly_error(error: LocalModelError) -> str:
    provider = error.provider or str(get_setting("local_model_provider", "ollama"))
    if error.code == "unavailable_service":
        return (
            f"I tried to use my local brain, but the configured {provider} service is unavailable. "
            "Start the local model service or update the provider endpoint, then try again."
        )
    if error.code == "missing_model":
        return (
            f"My local brain cannot find the configured model {error.model or DEFAULT_LOCAL_MODEL!r} "
            f"on the {provider} service. Model installation remains an explicit operator action."
        )
    if error.code == "timeout":
        return "My local brain took too long to answer. The model may be busy, too large, or using an unsuitable timeout."
    if error.code == "cancelled":
        return "My local brain request was cancelled cleanly."
    if error.code == "closed_client":
        return "My local brain client was already closed."
    return f"My local brain hit a {error.code} error: {error}"


def _config_for_call(
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> LocalModelConfig:
    return LocalModelConfig.from_settings(load_settings()).with_generation(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def local_generate(
    prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Generate through the configured provider using Eidolon's shared conversation seam."""
    try:
        with LocalModelClient(_config_for_call(model=model, temperature=temperature, max_tokens=max_tokens)) as client:
            return client.generate(prompt)
    except LocalModelError as error:
        return _friendly_error(error)


def local_generate_stream(
    prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Iterator[str]:
    """Stream through the configured provider without replaying interrupted requests."""
    client: LocalModelClient | None = None
    try:
        client = LocalModelClient(_config_for_call(model=model, temperature=temperature, max_tokens=max_tokens))
        yield from client.stream(prompt)
    except LocalModelError as error:
        yield _friendly_error(error)
    finally:
        if client is not None:
            client.close()


def local_generate_json(
    prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    raw = local_generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"content": raw, "parse_error": True}
    return parsed if isinstance(parsed, dict) else {"content": parsed, "parse_error": True}


def local_embed(text: str, model: str | None = None) -> list[float]:
    if not text.strip():
        return []
    try:
        config = LocalModelConfig.from_settings(load_settings())
        if model:
            config = LocalModelConfig(
                provider=config.provider,
                endpoint=config.endpoint,
                embedding_endpoint=config.embedding_endpoint,
                model=config.model,
                embed_model=model,
                context_size=config.context_size,
                connect_timeout_seconds=config.connect_timeout_seconds,
                read_timeout_seconds=config.read_timeout_seconds,
                retry_limit=config.retry_limit,
                retry_delay_seconds=config.retry_delay_seconds,
                generation=config.generation,
            ).validated()
        with LocalModelClient(config) as client:
            return client.embed(text)
    except LocalModelError as error:
        print(f"Vector memory skipped: {_friendly_error(error)}")
        return []


def local_model_status() -> dict[str, Any]:
    settings = load_settings()
    status = provider_health(settings)
    status["generation"] = {
        "context_size": settings.get("local_model_context_size"),
        "max_tokens": settings.get("local_model_max_tokens"),
        "temperature": settings.get("local_model_temperature"),
        "top_p": settings.get("local_model_top_p"),
        "top_k": settings.get("local_model_top_k"),
        "repeat_penalty": settings.get("local_model_repeat_penalty"),
        "seed": settings.get("local_model_seed"),
        "stop_sequences": settings.get("local_model_stop_sequences"),
        "retry_limit": settings.get("local_model_retry_limit"),
        "retry_delay_seconds": settings.get("local_model_retry_delay_seconds"),
        "connect_timeout_seconds": settings.get("local_model_connect_timeout_seconds"),
        "read_timeout_seconds": settings.get("local_model_read_timeout_seconds"),
    }
    status["operator_install_required"] = status.get("model_available") is False
    status["automatic_model_installation"] = False
    return status


def local_model_status_text() -> str:
    status = local_model_status()
    lines = [
        "# Local model status",
        "",
        f"Provider: {status.get('provider')}",
        f"Generation endpoint: {status.get('endpoint')}",
        f"Embedding endpoint: {status.get('embedding_endpoint')}",
        f"Status: {status.get('status')}",
        f"Generation service available: {status.get('service_available')}",
        f"Embedding service available: {status.get('embedding_service_available')}",
        f"Version/health: {status.get('version')}",
        f"Configured model: {status.get('configured_model')}",
        f"Model available: {status.get('model_available')}",
        f"Configured embedding model: {status.get('configured_embed_model')}",
        f"Embedding model available: {status.get('embed_model_available')}",
        "",
        "Available models:",
    ]
    models = status.get("models") or []
    lines.extend(f"- {model}" for model in models)
    if not models:
        lines.append("- [none reported]")
    generation = status.get("generation") or {}
    lines.extend(
        [
            "",
            "Generation settings:",
            f"- Context size: {generation.get('context_size')}",
            f"- Max tokens: {generation.get('max_tokens')}",
            f"- Temperature: {generation.get('temperature')}",
            f"- Top-p / top-k: {generation.get('top_p')} / {generation.get('top_k')}",
            f"- Repeat penalty: {generation.get('repeat_penalty')}",
            f"- Retries: {generation.get('retry_limit')} after {generation.get('retry_delay_seconds')}s",
            "",
            "Model installation, deletion, and replacement remain explicit operator actions.",
        ]
    )
    if status.get("error"):
        lines.extend(["", "Error:", json.dumps(status["error"], indent=2, default=str)])
    return "\n".join(lines)


def print_local_model_status(*, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(local_model_status(), indent=2, default=str))
    else:
        print(local_model_status_text())
