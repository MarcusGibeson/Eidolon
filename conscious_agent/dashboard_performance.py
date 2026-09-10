from __future__ import annotations

"""Dashboard response-time helpers for v1251.6-v1251.8."""

import importlib
from pathlib import Path
import re
import threading
import time
from typing import Any

CONTRACT_VERSION = "v1251.8"
_PREWARM_LOCK = threading.RLock()
_PREWARM_STATE: dict[str, Any] = {
    "started": False, "completed": False, "failed": False, "duration_ms": None,
    "provider_contacted": False, "runtime_mutation_performed": False,
}
_ASSET_ROOT = Path(__file__).resolve().parent / "static"
_ASSET_CACHE: dict[str, tuple[int, bytes]] = {}


def _prewarm_worker() -> None:
    started = time.perf_counter()
    try:
        importlib.import_module("api_server")
    except Exception as error:
        with _PREWARM_LOCK:
            _PREWARM_STATE.update({
                "completed": True, "failed": True, "error_type": type(error).__name__,
                "duration_ms": int((time.perf_counter() - started) * 1000),
            })
        return
    with _PREWARM_LOCK:
        _PREWARM_STATE.update({
            "completed": True, "failed": False,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        })


def prewarm_api_runtime_async() -> dict[str, Any]:
    with _PREWARM_LOCK:
        if _PREWARM_STATE["started"]:
            return prewarm_status()
        _PREWARM_STATE["started"] = True
        thread = threading.Thread(target=_prewarm_worker, name="eidolon-api-prewarm", daemon=True)
        thread.start()
    return prewarm_status()


def prewarm_status() -> dict[str, Any]:
    with _PREWARM_LOCK:
        return {**_PREWARM_STATE, "contract_version": CONTRACT_VERSION, "content_free": True}


def optimize_dashboard_html_assets(html: str) -> str:
    """Replace the frozen v1250.7 inline shell assets at response time.

    The historical renderer stays byte-for-byte compatible for retained tests;
    only the served HTML is optimized.
    """
    text = str(html or "")
    # The lightweight first-use shell has its own bounded layout contract. It
    # shares the response path with the full dashboard, but not its stylesheet.
    # Replacing that CSS creates a hybrid document whose restored history
    # expands the page and pushes the composer off-screen.
    if "data-first-use-shell=" not in text:
        text = re.sub(
            r"<style>.*?</style>",
            "<link rel='stylesheet' href='/assets/dashboard.css?v=2500.9-r1'>",
            text,
            count=1,
            flags=re.S,
        )
    text = re.sub(
        r"<script>\s*\(function \(\) \{.*?</script>",
        "<script src='/assets/dashboard.js?v=2500.9-r1' defer></script>",
        text,
        count=1,
        flags=re.S,
    )
    # v1253.5: the first live poll proves dashboard health without importing the
    # heavyweight API server. Later polls use the complete status surface.
    text = text.replace(
        "const response = await fetch('/api/status?ts=' + Date.now(), { cache: 'no-store' });",
        "const eidolonStatusPath = window.__eidolonFullStatusStarted ? '/api/status' : '/api/runtime-status'; "
        "window.__eidolonFullStatusStarted = true; "
        "const response = await fetch(eidolonStatusPath + '?ts=' + Date.now(), { cache: 'no-store' });",
        1,
    )
    return text


def load_dashboard_asset(name: str) -> tuple[str, bytes] | None:
    token = str(name or "").strip()
    if token not in {"dashboard.css", "dashboard.js"}:
        return None
    path = _ASSET_ROOT / token
    try:
        stat = path.stat()
    except OSError:
        return None
    cached = _ASSET_CACHE.get(token)
    if cached and cached[0] == int(stat.st_mtime_ns):
        data = cached[1]
    else:
        try:
            data = path.read_bytes()
        except OSError:
            return None
        _ASSET_CACHE[token] = (int(stat.st_mtime_ns), data)
    content_type = "text/css; charset=utf-8" if token.endswith(".css") else "application/javascript; charset=utf-8"
    return content_type, data


__all__ = [
    "CONTRACT_VERSION", "prewarm_api_runtime_async", "prewarm_status",
    "optimize_dashboard_html_assets", "load_dashboard_asset",
]
