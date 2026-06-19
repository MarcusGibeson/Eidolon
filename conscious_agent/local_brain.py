from __future__ import annotations

import json
from typing import Any

import requests

from settings_manager import get_setting


# Defaults are still exported for older modules, but runtime calls read from data/settings.json.
DEFAULT_LOCAL_MODEL = str(get_setting("local_model", "qwen2.5:7b"))
DEFAULT_EMBED_MODEL = str(get_setting("embed_model", "nomic-embed-text"))


def _ollama_base_url() -> str:
    return str(get_setting("ollama_base_url", "http://localhost:11434")).rstrip("/")


def _ollama_timeout() -> int:
    return int(get_setting("ollama_timeout_seconds", 120))


def _generate_url() -> str:
    return f"{_ollama_base_url()}/api/generate"


def _embed_url() -> str:
    return f"{_ollama_base_url()}/api/embed"


def local_generate(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 300,
) -> str:
    """
    Sends a prompt to a local Ollama model and returns the response text.
    This keeps Eidolon's everyday thinking local instead of spending API money.
    """
    selected_model = model or str(get_setting("local_model", DEFAULT_LOCAL_MODEL))

    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        response = requests.post(_generate_url(), json=payload, timeout=_ollama_timeout())
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return (
            "I tried to use my local brain, but Ollama is not running. "
            "Start Ollama first, then try again."
        )
    except requests.exceptions.Timeout:
        return (
            "My local brain took too long to answer. "
            "The model may be too large or the computer may be busy."
        )
    except requests.exceptions.RequestException as error:
        return f"My local brain hit an error: {error}"

    data = response.json()
    return data.get("response", "").strip()


def local_generate_json(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 300,
) -> dict[str, Any]:
    """
    Asks the local model for JSON and parses it safely.
    If the model outputs nonsense, return a plain fallback dict instead of crashing.
    """
    raw = local_generate(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"content": raw, "parse_error": True}


def local_embed(text: str, model: str | None = None) -> list[float]:
    """
    Creates a local embedding vector using Ollama.
    Supports both newer /api/embed and older /api/embeddings endpoint styles.
    """
    if not text.strip():
        return []

    selected_model = model or str(get_setting("embed_model", DEFAULT_EMBED_MODEL))

    modern_payload = {
        "model": selected_model,
        "input": text,
    }

    try:
        response = requests.post(_embed_url(), json=modern_payload, timeout=_ollama_timeout())
        if response.status_code != 404:
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
    except requests.exceptions.ConnectionError:
        print("Vector memory skipped: Ollama is not running.")
        return []
    except requests.exceptions.Timeout:
        print("Vector memory skipped: embedding request timed out.")
        return []
    except requests.exceptions.RequestException as error:
        print(f"Vector memory skipped: embedding error: {error}")

    # Fallback for older Ollama versions.
    legacy_payload = {
        "model": selected_model,
        "prompt": text,
    }
    legacy_url = f"{_ollama_base_url()}/api/embeddings"

    try:
        response = requests.post(legacy_url, json=legacy_payload, timeout=_ollama_timeout())
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("Vector memory skipped: Ollama is not running.")
        return []
    except requests.exceptions.Timeout:
        print("Vector memory skipped: legacy embedding request timed out.")
        return []
    except requests.exceptions.RequestException as error:
        print(f"Vector memory skipped: legacy embedding error: {error}")
        return []

    data = response.json()
    embedding = data.get("embedding", [])
    return embedding if isinstance(embedding, list) else []
