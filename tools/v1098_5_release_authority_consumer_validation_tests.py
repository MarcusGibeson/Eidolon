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
from release_candidate_identity import atomic_json, read_json
from release_authority_readiness_recovery import refresh_release_authority_readiness
from release_authority_handoff_plan import (
    HANDOFF_ACK_CONFIRMATION,
    acknowledge_release_authority_handoff_plan,
    create_release_authority_handoff_plan,
    preview_release_authority_handoff_acknowledgment,
)
from release_authority_consumer import (
    CONSUMER_ACK_CONFIRMATION,
    _consumer_key,
    _consumer_root,
    _record_digest,
    acknowledge_release_authority_consumer_validation,
    preview_release_authority_consumer_validation,
    release_authority_consumer_receipt_status,
)
from api_server import ApiError, handle_api_get, handle_api_post


def check(name: str, ok: object) -> dict[str, object]:
    return {"name": name, "ok": bool(ok)}


def tamper_receipt_binding(runtime_root: Path, identity: tuple[str, str, str, str], field: str, value: object) -> bytes:
    key = _consumer_key(*identity)
    root = _consumer_root(runtime_root, key)
    pointer_path = root / "active_receipt.json"
    pointer = read_json(pointer_path)
    receipt_path = root / "receipts" / f"{pointer['consumer_receipt_id']}.json"
    backup = receipt_path.read_bytes()
    receipt = read_json(receipt_path)
    receipt[field] = value
    receipt["consumer_receipt_sha256"] = _record_digest(receipt, "consumer_receipt_sha256")
    atomic_json(receipt_path, receipt)
    pointer["consumer_receipt_sha256"] = receipt["consumer_receipt_sha256"]
    atomic_json(pointer_path, pointer)
    return backup


def restore_receipt(runtime_root: Path, identity: tuple[str, str, str, str], backup: bytes) -> None:
    key = _consumer_key(*identity)
    root = _consumer_root(runtime_root, key)
    pointer = read_json(root / "active_receipt.json")
    receipt_path = root / "receipts" / f"{pointer['consumer_receipt_id']}.json"
    receipt_path.write_bytes(backup)
    receipt = read_json(receipt_path)
    pointer["consumer_receipt_sha256"] = receipt["consumer_receipt_sha256"]
    atomic_json(root / "active_receipt.json", pointer)


def main() -> int:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="eidolon-v1098-5-") as temp:
        fixture = prepare_ready_fixture(Path(temp))
        runtime_root = Path(fixture["runtime_root"])
        target = Path(fixture["target"])
        target_before = file_snapshot(target)
        refresh_release_authority_readiness(runtime_root=runtime_root)
        create_release_authority_handoff_plan(runtime_root=runtime_root)
        ack_preview = preview_release_authority_handoff_acknowledgment(operator_tab_id="consumer-tab", operation_revision=101, runtime_root=runtime_root)
        ack = acknowledge_release_authority_handoff_plan(
            ack_preview.get("authorization_token", ""), confirm=HANDOFF_ACK_CONFIRMATION,
            operator_tab_id="consumer-tab", operation_revision=101, runtime_root=runtime_root
        )
        rows.append(check("acknowledged-handoff-required", ack.get("ok")))

        identity = ("release-command-deck", "eidolon.consumer.command-deck", "1.0", "display exact release handoff status")
        required = ["installation", "promotion", "general_release"]
        unsupported = ["native_windows", "provider_ollama", "model_specific"]
        missing_identity = preview_release_authority_consumer_validation("", identity[1], identity[2], identity[3], required, unsupported, runtime_root=runtime_root)
        incomplete = preview_release_authority_consumer_validation(*identity, ["installation"], unsupported, runtime_root=runtime_root)
        overlap = preview_release_authority_consumer_validation(*identity, required + ["native_windows"], unsupported, runtime_root=runtime_root)
        overclaim = preview_release_authority_consumer_validation(
            *identity,
            required + ["native_windows"], ["provider_ollama", "model_specific"],
            runtime_root=runtime_root,
        )
        inference = preview_release_authority_consumer_validation(
            *identity, required, unsupported, scope_sources={"general_release": "promotion"}, runtime_root=runtime_root
        )
        rows += [
            check("exact-consumer-identity-required", not missing_identity.get("ok")),
            check("complete-scope-declaration-required", not incomplete.get("ok")),
            check("overlapping-scope-declaration-rejected", not overlap.get("ok")),
            check("scope-overclaim-rejected", not overclaim.get("ok")),
            check("cross-scope-authority-inference-rejected", not inference.get("ok")),
        ]

        validation = preview_release_authority_consumer_validation(*identity, required, unsupported, runtime_root=runtime_root)
        wrong_literal = acknowledge_release_authority_consumer_validation(
            validation.get("authorization_token", ""), confirm="yes", consumer_id=identity[0], consumer_schema=identity[1],
            consumer_version=identity[2], expected_use=identity[3], runtime_root=runtime_root
        )
        wrong_version = acknowledge_release_authority_consumer_validation(
            validation.get("authorization_token", ""), confirm=CONSUMER_ACK_CONFIRMATION, consumer_id=identity[0], consumer_schema=identity[1],
            consumer_version="2.0", expected_use=identity[3], runtime_root=runtime_root
        )
        interrupted = acknowledge_release_authority_consumer_validation(
            validation.get("authorization_token", ""), confirm=CONSUMER_ACK_CONFIRMATION, consumer_id=identity[0], consumer_schema=identity[1],
            consumer_version=identity[2], expected_use=identity[3], interrupt_after="receipt_written", runtime_root=runtime_root
        )
        recovered = acknowledge_release_authority_consumer_validation(
            validation.get("authorization_token", ""), confirm=CONSUMER_ACK_CONFIRMATION, consumer_id=identity[0], consumer_schema=identity[1],
            consumer_version=identity[2], expected_use=identity[3], runtime_root=runtime_root
        )
        reused = acknowledge_release_authority_consumer_validation(
            validation.get("authorization_token", ""), confirm=CONSUMER_ACK_CONFIRMATION, consumer_id=identity[0], consumer_schema=identity[1],
            consumer_version=identity[2], expected_use=identity[3], runtime_root=runtime_root
        )
        status = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
        rows += [
            check("consumer-validation-preview-exact", validation.get("ok") and validation.get("literal_confirmation_required") == CONSUMER_ACK_CONFIRMATION),
            check("consumer-literal-confirmation-required", not wrong_literal.get("ok")),
            check("cross-consumer-version-token-rejected", not wrong_version.get("ok")),
            check("consumer-receipt-interruption-detected", not interrupted.get("ok") and interrupted.get("consumer_receipt_operation_status") == "receipt_written"),
            check("consumer-receipt-resumed-without-duplicate", recovered.get("ok") and recovered.get("consumer_receipt_recovery_performed")),
            check("consumer-token-single-use", not reused.get("ok") and reused.get("status") == "authorization_reused"),
            check("consumer-receipt-current", status.get("ok") and status.get("receipt_present") and not status.get("receipt_stale")),
            check("consumer-receipt-grants-no-authority", not status.get("consumer_receipt_grants_authority") and not status.get("installation_authorized") and not status.get("promotion_authorized") and not status.get("certification_authorized")),
        ]

        duplicate_validation = preview_release_authority_consumer_validation(*identity, required, unsupported, runtime_root=runtime_root)
        duplicate_receipt = acknowledge_release_authority_consumer_validation(
            duplicate_validation.get("authorization_token", ""), confirm=CONSUMER_ACK_CONFIRMATION,
            consumer_id=identity[0], consumer_schema=identity[1], consumer_version=identity[2], expected_use=identity[3], runtime_root=runtime_root
        )
        unrelated = _consumer_root(runtime_root, "f" * 64)
        unrelated.mkdir(parents=True, exist_ok=True)
        (unrelated / "noise.json").write_text('{"content_free": true}\n', encoding="utf-8")
        explicit_again = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
        rows += [
            check("duplicate-consumer-receipt-blocked", not duplicate_receipt.get("ok") and duplicate_receipt.get("status") == "consumer_receipt_already_created"),
            check("consumer-not-scanned-or-inferred", explicit_again.get("ok") and not explicit_again.get("consumer_discovery_performed") and not explicit_again.get("newest_consumer_inferred")),
        ]

        drift_fields = {
            "target_inventory_sha256": "0" * 64,
            "policy_sha256": "1" * 64,
            "evidence_state_sha256": "2" * 64,
            "authority_state_sha256": "3" * 64,
            "candidate_id": "wrong-candidate",
            "archive_sha256": "4" * 64,
            "installed_receipt_sha256": "5" * 64,
            "promotion_receipt_sha256": "6" * 64,
            "certification_receipt_sha256": "7" * 64,
        }
        for field, value in drift_fields.items():
            backup = tamper_receipt_binding(runtime_root, identity, field, value)
            drifted = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
            rows.append(check(f"{field}-drift-detected", not drifted.get("ok") and drifted.get("receipt_stale")))
            restore_receipt(runtime_root, identity, backup)
        changed_version = release_authority_consumer_receipt_status(identity[0], identity[1], "2.0", identity[3], runtime_root=runtime_root)
        rows.append(check("consumer-version-drift-not-reused", changed_version.get("status") == "release_authority_consumer_receipt_not_created" and not changed_version.get("receipt_present")))

        # Actual bound authority/readiness drift makes the receipt stale without touching it.
        refresh_release_authority_readiness(runtime_root=runtime_root)
        actual_drift = release_authority_consumer_receipt_status(*identity, runtime_root=runtime_root)
        rows.append(check("actual-authority-readiness-drift-detected", not actual_drift.get("ok") and actual_drift.get("receipt_stale")))

        old_env = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime_root)
        query = urlencode({"consumer_id": identity[0], "consumer_schema": identity[1], "consumer_version": identity[2], "expected_use": identity[3]})
        code, payload = handle_api_get(f"/api/release-authority/consumer/receipt/status?{query}")
        post_code, post_payload = handle_api_post("/api/release-authority/consumer/validation-preview", {
            "consumer_id": identity[0], "consumer_schema": identity[1], "consumer_version": identity[2], "expected_use": identity[3],
            "required_scopes": required, "unsupported_scopes": unsupported,
        })
        try:
            handle_api_get("/api/release-authority/consumer/receipt/create")
            post_only = False
        except ApiError as exc:
            post_only = exc.status == 404
        if old_env is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_env
        rows += [
            check("consumer-status-get-explicit", code in {200, 409} and "data" in payload),
            check("consumer-preview-post", post_code in {200, 409} and "data" in post_payload),
            check("consumer-mutations-post-only", post_only),
        ]

        public = json.dumps({"current": status, "drift": actual_drift}, sort_keys=True)
        rows += [
            check("consumer-paths-suppressed", str(runtime_root) not in public and str(target) not in public and "/tmp/" not in public),
            check("target-source-unchanged", file_snapshot(target) == target_before),
            check("no-provider-native-model-actions", not status.get("provider_contacted") and not status.get("native_checks_run") and not status.get("models_mutated")),
            check("no-install-promotion-certification-actions", not status.get("installation_changed") and not status.get("promotion_changed") and not status.get("certification_changed") and not status.get("policy_migrated")),
        ]

    report = {
        "suite": "v1098.5-release-authority-consumer-validation-receipt-binding",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
