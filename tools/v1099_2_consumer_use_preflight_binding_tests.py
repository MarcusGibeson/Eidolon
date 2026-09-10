from __future__ import annotations
import json
import tempfile
from pathlib import Path

from v1099_bundle_a_test_support import *
import release_authority_consumer_daily_use as daily


def check(name, value):
    return {"name": name, "ok": bool(value)}


def create_selection(runtime_root: Path):
    preview = daily.preview_consumer_selection(*IDENTITY, "operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
    return daily.create_consumer_selection(preview["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-2-") as temp:
        runtime_root = Path(temp)
        make_receipt(runtime_root)
        patch_daily(daily, runtime_root)
        selection = create_selection(runtime_root)
        use = ("release-status-card", "eidolon.consumer.use", "1.0", "render bounded content-free release status")
        overclaim = daily.preview_consumer_use_preflight(*IDENTITY, "operator command-deck display", *use, ["general_release", "promotion"], UNSUPPORTED, scope_sources={"general_release": "general_release", "promotion": "promotion"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        inferred = daily.preview_consumer_use_preflight(*IDENTITY, "operator command-deck display", *use, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "promotion"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        preview = daily.preview_consumer_use_preflight(*IDENTITY, "operator command-deck display", *use, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        wrong_revision = daily.create_consumer_use_preflight_receipt(preview.get("authorization_token", ""), confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", use_id=use[0], use_schema=use[1], use_version=use[2], declared_use=use[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        interrupted = daily.create_consumer_use_preflight_receipt(preview.get("authorization_token", ""), confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", use_id=use[0], use_schema=use[1], use_version=use[2], declared_use=use[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, interrupt_after="receipt_written", runtime_root=runtime_root)
        recovered = daily.create_consumer_use_preflight_receipt(preview.get("authorization_token", ""), confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", use_id=use[0], use_schema=use[1], use_version=use[2], declared_use=use[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        status = daily.consumer_use_preflight_status(*IDENTITY, "operator command-deck display", *use, runtime_root=runtime_root)
        duplicate = daily.preview_consumer_use_preflight(*IDENTITY, "operator command-deck display", *use, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        replay = daily.create_consumer_use_preflight_receipt(preview.get("authorization_token", ""), confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", use_id=use[0], use_schema=use[1], use_version=use[2], declared_use=use[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        drift_policy(runtime_root)
        drifted = daily.consumer_use_preflight_status(*IDENTITY, "operator command-deck display", *use, runtime_root=runtime_root)
        rows += [
            check("selection-required-and-current", selection.get("ok")),
            check("scope-overclaim-rejected", not overclaim.get("ok")),
            check("cross-scope-inference-rejected", not inferred.get("ok")),
            check("exact-use-preflight-preview", preview.get("ok")),
            check("revision-binding-rejected", not wrong_revision.get("ok")),
            check("interruption-recorded", interrupted.get("status") == "consumer_use_preflight_interrupted"),
            check("exact-preflight-recovery", recovered.get("ok") and recovered.get("preflight_recovery_performed")),
            check("preflight-current", status.get("ok") and status.get("preflight_present")),
            check("required-scopes-bound", status.get("required_scopes") == REQUIRED),
            check("unsupported-scopes-bound", status.get("unsupported_scopes") == UNSUPPORTED),
            check("duplicate-preflight-rejected", not duplicate.get("ok")),
            check("single-use-preflight-token", not replay.get("ok")),
            check("policy-and-receipt-drift-detected", not drifted.get("ok") and drifted.get("preflight_stale")),
            check("consumer-not-executed", not recovered.get("downstream_consumer_executed")),
            check("no-authority", not recovered.get("authority_granted") and not recovered.get("certification_authorized")),
            check("content-free-path-suppressed", str(runtime_root) not in json.dumps(recovered) and recovered.get("content_free")),
        ]
    report = {"suite": "v1099.2-exact-consumer-use-preflight-binding", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
