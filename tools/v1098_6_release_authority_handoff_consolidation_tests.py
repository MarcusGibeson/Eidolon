from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from v1098_bundle_a_test_support import file_snapshot, prepare_ready_fixture
from release_authority_readiness_recovery import refresh_release_authority_readiness
from release_authority_handoff_plan import (
    HANDOFF_ACK_CONFIRMATION,
    acknowledge_release_authority_handoff_plan,
    create_release_authority_handoff_plan,
    preview_release_authority_handoff_acknowledgment,
    release_authority_handoff_acknowledgment_status,
)
from release_authority_handoff_ack_recovery import handoff_acknowledgment_recovery_status
from release_authority_consumer import (
    CONSUMER_ACK_CONFIRMATION,
    acknowledge_release_authority_consumer_validation,
    preview_release_authority_consumer_validation,
    release_authority_consumer_receipt_status,
)
from release_authority_daily_use import release_authority_daily_use_status
from release_certification_coherence import (
    OPERATION_CLAIM_CONFIRMATION,
    OPERATION_RELEASE_CONFIRMATION,
    claim_operation,
    preview_operation_claim,
    release_operation,
)
from api_server import ApiError, handle_api_get, handle_api_post


def check(name: str, ok: object) -> dict[str, object]:
    return {"name": name, "ok": bool(ok)}


def main() -> int:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1098-6-") as temp:
        fixture = prepare_ready_fixture(Path(temp))
        runtime_root = Path(fixture["runtime_root"])
        target = Path(fixture["target"])
        target_before = file_snapshot(target)

        refresh = refresh_release_authority_readiness(runtime_root=runtime_root)
        plan = create_release_authority_handoff_plan(runtime_root=runtime_root)
        ack_preview = preview_release_authority_handoff_acknowledgment(
            operator_tab_id="consolidation-tab", operation_revision=601, runtime_root=runtime_root
        )
        ack = acknowledge_release_authority_handoff_plan(
            ack_preview.get("authorization_token", ""),
            confirm=HANDOFF_ACK_CONFIRMATION,
            operator_tab_id="consolidation-tab",
            operation_revision=601,
            runtime_root=runtime_root,
        )
        identity = (
            "release-authority-command-deck",
            "eidolon.release-authority.consumer",
            "1.0",
            "display one exact acknowledged handoff without exercising authority",
        )
        required = ["installation", "promotion", "general_release"]
        unsupported = ["native_windows", "provider_ollama", "model_specific"]
        consumer_preview = preview_release_authority_consumer_validation(
            *identity, required, unsupported, runtime_root=runtime_root
        )
        consumer_receipt = acknowledge_release_authority_consumer_validation(
            consumer_preview.get("authorization_token", ""),
            confirm=CONSUMER_ACK_CONFIRMATION,
            consumer_id=identity[0],
            consumer_schema=identity[1],
            consumer_version=identity[2],
            expected_use=identity[3],
            runtime_root=runtime_root,
        )
        consolidated = release_authority_daily_use_status(
            consumer_id=identity[0], consumer_schema=identity[1],
            consumer_version=identity[2], consumer_expected_use=identity[3],
            runtime_root=runtime_root,
        )
        repeated = release_authority_daily_use_status(
            consumer_id=identity[0], consumer_schema=identity[1],
            consumer_version=identity[2], consumer_expected_use=identity[3],
            runtime_root=runtime_root,
        )
        ack_status = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        recovery_status = handoff_acknowledgment_recovery_status(runtime_root=runtime_root)
        consumer_status = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
        rows += [
            check("readiness-refresh-current", refresh.get("ok")),
            check("handoff-plan-current", plan.get("ok")),
            check("handoff-acknowledgment-current", ack.get("ok") and ack_status.get("ok")),
            check("acknowledgment-recovery-not-pending", recovery_status.get("ok") and not recovery_status.get("recovery_available")),
            check("consumer-receipt-current", consumer_receipt.get("ok") and consumer_status.get("ok")),
            check("consolidated-status-coherent", consolidated.get("ok") and consolidated.get("status") == "release_authority_daily_use_coherent"),
            check("consolidated-status-deterministic", consolidated == repeated),
            check("consolidated-exact-bindings", consolidated.get("readiness_binding_sha256") and consolidated.get("handoff_plan_binding_sha256") and consolidated.get("handoff_acknowledgment_receipt_sha256") and consolidated.get("consumer_receipt_sha256")),
            check("consolidated-authority-separated", not consolidated.get("installation_inferred") and not consolidated.get("promotion_inferred") and not consolidated.get("general_release_certification_inferred") and not consolidated.get("native_windows_inferred") and not consolidated.get("provider_ollama_inferred") and not consolidated.get("model_specific_inferred")),
        ]

        duplicate_ack_preview = preview_release_authority_handoff_acknowledgment(
            operator_tab_id="consolidation-tab", operation_revision=602, runtime_root=runtime_root
        )
        duplicate_consumer_preview = preview_release_authority_consumer_validation(
            *identity, required, unsupported, runtime_root=runtime_root
        )
        duplicate_consumer = acknowledge_release_authority_consumer_validation(
            duplicate_consumer_preview.get("authorization_token", ""),
            confirm=CONSUMER_ACK_CONFIRMATION,
            consumer_id=identity[0], consumer_schema=identity[1], consumer_version=identity[2], expected_use=identity[3],
            runtime_root=runtime_root,
        )
        rows += [
            check("duplicate-acknowledgment-preview-blocked", not duplicate_ack_preview.get("ok")),
            check("duplicate-consumer-receipt-blocked", not duplicate_consumer.get("ok") and duplicate_consumer.get("status") == "consumer_receipt_already_created"),
        ]

        claim_preview = preview_operation_claim(
            "release_authority_consumer_receipt", "owner-tab", 700, runtime_root=runtime_root
        )
        claimed = claim_operation(
            claim_preview.get("authorization_token", ""), confirm=OPERATION_CLAIM_CONFIRMATION, runtime_root=runtime_root
        )
        other_tab = preview_operation_claim(
            "release_authority_handoff_acknowledgment_recovery", "other-tab", 701, runtime_root=runtime_root
        )
        stale_revision = preview_operation_claim(
            "release_authority_handoff_acknowledgment_replacement", "owner-tab", 700, runtime_root=runtime_root
        )
        active_status = release_authority_daily_use_status(
            consumer_id=identity[0], consumer_schema=identity[1], consumer_version=identity[2], consumer_expected_use=identity[3],
            runtime_root=runtime_root,
        )
        released = release_operation(
            "owner-tab", int(claimed.get("operation_generation") or 0), confirm=OPERATION_RELEASE_CONFIRMATION, runtime_root=runtime_root
        )
        rows += [
            check("consumer-operation-owner-claimable", claim_preview.get("ok") and claimed.get("ok")),
            check("cross-tab-operation-claim-rejected", not other_tab.get("ok") and other_tab.get("status") == "operation_owned_by_other_tab"),
            check("stale-operation-revision-rejected", not stale_revision.get("ok") and stale_revision.get("status") == "stale_operation_revision"),
            check("operation-owner-consolidated", active_status.get("operation_owner_present") and active_status.get("operation") == "release_authority_consumer_receipt" and active_status.get("operation_revision") == 700),
            check("exact-operation-release", released.get("ok")),
        ]

        old_env = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime_root)
        query = urlencode({
            "consumer_id": identity[0], "consumer_schema": identity[1],
            "consumer_version": identity[2], "expected_use": identity[3],
        })
        get_code, get_payload = handle_api_get(f"/api/release-authority/daily-use/status?{query}")
        ack_get_code, ack_get_payload = handle_api_get("/api/release-authority/handoff-plan/acknowledgment/status")
        recovery_get_code, recovery_get_payload = handle_api_get("/api/release-authority/handoff-plan/acknowledgment/recovery/status")
        consumer_get_code, consumer_get_payload = handle_api_get(f"/api/release-authority/consumer/receipt/status?{query}")
        preview_code, preview_payload = handle_api_post("/api/release-authority/consumer/validation-preview", {
            "consumer_id": identity[0], "consumer_schema": identity[1], "consumer_version": identity[2],
            "expected_use": identity[3], "required_scopes": required, "unsupported_scopes": unsupported,
        })
        try:
            handle_api_get("/api/release-authority/handoff-plan/acknowledgment/recover")
            recovery_post_only = False
        except ApiError as exc:
            recovery_post_only = exc.status == 404
        try:
            handle_api_get("/api/release-authority/consumer/receipt/create")
            consumer_post_only = False
        except ApiError as exc:
            consumer_post_only = exc.status == 404
        if old_env is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_env
        rows += [
            check("consolidated-status-get", get_code in {200, 409} and "data" in get_payload),
            check("acknowledgment-status-get", ack_get_code in {200, 409} and "data" in ack_get_payload),
            check("recovery-status-get", recovery_get_code in {200, 409} and "data" in recovery_get_payload),
            check("consumer-status-get", consumer_get_code in {200, 409} and "data" in consumer_get_payload),
            check("consumer-preview-post", preview_code in {200, 409} and "data" in preview_payload),
            check("acknowledgment-recovery-post-only", recovery_post_only),
            check("consumer-receipt-create-post-only", consumer_post_only),
        ]

        dashboard_text = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        api_text = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
        rows += [
            check("dashboard-ack-recovery-surface", "Handoff acknowledgment recovery" in dashboard_text),
            check("dashboard-explicit-consumer-surface", "Explicit consumer validation" in dashboard_text),
            check("api-content-free-consolidation-registered", "refresh, handoff, acknowledgment, consumer, scope, history, policy, and multi-tab status" in api_text),
        ]

        # Any exact authority/readiness drift makes all downstream handoff artifacts stale; no role silently repairs or transfers authority.
        drift_refresh = refresh_release_authority_readiness(runtime_root=runtime_root)
        drifted = release_authority_daily_use_status(
            consumer_id=identity[0], consumer_schema=identity[1], consumer_version=identity[2], consumer_expected_use=identity[3],
            runtime_root=runtime_root,
        )
        drift_ack = release_authority_handoff_acknowledgment_status(runtime_root=runtime_root)
        drift_consumer = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
        rows += [
            check("readiness-drift-refresh-completes", drift_refresh.get("ok")),
            check("handoff-acknowledgment-drift-consolidated", not drift_ack.get("ok") and not drifted.get("ok")),
            check("consumer-receipt-drift-consolidated", not drift_consumer.get("ok") and drift_consumer.get("receipt_stale")),
            check("drift-does-not-transfer-authority", not drifted.get("authority_transfer_on_refresh") and not drifted.get("authority_transfer_on_restart")),
        ]

        public = json.dumps({
            "consolidated": consolidated,
            "active": active_status,
            "drifted": drifted,
            "ack": drift_ack,
            "consumer": drift_consumer,
        }, sort_keys=True)
        rows += [
            check("content-free-path-suppression", str(runtime_root) not in public and str(target) not in public and "/tmp/" not in public),
            check("consumer-not-discovered-or-inferred", not consolidated.get("consumer_discovery_performed") and not consolidated.get("newest_consumer_inferred")),
            check("duplicate-execution-disabled", not consolidated.get("duplicate_execution_allowed")),
            check("ordinary-conversation-unaffected", not consolidated.get("ordinary_conversation_affected")),
            check("target-source-unchanged", file_snapshot(target) == target_before),
            check("no-provider-native-model-actions", not consolidated.get("provider_contacted") and not consolidated.get("native_checks_run") and not consolidated.get("models_mutated")),
            check("no-install-promotion-certification-policy-actions", not consolidated.get("installation_changed") and not consolidated.get("promotion_changed") and not consolidated.get("certification_changed") and not consolidated.get("policy_migrated")),
        ]

    report = {
        "suite": "v1098.6-release-authority-handoff-consolidation-checkpoint",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
