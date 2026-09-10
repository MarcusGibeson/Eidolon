from __future__ import annotations
import importlib
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
    selection = daily.create_consumer_selection(sp["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
    pp = daily.preview_consumer_use_preflight(*IDENTITY, PURPOSE, *USE, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
    preflight = daily.create_consumer_use_preflight_receipt(pp["authorization_token"], confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
    hp = handoff.preview_consumer_use_handoff_plan(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
    plan = handoff.create_consumer_use_handoff_plan(hp["authorization_token"], confirm=handoff.PLAN_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], downstream_consumer_id=DOWNSTREAM[0], downstream_consumer_schema=DOWNSTREAM[1], downstream_consumer_version=DOWNSTREAM[2], downstream_expected_use=DOWNSTREAM[3], expected_result_schema=RESULT_SPEC[0], expected_result_version=RESULT_SPEC[1], expected_outcome=RESULT_SPEC[2], operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
    result = {
        "result_id": "result-a", "result_schema": RESULT_SPEC[0], "result_version": RESULT_SPEC[1],
        "result_status": "completed", "output_sha256": "output-a",
        "handoff_plan_id": plan["handoff_plan_id"], "handoff_plan_sha256": plan["handoff_plan_sha256"],
        "downstream_consumer_id": DOWNSTREAM[0], "downstream_consumer_schema": DOWNSTREAM[1],
        "downstream_consumer_version": DOWNSTREAM[2], "downstream_expected_use": DOWNSTREAM[3],
        "content_free": True,
    }
    rp = handoff.preview_downstream_consumer_result_validation(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, result, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
    receipt = handoff.create_downstream_consumer_result_validation_receipt(rp["authorization_token"], confirm=handoff.RESULT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], result=result, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
    return selection, preflight, plan, receipt, rp, result


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-9-") as temp:
        runtime_root = Path(temp)
        selection, preflight, plan, receipt, result_preview, result = setup(runtime_root)
        status = handoff.release_authority_consumer_use_lifecycle_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, runtime_root=runtime_root)
        repeat = handoff.release_authority_consumer_use_lifecycle_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, runtime_root=runtime_root)
        no_selection = handoff.release_authority_consumer_use_lifecycle_status(runtime_root=runtime_root)
        reloaded = importlib.reload(handoff)
        reloaded.release_authority_consumer_daily_use_binding_status = recovery.release_authority_consumer_daily_use_binding_status
        after_restart = reloaded.release_authority_consumer_use_lifecycle_status(*IDENTITY, PURPOSE, *USE, *DOWNSTREAM, *RESULT_SPEC, runtime_root=runtime_root)
        replay = reloaded.create_downstream_consumer_result_validation_receipt(result_preview["authorization_token"], confirm=reloaded.RESULT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], result=result, operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)

        api_text = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
        dashboard_text = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        verifier_text = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
        release_verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")

        rows += [
            check("selection-preflight-plan-result-created", selection.get("ok") and preflight.get("ok") and plan.get("ok") and receipt.get("ok")),
            check("consumer-use-lifecycle-coherent", status.get("ok") and status.get("status") == "release_authority_consumer_use_lifecycle_coherent"),
            check("plan-and-result-present", status.get("handoff_plan_present") and status.get("result_validation_present")),
            check("deterministic-content-free-status", status == repeat and status.get("content_free")),
            check("restart-status-stable", after_restart.get("ok") and after_restart.get("result_validation_id") == status.get("result_validation_id")),
            check("restart-result-replay-rejected", not replay.get("ok")),
            check("explicit-not-selected-state", no_selection.get("ok") and no_selection.get("status") == "consumer_use_lifecycle_not_selected"),
            check("get-handoff-result-lifecycle-registered", '["release-authority", "consumer-use-handoff", "status"]' in api_text and '["release-authority", "consumer", "result-validation", "status"]' in api_text and '["release-authority", "consumer-use-lifecycle", "status"]' in api_text),
            check("post-handoff-result-registered", '["release-authority", "consumer-use-handoff", "preview"]' in api_text and '["release-authority", "consumer", "result-validation", "create"]' in api_text),
            check("exact-tab-revision-no-default", 'operator_tab_id=str(body.get("operator_tab_id") or "")' in api_text and 'operation_revision=int(body.get("operation_revision") or 0)' in api_text),
            check("dashboard-content-free-registration", "consumer_use_lifecycle" in dashboard_text and "Consumer use handoff and downstream result validation" in dashboard_text),
            check("focused-verifier-registration", "v1099_7_exact_consumer_use_handoff_plan_tests.py" in verifier_text and "v1099_9_consumer_use_lifecycle_consolidation_tests.py" in verifier_text),
            check("release-verifier-registration", "v1099.9-consumer-use-lifecycle-consolidation" in release_verifier),
            check("no-discovery-newest-or-execution", not status.get("consumer_discovery_performed") and not status.get("newest_handoff_plan_inferred") and not status.get("newest_result_inferred") and not status.get("downstream_consumer_executed")),
            check("no-authority-or-release-action", not status.get("authority_granted") and not status.get("installation_changed") and not status.get("promotion_changed") and not status.get("certification_changed") and not status.get("policy_migrated")),
            check("ordinary-provider-native-preserved", not status.get("ordinary_conversation_affected") and not status.get("provider_contacted") and not status.get("native_checks_run") and not status.get("models_mutated")),
        ]
    report = {"suite": "v1099.9-consumer-use-lifecycle-consolidation", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
