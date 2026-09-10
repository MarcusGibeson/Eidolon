from __future__ import annotations
"""v1337 real-browser validation for disposable candidate workspaces.

Browser validation is deliberately bounded: it can render a candidate-local HTML
artifact or navigate to a loopback-only HTTP(S) target, perform a small typed set
of UI interactions, run typed DOM checks, and capture screenshot evidence into
runtime-private storage. It never grants network, source-mutation, release, or
application authority. External network requests are aborted by routing policy.
"""
import hashlib
import re
import shutil
import time
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from ordinary_chat_development_campaign import _atomic_json, _read_json, _store_root
from standing_session_grants import standing_session_allows
from tool_preconditions import load_tool_preconditions
from workspace_isolation import _is_link_like, _record_path as _workspace_record_path, _within

CONTRACT_VERSION = "v1337.8"
TARGET_KINDS = ("offline_document", "loopback_url")
INTERACTION_KINDS = ("click", "fill", "press")
CHECK_KINDS = ("attached", "visible", "text_equals")
MAX_INTERACTIONS = 16
MAX_CHECKS = 32
MAX_SELECTOR_BYTES = 4096
MAX_INPUT_BYTES = 64 * 1024
MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT_MS = 4000
BROWSER_DENIED_AUTHORITY = {
    **DENIED_AUTHORITY,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
    "release_authorized": False,
    "network_authorized": False,
    "external_network_authorized": False,
}


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "phase4_browser_validation"


def _record_path(operation_id: str, runtime_root=None) -> Path:
    if not re.fullmatch(r"browser_[a-f0-9]{24}", str(operation_id or "")):
        raise ValueError("invalid_browser_validation_id")
    return _root(runtime_root) / "records" / f"{operation_id}.json"


def _load_sealed(path: Path) -> dict[str, Any]:
    row = _read_json(path)
    if not row or row.get("record_digest") != digest({k: v for k, v in row.items() if k != "record_digest"}):
        return {}
    return row


def _save(row: dict[str, Any], runtime_root=None) -> dict[str, Any]:
    row.pop("record_digest", None)
    row["record_digest"] = digest(row)
    _atomic_json(_record_path(str(row["browser_validation_id"]), runtime_root), row)
    return row


def _workspace(workspace_id: str, runtime_root=None) -> dict[str, Any]:
    row = _load_sealed(_workspace_record_path(workspace_id, runtime_root))
    if not row or row.get("cleaned") or not row.get("workspace_created"):
        return {}
    root = Path(str(row.get("candidate_private_path") or ""))
    if not root.is_dir() or _is_link_like(root):
        return {}
    return row


def _precondition(record_id: str, runtime_root=None) -> dict[str, Any]:
    row = load_tool_preconditions(str(record_id or ""), runtime_root=runtime_root, include_private=True)
    if not row or row.get("preconditions_satisfied") is not True or row.get("tool_code") != "browser" or row.get("tool_invoked") is not False:
        return {}
    return row


def _grant_ok(workspace: Mapping[str, Any], grant: Mapping[str, Any], now_unix: int | None) -> tuple[bool, str]:
    if str(grant.get("workspace_digest") or "") != str(workspace.get("source_workspace_digest") or ""):
        return False, "standing_grant_workspace_mismatch"
    if not standing_session_allows(grant, "command", now_unix=now_unix):
        return False, "active_command_grant_required"
    classes = set((grant.get("profile_snapshot") or {}).get("command_classes") or [])
    if not ({"browser", "shell", "process"} & classes):
        return False, "browser_command_class_required"
    return True, ""


def _candidate_file(workspace: Mapping[str, Any], relative: str) -> Path:
    root = Path(str(workspace.get("candidate_private_path") or "")).resolve(strict=True)
    pure = PurePosixPath(str(relative or "").replace("\\", "/").strip())
    if not pure.parts or pure.is_absolute() or any(p in {"", ".", ".."} for p in pure.parts):
        raise ValueError("unsafe_browser_artifact_path")
    current = root
    for part in pure.parts:
        current = current / part
        if current.exists() and _is_link_like(current):
            raise ValueError("browser_artifact_link_or_junction_rejected")
    resolved = current.resolve(strict=True)
    if not resolved.is_file() or not _within(root, resolved):
        raise ValueError("browser_artifact_outside_candidate")
    return resolved


def _loopback(url: str) -> bool:
    try:
        parsed = urlparse(str(url or ""))
        return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}
    except Exception:
        return False


def _bounded_text(value: Any, *, limit: int, code: str) -> str:
    text = str(value or "")
    if not text or len(text.encode("utf-8")) > limit or "\x00" in text:
        raise ValueError(code)
    return text


def _typed_interactions(items: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if len(items) > MAX_INTERACTIONS:
        raise ValueError("browser_interaction_budget_exceeded")
    rows: list[dict[str, str]] = []
    for raw in items:
        op = str(raw.get("op") or "")
        if op not in INTERACTION_KINDS:
            raise ValueError("browser_interaction_kind_invalid")
        selector = _bounded_text(raw.get("selector"), limit=MAX_SELECTOR_BYTES, code="browser_selector_invalid")
        row = {"op": op, "selector": selector}
        if op in {"fill", "press"}:
            row["value"] = _bounded_text(raw.get("value"), limit=MAX_INPUT_BYTES, code="browser_interaction_value_invalid")
        rows.append(row)
    return rows


def _typed_checks(items: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if len(items) > MAX_CHECKS:
        raise ValueError("browser_check_budget_exceeded")
    rows: list[dict[str, str]] = []
    for raw in items:
        kind = str(raw.get("kind") or "")
        if kind not in CHECK_KINDS:
            raise ValueError("browser_check_kind_invalid")
        selector = _bounded_text(raw.get("selector"), limit=MAX_SELECTOR_BYTES, code="browser_selector_invalid")
        row = {"kind": kind, "selector": selector}
        if kind == "text_equals":
            row["expected"] = _bounded_text(raw.get("expected"), limit=MAX_INPUT_BYTES, code="browser_expected_text_invalid")
        rows.append(row)
    return rows


def _public(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "browser_validation_id": row.get("browser_validation_id"),
        "workspace_id": row.get("workspace_id"),
        "source_workspace_digest": row.get("source_workspace_digest"),
        "precondition_record_id": row.get("precondition_record_id"),
        "grant_digest": row.get("grant_digest"),
        "target_kind": row.get("target_kind"),
        "target_digest": row.get("target_digest"),
        "interaction_count": int(row.get("interaction_count") or 0),
        "interaction_digest": row.get("interaction_digest"),
        "check_count": int(row.get("check_count") or 0),
        "check_digest": row.get("check_digest"),
        "browser_executable_digest": row.get("browser_executable_digest"),
        "browser_launched": row.get("browser_launched") is True,
        "page_rendered": row.get("page_rendered") is True,
        "loopback_navigation_attempted": row.get("loopback_navigation_attempted") is True,
        "loopback_navigation_validated": row.get("loopback_navigation_validated") is True,
        "offline_fallback_rendered": row.get("offline_fallback_rendered") is True,
        "external_requests_blocked": int(row.get("external_requests_blocked") or 0),
        "console_error_count": int(row.get("console_error_count") or 0),
        "checks_passed": int(row.get("checks_passed") or 0),
        "checks_failed": int(row.get("checks_failed") or 0),
        "screenshot_captured": row.get("screenshot_captured") is True,
        "screenshot_bytes": int(row.get("screenshot_bytes") or 0),
        "screenshot_digest": row.get("screenshot_digest") or "",
        "failure_domain": row.get("failure_domain") or "",
        "failure_code": row.get("failure_code") or "",
        "validation_status": row.get("validation_status") or "unknown",
        "raw_url_exposed": False,
        "raw_selector_exposed": False,
        "interaction_values_exposed": False,
        "screenshot_path_exposed": False,
        "selected_source_modified": False,
        "candidate_workspace_only": True,
        "content_free": True,
        "action_executed": row.get("browser_launched") is True,
        **BROWSER_DENIED_AUTHORITY,
    }


def validate_browser_candidate(
    workspace_id: str,
    *,
    target: Mapping[str, Any],
    active_grant: Mapping[str, Any],
    precondition_record_id: str,
    interactions: Sequence[Mapping[str, Any]] = (),
    checks: Sequence[Mapping[str, Any]] = (),
    browser_executable: str | None = None,
    fallback_html_relative_path: str | None = None,
    runtime_root=None,
    now_unix: int | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> dict[str, Any]:
    """Run one bounded real-browser validation. External URLs are rejected."""
    workspace = _workspace(str(workspace_id or ""), runtime_root)
    pre = _precondition(str(precondition_record_id or ""), runtime_root)
    if not workspace:
        return {"ok": False, "status": "candidate_workspace_required", "action_executed": False, **BROWSER_DENIED_AUTHORITY}
    if not pre:
        return {"ok": False, "status": "satisfied_browser_precondition_required", "action_executed": False, **BROWSER_DENIED_AUTHORITY}
    grant_ok, reason = _grant_ok(workspace, active_grant, now_unix)
    if not grant_ok:
        return {"ok": False, "status": reason, "action_executed": False, **BROWSER_DENIED_AUTHORITY}

    kind = str(target.get("kind") or "")
    if kind not in TARGET_KINDS:
        return {"ok": False, "status": "browser_target_kind_invalid", "action_executed": False, **BROWSER_DENIED_AUTHORITY}
    try:
        typed_interactions = _typed_interactions(interactions)
        typed_checks = _typed_checks(checks)
        offline_file: Path | None = None
        fallback_file: Path | None = None
        target_material: dict[str, Any]
        if kind == "offline_document":
            offline_file = _candidate_file(workspace, str(target.get("html_relative_path") or ""))
            target_material = {"kind": kind, "artifact_digest": hashlib.sha256(offline_file.read_bytes()).hexdigest()}
        else:
            url = str(target.get("url") or "")
            if not _loopback(url):
                return {"ok": False, "status": "external_browser_target_rejected", "action_executed": False, **BROWSER_DENIED_AUTHORITY}
            target_material = {"kind": kind, "url_digest": hashlib.sha256(url.encode("utf-8")).hexdigest()}
            if fallback_html_relative_path:
                fallback_file = _candidate_file(workspace, fallback_html_relative_path)
                target_material["fallback_digest"] = hashlib.sha256(fallback_file.read_bytes()).hexdigest()
    except (OSError, ValueError) as error:
        return {"ok": False, "status": str(error), "action_executed": False, **BROWSER_DENIED_AUTHORITY}

    timeout = max(250, min(30000, int(timeout_ms)))
    executable = str(browser_executable or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome") or "")
    op_id = "browser_" + digest({
        "contract": CONTRACT_VERSION,
        "workspace": workspace_id,
        "target": target_material,
        "interactions": typed_interactions,
        "checks": typed_checks,
        "precondition": precondition_record_id,
        "grant": active_grant.get("grant_digest"),
        "browser": executable,
    })[:24]
    existing = _load_sealed(_record_path(op_id, runtime_root))
    if existing:
        return {"ok": existing.get("validation_status") == "passed", "status": "browser_validation_duplicate", "browser_validation": _public(existing), "action_executed": False, **BROWSER_DENIED_AUTHORITY}

    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "browser_validation_id": op_id,
        "workspace_id": workspace_id,
        "source_workspace_digest": workspace.get("source_workspace_digest"),
        "precondition_record_id": precondition_record_id,
        "grant_digest": active_grant.get("grant_digest"),
        "target_kind": kind,
        "target_digest": digest(target_material),
        "interaction_count": len(typed_interactions),
        "interaction_digest": digest(typed_interactions),
        "check_count": len(typed_checks),
        "check_digest": digest(typed_checks),
        "browser_executable_digest": hashlib.sha256(executable.encode("utf-8")).hexdigest() if executable else "",
        "browser_launched": False,
        "page_rendered": False,
        "loopback_navigation_attempted": False,
        "loopback_navigation_validated": False,
        "offline_fallback_rendered": False,
        "external_requests_blocked": 0,
        "console_error_count": 0,
        "checks_passed": 0,
        "checks_failed": 0,
        "screenshot_captured": False,
        "screenshot_bytes": 0,
        "screenshot_digest": "",
        "failure_domain": "",
        "failure_code": "",
        "validation_status": "running",
        "created_unix": int(time.time() if now_unix is None else now_unix),
        **BROWSER_DENIED_AUTHORITY,
    }
    if not executable or not Path(executable).is_file():
        row.update(validation_status="failed", failure_domain="browser_tool", failure_code="browser_executable_unavailable")
        _save(row, runtime_root)
        return {"ok": False, "status": "browser_tool_failure", "browser_validation": _public(row), "action_executed": False, **BROWSER_DENIED_AUTHORITY}

    screenshot_dir = _root(runtime_root) / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"{op_id}.png"
    console_errors: list[bool] = []
    blocked_external = [0]
    browser = None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, executable_path=executable, args=["--no-sandbox", "--disable-dev-shm-usage"])
            row["browser_launched"] = True
            context = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
            page = context.new_page()
            page.set_default_timeout(timeout)
            page.on("console", lambda msg: console_errors.append(True) if msg.type == "error" else None)
            def route_handler(route):
                request_url = route.request.url
                parsed = urlparse(request_url)
                allowed = parsed.scheme in {"data", "about", "blob"} or (parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in {"127.0.0.1", "localhost", "::1"})
                if allowed:
                    route.continue_()
                else:
                    blocked_external[0] += 1
                    route.abort()
            context.route("**/*", route_handler)

            policy_limited = False
            if kind == "offline_document":
                page.set_content(offline_file.read_text(encoding="utf-8"), wait_until="domcontentloaded", timeout=timeout)
                row["page_rendered"] = True
            else:
                row["loopback_navigation_attempted"] = True
                try:
                    response = page.goto(str(target.get("url")), wait_until="domcontentloaded", timeout=timeout)
                    row["page_rendered"] = True
                    row["loopback_navigation_validated"] = bool(response is None or response.status < 500)
                    if response is not None and response.status >= 500:
                        row.update(failure_domain="product_runtime", failure_code="loopback_http_server_error")
                except Exception as nav_error:
                    text = str(nav_error)
                    if "ERR_BLOCKED_BY_ADMINISTRATOR" in text or "blocked by administrator" in text.lower():
                        policy_limited = True
                        row.update(failure_domain="browser_policy", failure_code="managed_navigation_policy_blocked")
                        if fallback_file is not None:
                            # A policy-aborted navigation can destroy the page's
                            # execution context. Use a fresh page in the same real
                            # browser/context for the bounded offline engine check.
                            try:
                                page.close()
                            except Exception:
                                pass
                            page = context.new_page()
                            page.set_default_timeout(timeout)
                            page.on("console", lambda msg: console_errors.append(True) if msg.type == "error" else None)
                            page.set_content(fallback_file.read_text(encoding="utf-8"), wait_until="domcontentloaded", timeout=timeout)
                            row["page_rendered"] = True
                            row["offline_fallback_rendered"] = True
                    else:
                        row.update(failure_domain="browser_tool", failure_code="loopback_navigation_failed")

            if row["page_rendered"]:
                # A policy-blocked loopback target was never loaded. The offline
                # fallback proves the real browser engine can render/capture, but
                # running target-specific interactions/checks against that fallback
                # would incorrectly convert a browser-policy limitation into a
                # product UI failure.
                if not policy_limited:
                    for item in typed_interactions:
                        locator = page.locator(item["selector"]).first
                        if item["op"] == "click": locator.click(timeout=timeout)
                        elif item["op"] == "fill": locator.fill(item["value"], timeout=timeout)
                        elif item["op"] == "press": locator.press(item["value"], timeout=timeout)
                    passed = failed = 0
                    for item in typed_checks:
                        locator = page.locator(item["selector"]).first
                        if item["kind"] == "attached": ok = locator.count() > 0
                        elif item["kind"] == "visible": ok = locator.count() > 0 and locator.is_visible(timeout=timeout)
                        else: ok = locator.count() > 0 and (locator.text_content(timeout=timeout) or "") == item["expected"]
                        passed += int(ok); failed += int(not ok)
                    row["checks_passed"] = passed
                    row["checks_failed"] = failed
                    if failed and not row["failure_domain"]:
                        row.update(failure_domain="product_ui", failure_code="dom_check_failed")
                page.screenshot(path=str(screenshot_path), full_page=True)
                data = screenshot_path.read_bytes()
                if len(data) > MAX_SCREENSHOT_BYTES:
                    screenshot_path.unlink(missing_ok=True)
                    row.update(failure_domain="browser_tool", failure_code="screenshot_budget_exceeded")
                else:
                    row.update(screenshot_captured=True, screenshot_bytes=len(data), screenshot_digest=hashlib.sha256(data).hexdigest())
            row["console_error_count"] = len(console_errors)
            row["external_requests_blocked"] = blocked_external[0]
            if row["failure_domain"] == "browser_policy" and policy_limited:
                row["validation_status"] = "policy_limited"
            elif row["failure_domain"]:
                row["validation_status"] = "failed"
            else:
                row["validation_status"] = "passed"
            context.close(); browser.close(); browser = None
    except Exception as error:
        code = "browser_runtime_failed"
        if row.get("page_rendered"):
            row.update(failure_domain="product_ui", failure_code="browser_interaction_failed")
        else:
            row.update(failure_domain="browser_tool", failure_code=code)
        row["validation_status"] = "failed"
    finally:
        try:
            if browser is not None: browser.close()
        except Exception:
            pass

    _save(row, runtime_root)
    public = _public(row)
    ok = row.get("validation_status") == "passed"
    status = "browser_validation_passed" if ok else "browser_validation_policy_limited" if row.get("validation_status") == "policy_limited" else "browser_validation_failed"
    return {"ok": ok, "status": status, "browser_validation": public, "action_executed": row.get("browser_launched") is True, **BROWSER_DENIED_AUTHORITY}


def load_browser_validation(operation_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _load_sealed(_record_path(str(operation_id), runtime_root))
    return _public(row) if row else {}


def process_browser_validation_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show browser validation", "inspect browser validation", "show browser evidence"}:
        return {"active": False}
    operation_id = str((project_state or {}).get("browser_validation_id") or "")
    row = load_browser_validation(operation_id, runtime_root=runtime_root) if operation_id else {}
    return {"active": True, "ok": bool(row), "status": "browser_validation_found" if row else "browser_validation_missing", "browser_validation": row, "action_executed": False, **BROWSER_DENIED_AUTHORITY}


__all__ = [
    "CONTRACT_VERSION", "TARGET_KINDS", "INTERACTION_KINDS", "CHECK_KINDS", "BROWSER_DENIED_AUTHORITY",
    "validate_browser_candidate", "load_browser_validation", "process_browser_validation_control",
]
