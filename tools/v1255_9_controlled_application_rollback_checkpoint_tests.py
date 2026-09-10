from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
for path in (ROOT, ROOT / "conscious_agent"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from checkpoint_registry import checkpoint_registry_manifest, lookup_checkpoint, validate_checkpoint_report
from controlled_application_rollback_checkpoint import build_controlled_application_rollback_checkpoint
from release_authority import CODEX_REVIEW_STATE, NEXT_BOUNDED_UNIT, PREVIOUS_WORKING_SOURCE_VERSION, WORKING_SOURCE_VERSION

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


before = source_signature()
report = build_controlled_application_rollback_checkpoint(source_root=ROOT)
validation = validate_checkpoint_report(report, source_root=ROOT)
manifest = checkpoint_registry_manifest(source_root=ROOT)
record = lookup_checkpoint("1255.9")
details = report.get("details") or {}

require(report["ok"] and report["status"] == "controlled_application_rollback_checkpoint_ready", "checkpoint_ready")
require(report["checkpoint_version"] == "1255.9" and report["contract_version"] == "v1255.9", "checkpoint_version_exact")
require(report["passed"] == report["total"] and all(report["checks"].values()), "checkpoint_structural_checks_all_pass")
require(validation["ok"] and validation["passed"] == validation["total"], "checkpoint_report_schema_valid")
require(report["read_only"] and report["content_free"], "checkpoint_read_only_and_content_free")
require(report["provider_contact_authorized"] is False and report["commands_executed"] is False and report["tests_executed"] is False, "checkpoint_executes_nothing")
require(report["source_mutation_authorized"] is False and report["project_mutation_authorized"] is False, "checkpoint_mutates_nothing")
require(report["release_authorized"] is False and report["independent_authority_granted"] is False, "checkpoint_grants_no_release_or_independent_authority")
require(details["controlled_application_authority_requires_exact_operator_phrase"] is True, "application_authority_exact_operator_phrase")
require(details["rollback_requires_separate_exact_operator_phrase"] is True, "rollback_separate_exact_operator_phrase")
require(details["installation_authorized"] is False and details["promotion_authorized"] is False and details["certification_authorized"] is False, "install_promotion_certification_denied")
require(details["permanent_approval_granted"] is False and details["independent_authority_granted"] is False, "permanent_and_independent_authority_denied")
require(details["native_windows_junction_atomic_replace_validation"] == "desktop_review_required", "native_windows_review_honest")
require(len(details["behavioral_evidence"]) == 3, "three_retained_v1255_behavioral_suites_named")
require(details["present_source_count"] == details["required_source_count"] == 9, "required_checkpoint_surfaces_hashed")
require(all(len(value) == 64 for value in details["source_sha256"].values()), "checkpoint_source_hashes_complete")
require(tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1255, 9), "release_metadata_retains_v1255_or_later")
require(bool(CODEX_REVIEW_STATE), "desktop_review_state_present")
require(bool(NEXT_BOUNDED_UNIT), "next_bounded_unit_present")
require(record is not None and record.test_selector == "tools/v1255_9_controlled_application_rollback_checkpoint_tests.py", "checkpoint_registry_selector_exact")
require(manifest["ok"] and tuple(int(part) for part in manifest["working_source_version"].split(".")) >= (1255, 9), "checkpoint_registry_manifest_retains_v1255_or_later")
for version, selector in {
    "1255.0": "tools/v1255_0_2_controlled_application_foundations_tests.py",
    "1255.3": "tools/v1255_3_5_controlled_application_integration_tests.py",
    "1255.6": "tools/v1255_6_8_controlled_application_reliability_tests.py",
    "1255.9": "tools/v1255_9_controlled_application_rollback_checkpoint_tests.py",
}.items():
    row = lookup_checkpoint(version)
    require(row is not None and row.test_selector == selector and row.lifecycle == "controlled_application_rollback_arc", f"registry_selector_{version}_coherent")

for name in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md"):
    text = (ROOT / name).read_text(encoding="utf-8").split('<details id="retained-pre-v1250-compatibility">', 1)[0]
    require("v1255.9" in text or "v1255" in text, f"{name}_retains_v1255_checkpoint_visible")
require("v1256" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1256_successor_history_visible")
require(source_signature() == before, "checkpoint_builder_preserves_source_immutability")

print(json.dumps({
    "ok": True,
    "suite": "v1255.9-controlled-application-rollback-checkpoint",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "read_only_checkpoint": True,
    "native_provider_contacted": False,
    "installation_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}, indent=2, sort_keys=True))
