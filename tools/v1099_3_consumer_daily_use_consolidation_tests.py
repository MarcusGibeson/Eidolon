from __future__ import annotations
import importlib
import json
import tempfile
from pathlib import Path

from v1099_bundle_a_test_support import *
import release_authority_consumer_daily_use as daily


def check(name, value):
    return {"name": name, "ok": bool(value)}


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-3-") as temp:
        runtime_root = Path(temp)
        make_receipt(runtime_root)
        patch_daily(daily, runtime_root)
        selection_preview = daily.preview_consumer_selection(*IDENTITY, "operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        selection = daily.create_consumer_selection(selection_preview["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        use = ("release-status-card", "eidolon.consumer.use", "1.0", "render bounded content-free release status")
        preflight_preview = daily.preview_consumer_use_preflight(*IDENTITY, "operator command-deck display", *use, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        preflight = daily.create_consumer_use_preflight_receipt(preflight_preview["authorization_token"], confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", use_id=use[0], use_schema=use[1], use_version=use[2], declared_use=use[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        status = daily.release_authority_consumer_daily_use_status(*IDENTITY, "operator command-deck display", *use, runtime_root=runtime_root)
        repeat = daily.release_authority_consumer_daily_use_status(*IDENTITY, "operator command-deck display", *use, runtime_root=runtime_root)
        no_selection = daily.release_authority_consumer_daily_use_status(runtime_root=runtime_root)
        reloaded = importlib.reload(daily)
        patch_daily(reloaded, runtime_root)
        replay_selection = reloaded.create_consumer_selection(selection_preview["authorization_token"], confirm=reloaded.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose="operator command-deck display", operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        api_text = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
        verifier_text = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
        rows += [
            check("selection-created", selection.get("ok")),
            check("preflight-created", preflight.get("ok")),
            check("consolidated-coherent", status.get("ok") and status.get("status") == "release_authority_consumer_daily_use_coherent"),
            check("deterministic-status", status == repeat),
            check("explicit-no-selection-state", no_selection.get("ok") and no_selection.get("status") == "release_authority_consumer_not_selected"),
            check("restart-replay-rejected", not replay_selection.get("ok")),
            check("get-status-registered", "[\"release-authority\", \"consumer-daily-use\", \"status\"]" in api_text and "[\"release-authority\", \"consumer\", \"selection\", \"status\"]" in api_text and "[\"release-authority\", \"consumer\", \"use-preflight\", \"status\"]" in api_text),
            check("post-mutations-registered", "selection-preview" in api_text and "use-preflight" in api_text),
            check("verification-registered", "v1099_1_consumer_selection_pinning_tests.py" in verifier_text and "v1099_3_consumer_daily_use_consolidation_tests.py" in verifier_text),
            check("no-consumer-discovery", not status.get("consumer_discovery_performed")),
            check("no-newest-inference", not status.get("newest_consumer_inferred") and not status.get("newest_selection_inferred") and not status.get("newest_preflight_inferred")),
            check("content-free-path-suppressed", status.get("content_free") and str(runtime_root) not in json.dumps(status)),
            check("ordinary-conversation-preserved", not status.get("ordinary_conversation_affected")),
            check("provider-native-model-preserved", not status.get("provider_contacted") and not status.get("native_checks_run") and not status.get("models_mutated")),
            check("release-actions-not-performed", not status.get("installation_changed") and not status.get("promotion_changed") and not status.get("certification_changed") and not status.get("policy_migrated")),
            check("consumer-not-executed", not status.get("downstream_consumer_executed")),
        ]
    report = {"suite": "v1099.3-release-authority-consumer-daily-use-consolidation", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
