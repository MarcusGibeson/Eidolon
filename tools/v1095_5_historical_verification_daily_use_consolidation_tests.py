from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

RESULTS: list[dict[str, object]] = []


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def check(name: str, fn) -> None:
    try:
        fn(); RESULTS.append({"name": name, "ok": True})
    except Exception as exc:
        RESULTS.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def main() -> int:
    from release_history import parse_release_history_file, parse_release_history_text, release_history_status
    from release_history_reconciliation import preview_release_history_reconciliation
    from release_metadata import RUNTIME_VERSION

    def current_history_and_registration_are_coherent() -> None:
        parsed = parse_release_history_file(ROOT / "README_RELEASE_HISTORY.md")
        require(parsed.get("ok"), parsed)
        entries = parsed.get("public_entries") or []
        require(entries and entries[0].get("version") == RUNTIME_VERSION, entries[:2])
        require(parsed.get("duplicate_version_count") == 0 and parsed.get("ordering_violation_count") == 0, parsed)
        require(sum(1 for row in entries if row.get("version") == "1095.5" and not row.get("range_end")) == 1, "v1095.5 history entry missing/duplicated")
        registry = (ROOT / "tools/post_review_development_verify.py").read_text(encoding="utf-8")
        for version in ("1095.3", "1095.4", "1095.5"):
            require(f"v{version}-" in registry, f"v{version} registration missing")
        require(registry.index("v1095.5-") < registry.index("v1095.4-") < registry.index("v1095.3-"), "registration order")

    def historical_checkpoints_use_shared_parser() -> None:
        for rel in (
            "tools/v1092_9_active_project_recovery_checkpoint_tests.py",
            "tools/v1093_9_metadata_reliability_checkpoint_tests.py",
            "tools/v1094_9_process_reliability_checkpoint_tests.py",
        ):
            source = (ROOT / rel).read_text(encoding="utf-8")
            require("parse_release_history_file" in source, f"{rel} bypasses shared parser")
            require("float(" not in source, f"{rel} uses float versions")

    def api_status_and_preview_are_content_free() -> None:
        import api_server
        status_code, response = api_server.dispatch_api("GET", "/api/release-history-status")
        require(status_code == 200 and response.get("ok"), response)
        data = response.get("data") or {}
        require(data.get("content_free") and data.get("provider_contacted") is False, data)
        status_code, response = api_server.dispatch_api("GET", "/api/release-history-reconciliation/preview")
        require(status_code == 200 and response.get("ok"), response)
        preview = response.get("data") or {}
        require(preview.get("status") == "already_aligned" and preview.get("preview_only"), preview)
        encoded = repr(response).lower()
        for forbidden in ("section_text", str(ROOT).lower(), "backup_path", "provider_payload"):
            require(forbidden not in encoded, forbidden)

    def api_apply_is_post_only_and_literal_confirmation_bound() -> None:
        import api_server
        status, response = api_server.dispatch_api("GET", "/api/release-history-reconciliation/preview")
        preview = response.get("data") or {}
        denied_status, denied = api_server.dispatch_api(
            "POST", "/api/release-history-reconciliation/apply",
            body={"preview_token": preview.get("preview_token"), "operator_confirmed": "true"},
        )
        require(denied_status == 409 and (denied.get("data") or {}).get("status") == "literal_confirmation_required", denied)
        ok_status, ok = api_server.dispatch_api(
            "POST", "/api/release-history-reconciliation/apply",
            body={"preview_token": preview.get("preview_token"), "operator_confirmed": True},
        )
        require(ok_status == 200 and (ok.get("data") or {}).get("status") == "already_aligned", ok)

    def dashboard_routes_are_get_read_only_and_post_mutating() -> None:
        source = (ROOT / "conscious_agent/dashboard.py").read_text(encoding="utf-8")
        get_at = source.index('if path == "/api/release-history-status"')
        preview_at = source.index('if path == "/api/release-history-reconciliation/preview"')
        post_at = source.index('if parsed.path == "/api/release-history-reconciliation/apply"')
        require(get_at < source.index("def do_POST") and preview_at < source.index("def do_POST"), "read routes not GET")
        require(post_at > source.index("def do_POST"), "apply route not POST")
        require("operator_confirmed=body.get(\"operator_confirmed\") is True" in source, "literal confirmation missing")

    def version_drift_uses_structured_history_status() -> None:
        from version_drift_reconciliation import build_version_drift_preview
        preview = build_version_drift_preview(ROOT)
        rows = {row.get("surface"): row for row in preview.get("rows") or []}
        require("release.history" in rows and rows["release.history"].get("ok"), rows.get("release.history"))
        require(rows["release.history"].get("duplicate_version_count") == 0, rows["release.history"])

    def long_mixed_history_is_bounded_and_ordered() -> None:
        text = "".join(
            ("##" if index % 2 else "#") + f" v3.{index} Entry {index}\nBody {index}\n"
            for index in range(300, -1, -1)
        )
        parsed = parse_release_history_text(text)
        require(parsed.get("ok") and parsed.get("entry_count") == 301, parsed)
        require(parsed.get("ordering_violation_count") == 0 and parsed.get("duplicate_version_count") == 0, parsed)
        require(len(parsed.get("public_entries") or []) == 301, "history truncated unexpectedly")

    def ordinary_conversation_remains_release_history_free() -> None:
        import project_manager
        ordinary = project_manager.project_context_text(limit_items=1, include_version_roles=False)
        for forbidden in ("Working-source version:", "Installed version:", "Candidate version:", "Packaged archive version:", "Release-history status:"):
            require(forbidden not in ordinary, ordinary)
        chat_source = (ROOT / "conscious_agent/chat.py").read_text(encoding="utf-8")
        runtime_source = (ROOT / "conscious_agent/conversation_runtime.py").read_text(encoding="utf-8")
        require("project_context_text(include_version_roles=False)" in chat_source, "chat version roles changed")
        require("project_context_text(include_version_roles=False)" in runtime_source, "runtime version roles changed")

    def current_status_is_provider_independent_and_non_authoritative() -> None:
        status = release_history_status(ROOT)
        require(status.get("provider_contacted") is False, status)
        require(status.get("installation_changed") is False and status.get("promotion_changed") is False and status.get("certification_performed") is False, status)
        docs = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
        require("v1150" in docs, "Codex schedule missing")

    def source_only_privacy_excludes_private_history_artifacts() -> None:
        forbidden = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix().lower()
            if "release_history_reconciliation/backups" in rel or rel.endswith(".bak") or ".history-" in rel:
                forbidden.append(rel)
        require(not forbidden, forbidden)

    checks = [
        ("current-history-registration-coherent", current_history_and_registration_are_coherent),
        ("historical-checkpoints-shared-parser", historical_checkpoints_use_shared_parser),
        ("api-status-preview-content-free", api_status_and_preview_are_content_free),
        ("api-apply-post-literal-confirmation", api_apply_is_post_only_and_literal_confirmation_bound),
        ("dashboard-route-authority", dashboard_routes_are_get_read_only_and_post_mutating),
        ("version-drift-structured-history", version_drift_uses_structured_history_status),
        ("long-mixed-history", long_mixed_history_is_bounded_and_ordered),
        ("ordinary-conversation-history-free", ordinary_conversation_remains_release_history_free),
        ("provider-independent-nonauthoritative", current_status_is_provider_independent_and_non_authoritative),
        ("source-only-private-history-artifacts", source_only_privacy_excludes_private_history_artifacts),
    ]
    for name, fn in checks:
        check(name, fn)
    passed = sum(bool(row.get("ok")) for row in RESULTS)
    print(json.dumps({"suite": "v1095.5-historical-verification-daily-use-consolidation", "passed": passed, "failed": len(RESULTS)-passed, "total": len(RESULTS), "checks": RESULTS}, indent=2))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
