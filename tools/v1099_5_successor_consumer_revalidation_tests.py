from __future__ import annotations
import json
import tempfile
from pathlib import Path

from v1099_bundle_a_test_support import *
import release_authority_consumer_daily_use as daily
import release_authority_consumer_daily_use_recovery as recovery
from release_candidate_identity import atomic_json

PRED = IDENTITY
SUCC = (IDENTITY[0], IDENTITY[1], "2.0", IDENTITY[3])
CROSS = ("other-consumer", IDENTITY[1], "2.0", IDENTITY[3])
PRED_USE = ("release-status-card", "eidolon.consumer.use", "1.0", "render bounded content-free release status")
SUCC_USE = (PRED_USE[0], PRED_USE[1], "2.0", PRED_USE[3])
PURPOSE = "operator command-deck display"


def check(name, value):
    return {"name": name, "ok": bool(value)}


def patch_multi(runtime_root: Path):
    def receipt_status(*args, **kwargs):
        identity = tuple(args[:4])
        try:
            receipt = current_receipt(runtime_root, identity)
        except Exception:
            return {"ok": False, "status": "wrong-consumer", "receipt_present": False}
        if not receipt:
            return {"ok": False, "status": "wrong-consumer", "receipt_present": False}
        return {**receipt, "ok": True, "status": "release_authority_consumer_receipt_current", "receipt_present": True, "receipt_stale": False}

    def lifecycle_status(*args, **kwargs):
        identity = tuple(args[:4])
        receipt = current_receipt(runtime_root, identity)
        return {"ok": bool(receipt), "status": "consumer_receipt_lifecycle_current" if receipt else "wrong-consumer", "consumer_receipt_id": receipt.get("consumer_receipt_id", ""), "consumer_receipt_sha256": receipt.get("consumer_receipt_sha256", ""), "operation_status": "completed", "finding_count": 0}

    daily.release_authority_consumer_receipt_status = receipt_status
    daily.consumer_receipt_lifecycle_status = lifecycle_status
    recovery.consumer_selection_status = daily.consumer_selection_status
    recovery.consumer_use_preflight_status = daily.consumer_use_preflight_status


def create_chain(runtime_root: Path, identity, use, start_revision: int):
    selection_preview = daily.preview_consumer_selection(*identity, PURPOSE, operator_tab_id="tab-a", operation_revision=start_revision, runtime_root=runtime_root)
    selection = daily.create_consumer_selection(selection_preview["authorization_token"], confirm=daily.SELECTION_CONFIRMATION, consumer_id=identity[0], consumer_schema=identity[1], consumer_version=identity[2], expected_use=identity[3], selection_purpose=PURPOSE, operator_tab_id="tab-a", operation_revision=start_revision, runtime_root=runtime_root)
    preflight_preview = daily.preview_consumer_use_preflight(*identity, PURPOSE, *use, REQUIRED, UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=start_revision + 1, runtime_root=runtime_root)
    preflight = daily.create_consumer_use_preflight_receipt(preflight_preview["authorization_token"], confirm=daily.PREFLIGHT_CONFIRMATION, consumer_id=identity[0], consumer_schema=identity[1], consumer_version=identity[2], expected_use=identity[3], selection_purpose=PURPOSE, use_id=use[0], use_schema=use[1], use_version=use[2], declared_use=use[3], required_scopes=REQUIRED, unsupported_scopes=UNSUPPORTED, scope_sources={"general_release": "general_release"}, operator_tab_id="tab-a", operation_revision=start_revision + 1, runtime_root=runtime_root)
    return selection, preflight


def expire_chain(runtime_root: Path, identity, use):
    daily_root, pointer, selection = daily._selection_private(runtime_root, identity)
    selection["selection_expires_at"] = "2000-01-01T00:00:00+00:00"
    selection["selection_sha256"] = daily._record_digest(selection, "selection_sha256")
    atomic_json(daily_root / "selections" / f"{selection['selection_id']}.json", selection)
    pointer["selection_sha256"] = selection["selection_sha256"]
    atomic_json(daily_root / "active_selection.json", pointer)
    use_root = daily._use_root(runtime_root, identity, use)
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
    with tempfile.TemporaryDirectory(prefix="eidolon-v1099-5-") as temp:
        runtime_root = Path(temp)
        make_receipt(runtime_root, PRED)
        make_receipt(runtime_root, SUCC)
        make_receipt(runtime_root, CROSS)
        patch_multi(runtime_root)
        create_chain(runtime_root, PRED, PRED_USE, 1)
        create_chain(runtime_root, SUCC, SUCC_USE, 3)
        create_chain(runtime_root, CROSS, SUCC_USE, 5)
        expire_chain(runtime_root, PRED, PRED_USE)

        self_preview = recovery.preview_successor_consumer_daily_use_revalidation(PRED, PURPOSE, PRED_USE, PRED, PURPOSE, PRED_USE, operator_tab_id="tab-a", operation_revision=7, runtime_root=runtime_root)
        cross_preview = recovery.preview_successor_consumer_daily_use_revalidation(PRED, PURPOSE, PRED_USE, CROSS, PURPOSE, SUCC_USE, operator_tab_id="tab-a", operation_revision=7, runtime_root=runtime_root)
        preview = recovery.preview_successor_consumer_daily_use_revalidation(PRED, PURPOSE, PRED_USE, SUCC, PURPOSE, SUCC_USE, operator_tab_id="tab-a", operation_revision=7, runtime_root=runtime_root)
        wrong_revision = recovery.create_successor_consumer_daily_use_revalidation(preview.get("authorization_token", ""), confirm=recovery.SUCCESSOR_CONFIRMATION, predecessor_consumer=PRED, predecessor_selection_purpose=PURPOSE, predecessor_use=PRED_USE, successor_consumer=SUCC, successor_selection_purpose=PURPOSE, successor_use=SUCC_USE, operator_tab_id="tab-a", operation_revision=8, runtime_root=runtime_root)
        interrupted = recovery.create_successor_consumer_daily_use_revalidation(preview.get("authorization_token", ""), confirm=recovery.SUCCESSOR_CONFIRMATION, predecessor_consumer=PRED, predecessor_selection_purpose=PURPOSE, predecessor_use=PRED_USE, successor_consumer=SUCC, successor_selection_purpose=PURPOSE, successor_use=SUCC_USE, operator_tab_id="tab-a", operation_revision=7, interrupt_after="record_written", runtime_root=runtime_root)
        created = recovery.create_successor_consumer_daily_use_revalidation(preview.get("authorization_token", ""), confirm=recovery.SUCCESSOR_CONFIRMATION, predecessor_consumer=PRED, predecessor_selection_purpose=PURPOSE, predecessor_use=PRED_USE, successor_consumer=SUCC, successor_selection_purpose=PURPOSE, successor_use=SUCC_USE, operator_tab_id="tab-a", operation_revision=7, runtime_root=runtime_root)
        status = recovery.successor_consumer_daily_use_revalidation_status(PRED, PURPOSE, PRED_USE, SUCC, PURPOSE, SUCC_USE, runtime_root=runtime_root)
        replay = recovery.create_successor_consumer_daily_use_revalidation(preview.get("authorization_token", ""), confirm=recovery.SUCCESSOR_CONFIRMATION, predecessor_consumer=PRED, predecessor_selection_purpose=PURPOSE, predecessor_use=PRED_USE, successor_consumer=SUCC, successor_selection_purpose=PURPOSE, successor_use=SUCC_USE, operator_tab_id="tab-a", operation_revision=7, runtime_root=runtime_root)
        fork = recovery.preview_successor_consumer_daily_use_revalidation(PRED, PURPOSE, PRED_USE, SUCC, PURPOSE, SUCC_USE, operator_tab_id="tab-a", operation_revision=9, runtime_root=runtime_root)
        drift_policy(runtime_root, SUCC)
        drifted = recovery.successor_consumer_daily_use_revalidation_status(PRED, PURPOSE, PRED_USE, SUCC, PURPOSE, SUCC_USE, runtime_root=runtime_root)

        rows += [
            check("self-replacement-rejected", not self_preview.get("ok")),
            check("cross-consumer-rejected", not cross_preview.get("ok")),
            check("explicit-successor-preview", preview.get("ok") and not preview.get("successor_inferred")),
            check("cross-revision-token-rejected", not wrong_revision.get("ok")),
            check("interruption-recorded", interrupted.get("status") == "successor_revalidation_interrupted"),
            check("exact-revalidation-recovered", created.get("ok") and created.get("successor_revalidation_recovery_performed")),
            check("immutable-revalidation-current", status.get("ok") and status.get("successor_revalidation_present")),
            check("single-use-token", not replay.get("ok")),
            check("predecessor-fork-rejected", not fork.get("ok")),
            check("successor-policy-drift-detected", not drifted.get("ok") and drifted.get("successor_revalidation_stale")),
            check("no-newest-or-successor-inference", not created.get("newest_consumer_inferred") and not created.get("successor_inferred")),
            check("no-authority-transfer", not created.get("authority_granted") and not created.get("installation_authorized") and not created.get("certification_authorized")),
            check("no-future-use-authority", not created.get("provider_access_authorized") and not created.get("model_access_authorized")),
            check("consumer-not-executed", not created.get("consumer_executed")),
            check("external-content-free", created.get("records_external") and created.get("content_free")),
            check("path-suppressed", str(runtime_root) not in json.dumps(created)),
        ]
    report = {"suite": "v1099.5-exact-successor-consumer-selection-preflight-revalidation", "passed": sum(row["ok"] for row in rows), "failed": sum(not row["ok"] for row in rows), "checks": rows}
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
