from __future__ import annotations
import json
import tempfile
from pathlib import Path

from v1099_bundle_a_test_support import *
import release_authority_consumer_daily_use as daily


def check(name, value):
    return {"name": name, "ok": bool(value)}


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-1-") as temp:
        runtime_root = Path(temp)
        make_receipt(runtime_root)
        patch_daily(daily, runtime_root)
        preview = daily.preview_consumer_selection(*IDENTITY, "operator command-deck display", operator_tab_id="tab-a", operation_revision=1, selection_ttl_seconds=3600, runtime_root=runtime_root)
        wrong_confirm = daily.create_consumer_selection(preview.get("authorization_token", ""), confirm="yes", consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        cross_tab = daily.create_consumer_selection(preview.get("authorization_token", ""), confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-b", operation_revision=1, runtime_root=runtime_root)
        interrupted = daily.create_consumer_selection(preview.get("authorization_token", ""), confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=1, interrupt_after="selection_written", runtime_root=runtime_root)
        recovered = daily.create_consumer_selection(preview.get("authorization_token", ""), confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        status = daily.consumer_selection_status(*IDENTITY, "operator command-deck display", runtime_root=runtime_root)
        duplicate = daily.preview_consumer_selection(*IDENTITY, "operator command-deck display", operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        reused = daily.create_consumer_selection(preview.get("authorization_token", ""), confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        expired_record = expire_selection(runtime_root, daily)
        expired = daily.consumer_selection_status(*IDENTITY, "operator command-deck display", runtime_root=runtime_root)
        replacement_preview = daily.preview_consumer_selection(*IDENTITY, "operator command-deck display", operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        replacement = daily.create_consumer_selection(replacement_preview.get("authorization_token", ""), confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        with tempfile.TemporaryDirectory(prefix="eidolon-v1099-1-cross-") as other:
            cross_runtime = daily.create_consumer_selection(replacement_preview.get("authorization_token", ""), confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=3, runtime_root=Path(other))
        rows += [
            check("exact-selection-preview", preview.get("ok")),
            check("literal-confirmation-required", not wrong_confirm.get("ok")),
            check("cross-tab-rejected", not cross_tab.get("ok")),
            check("interruption-recorded", interrupted.get("status") == "consumer_selection_interrupted"),
            check("exact-recovery", recovered.get("ok") and recovered.get("selection_recovery_performed")),
            check("selection-current", status.get("ok") and status.get("selection_present")),
            check("required-scopes-pinned", status.get("required_scopes") == REQUIRED),
            check("unsupported-scopes-pinned", status.get("unsupported_scopes") == UNSUPPORTED),
            check("duplicate-preview-rejected", not duplicate.get("ok")),
            check("single-use-token", not reused.get("ok")),
            check("expiry-detected", expired.get("selection_expired") and not expired.get("ok")),
            check("preview-first-expiry-replacement", replacement_preview.get("ok") and replacement.get("ok")),
            check("cross-runtime-rejected", not cross_runtime.get("ok")),
            check("old-selection-preserved", bool(expired_record.get("selection_id"))),
            check("no-authority", not replacement.get("authority_granted") and not replacement.get("installation_authorized")),
            check("content-free-path-suppressed", str(runtime_root) not in json.dumps(replacement) and replacement.get("content_free")),
        ]
    report = {"suite": "v1099.1-exact-consumer-selection-pinning", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
