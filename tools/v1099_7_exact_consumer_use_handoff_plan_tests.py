from __future__ import annotations
import json
import tempfile
from pathlib import Path

from v1099_bundle_a_test_support import *
import release_authority_consumer_daily_use as daily
import release_authority_consumer_daily_use_recovery as recovery
import release_authority_consumer_use_handoff as handoff

USE = ("release-status-card", "eidolon.consumer.use", "1.0", "render bounded content-free release status")
PURPOSE = "operator command-deck display"
DOWNSTREAM = ("release-status-renderer", "eidolon.downstream.consumer", "1.0", "render one exact content-free status")
RESULT = ("eidolon.downstream.result", "1.0", "one bounded content-free render result")


def check(name, value):
    return {"name": name, "ok": bool(value)}


def create_daily_chain(runtime_root: Path):
    make_receipt(runtime_root)
    patch_daily(daily, runtime_root)
    recovery.consumer_selection_status = daily.consumer_selection_status
    recovery.consumer_use_preflight_status = daily.consumer_use_preflight_status
    recovery.release_authority_consumer_daily_use_status = daily.release_authority_consumer_daily_use_status
    handoff.release_authority_consumer_daily_use_binding_status = recovery.release_authority_consumer_daily_use_binding_status
    selection_preview = daily.preview_consumer_selection(*IDENTITY, PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
    daily.create_consumer_selection(selection_preview["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
    preflight_preview = daily.preview_consumer_use_preflight(*IDENTITY, PURPOSE, *USE, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
    daily.create_consumer_use_preflight_receipt(preflight_preview["authorization_token"], confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-7-") as temp:
        runtime_root = Path(temp)
        create_daily_chain(runtime_root)
        incomplete = handoff.preview_consumer_use_handoff_plan(*IDENTITY, PURPOSE, *USE, "", DOWNSTREAM[1], DOWNSTREAM[2], DOWNSTREAM[3], *RESULT, operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        preview = handoff.preview_consumer_use_handoff_plan(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT, operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        wrong_revision = handoff.create_consumer_use_handoff_plan(preview.get("authorization_token", ""), confirm=handoff.PLAN_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], downstream_consumer_id=DOWNSTREAM[0], downstream_consumer_schema=DOWNSTREAM[1], downstream_consumer_version=DOWNSTREAM[2], downstream_expected_use=DOWNSTREAM[3], expected_result_schema=RESULT[0], expected_result_version=RESULT[1], expected_outcome=RESULT[2], operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        interrupted = handoff.create_consumer_use_handoff_plan(preview.get("authorization_token", ""), confirm=handoff.PLAN_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], downstream_consumer_id=DOWNSTREAM[0], downstream_consumer_schema=DOWNSTREAM[1], downstream_consumer_version=DOWNSTREAM[2], downstream_expected_use=DOWNSTREAM[3], expected_result_schema=RESULT[0], expected_result_version=RESULT[1], expected_outcome=RESULT[2], operator_tab_id="tab-a", operation_revision=3, interrupt_after="plan_written", runtime_root=runtime_root)
        created = handoff.create_consumer_use_handoff_plan(preview.get("authorization_token", ""), confirm=handoff.PLAN_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], downstream_consumer_id=DOWNSTREAM[0], downstream_consumer_schema=DOWNSTREAM[1], downstream_consumer_version=DOWNSTREAM[2], downstream_expected_use=DOWNSTREAM[3], expected_result_schema=RESULT[0], expected_result_version=RESULT[1], expected_outcome=RESULT[2], operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        status = handoff.consumer_use_handoff_plan_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT, runtime_root=runtime_root)
        repeat = handoff.consumer_use_handoff_plan_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT, runtime_root=runtime_root)
        duplicate = handoff.preview_consumer_use_handoff_plan(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT, operator_tab_id="tab-a", operation_revision=5, runtime_root=runtime_root)
        replay = handoff.create_consumer_use_handoff_plan(preview.get("authorization_token", ""), confirm=handoff.PLAN_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], downstream_consumer_id=DOWNSTREAM[0], downstream_consumer_schema=DOWNSTREAM[1], downstream_consumer_version=DOWNSTREAM[2], downstream_expected_use=DOWNSTREAM[3], expected_result_schema=RESULT[0], expected_result_version=RESULT[1], expected_outcome=RESULT[2], operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        drift_policy(runtime_root)
        drifted = handoff.consumer_use_handoff_plan_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT, runtime_root=runtime_root)

        rows += [
            check("exact-downstream-declaration-required", not incomplete.get("ok")),
            check("handoff-preview-ready", preview.get("ok") and preview.get("literal_confirmation_required") == handoff.PLAN_CONFIRMATION),
            check("cross-revision-token-rejected", not wrong_revision.get("ok")),
            check("interruption-recorded", interrupted.get("status") == "consumer_use_handoff_plan_interrupted"),
            check("handoff-plan-recovered", created.get("ok") and created.get("handoff_recovery_performed")),
            check("immutable-plan-current", status.get("ok") and status.get("handoff_plan_present")),
            check("deterministic-status", status == repeat),
            check("duplicate-plan-preview-rejected", not duplicate.get("ok")),
            check("single-use-plan-token", not replay.get("ok")),
            check("policy-receipt-drift-detected", not drifted.get("ok") and drifted.get("handoff_plan_stale")),
            check("no-consumer-discovery", not created.get("consumer_discovery_performed")),
            check("no-newest-plan-inference", not created.get("newest_handoff_plan_inferred")),
            check("downstream-not-executed", not created.get("downstream_consumer_executed")),
            check("no-authority", not created.get("authority_granted") and not created.get("certification_authorized")),
            check("content-free-external", created.get("content_free") and created.get("records_external")),
            check("path-suppressed", str(runtime_root) not in json.dumps(created)),
        ]
    report = {"suite": "v1099.7-exact-consumer-use-handoff-plan", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
