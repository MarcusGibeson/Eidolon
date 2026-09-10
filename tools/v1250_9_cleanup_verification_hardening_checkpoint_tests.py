from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-9-"))

from checkpoint_registry import (  # noqa: E402
    checkpoint_registry_manifest,
    lookup_checkpoint,
    validate_checkpoint_report,
)
from cleanup_verification_hardening import (  # noqa: E402
    AUTHORITY_FLAGS,
    CONTRACT_VERSION,
    EXPECTED_STAGE_IDS,
    validate_cleanup_verification_hardening,
)
from cleanup_verification_hardening_checkpoint import (  # noqa: E402
    build_cleanup_verification_hardening_checkpoint,
)
from hermetic_verification_runtime import run_bounded_command  # noqa: E402
import segmented_release_verifier as verifier  # noqa: E402

from release_authority import CODEX_REVIEW_STATE
checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


validation = validate_cleanup_verification_hardening(source_root=ROOT)
checkpoint = build_cleanup_verification_hardening_checkpoint(source_root=ROOT)
checkpoint_validation = validate_checkpoint_report(checkpoint, source_root=ROOT)
manifest = verifier.build_segmented_verifier_manifest(source_root=ROOT)
registry = checkpoint_registry_manifest(source_root=ROOT)
record = lookup_checkpoint("1250.9")

require(CONTRACT_VERSION == "v1250.9")
require(validation["ok"] is True)
require(validation["passed"] == validation["total"] == 16)
require(tuple(validation["stage_ids"]) == EXPECTED_STAGE_IDS)
require(validation["stage_count"] == 10)
require(validation["retained_suite_count"] >= 11)
require(validation["per_suite_timeout_seconds"] == verifier.DEFAULT_SUITE_TIMEOUT_SECONDS == 240)
require(validation["codex_review_state"] == CODEX_REVIEW_STATE)
require(all(validation["checks"].values()))
require(manifest["suite_level_progress_receipts"] is True)
require(manifest["per_suite_runtime_isolation"] is True)
require(manifest["per_suite_timeout_seconds"] == verifier.DEFAULT_SUITE_TIMEOUT_SECONDS == 240)
require(registry["ok"] is True)
require(registry["record_count"] >= 60)
require(record is not None)
require(record.title == "Cleanup and Verification Hardening Checkpoint")
require(checkpoint["ok"] is True)
require(checkpoint["checkpoint_version"] == "1250.9")
require(checkpoint["status"] == "cleanup_verification_hardening_checkpoint_ready")
require(checkpoint["passed"] == checkpoint["total"] == 6)
require(checkpoint_validation["ok"] is True)
require(checkpoint_validation["passed"] == checkpoint_validation["total"])

# A successful direct child must not leave an inherited stdout handle capable
# of holding the verifier open forever. The fixture child deliberately sleeps.
with tempfile.TemporaryDirectory(prefix="eidolon-v1250-9-process-") as tmp:
    fixture = Path(tmp) / "leaky_child.py"
    fixture.write_text(
        "import json, subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "print(json.dumps({'ok': True, 'suite': 'residual-child-fixture'}), flush=True)\n",
        encoding="utf-8",
    )
    started = time.monotonic()
    command = run_bounded_command(
        (sys.executable, str(fixture)),
        cwd=ROOT,
        env=dict(os.environ),
        timeout_seconds=8,
    )
    elapsed = time.monotonic() - started
require(command.ok is True)
require(command.timed_out is False)
require(command.returncode == 0)
require(command.residual_process_group_terminated is True)
require(elapsed < 8)
require(command.parsed_json is not None and command.parsed_json["ok"] is True)

# Capture intermediate atomic receipts from a tiny manifest fixture. This
# proves progress is written before and after each suite, not merely promised.
with tempfile.TemporaryDirectory(prefix="eidolon-v1250-9-progress-") as tmp:
    fixture_root = Path(tmp) / "source"
    (fixture_root / "tools").mkdir(parents=True)
    for index in (1, 2):
        (fixture_root / "tools" / f"suite_{index}.py").write_text(
            "import json\nprint(json.dumps({'ok': True, 'suite': 'fixture'}))\n",
            encoding="utf-8",
        )
    stage = verifier.VerificationStage(
        "fixture-stage",
        "Fixture stage",
        ("tools/suite_1.py", "tools/suite_2.py"),
        ("tools/*.py",),
        30,
        "fixture",
    )
    captured: list[dict] = []
    original_write = verifier.atomic_write_json
    try:
        verifier.atomic_write_json = lambda path, payload, source_root: captured.append(dict(payload)) or {"ok": True}
        result = verifier.run_segmented_verification(
            source_root=fixture_root,
            receipt_path=Path(tmp) / "receipt.json",
            stage_ids=("fixture-stage",),
            stages=(stage,),
        )
    finally:
        verifier.atomic_write_json = original_write
require(result["status"] == "segmented_verification_complete")
require(result["stage_receipts"][0]["completed_suite_count"] == 2)
require(any(row.get("active_phase") == "suite_running" for row in captured))
require(any(row.get("active_phase") == "suite_completed" for row in captured))
require(any(row.get("active_suite_index") == 2 for row in captured))

for key, expected in AUTHORITY_FLAGS.items():
    require(expected is False)
    require(validation[key] is False)
    require(checkpoint.get(key, False) is False)

result = {
    "suite": "v1250.9-cleanup-verification-hardening-checkpoint",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
