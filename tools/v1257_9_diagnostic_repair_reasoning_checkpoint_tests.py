from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from checkpoint_registry import checkpoint_registry_manifest, lookup_checkpoint, validate_checkpoint_report
from diagnostic_repair_reasoning_checkpoint import build_diagnostic_repair_reasoning_checkpoint
from release_authority import CODEX_REVIEW_STATE, NEXT_BOUNDED_UNIT, PREVIOUS_WORKING_SOURCE_VERSION, WORKING_SOURCE_VERSION

CHECKS: list[str] = []


def require(condition: bool, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def source_signature() -> str:
    rows: list[tuple[str, str]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel or rel.endswith((".pyc", ".pyo")):
            continue
        rows.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8")).hexdigest()


before = source_signature()
report = build_diagnostic_repair_reasoning_checkpoint(source_root=ROOT)
details = report["details"]
validation = validate_checkpoint_report(report)
manifest = checkpoint_registry_manifest(source_root=ROOT)
record = lookup_checkpoint("1257.9")

require(report["ok"] is True and validation["ok"] is True, "checkpoint_report_ok")
require(report["checkpoint_version"] == "1257.9" and report["contract_version"] == "v1257.9", "checkpoint_version_exact")
require(report["status"] == "diagnostic_repair_reasoning_checkpoint_ready", "checkpoint_status_exact")
require(all(report["checks"].values()), "all_structural_checkpoint_checks_pass")
require(report["read_only"] is True and report["content_free"] is True, "checkpoint_read_only_content_free")
require(report["provider_contact_authorized"] is False and report["commands_executed"] is False and report["tests_executed"] is False, "checkpoint_executes_nothing")
require(report["source_mutation_authorized"] is False and report["project_mutation_authorized"] is False, "checkpoint_mutates_nothing")
require(report["installation_authorized"] is False and report["release_authorized"] is False, "checkpoint_grants_no_install_or_release")
require(report["independent_authority_granted"] is False, "checkpoint_grants_no_independent_authority")
require(details["competing_explanations_required"] is True and details["root_cause_proven_by_default"] is False, "competing_explanations_without_false_root_cause")
require(details["focused_diagnostics_bounded"] is True, "focused_diagnostics_bounded")
require(details["repeated_failed_repair_blocked"] is True, "repeated_failed_repair_blocked")
require(details["environment_failure_can_block_repair"] is True, "environment_failure_can_block_repair")
require(details["persistent_session_diagnostic_lineage"] is True, "persistent_session_diagnostic_lineage")
require(details["provider_contact_authorized"] is False and details["diagnostic_execution_authorized"] is False and details["repair_authorized"] is False, "diagnostic_authority_denied")
require(details["project_mutation_authorized"] is False, "project_mutation_denied")
require(details["installation_authorized"] is False and details["promotion_authorized"] is False and details["certification_authorized"] is False, "install_promotion_certification_denied")
require(details["permanent_approval_granted"] is False and details["independent_authority_granted"] is False, "permanent_independent_authority_denied")
require(details["native_windows_cross_process_diagnostic_validation"] == "desktop_review_required", "native_windows_review_honest")
require(len(details["behavioral_evidence"]) == 3, "three_behavioral_suites_named")
require(details["present_source_count"] == details["required_source_count"] == 9, "required_checkpoint_surfaces_hashed")
require(all(len(value) == 64 for value in details["source_sha256"].values()), "checkpoint_hashes_complete")
require(tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1257, 9), "release_metadata_retains_v1257_9_or_later")
require("desktop_codex_review" in CODEX_REVIEW_STATE, "desktop_review_state_retained")
require(bool(NEXT_BOUNDED_UNIT), "later_source_next_bounded_unit_retained")
require(record is not None and record.test_selector == "tools/v1257_9_diagnostic_repair_reasoning_checkpoint_tests.py", "checkpoint_selector_exact")
require(record is not None and record.lifecycle == "diagnostic_repair_reasoning_arc", "checkpoint_lifecycle_exact")
require(manifest["ok"] and tuple(int(part) for part in manifest["working_source_version"].split(".")) >= (1257, 9), "registry_manifest_retains_v1257_or_later")
for version, selector in {
    "1257.0": "tools/v1257_0_2_diagnostic_repair_reasoning_foundations_tests.py",
    "1257.3": "tools/v1257_3_5_diagnostic_repair_reasoning_integration_tests.py",
    "1257.6": "tools/v1257_6_8_diagnostic_repair_reasoning_reliability_tests.py",
    "1257.9": "tools/v1257_9_diagnostic_repair_reasoning_checkpoint_tests.py",
}.items():
    row = lookup_checkpoint(version)
    require(row is not None and row.test_selector == selector and row.lifecycle == "diagnostic_repair_reasoning_arc", f"registry_selector_{version}_coherent")
for name in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md"):
    active = (ROOT / name).read_text(encoding="utf-8").split('<details id="retained-pre-v1250-compatibility">', 1)[0]
    require("v1257.9" in active, f"{name}_current_checkpoint_visible")
    require("v1258" in active, f"{name}_next_section_visible")
require("## Next bounded unit" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "later_arc_next_unit_boundary_retained")
require(source_signature() == before, "checkpoint_builder_preserves_source_immutability")

print(json.dumps({
    "ok": True,
    "suite": "v1257.9-diagnostic-repair-reasoning-checkpoint",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "read_only_checkpoint": True,
    "native_provider_contacted": False,
    "installation_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}, indent=2, sort_keys=True))
