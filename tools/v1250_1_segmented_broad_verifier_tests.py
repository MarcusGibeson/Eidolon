from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from segmented_release_verifier import (  # noqa: E402
    CONTRACT_VERSION,
    DEFAULT_STAGES,
    VerificationStage,
    build_segmented_verifier_manifest,
    run_segmented_verification,
    stage_input_digest,
    validate_stage_definitions,
)

checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


manifest = build_segmented_verifier_manifest(source_root=ROOT)
require(manifest["ok"] is True)
require(manifest["contract_version"] == CONTRACT_VERSION == "v1250.1")
require(manifest["stage_count"] == len(DEFAULT_STAGES) == 10)
require(manifest["independently_runnable"] is True)
require(manifest["partial_receipts_supported"] is True)
require(manifest["exact_resume_supported"] is True)
require(manifest["stale_receipt_rejected"] is True)
require(manifest["clean_external_snapshot_default"] is True)
require(manifest["repository_size_thresholds_used"] is False)
require(len(manifest["manifest_digest"]) == 64)
require([row["ordinal"] for row in manifest["stages"]] == list(range(1, 11)))
require(len({row["stage_id"] for row in manifest["stages"]}) == 10)
require(all(row["input_file_count"] > 0 for row in manifest["stages"]))
require(all(len(row["input_digest"]) == 64 for row in manifest["stages"]))
require(all(len(row["stage_manifest_digest"]) == 64 for row in manifest["stages"]))
require(all(row["authority_state"] == "verification_only_no_release_authority" for row in manifest["stages"]))
require(validate_stage_definitions(DEFAULT_STAGES, source_root=ROOT) == [])

expected_ids = [
    "source-privacy",
    "authority-approval",
    "conversation-command",
    "development-lifecycle",
    "apply-rollback",
    "queue-execution-recovery",
    "cognition-lessons",
    "provider-project-governance",
    "dashboard-interface",
    "retained-checkpoints",
]
require([row["stage_id"] for row in manifest["stages"]] == expected_ids)

release_verify_text = (ROOT / "tools/release_verify.py").read_text(encoding="utf-8")
for stage_name in (
    "v1250.0-authoritative-cleanup-baseline",
    "v1250.1-segmented-broad-verifier",
    "v1250.2-hermetic-verification-runtime",
):
    # The active and retained historical profile inventories may both name a
    # stage. Registration is the contract; an exact source-text count is not.
    require(release_verify_text.count(f'"{stage_name}"') >= 2)
require("tools/v1250_0_authoritative_cleanup_baseline_tests.py" in release_verify_text)
require("tools/v1250_1_segmented_broad_verifier_tests.py" in release_verify_text)
require("tools/v1250_2_hermetic_verification_runtime_tests.py" in release_verify_text)
cli_text = (ROOT / "tools/segmented_release_verify.py").read_text(encoding="utf-8")
require("--list-stages" in cli_text)
require("--resume-receipt" in cli_text)
require("--receipt" in cli_text)

with tempfile.TemporaryDirectory(prefix="eidolon-v1250-1-fixture-") as temp_text:
    temp = Path(temp_text)
    source = temp / "source"
    tools = source / "tools"
    inputs = source / "inputs"
    tools.mkdir(parents=True)
    inputs.mkdir(parents=True)
    (inputs / "a.txt").write_text("alpha\n", encoding="utf-8")
    (inputs / "b.txt").write_text("beta\n", encoding="utf-8")
    (tools / "pass_a.py").write_text(
        "import json\nprint(json.dumps({'ok': True, 'passed': 3, 'total': 3}))\n",
        encoding="utf-8",
    )
    (tools / "pass_b.py").write_text(
        "import json\nprint(json.dumps({'ok': True, 'passed': 2, 'total': 2}))\n",
        encoding="utf-8",
    )
    (tools / "fail.py").write_text(
        "import json,sys\nprint(json.dumps({'ok': False, 'passed': 0, 'total': 1}))\nsys.exit(1)\n",
        encoding="utf-8",
    )
    (tools / "slow.py").write_text(
        "import time\ntime.sleep(5)\nprint('{\"ok\": true}')\n",
        encoding="utf-8",
    )

    stage_a = VerificationStage(
        "fixture-a",
        "Fixture A",
        ("tools/pass_a.py",),
        ("inputs/a.txt", "tools/pass_a.py"),
        10,
        "release",
    )
    stage_b = VerificationStage(
        "fixture-b",
        "Fixture B",
        ("tools/pass_b.py",),
        ("inputs/b.txt", "tools/pass_b.py"),
        10,
        "release",
    )
    fail_stage = VerificationStage(
        "fixture-fail",
        "Fixture failure",
        ("tools/fail.py",),
        ("tools/fail.py",),
        10,
        "release",
    )
    slow_stage = VerificationStage(
        "fixture-timeout",
        "Fixture timeout",
        ("tools/slow.py",),
        ("tools/slow.py",),
        1,
        "release",
    )
    stages = (stage_a, stage_b)
    require(validate_stage_definitions(stages, source_root=source) == [])
    state_a = stage_input_digest(stage_a, source_root=source)
    require(state_a["input_file_count"] == 2)
    require(len(state_a["input_digest"]) == 64)
    require(len(state_a["stage_state_digest"]) == 64)

    receipt = temp / "receipts" / "session.json"
    run = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-a", "fixture-b"],
        receipt_path=receipt,
        stages=stages,
    )
    require(run["ok"] is True)
    require(run["status"] == "segmented_verification_complete")
    require(run["requested_stage_count"] == 2)
    require(run["completed_stage_count"] == 2)
    require(run["executed_stage_count"] == 2)
    require(run["reused_stage_count"] == 0)
    require(run["failed_stage_count"] == 0)
    require(run["resumable_next_stage"] is None)
    require(run["partial_receipt"] is False)
    require(run["source_unchanged"] is True)
    require(run["runtime_cleanup_ok"] is True)
    require(run["snapshot_enabled"] is True)
    require(run["snapshot_receipt"]["snapshot_external_to_source"] is True)
    require(receipt.is_file())
    persisted = json.loads(receipt.read_text(encoding="utf-8"))
    require(persisted["ok"] is True)
    require(persisted["session_receipt_digest"] == run["session_receipt_digest"])
    require([row["status"] for row in run["stage_receipts"]] == ["passed", "passed"])
    require(all(row["runtime_debris_scan"]["ok"] for row in run["stage_receipts"]))
    require(all(row["suite_receipts"][0]["parsed_json"]["ok"] is True for row in run["stage_receipts"]))
    require(all("stdout" not in row["suite_receipts"][0] for row in run["stage_receipts"]))
    require(all("stderr" not in row["suite_receipts"][0] for row in run["stage_receipts"]))

    resumed = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-a", "fixture-b"],
        resume_receipt=run,
        stages=stages,
    )
    require(resumed["ok"] is True)
    require(resumed["executed_stage_count"] == 0)
    require(resumed["reused_stage_count"] == 2)
    require([row["status"] for row in resumed["stage_receipts"]] == ["reused_pass", "reused_pass"])
    require(all(row["reused_without_execution"] for row in resumed["stage_receipts"]))

    (inputs / "b.txt").write_text("beta changed\n", encoding="utf-8")
    stale = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-a", "fixture-b"],
        resume_receipt=run,
        stages=stages,
    )
    require(stale["ok"] is True)
    require(stale["reused_stage_count"] == 1)
    require(stale["executed_stage_count"] == 1)
    require(stale["stage_receipts"][0]["status"] == "reused_pass")
    require(stale["stage_receipts"][1]["status"] == "passed")
    require(stale["stage_receipts"][1]["input_digest"] != run["stage_receipts"][1]["input_digest"])

    blocked = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-a", "fixture-fail", "fixture-b"],
        stages=(stage_a, fail_stage, stage_b),
    )
    require(blocked["ok"] is False)
    require(blocked["status"] == "segmented_verification_blocked")
    require(blocked["completed_stage_count"] == 1)
    require(blocked["failed_stage_count"] == 1)
    require(blocked["resumable_next_stage"] == "fixture-fail")
    require(blocked["partial_receipt"] is True)
    require(len(blocked["stage_receipts"]) == 2)
    require(blocked["stage_receipts"][1]["status"] == "failed")
    require(blocked["stage_receipts"][1]["suite_receipts"][0]["returncode"] == 1)

    timed = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-timeout"],
        stages=(slow_stage,),
    )
    require(timed["ok"] is False)
    require(timed["status"] == "segmented_verification_blocked")
    require(timed["resumable_next_stage"] == "fixture-timeout")
    require(timed["stage_receipts"][0]["status"] == "timeout")
    require(timed["stage_receipts"][0]["suite_receipts"][0]["timed_out"] is True)
    require(timed["stage_receipts"][0]["suite_receipts"][0]["process_group_terminated"] is True)
    # Windows process-tree teardown can add several seconds after the one-second
    # suite timeout. Keep a bounded wall-clock assertion without conflating that
    # cleanup latency with a verifier timeout failure.
    require(timed["elapsed_seconds"] < 8)

    unknown = run_segmented_verification(
        source_root=source,
        stage_ids=["missing"],
        stages=stages,
    )
    require(unknown["ok"] is False)
    require(unknown["status"] == "segmented_verification_request_blocked")
    require(unknown["unknown_stage_ids"] == ["missing"])

    duplicate = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-a", "fixture-a"],
        stages=stages,
    )
    require(duplicate["ok"] is False)
    require(duplicate["duplicate_stage_request"] is True)

    inside_receipt = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-a"],
        receipt_path=source / "receipt.json",
        stages=stages,
    )
    require(inside_receipt["ok"] is False)
    require(inside_receipt["status"] == "receipt_path_inside_source_blocked")
    require(not (source / "receipt.json").exists())

    private_resume = run_segmented_verification(
        source_root=source,
        stage_ids=["fixture-a"],
        resume_receipt={"content": "private", "stage_receipts": []},
        stages=stages,
    )
    require(private_resume["ok"] is False)
    require(private_resume["status"] == "private_resume_receipt_blocked")

    invalid = VerificationStage("Bad Stage", "bad", ("../bad.py",), (), 0, "release")
    errors = validate_stage_definitions((invalid,), source_root=source)
    require("invalid_stage_id" in errors)
    require("stage_without_input_globs" in errors)
    require("invalid_stage_budget" in errors)
    require("invalid_suite_path" in errors)

for key in (
    "installation_authorized",
    "promotion_authorized",
    "certification_authorized",
    "release_authorized",
    "provider_contact_authorized",
    "project_mutation_authorized",
    "source_mutation_authorized",
    "independent_authority_granted",
):
    require(manifest.get(key) is False)

result = {
    "suite": "v1250.1-segmented-broad-verifier",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
