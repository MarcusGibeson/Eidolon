from __future__ import annotations
import json
import tempfile
from pathlib import Path

from v1099_bundle_a_test_support import *
import release_authority_consumer_daily_use as daily
import release_authority_consumer_daily_use_recovery as recovery
from release_candidate_identity import atomic_json

USE = ("release-status-card", "eidolon.consumer.use", "1.0", "render bounded content-free release status")
PURPOSE = "operator command-deck display"


def check(name, value):
    return {"name": name, "ok": bool(value)}


def expire_chain(runtime_root: Path):
    daily_root, pointer, selection = daily._selection_private(runtime_root, IDENTITY)
    selection["selection_expires_at"] = "2000-01-01T00:00:00+00:00"
    selection["selection_sha256"] = daily._record_digest(selection, "selection_sha256")
    atomic_json(daily_root / "selections" / f"{selection['selection_id']}.json", selection)
    pointer["selection_sha256"] = selection["selection_sha256"]
    atomic_json(daily_root / "active_selection.json", pointer)
    use_root = daily._use_root(runtime_root, IDENTITY, USE)
    pre_pointer = daily.read_json(use_root / "active_preflight.json")
    preflight = daily.read_json(use_root / "receipts" / f"{pre_pointer['preflight_receipt_id']}.json")
    preflight["selection_sha256"] = selection["selection_sha256"]
    preflight["selection_expires_at"] = selection["selection_expires_at"]
    preflight["preflight_expires_at"] = selection["selection_expires_at"]
    preflight["preflight_receipt_sha256"] = daily._record_digest(preflight, "preflight_receipt_sha256")
    atomic_json(use_root / "receipts" / f"{preflight['preflight_receipt_id']}.json", preflight)
    pre_pointer["preflight_receipt_sha256"] = preflight["preflight_receipt_sha256"]
    pre_pointer["selection_sha256"] = selection["selection_sha256"]
    atomic_json(use_root / "active_preflight.json", pre_pointer)


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-4-") as temp:
        runtime_root = Path(temp)
        make_receipt(runtime_root)
        patch_daily(daily, runtime_root)

        preview = daily.preview_consumer_selection(*IDENTITY, PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)
        interrupted = daily.create_consumer_selection(preview["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, operator_tab_id="tab-a", operation_revision=1, interrupt_after="selection_written", runtime_root=runtime_root)
        status = recovery.consumer_daily_use_recovery_status(*IDENTITY, PURPOSE, *USE, runtime_root=runtime_root)
        rec_preview = recovery.preview_consumer_daily_use_recovery(*IDENTITY, PURPOSE, *USE, "selection", operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        wrong_tab = recovery.recover_consumer_daily_use_binding(rec_preview.get("authorization_token", ""), confirm=recovery.RECOVERY_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], recovery_target="selection", operator_tab_id="tab-b", operation_revision=2, runtime_root=runtime_root)
        recovered = recovery.recover_consumer_daily_use_binding(rec_preview.get("authorization_token", ""), confirm=recovery.RECOVERY_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], recovery_target="selection", operator_tab_id="tab-a", operation_revision=2, runtime_root=runtime_root)
        original_replay = daily.create_consumer_selection(preview["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, operator_tab_id="tab-a", operation_revision=1, runtime_root=runtime_root)

        pf_preview = daily.preview_consumer_use_preflight(*IDENTITY, PURPOSE, *USE, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=3, runtime_root=runtime_root)
        pf_interrupted = daily.create_consumer_use_preflight_receipt(pf_preview["authorization_token"], confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=3, interrupt_after="receipt_written", runtime_root=runtime_root)
        pf_rec_preview = recovery.preview_consumer_daily_use_recovery(*IDENTITY, PURPOSE, *USE, "preflight", operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)
        pf_recovered = recovery.recover_consumer_daily_use_binding(pf_rec_preview.get("authorization_token", ""), confirm=recovery.RECOVERY_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], recovery_target="preflight", operator_tab_id="tab-a", operation_revision=4, runtime_root=runtime_root)

        expire_chain(runtime_root)
        replacement_preview = recovery.preview_expired_daily_use_replacement(*IDENTITY, PURPOSE, *USE, operator_tab_id="tab-a", operation_revision=5, replacement_ttl_seconds=600, runtime_root=runtime_root)
        cross_runtime = recovery.replace_expired_daily_use_binding(replacement_preview.get("authorization_token", ""), confirm=recovery.REPLACEMENT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], operator_tab_id="tab-a", operation_revision=5, runtime_root=Path(temp) / "other")
        replacement_interrupted = recovery.replace_expired_daily_use_binding(replacement_preview.get("authorization_token", ""), confirm=recovery.REPLACEMENT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], operator_tab_id="tab-a", operation_revision=5, interrupt_after="records_written", runtime_root=runtime_root)
        replacement = recovery.replace_expired_daily_use_binding(replacement_preview.get("authorization_token", ""), confirm=recovery.REPLACEMENT_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], selection_purpose=PURPOSE, use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], operator_tab_id="tab-a", operation_revision=5, runtime_root=runtime_root)
        final_selection = daily.consumer_selection_status(*IDENTITY, PURPOSE, runtime_root=runtime_root)
        final_preflight = daily.consumer_use_preflight_status(*IDENTITY, PURPOSE, *USE, runtime_root=runtime_root)

        daily_root = daily._daily_root(runtime_root, IDENTITY)
        abandoned = {"schema": "eidolon-abandoned-daily-use-artifact-v1", "abandoned": True, "runtime_root_sha256": daily._runtime_binding(runtime_root), "artifact_id": "abandoned-a", "content_free": True}
        abandoned["record_sha256"] = daily._record_digest(abandoned, "record_sha256")
        atomic_json(daily_root / "abandoned" / "abandoned-a.json", abandoned)
        cleanup_preview = recovery.preview_consumer_daily_use_cleanup(*IDENTITY, PURPOSE, *USE, operator_tab_id="tab-a", operation_revision=6, runtime_root=runtime_root)
        bad_cleanup = recovery.cleanup_consumer_daily_use_artifacts(cleanup_preview.get("authorization_token", ""), confirm="yes", consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], operator_tab_id="tab-a", operation_revision=6, runtime_root=runtime_root)
        cleanup = recovery.cleanup_consumer_daily_use_artifacts(cleanup_preview.get("authorization_token", ""), confirm=recovery.CLEANUP_CONFIRMATION, consumer_id=IDENTITY[0], consumer_schema=IDENTITY[1], consumer_version=IDENTITY[2], expected_use=IDENTITY[3], use_id=USE[0], use_schema=USE[1], use_version=USE[2], declared_use=USE[3], operator_tab_id="tab-a", operation_revision=6, runtime_root=runtime_root)

        rows += [
            check("selection-interruption-detected", interrupted.get("status") == "consumer_selection_interrupted" and status.get("recovery_target") == "selection"),
            check("recovery-preview-exact", rec_preview.get("ok") and rec_preview.get("literal_confirmation_required") == recovery.RECOVERY_CONFIRMATION),
            check("cross-tab-recovery-rejected", not wrong_tab.get("ok")),
            check("selection-recovered", recovered.get("ok")),
            check("original-selection-token-burned", not original_replay.get("ok")),
            check("preflight-interruption-detected", pf_interrupted.get("status") == "consumer_use_preflight_interrupted"),
            check("preflight-recovered", pf_recovered.get("ok")),
            check("expiry-replacement-preview", replacement_preview.get("ok") and replacement_preview.get("replacement_available")),
            check("cross-runtime-replacement-rejected", not cross_runtime.get("ok")),
            check("replacement-interruption-recorded", replacement_interrupted.get("status") == "consumer_daily_use_replacement_interrupted"),
            check("replacement-recovered", replacement.get("ok") and replacement.get("replacement_recovery_performed")),
            check("replacement-chain-current", final_selection.get("ok") and final_preflight.get("ok")),
            check("truthy-cleanup-confirmation-rejected", not bad_cleanup.get("ok")),
            check("exact-cleanup-completed", cleanup.get("ok") and not (daily_root / "abandoned" / "abandoned-a.json").exists()),
            check("no-authority-or-execution", not replacement.get("authority_granted") and not replacement.get("consumer_executed")),
            check("content-free-path-suppressed", str(runtime_root) not in json.dumps(replacement) and replacement.get("content_free")),
        ]
    report = {"suite": "v1099.4-consumer-daily-use-binding-recovery-expiry", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
