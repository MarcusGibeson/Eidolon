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
from persistent_development_sessions_checkpoint import build_persistent_development_sessions_checkpoint
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
report = build_persistent_development_sessions_checkpoint(source_root=ROOT)
details = report["details"]
validation = validate_checkpoint_report(report)
manifest = checkpoint_registry_manifest(source_root=ROOT)
record = lookup_checkpoint("1256.9")

require(report["ok"] is True and validation["ok"] is True, "checkpoint_report_ok")
require(report["checkpoint_version"] == "1256.9" and report["contract_version"] == "v1256.9" and report["registry_contract_version"] == "v1250.4", "checkpoint_version_and_registry_contract")
require(report["status"] == "persistent_development_sessions_checkpoint_ready", "checkpoint_status_exact")
require(all(report["checks"].values()), "all_structural_checkpoint_checks_pass")
require(report["read_only"] is True and report["content_free"] is True, "checkpoint_read_only_content_free")
require(report["provider_contact_authorized"] is False and report["commands_executed"] is False and report["tests_executed"] is False, "checkpoint_executes_nothing")
require(report["source_mutation_authorized"] is False and report["project_mutation_authorized"] is False, "checkpoint_mutates_nothing")
require(report["installation_authorized"] is False and report["release_authorized"] is False, "checkpoint_grants_no_install_or_release_authority")
require(report["independent_authority_granted"] is False, "checkpoint_grants_no_independent_authority")
require(details["requirements_preserved_across_restart"] is True, "requirements_continuity_recorded")
require(details["plans_preserved_across_restart"] is True, "plan_continuity_recorded")
require(details["attempt_and_verification_evidence_preserved"] is True, "attempt_evidence_continuity_recorded")
require(details["duplicate_execution_authorized"] is False and details["automatic_resume_authorized"] is False, "resume_and_duplicate_execution_denied")
require(details["provider_contact_authorized"] is False and details["project_mutation_authorized"] is False, "provider_and_project_mutation_denied")
require(details["installation_authorized"] is False and details["promotion_authorized"] is False and details["certification_authorized"] is False, "install_promotion_certification_denied")
require(details["permanent_approval_granted"] is False and details["independent_authority_granted"] is False, "permanent_and_independent_authority_denied")
require(details["native_windows_lock_long_path_restart_validation"] == "desktop_review_required", "native_windows_review_honest")
require(len(details["behavioral_evidence"]) == 3, "three_retained_v1256_behavioral_suites_named")
require(details["present_source_count"] == details["required_source_count"] == 8, "required_checkpoint_surfaces_hashed")
require(all(len(value) == 64 for value in details["source_sha256"].values()), "checkpoint_source_hashes_complete")
require(tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1256, 9), "release_metadata_retains_v1256_9_or_later")
require("desktop_codex_review" in CODEX_REVIEW_STATE, "desktop_review_state_retained")
require(bool(NEXT_BOUNDED_UNIT), "later_source_next_bounded_unit_present")
require(record is not None and record.test_selector == "tools/v1256_9_persistent_development_sessions_checkpoint_tests.py", "checkpoint_registry_selector_exact")
require(record is not None and record.lifecycle == "persistent_development_sessions_arc", "checkpoint_registry_lifecycle_exact")
require(manifest["ok"] and tuple(int(part) for part in manifest["working_source_version"].split(".")) >= (1256, 9), "checkpoint_registry_manifest_retains_v1256_or_later")
for version, selector in {
    "1256.0": "tools/v1256_0_2_persistent_development_session_foundations_tests.py",
    "1256.3": "tools/v1256_3_5_persistent_development_session_integration_tests.py",
    "1256.6": "tools/v1256_6_8_persistent_development_session_reliability_tests.py",
    "1256.9": "tools/v1256_9_persistent_development_sessions_checkpoint_tests.py",
}.items():
    row = lookup_checkpoint(version)
    require(row is not None and row.test_selector == selector and row.lifecycle == "persistent_development_sessions_arc", f"registry_selector_{version}_coherent")

for name in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md"):
    text = (ROOT / name).read_text(encoding="utf-8").split('<details id="retained-pre-v1250-compatibility">', 1)[0]
    require("v1256.9" in text, f"{name}_current_checkpoint_visible")
    require("v1257" in text, f"{name}_v1257_lineage_visible")
require("## Next bounded unit" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "later_arc_next_unit_boundary_retained")
require(source_signature() == before, "checkpoint_builder_preserves_source_immutability")

print(json.dumps({
    "ok": True,
    "suite": "v1256.9-persistent-development-sessions-checkpoint",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "read_only_checkpoint": True,
    "native_provider_contacted": False,
    "installation_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}, indent=2, sort_keys=True))
