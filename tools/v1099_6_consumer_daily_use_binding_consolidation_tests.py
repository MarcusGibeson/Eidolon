from __future__ import annotations
import importlib
import json
import tempfile
from pathlib import Path

from v1099_bundle_a_test_support import *
import release_authority_consumer_daily_use as daily
import release_authority_consumer_daily_use_recovery as recovery

USE = ("release-status-card", "eidolon.consumer.use", "1.0", "render bounded content-free release status")
PURPOSE = "operator command-deck display"


def check(name, value):
    return {"name": name, "ok": bool(value)}


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-6-") as temp:
        runtime_root = Path(temp)
        make_receipt(runtime_root)
        patch_daily(daily, runtime_root)
        recovery.consumer_selection_status = daily.consumer_selection_status
        recovery.consumer_use_preflight_status = daily.consumer_use_preflight_status
        recovery.release_authority_consumer_daily_use_status = daily.release_authority_consumer_daily_use_status

        selection_preview = daily.preview_consumer_selection(*IDENTITY, PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        selection = daily.create_consumer_selection(selection_preview["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        preflight_preview = daily.preview_consumer_use_preflight(*IDENTITY, PURPOSE, *USE, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        preflight = daily.create_consumer_use_preflight_receipt(preflight_preview["authorization_token"], confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)

        status = recovery.release_authority_consumer_daily_use_binding_status(*IDENTITY, PURPOSE, *USE, runtime_root=runtime_root)
        repeat = recovery.release_authority_consumer_daily_use_binding_status(*IDENTITY, PURPOSE, *USE, runtime_root=runtime_root)
        no_selection = recovery.release_authority_consumer_daily_use_binding_status(runtime_root=runtime_root)
        reloaded = importlib.reload(recovery)
        reloaded.consumer_selection_status = daily.consumer_selection_status
        reloaded.consumer_use_preflight_status = daily.consumer_use_preflight_status
        reloaded.release_authority_consumer_daily_use_status = daily.release_authority_consumer_daily_use_status
        after_restart = reloaded.release_authority_consumer_daily_use_binding_status(*IDENTITY, PURPOSE, *USE, runtime_root=runtime_root)

        api_text = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
        dashboard_text = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        verifier_text = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
        release_verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")

        rows += [
            check("selection-created", selection.get("ok")),
            check("preflight-created", preflight.get("ok")),
            check("consolidated-binding-coherent", status.get("ok") and status.get("status") == "release_authority_consumer_daily_use_binding_coherent"),
            check("deterministic-content-free-status", status == repeat and status.get("content_free")),
            check("restart-status-stable", after_restart.get("ok") and after_restart.get("selection_id") == status.get("selection_id")),
            check("explicit-not-selected-state", no_selection.get("ok") and no_selection.get("status") == "consumer_daily_use_binding_not_selected"),
            check("get-status-registered", '["release-authority", "consumer-daily-use-binding", "status"]' in api_text and '["release-authority", "consumer", "daily-use-recovery", "status"]' in api_text),
            check("post-recovery-registered", "daily-use-recovery" in api_text and "daily-use-replacement" in api_text),
            check("post-cleanup-successor-registered", "daily-use-cleanup" in api_text and "successor-revalidation" in api_text),
            check("exact-tab-revision-required", 'operator_tab_id=str(body.get("operator_tab_id") or "")' in api_text and 'operation_revision=int(body.get("operation_revision") or 0)' in api_text),
            check("dashboard-content-free-registration", "consumer_daily_use_binding" in dashboard_text and "Consumer binding recovery and successor revalidation" in dashboard_text),
            check("development-verifier-registration", "v1099_4_consumer_daily_use_recovery_tests.py" in verifier_text and "v1099_6_consumer_daily_use_binding_consolidation_tests.py" in verifier_text),
            check("release-verifier-registration", "v1099.6-consumer-daily-use-binding-consolidation" in release_verifier),
            check("no-consumer-discovery-or-newest-inference", not status.get("consumer_discovery_performed") and not status.get("newest_consumer_inferred") and not status.get("newest_selection_inferred")),
            check("no-authority-or-consumer-execution", not status.get("authority_granted") and not status.get("consumer_executed")),
            check("ordinary-provider-native-preserved", not status.get("ordinary_conversation_affected") and not status.get("provider_contacted") and not status.get("native_checks_run") and not status.get("models_mutated")),
        ]
    report = {"suite": "v1099.6-consumer-daily-use-binding-consolidation", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
