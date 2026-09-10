from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

from release_candidate_identity import read_json
from release_installation_plan import plan_directory
from release_installation_staging import staging_directory
from release_installation_transaction import (
    INSTALLATION_APPLY_CONFIRMATION,
    apply_authorized_installation,
    installation_transaction_status,
    preview_installation_apply_authorization,
    transaction_directory,
)
from v1096_bundle_c_test_support import prepare_staged_fixture


def check(name: str, ok: object, detail: str = "") -> dict[str, object]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    rows: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-5-") as td:
        fixture = prepare_staged_fixture(Path(td))
        runtime = fixture["handoff_runtime"]
        target = fixture["target"]
        source = fixture["source"]

        auth = preview_installation_apply_authorization(runtime_root=runtime)
        token = str(auth.get("authorization_token") or "")
        rows.append(check("exact-apply-authorization", auth.get("ok") and token and auth.get("literal_confirmation") == INSTALLATION_APPLY_CONFIRMATION))
        bad = apply_authorized_installation(token, confirm="true", runtime_root=runtime)
        rows.append(check("literal-confirmation-required", not bad.get("ok") and bad.get("status") == "literal_confirmation_required"))

        applied = apply_authorized_installation(token, confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=runtime)
        rows.append(check("transaction-installed-unpromoted", applied.get("ok") and applied.get("status") == "installed_unpromoted" and applied.get("installed")))
        rows.append(check("add-applied", (target / fixture["add_relative"]).read_bytes() == (source / fixture["add_relative"]).read_bytes()))
        rows.append(check("replace-applied", (target / fixture["replace_relative"]).read_bytes() == (source / fixture["replace_relative"]).read_bytes()))
        rows.append(check("remove-applied", not (target / fixture["remove_relative"]).exists()))
        rows.append(check("protected-preserved", fixture["protected_path"].read_bytes() == fixture["protected_bytes"]))
        rows.append(check("backups-before-mutation", applied.get("backups_verified_before_mutation") and applied.get("backup_count", 0) >= 2))

        tx_dir = transaction_directory(runtime)
        pointer = read_json(tx_dir / "active_transaction.json")
        txid = str(pointer.get("transaction_id") or "")
        record = read_json(tx_dir / "records" / f"{txid}.json")
        events_path = tx_dir / "events" / f"{txid}.jsonl"
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        event_kinds = [str(row.get("kind") or "") for row in events]
        rows.append(check("append-only-per-file-events", event_kinds.count("effect_applied") == 3 and "all_backups_verified" in event_kinds and event_kinds[-1] == "transaction_finalized"))
        receipt = read_json(tx_dir / "installed_receipts" / f"{txid}.json")
        rows.append(check("external-installed-receipt", receipt.get("state") == "installed_unpromoted" and receipt.get("transaction_id") == txid and receipt.get("receipt_sha256")))
        status = installation_transaction_status(runtime_root=runtime)
        rows.append(check("transaction-status-coherent", status.get("ok") and status.get("transaction_identity_sha256") == record.get("transaction_identity_sha256")))
        reused = apply_authorized_installation(token, confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=runtime)
        rows.append(check("apply-token-single-use", not reused.get("ok") and reused.get("status") == "authorization_reused"))
        public_blob = json.dumps(applied, sort_keys=True)
        rows.append(check("public-paths-suppressed", str(target) not in public_blob and str(fixture["archive"]) not in public_blob))
        rows.append(check("authority-remains-separate", not applied.get("promoted") and not applied.get("certified") and not receipt.get("promoted") and not receipt.get("certified")))
        rows.append(check("target-local-temps-cleaned", not any(p.name.endswith(".tmp") and txid in p.name for p in target.rglob("*"))))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-5-drift-") as td:
        fixture = prepare_staged_fixture(Path(td))
        runtime = fixture["handoff_runtime"]
        auth = preview_installation_apply_authorization(runtime_root=runtime)
        token = str(auth.get("authorization_token") or "")
        (fixture["target"] / "README.md").write_text("external drift after apply preview\n", encoding="utf-8")
        rejected = apply_authorized_installation(token, confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=runtime)
        rows.append(check("target-drift-rejected-before-mutation", not rejected.get("ok") and rejected.get("status") == "authorization_stale_or_mismatched"))
        rows.append(check("drift-rejection-no-transaction", not read_json(transaction_directory(runtime) / "active_transaction.json")))


    # Malformed and cross-runtime tokens never start a transaction.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-5-token-a-") as td_a, tempfile.TemporaryDirectory(prefix="eidolon-v1096-5-token-b-") as td_b:
        fixture_a = prepare_staged_fixture(Path(td_a))
        fixture_b = prepare_staged_fixture(Path(td_b))
        auth_a = preview_installation_apply_authorization(runtime_root=fixture_a["handoff_runtime"])
        token_a = str(auth_a.get("authorization_token") or "")
        malformed = apply_authorized_installation(token_a + "-tampered", confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=fixture_a["handoff_runtime"])
        rows.append(check("malformed-apply-token-rejected", not malformed.get("ok") and malformed.get("status") == "authorization_missing_or_malformed"))
        crossed = apply_authorized_installation(token_a, confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=fixture_b["handoff_runtime"])
        rows.append(check("cross-runtime-stage-token-rejected", not crossed.get("ok") and crossed.get("status") == "authorization_missing_or_malformed"))
        rows.append(check("cross-runtime-rejection-no-transaction", not read_json(transaction_directory(fixture_b["handoff_runtime"]) / "active_transaction.json")))

    # Stage and plan drift after preview invalidate the exact authorization.
    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-5-stage-drift-") as td:
        fixture = prepare_staged_fixture(Path(td))
        runtime = fixture["handoff_runtime"]
        auth = preview_installation_apply_authorization(runtime_root=runtime)
        token = str(auth.get("authorization_token") or "")
        stage_pointer = read_json(staging_directory(runtime) / "active_stage.json")
        stage_path = staging_directory(runtime) / "records" / f"{stage_pointer.get('stage_id','')}.json"
        stage = read_json(stage_path)
        stage["candidate_id"] = str(stage.get("candidate_id") or "") + "-changed"
        stage_path.write_text(json.dumps(stage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rejected = apply_authorized_installation(token, confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=runtime)
        rows.append(check("stage-drift-rejected-before-mutation", not rejected.get("ok") and rejected.get("status") == "authorization_stale_or_mismatched"))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1096-5-plan-drift-") as td:
        fixture = prepare_staged_fixture(Path(td))
        runtime = fixture["handoff_runtime"]
        auth = preview_installation_apply_authorization(runtime_root=runtime)
        token = str(auth.get("authorization_token") or "")
        stage_pointer = read_json(staging_directory(runtime) / "active_stage.json")
        stage = read_json(staging_directory(runtime) / "records" / f"{stage_pointer.get('stage_id','')}.json")
        plan_path = plan_directory(runtime) / "records" / f"{stage.get('plan_id','')}.json"
        plan = read_json(plan_path)
        plan["effects_sha256"] = "0" * 64
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rejected = apply_authorized_installation(token, confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=runtime)
        rows.append(check("plan-drift-rejected-before-mutation", not rejected.get("ok") and rejected.get("status") == "authorization_stale_or_mismatched"))

    report = {
        "suite": "v1096.5-exact-transactional-installation-apply-foundation",
        "passed": sum(bool(row["ok"]) for row in rows),
        "failed": sum(not bool(row["ok"]) for row in rows),
        "checks": rows,
    }
    report["ok"] = report["failed"] == 0
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
