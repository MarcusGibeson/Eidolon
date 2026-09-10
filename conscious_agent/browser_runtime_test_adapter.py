from __future__ import annotations
"""Bounded Chromium runtime validation for isolated website workspaces.

v1206.3-v1206.5 executes only the already-materialized website inside a
loopback-only browser session. It records content-free evidence and grants no
apply, repair, provider, source, model, network, or release authority.
"""
import hashlib
import http.server
import os
import platform
import re
import shutil
import threading
import time
import urllib.parse
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_implementation_workspace import _record_path, _workspace_root, _verify_record
from isolated_workspace_preview import _preview_path
from browser_runtime_test_adapter_runtime_path import (
    SymbolDependencies as _BrowserRuntimeTestAdapterRuntimePathSymbolDependencies,
    _runtime_operation_path as _runtime_operation_path_implementation,
    _runtime_test_path as _runtime_test_path_implementation,
)
from browser_runtime_test_adapter_operation import (
    SymbolDependencies as _BrowserRuntimeTestAdapterOperationSymbolDependencies,
    _operation_valid as _operation_valid_implementation,
    _write_operation as _write_operation_implementation,
)



SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1206.8"
NAVIGATION_TIMEOUT_MS = 8_000
MAX_RUNTIME_ASSETS = 64
MAX_RUNTIME_TOTAL_BYTES = 4 * 1024 * 1024
MAX_BROWSER_LAUNCH_ATTEMPTS = 4
OPERATION_STALE_SECONDS = 30


def _build_browser_runtime_test_adapter_runtime_path_dependencies() -> _BrowserRuntimeTestAdapterRuntimePathSymbolDependencies:
    return _BrowserRuntimeTestAdapterRuntimePathSymbolDependencies(
        _store_root=_store_root,
    )

def _runtime_test_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _runtime_test_path_implementation(pid, rev, runtime_root, _deps=_build_browser_runtime_test_adapter_runtime_path_dependencies())




def _runtime_operation_path(pid: str, rev: int, runtime_root=None) -> Path:
    return _runtime_operation_path_implementation(pid, rev, runtime_root, _deps=_build_browser_runtime_test_adapter_runtime_path_dependencies())



def _platform_family() -> str:
    value = platform.system().lower()
    if value.startswith("win"):
        return "windows"
    if value == "darwin":
        return "macos"
    return "linux"


def _chromium_candidates(explicit: str | None = None) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    def add(source: str, value: str | None) -> None:
        if not value:
            return
        text = str(value)
        if text and all(existing != text for _, existing in rows):
            rows.append((source, text))
    add("explicit", explicit)
    add("environment", os.environ.get("EIDOLON_CHROMIUM_EXECUTABLE"))
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome", "msedge"):
        add("path", shutil.which(name))
    family = _platform_family()
    if family == "windows":
        roots = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")]
        suffixes = [r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe", r"Chromium\Application\chrome.exe"]
        for root in roots:
            for suffix in suffixes:
                add("platform_default", str(Path(root) / suffix) if root else None)
    elif family == "macos":
        add("platform_default", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        add("platform_default", "/Applications/Chromium.app/Contents/MacOS/Chromium")
    else:
        add("platform_default", "/usr/bin/chromium")
        add("platform_default", "/usr/bin/chromium-browser")
        add("platform_default", "/usr/bin/google-chrome")
    return rows[:MAX_BROWSER_LAUNCH_ATTEMPTS]


def _build_browser_runtime_test_adapter_operation_dependencies() -> _BrowserRuntimeTestAdapterOperationSymbolDependencies:
    return _BrowserRuntimeTestAdapterOperationSymbolDependencies(
        Mapping=Mapping,
        _atomic_json=_atomic_json,
        _digest=_digest,
    )

def _operation_valid(record: Mapping[str, Any]) -> bool:
    return _operation_valid_implementation(record, _deps=_build_browser_runtime_test_adapter_operation_dependencies())



def _write_operation(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return _write_operation_implementation(path, payload, _deps=_build_browser_runtime_test_adapter_operation_dependencies())


def _record_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("browser_runtime_test_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "browser_runtime_test_digest"}))


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:
        return


@contextmanager
def _loopback_server(root: Path):
    def factory(*args: Any, **kwargs: Any):
        return _QuietHandler(*args, directory=str(root), **kwargs)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _workspace_budget_ok(workspace: Mapping[str, Any]) -> bool:
    rows = list(workspace.get("files") or [])
    return len(rows) <= MAX_RUNTIME_ASSETS and sum(int(row.get("size_bytes") or 0) for row in rows) <= MAX_RUNTIME_TOTAL_BYTES


def run_or_resume_browser_runtime_test(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_workspace_digest: str,
    expected_preview_digest: str,
    runtime_root=None,
    chromium_executable: str | None = None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        workspace = _read_json(_record_path(proposal_id, expected_revision, runtime_root))
        preview = _read_json(_preview_path(proposal_id, expected_revision, runtime_root))
        if not workspace or not preview:
            return {"ok": False, "status": "workspace_or_preview_missing"}
        if workspace.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if workspace.get("workspace_digest") != expected_workspace_digest:
            return {"ok": False, "status": "stale_workspace_revision"}
        if preview.get("preview_digest") != expected_preview_digest or preview.get("workspace_digest") != expected_workspace_digest:
            return {"ok": False, "status": "stale_preview_revision"}
        root = _workspace_root(proposal_id, expected_revision, str(workspace.get("generation_digest") or ""), runtime_root)
        if not _verify_record(workspace, root):
            return {"ok": False, "status": "workspace_record_invalid"}
        if not _workspace_budget_ok(workspace):
            return {"ok": False, "status": "browser_runtime_budget_exceeded"}
        record_path = _runtime_test_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(record_path)
        if existing:
            bindings = existing.get("workspace_digest") == expected_workspace_digest and existing.get("preview_digest") == expected_preview_digest
            return ({**existing, "operation_status": "resumed"} if bindings and _record_valid(existing) else {"ok": False, "status": "browser_runtime_record_invalid"})

        operation_path = _runtime_operation_path(proposal_id, expected_revision, runtime_root)
        operation = _read_json(operation_path)
        recovery_count = 0
        if operation:
            if not _operation_valid(operation):
                return {"ok": False, "status": "browser_runtime_operation_invalid"}
            bindings = operation.get("workspace_digest") == expected_workspace_digest and operation.get("preview_digest") == expected_preview_digest
            if not bindings:
                return {"ok": False, "status": "stale_browser_runtime_operation"}
            if operation.get("phase") == "sealed":
                return {"ok": False, "status": "browser_runtime_result_missing"}
            age = max(0.0, time.time() - float(operation.get("updated_at_epoch") or 0.0))
            if age < OPERATION_STALE_SECONDS:
                return {"ok": False, "status": "browser_runtime_operation_in_progress"}
            recovery_count = int(operation.get("recovery_count") or 0) + 1
        operation = _write_operation(operation_path, {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "phase": "prepared",
            "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest, "workspace_digest": expected_workspace_digest,
            "preview_digest": expected_preview_digest, "attempt_count": int((operation or {}).get("attempt_count") or 0) + 1,
            "recovery_count": recovery_count, "updated_at_epoch": time.time(),
            "selected_project_modified": False, "authority_granted": False,
        })

        entrypoint = str(preview.get("entrypoint") or "")
        if not entrypoint or not (root / entrypoint).is_file():
            return {"ok": False, "status": "browser_entrypoint_missing"}

        console_digests: list[str] = []
        page_error_digests: list[str] = []
        failed_request_digests: list[str] = []
        blocked_request_count = 0
        popup_count = 0
        download_count = 0
        navigation_status = "not_started"
        dom_ready = False
        runtime_marker_present = False
        browser_source_class = "none"
        launch_attempt_count = 0
        launch_failure_digests: list[str] = []
        cleanup_confirmed = False
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser = None
                browser_source_class = "none"
                launch_attempt_count = 0
                launch_failure_digests: list[str] = []
                candidates = _chromium_candidates(chromium_executable)
                for source_class, executable in candidates:
                    launch_attempt_count += 1
                    try:
                        browser = playwright.chromium.launch(
                            executable_path=executable,
                            headless=True,
                            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-background-networking", "--disable-extensions", "--disable-sync", "--disable-component-update"],
                            timeout=NAVIGATION_TIMEOUT_MS,
                        )
                        browser_source_class = source_class
                        break
                    except Exception as launch_error:
                        launch_failure_digests.append(hashlib.sha256(type(launch_error).__name__.encode()).hexdigest())
                if browser is None:
                    raise RuntimeError("bounded_chromium_launch_failed")
                context = browser.new_context(service_workers="block", accept_downloads=False)
                page = context.new_page()
                page.set_default_timeout(NAVIGATION_TIMEOUT_MS)

                def digest_text(value: str) -> str:
                    return hashlib.sha256(str(value)[:4096].encode("utf-8", errors="replace")).hexdigest()

                with _loopback_server(root) as base_url:
                    def route_handler(route: Any) -> None:
                        nonlocal blocked_request_count
                        url = str(route.request.url)
                        if url == base_url or url.startswith(base_url + "/"):
                            route.continue_()
                        else:
                            blocked_request_count += 1
                            route.abort("blockedbyclient")

                    def popup_handler(popup: Any) -> None:
                        nonlocal popup_count
                        popup_count += 1
                        try:
                            popup.close()
                        except Exception:
                            pass

                    def download_handler(download: Any) -> None:
                        nonlocal download_count
                        download_count += 1
                        try:
                            download.cancel()
                        except Exception:
                            pass

                    context.route("**/*", route_handler)
                    page.on("console", lambda msg: console_digests.append(digest_text(f"{msg.type}:{msg.text}")))
                    page.on("pageerror", lambda error: page_error_digests.append(digest_text(str(error))))
                    page.on("requestfailed", lambda request: failed_request_digests.append(digest_text(str(request.url))))
                    page.on("popup", popup_handler)
                    page.on("download", download_handler)
                    try:
                        encoded_entrypoint = "/".join(urllib.parse.quote(part, safe="") for part in Path(entrypoint).parts)
                        page.goto(f"{base_url}/{encoded_entrypoint}", wait_until="load", timeout=NAVIGATION_TIMEOUT_MS)
                        navigation_status = "loaded"
                        dom_ready = page.evaluate("document.readyState === 'complete'") is True
                        runtime_marker_present = page.locator("[data-eidolon-runtime-ready], [data-runtime-ready]").count() > 0
                        page.wait_for_timeout(250)
                        popup_count = max(popup_count, len(page.context.pages) - 1)
                    finally:
                        context.close()
                        browser.close()
                        cleanup_confirmed = True
        except Exception as error:
            failure_digest = hashlib.sha256(type(error).__name__.encode()).hexdigest()
            record = {
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "ok": True,
                "status": "browser_runtime_test_failed",
                "passed": False,
                "reason_code": "browser_runtime_execution_failed",
                "failure_digest": failure_digest,
                "proposal_id": proposal_id,
                "proposal_revision": int(expected_revision),
                "proposal_revision_digest": expected_revision_digest,
                "workspace_digest": expected_workspace_digest,
                "preview_digest": expected_preview_digest,
                "browser_executed": launch_attempt_count > 0,
                "platform_family": _platform_family(),
                "browser_source_class": browser_source_class,
                "launch_attempt_count": launch_attempt_count,
                "launch_failure_digests": sorted(launch_failure_digests),
                "cleanup_confirmed": cleanup_confirmed,
                "operation_recovery_count": recovery_count,
                "network_allowed": False,
                "selected_project_modified": False,
                "source_modified": False,
                "apply_authorized": False,
                "repair_authorized": False,
                "release_authorized": False,
                "authority_granted": False,
            }
        else:
            passed = navigation_status == "loaded" and dom_ready and runtime_marker_present and not page_error_digests and popup_count == 0 and download_count == 0
            record = {
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "ok": True,
                "status": "browser_runtime_test_passed" if passed else "browser_runtime_test_failed",
                "passed": passed,
                "proposal_id": proposal_id,
                "proposal_revision": int(expected_revision),
                "proposal_revision_digest": expected_revision_digest,
                "planning_digest": workspace.get("planning_digest"),
                "generation_digest": workspace.get("generation_digest"),
                "workspace_digest": expected_workspace_digest,
                "preview_digest": expected_preview_digest,
                "navigation_status": navigation_status,
                "dom_ready": dom_ready,
                "runtime_marker_present": runtime_marker_present,
                "console_event_count": len(console_digests),
                "console_event_digests": sorted(console_digests),
                "page_error_count": len(page_error_digests),
                "page_error_digests": sorted(page_error_digests),
                "failed_request_count": len(failed_request_digests),
                "failed_request_digests": sorted(failed_request_digests),
                "blocked_external_request_count": blocked_request_count,
                "popup_count": popup_count,
                "download_count": download_count,
                "browser_executed": True,
                "platform_family": _platform_family(),
                "browser_source_class": browser_source_class,
                "launch_attempt_count": launch_attempt_count,
                "launch_failure_digests": sorted(launch_failure_digests),
                "cleanup_confirmed": cleanup_confirmed,
                "operation_recovery_count": recovery_count,
                "network_allowed": False,
                "selected_project_modified": False,
                "source_modified": False,
                "apply_authorized": False,
                "repair_authorized": False,
                "release_authorized": False,
                "authority_granted": False,
            }
        record["browser_runtime_test_digest"] = _digest(record)
        _atomic_json(record_path, record)
        _write_operation(operation_path, {**{k: v for k, v in operation.items() if k != "operation_digest"}, "phase": "sealed", "result_digest": record["browser_runtime_test_digest"], "updated_at_epoch": time.time()})
        return {**record, "operation_status": "created"}


def public_browser_runtime_test(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok", "status", "passed", "proposal_id", "proposal_revision", "workspace_digest", "preview_digest",
        "browser_runtime_test_digest", "navigation_status", "dom_ready", "runtime_marker_present",
        "console_event_count", "page_error_count", "failed_request_count", "blocked_external_request_count",
        "popup_count", "download_count", "browser_executed", "network_allowed", "selected_project_modified",
        "source_modified", "apply_authorized", "repair_authorized", "release_authorized", "authority_granted",
        "reason_code", "failure_digest", "platform_family", "browser_source_class", "launch_attempt_count",
        "cleanup_confirmed", "operation_recovery_count",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({"private_path_exposed": False, "private_content_exposed": False, "raw_browser_output_exposed": False})
    return public
