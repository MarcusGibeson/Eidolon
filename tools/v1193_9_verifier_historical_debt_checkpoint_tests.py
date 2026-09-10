from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1193-9-data-"))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.fixture_historical_debt_consolidation import (
    consolidate_fixture_records,
    create_fixture_record,
    public_consolidation_summary,
)
from conscious_agent.verifier_historical_debt_checkpoint import (
    CONTRACT_VERSION,
    _digest,
    _validate_public_snapshot,
    build_verifier_historical_debt_checkpoint,
)
from conscious_agent.verifier_ownership import (
    build_ownership_registry,
    create_verifier_record,
    public_ownership_summary,
)
from conscious_agent.verifier_profile_reconciliation import (
    create_profile_result,
    public_profile_summary,
    reconcile_profile,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


with tempfile.TemporaryDirectory(prefix="eidolon-v1193-9-suite-") as temp:
    report = build_verifier_historical_debt_checkpoint(
        source_root=ROOT,
        runtime_root=Path(temp) / "runtime",
    )

for key, expected in (
    ("ok", True),
    ("contract_version", "v1193.9"),
    ("checkpoint_id", "verifier-ownership-historical-debt:v1193.9"),
    ("read_only", True),
    ("post_available", False),
    ("content_free", True),
    ("source_unchanged", True),
    ("runtime_mutated", False),
    ("production_source_modified", False),
    ("fixture_deleted", False),
    ("verifier_retired", False),
    ("global_profile_pass_claimed", False),
    ("provider_contacted", False),
    ("model_contacted", False),
    ("thread_started", False),
    ("process_started", False),
    ("execution_invoked", False),
    ("approval_consumed", False),
    ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 90)
require(report["validation_errors"] == [])
require(len(report["limitations"]) == 5)
require("v1200" in report["limitations"][-1])

summary = report["summary"]
expected_summary = {
    "contract_version": "v1193.9",
    "checkpoint_id": "verifier-ownership-historical-debt:v1193.9",
    "ownership_record_count": 6,
    "owner_count": 5,
    "current_regression_count": 1,
    "retained_checkpoint_count": 3,
    "historical_debt_count": 2,
    "profile_count": 3,
    "focused_current_pass": True,
    "focused_global_pass": True,
    "quick_current_pass": True,
    "quick_global_pass": False,
    "full_current_pass": True,
    "full_global_pass": False,
    "inherited_nonpass_count": 1,
    "fixture_record_count": 4,
    "fixture_group_count": 3,
    "alias_count": 1,
    "deferred_count": 1,
    "cleanup_owner_count": 2,
    "historical_truth_preserved": True,
    "current_regressions_separate": True,
    "profile_membership_deterministic": True,
    "cleanup_ownership_assigned": True,
    "fixture_deleted": False,
    "verifier_retired": False,
    "suite_execution_invoked": False,
    "runtime_mutated": False,
    "production_source_modified": False,
    "global_profile_pass_claimed": False,
    "authority_state": "separate_not_granted",
}
for key, expected in expected_summary.items():
    require(summary.get(key) == expected)
require(len(summary["checkpoint_digest"]) == 64)
require(summary["checkpoint_digest"] == _digest({k: v for k, v in summary.items() if k != "checkpoint_digest"}))
require(_validate_public_snapshot(summary) == [])

for version in ("v1193.2", "v1193.5", "v1193.8"):
    retained = report["retained_checkpoints"][version]
    require(retained["passed"] == retained["total"])
    require(retained["total"] > 0)

blocked_names = (
    "private-field", "authority", "fixture-delete", "verifier-retire", "suite-execution",
    "runtime-mutation", "source-mutation", "global-pass-claim", "truth-loss",
    "boundary-loss", "membership-drift", "cleanup-owner-loss", "tamper",
)
for name in blocked_names:
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))
for error in (
    "private_field", "authority_expansion", "invalid_fixture_deleted",
    "invalid_verifier_retired", "invalid_suite_execution_invoked", "invalid_runtime_mutated",
    "invalid_production_source_modified", "invalid_global_profile_pass_claimed",
    "historical_truth_loss", "current_debt_boundary_loss", "profile_membership_drift",
    "cleanup_ownership_missing", "checkpoint_tamper",
):
    require(any(error in errors for errors in report["blocked_cases"].values()))

# Ownership remains deterministic and separates current work from inherited debt.
ownership_rows = [
    create_verifier_record(
        verifier_id="current", owner="release", classification="current_regression",
        suite_path="tools/current.py", source_version="1193.9", fixture_group="current",
        expected_checks=10, budget_seconds=15, profile_membership=("focused", "quick", "full"),
    ),
    create_verifier_record(
        verifier_id="retained", owner="runtime", classification="retained_checkpoint",
        suite_path="tools/retained.py", source_version="1192.9", fixture_group="retained",
        expected_checks=20, budget_seconds=30, profile_membership=("quick", "full"),
    ),
    create_verifier_record(
        verifier_id="debt", owner="platform", classification="historical_debt",
        suite_path="tools/debt.py", source_version="1180-1189", fixture_group="legacy",
        expected_checks=4, budget_seconds=60, profile_membership=("quick", "full"),
        inherited_from="v1190.9 quick review", debt_severity="high",
    ),
]
ownership_report = build_ownership_registry(ownership_rows)
ownership_summary = public_ownership_summary(ownership_report)
require(ownership_report["status"] == "registered")
require(ownership_report["errors"] == [])
require(ownership_summary["record_count"] == 3)
require(ownership_summary["owner_count"] == 3)
require(ownership_summary["current_regression_count"] == 1)
require(ownership_summary["retained_checkpoint_count"] == 1)
require(ownership_summary["historical_debt_count"] == 1)
require(ownership_summary["debt_separated"] is True)
require(ownership_summary["profile_budgets_seconds"] == {"focused": 15, "full": 105, "quick": 105})
require(ownership_report["execution_invoked"] is False)
require(ownership_report["authority_granted"] is False)

# Focused may pass globally while quick/full preserve inherited non-pass truth.
def profile_rows(profile: str) -> list[dict[str, object]]:
    rows = [create_profile_result(
        verifier_id="current", classification="current_regression", profile=profile, sequence=0,
        expected_checks=10, actual_checks=10, budget_seconds=15,
        elapsed_milliseconds=100, outcome="passed",
    )]
    if profile != "focused":
        rows.extend([
            create_profile_result(
                verifier_id="retained", classification="retained_checkpoint", profile=profile, sequence=1,
                expected_checks=20, actual_checks=20, budget_seconds=30,
                elapsed_milliseconds=200, outcome="passed",
            ),
            create_profile_result(
                verifier_id="debt", classification="historical_debt", profile=profile, sequence=2,
                expected_checks=4, actual_checks=0, budget_seconds=60,
                elapsed_milliseconds=300, outcome="blocked", debt_group="legacy",
            ),
        ])
    return rows

for profile, budget in (("focused", 15), ("quick", 105), ("full", 105)):
    rows = profile_rows(profile)
    reconciled = reconcile_profile(
        profile=profile,
        expected_verifiers=[row["verifier_id"] for row in rows],
        results=rows,
        profile_budget_seconds=budget,
    )
    public = public_profile_summary(reconciled)
    require(reconciled["status"] == "reconciled")
    require(public["profile"] == profile)
    require(public["current_regressions_passed"] is True)
    require(public["within_profile_budget"] is True)
    require(public["historical_debt_separate"] is True)
    require(public["execution_invoked"] is False)
    require(public["authority_granted"] is False)
    require(public["global_profile_pass"] is (profile == "focused"))
    require(public["inherited_nonpass_count"] == (0 if profile == "focused" else 1))

# Fixture aliases and deferred overlaps retain originals and cleanup ownership.
fixture_rows = [
    create_fixture_record(
        fixture_id="canonical", owner="release", cleanup_owner="release",
        fixture_group="historical", suite_path="tools/canonical.py", source_version="v1189.9",
        overlap_class="unique", disposition="retain_independent", expected_checks=72,
    ),
    create_fixture_record(
        fixture_id="alias", owner="release", cleanup_owner="release",
        fixture_group="historical", suite_path="tools/alias.py", source_version="v1189.8",
        overlap_class="exact_duplicate", canonical_fixture_id="canonical",
        disposition="retain_alias", historical_debt_id="debt-alias", debt_severity="medium",
        expected_checks=72,
    ),
    create_fixture_record(
        fixture_id="partial", owner="platform", cleanup_owner="platform",
        fixture_group="legacy", suite_path="tools/partial.py", source_version="v1174.9",
        overlap_class="partial_overlap", canonical_fixture_id="canonical",
        disposition="defer_consolidation", historical_debt_id="debt-partial", debt_severity="high",
        expected_checks=90,
    ),
]
fixture_report = consolidate_fixture_records(fixture_rows)
fixture_public = public_consolidation_summary(fixture_report)
require(fixture_report["status"] == "consolidated")
require(fixture_report["consolidation"]["alias_map"] == {"alias": "canonical"})
require(fixture_public["record_count"] == 3)
require(fixture_public["fixture_group_count"] == 2)
require(fixture_public["alias_count"] == 1)
require(fixture_public["deferred_count"] == 1)
require(fixture_public["cleanup_owner_count"] == 2)
require(fixture_public["historical_truth_preserved"] is True)
require(fixture_public["fixture_deleted"] is False)
require(fixture_public["verifier_retired"] is False)
require(fixture_public["execution_invoked"] is False)
require(fixture_public["authority_granted"] is False)

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry["checkpoints"] if item["checkpoint_id"] == "verifier-historical-debt-checkpoint"), None)
require(row is not None)
require((row or {}).get("contract_version") == CONTRACT_VERSION)
require((row or {}).get("builder") == "build_verifier_historical_debt_checkpoint")
require((row or {}).get("read_only") is True)
require((row or {}).get("post_available") is False)
require((row or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])
for checkpoint_id in (
    "verifier-ownership-checkpoint",
    "verifier-profile-reconciliation-checkpoint",
    "fixture-historical-debt-consolidation-checkpoint",
    "verifier-historical-debt-checkpoint",
):
    require(any(item["checkpoint_id"] == checkpoint_id for item in registry["checkpoints"]))

proc = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "verifier-historical-debt-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1193-9-cli-"),
    },
)
require(proc.returncode == 0)
try:
    cli = json.loads(proc.stdout.strip().splitlines()[-1])
    require(cli["ok"] is True)
    require(cli["contract_version"] == "v1193.9")
    require(cli["summary"]["quick_current_pass"] is True)
    require(cli["summary"]["quick_global_pass"] is False)
except Exception:
    require(False)
    require(False)
    require(False)
    require(False)

status, payload = dispatch_api("GET", "/api/cognition/verifier-historical-debt-checkpoint")
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1193.9")
require(payload["data"]["summary"]["historical_truth_preserved"] is True)
require(payload["data"]["global_profile_pass_claimed"] is False)
status_post, _ = dispatch_api("POST", "/api/cognition/verifier-historical-debt-checkpoint")
require(status_post in {404, 405})

html = render_first_use_shell()
require("verifier-historical-debt-checkpoint-panel" in html)
require("verifier-ownership-checkpoint-panel" in html)
require("verifier-profile-reconciliation-checkpoint-panel" in html)
require("fixture-historical-debt-consolidation-checkpoint-panel" in html)
require("/api/cognition/verifier-historical-debt-checkpoint" in html)
require("global pass not claimed" in html.lower())
require("next bounded unit: v1194.0-v1194.2" in html.lower())

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1193.9-verifier-ownership-historical-debt-checkpoint") == 1)
require(release.count("v1193_9_verifier_historical_debt_checkpoint_tests.py") == 1)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1193.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1193.8"' in metadata)
require("v1193.9 Verifier Ownership and Historical-Debt Consolidation Checkpoint" in metadata)
require("v1194.0-v1194.2 Unified Cognitive and Developer Experience Foundations" in metadata)
require('WORKING_SOURCE_VERSION = "1193.5"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1193.2"' in metadata)

for name in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    require("v1193.9 Verifier Ownership and Historical-Debt Consolidation Checkpoint" in text)
    require("Current source: v1193.9" in text)
    require("deterministic focused/quick/full profile membership and budgets" in text)
    require("partial-overlap deferral" in text)
    require("does not execute suites, delete fixtures, retire verifiers" in text)
    require("global quick/full-profile pass" in text)
    require("v1194.0-v1194.2 Unified Cognitive and Developer Experience Foundations" in text)
    require("v1200" in text)

result = {
    "suite": "v1193.9-verifier-ownership-historical-debt-checkpoint",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
    "global_profile_pass_claimed": False,
    "fixture_deleted": False,
    "verifier_retired": False,
    "suite_execution_invoked": False,
    "authority_expanded": False,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
