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
RESULT_SPEC = ("eidolon.downstream.result", "1.0", "one bounded content-free render result")


def check(name, value):
    return {"name": name, "ok": bool(value)}


def setup(runtime_root: Path):
    make_receipt(runtime_root)
    patch_daily(daily, runtime_root)
    recovery.consumer_selection_status = daily.consumer_selection_status
    recovery.consumer_use_preflight_status = daily.consumer_use_preflight_status
    recovery.release_authority_consumer_daily_use_status = daily.release_authority_consumer_daily_use_status
    handoff.release_authority_consumer_daily_use_binding_status = recovery.release_authority_consumer_daily_use_binding_status
    sp = daily.preview_consumer_selection(*IDENTITY, PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
    daily.create_consumer_selection(sp["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
    pp = daily.preview_consumer_use_preflight(*IDENTITY, PURPOSE, *USE, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
    daily.create_consumer_use_preflight_receipt(pp["authorization_token"], confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
    hp = handoff.preview_consumer_use_handoff_plan(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
    plan = handoff.create_consumer_use_handoff_plan(hp["authorization_token"], confirm=handoff.PLAN_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], downstream_consumer_id=DOWNSTREAM[0], downstream_consumer_schema=DOWNSTREAM[1], downstream_consumer_version=DOWNSTREAM[2], downstream_expected_use=DOWNSTREAM[3], expected_result_schema=RESULT_SPEC[0], expected_result_version=RESULT_SPEC[1], expected_outcome=RESULT_SPEC[2], operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
    return plan


def result_for(plan):
    return {
        "result_id": "result-a", "result_schema": RESULT_SPEC[0], "result_version": RESULT_SPEC[1],
        "result_status": "completed", "output_sha256": "output-a",
        "handoff_plan_id": plan["handoff_plan_id"], "handoff_plan_sha256": plan["handoff_plan_sha256"],
        "downstream_consumer_id": DOWNSTREAM[0], "downstream_consumer_schema": DOWNSTREAM[1],
        "downstream_consumer_version": DOWNSTREAM[2], "downstream_expected_use": DOWNSTREAM[3],
        "content_free": True,
    }


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-8-") as temp:
        runtime_root = Path(temp)
        plan = setup(runtime_root)
        result = result_for(plan)
        missing = dict(result); missing["output_sha256"] = ""
        overclaim = dict(result); overclaim["certification_authorized"] = True
        private = dict(result); private["content"] = "secret"
        wrong_plan = dict(result); wrong_plan["handoff_plan_sha256"] = "wrong"
        missing_preview = handoff.preview_downstream_consumer_result_validation(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, missing, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        overclaim_preview = handoff.preview_downstream_consumer_result_validation(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, overclaim, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        private_preview = handoff.preview_downstream_consumer_result_validation(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, private, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        wrong_plan_preview = handoff.preview_downstream_consumer_result_validation(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, wrong_plan, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        preview = handoff.preview_downstream_consumer_result_validation(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, result, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        wrong_revision = handoff.create_downstream_consumer_result_validation_receipt(preview.get("authorization_token", ""), confirm=handoff.RESULT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], result=result, operator_tab_id="tab-a", operation_revision=5, runtime_root=runtime_root)
        interrupted = handoff.create_downstream_consumer_result_validation_receipt(preview.get("authorization_token", ""), confirm=handoff.RESULT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], result=result, operator_tab_id="tab-a", operation_revision=4, interrupt_after="receipt_written", runtime_root=runtime_root)
        created = handoff.create_downstream_consumer_result_validation_receipt(preview.get("authorization_token", ""), confirm=handoff.RESULT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], result=result, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        status = handoff.downstream_consumer_result_validation_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, runtime_root=runtime_root)
        replay = handoff.create_downstream_consumer_result_validation_receipt(preview.get("authorization_token", ""), confirm=handoff.RESULT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], result=result, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        duplicate = handoff.preview_downstream_consumer_result_validation(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, result, operator_tab_id="tab-a", operation_revision=6, runtime_root=runtime_root)
        drift_policy(runtime_root)
        drifted = handoff.downstream_consumer_result_validation_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, runtime_root=runtime_root)

        rows += [
            check("exact-result-fields-required", not missing_preview.get("ok")),
            check("authority-overclaim-rejected", not overclaim_preview.get("ok")),
            check("private-result-content-rejected", not private_preview.get("ok")),
            check("cross-plan-result-rejected", not wrong_plan_preview.get("ok")),
            check("exact-result-preview", preview.get("ok") and preview.get("literal_confirmation_required") == handoff.RESULT_CONFIRMATION),
            check("cross-revision-token-rejected", not wrong_revision.get("ok")),
            check("result-interruption-recorded", interrupted.get("status") == "downstream_result_validation_interrupted"),
            check("result-recovery-completed", created.get("ok") and created.get("result_recovery_performed")),
            check("immutable-result-current", status.get("ok") and status.get("result_validation_present")),
            check("single-use-result-token", not replay.get("ok")),
            check("duplicate-result-rejected", not duplicate.get("ok")),
            check("plan-policy-drift-detected", not drifted.get("ok") and drifted.get("result_validation_stale")),
            check("no-result-content-imported", not created.get("result_content_imported")),
            check("no-authority-or-future-use", not created.get("authority_granted") and not created.get("future_use_authorized")),
            check("consumer-not-executed", not created.get("downstream_consumer_executed")),
            check("content-free-path-suppressed", created.get("content_free") and str(runtime_root) not in json.dumps(created)),
        ]
    report = {"suite": "v1099.8-downstream-consumer-result-validation", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
