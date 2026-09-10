from __future__ import annotations

import hashlib
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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-4-"))

from checkpoint_registry import (  # noqa: E402
    AUTHORITY_FLAGS,
    CONTRACT_VERSION,
    REPORT_SCHEMA,
    build_read_only_checkpoint_report,
    checkpoint_descriptors,
    checkpoint_records,
    checkpoint_registry_manifest,
    inspect_checkpoint_registry,
    lookup_checkpoint,
    resolve_checkpoint_descriptor,
    validate_checkpoint_report,
)
from checkpoint_registry_consolidation_checkpoint import build_checkpoint_registry_consolidation_checkpoint  # noqa: E402
from compatibility_registry_migration_checkpoint import build_compatibility_registry_migration_checkpoint  # noqa: E402
from release_metadata_consolidation_checkpoint import build_release_metadata_consolidation_checkpoint  # noqa: E402

from release_authority import WORKING_SOURCE_VERSION
checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


def digest_paths(paths: list[Path]) -> str:
    rows = []
    for path in paths:
        rows.append(f"{path.relative_to(ROOT).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


watched = [
    ROOT / "conscious_agent/checkpoint_registry.py",
    ROOT / "conscious_agent/release_authority.py",
    ROOT / "conscious_agent/release_metadata.py",
]
before = digest_paths(watched)
records = checkpoint_records()
manifest = checkpoint_registry_manifest(source_root=ROOT)
after = digest_paths(watched)

require(CONTRACT_VERSION == "v1250.4")
require(REPORT_SCHEMA == "eidolon.read-only-checkpoint-report.v1")
require(before == after)
require(manifest["ok"] is True)
require(manifest["status"] == "checkpoint_registry_ready")
require(manifest["contract_version"] == CONTRACT_VERSION)
require(manifest["report_schema"] == REPORT_SCHEMA)
require(manifest["working_source_version"] == WORKING_SOURCE_VERSION)
require(manifest["record_count"] == len(records))
require(manifest["versions"] == [record.version for record in records])
require(len(set(manifest["versions"])) == len(records))
require(manifest["errors"] == [])
require(manifest["single_registry_authority"] is True)
require(manifest["historical_module_deletion_performed"] is False)
require(manifest["checkpoint_execution_performed"] is False)
require(manifest["read_only"] is True)
require(manifest["content_free"] is True)
require(len(manifest["registry_digest"]) == 64)
require(records[0].version == "1200.0")
require(records[-1].version == WORKING_SOURCE_VERSION)
require(lookup_checkpoint("1250.3") is not None)
require(lookup_checkpoint("1250.4") is not None)
require(lookup_checkpoint("1250.9").lifecycle == "cleanup_bundle")
require(records[0].lifecycle == "retained_checkpoint")
require([record.ordinal for record in records] == list(range(1, len(records) + 1)))
require(len({record.checkpoint_id for record in records}) == len(records))
require(all(record.test_selector.startswith("tools/v") for record in records))
require(all(row["test_path_count"] == 1 for row in manifest["records"]))
require(all(len(row["test_paths"]) == 1 for row in manifest["records"]))
require(all(len(row["test_paths_digest"]) == 64 for row in manifest["records"]))
require(all(len(row["record_digest"]) == 64 for row in manifest["records"]))
require(all(row["authority_state"] == "evidence_only_no_authority" for row in manifest["records"]))
require(manifest["records"][8]["version"] == "1208.9.1")
require(manifest["records"][8]["test_paths"] == ["tools/v1208_9_python_test_adapter_checkpoint_tests.py"])
require(next(row for row in manifest["records"] if row["version"]=="1250.3")["test_paths"] == ["tools/v1250_3_release_metadata_consolidation_tests.py"])
require(next(row for row in manifest["records"] if row["version"]=="1250.4")["test_paths"] == ["tools/v1250_4_checkpoint_registry_consolidation_tests.py"])
require(next(row for row in manifest["records"] if row["version"]=="1250.5")["test_paths"] == ["tools/v1250_5_compatibility_registry_migration_tests.py"])
require(next(row for row in manifest["records"] if row["version"]=="1250.6")["test_paths"] == ["tools/v1250_6_self_maintenance_signature_primitive_decomposition_tests.py"])
require(next(row for row in manifest["records"] if row["version"]=="1250.7")["test_paths"] == ["tools/v1250_7_dashboard_shell_decomposition_tests.py"])
require(next(row for row in manifest["records"] if row["version"]=="1250.8")["test_paths"] == ["tools/v1250_8_api_catalog_http_runtime_decomposition_tests.py"])
require(next(row for row in manifest["records"] if row["version"]=="1250.9")["test_paths"] == ["tools/v1250_9_cleanup_verification_hardening_checkpoint_tests.py"])

legacy_descriptors = checkpoint_descriptors(source_root=ROOT)
legacy_registry = inspect_checkpoint_registry(source_root=ROOT)
legacy_mindful = resolve_checkpoint_descriptor(
    "mindful-execution-alpha-integration-benchmark-checkpoint", source_root=ROOT
)
require(legacy_registry["contract_version"] == "v1150.2")
require(legacy_registry["checkpoint_count"] == len(legacy_descriptors) >= 300)
require(legacy_registry["duplicate_checkpoint_ids"] == [])
require(legacy_registry["duplicate_builder_targets"] == [])
require(legacy_registry["all_compatibility_targets_available"] is True)
require(legacy_registry["all_required_inputs_dispatch_supported"] is True)
require(legacy_mindful["builder"] == "build_mindful_execution_alpha_integration_benchmark_checkpoint")
require(legacy_mindful["read_only"] is True)
require(manifest["legacy_descriptor_contract_version"] == "v1150.2")
require(manifest["legacy_descriptor_count"] == len(legacy_descriptors))

record_1249 = lookup_checkpoint("1249.9")
record_1250_4 = lookup_checkpoint("1250.4")
require(record_1249 is not None)
require(record_1249.title == "Feature Freeze and Final Hardening")
require(record_1250_4 is not None)
require(record_1250_4.title == "Checkpoint Registry Consolidation")
require(lookup_checkpoint("9999.9") is None)

report = build_read_only_checkpoint_report(
    version="1250.4",
    status="fixture_checkpoint_ready",
    checks={"alpha": True, "beta": True, "gamma": True},
    source_root=ROOT,
    details={"fixture": "content_free"},
)
validation = validate_checkpoint_report(report, source_root=ROOT)
require(report["ok"] is True)
require(report["status"] == "fixture_checkpoint_ready")
require(report["schema"] == REPORT_SCHEMA)
require(report["contract_version"] == "v1250.4")
require(report["registry_contract_version"] == CONTRACT_VERSION)
require(report["checkpoint_version"] == "1250.4")
require(report["checkpoint_title"] == "Checkpoint Registry Consolidation")
require(report["passed"] == report["total"] == 3)
require(report["details"] == {"fixture": "content_free"})
require(len(report["checkpoint_receipt_digest"]) == 64)
require(validation["ok"] is True)
require(validation["passed"] == validation["total"] == 11)
require(all(validation["checks"].values()))

tampered = dict(report)
tampered["checkpoint_title"] = "tampered"
require(validate_checkpoint_report(tampered, source_root=ROOT)["ok"] is False)
failed = build_read_only_checkpoint_report(version="1250.4", status="fixture", checks={"alpha": True, "beta": False}, source_root=ROOT)
require(failed["ok"] is False)
require(failed["status"] == "fixture_blocked")
require(validate_checkpoint_report(failed, source_root=ROOT)["ok"] is False)
try:
    build_read_only_checkpoint_report(version="9999.9", status="x", checks={"x": True}, source_root=ROOT)
except ValueError as exc:
    require(str(exc) == "checkpoint_version_not_registered")
else:
    require(False)

bundle_reports = [
    build_release_metadata_consolidation_checkpoint(source_root=ROOT),
    build_checkpoint_registry_consolidation_checkpoint(source_root=ROOT),
    build_compatibility_registry_migration_checkpoint(source_root=ROOT),
]
require([row["checkpoint_version"] for row in bundle_reports] == ["1250.3", "1250.4", "1250.5"])
require(all(row["ok"] is True for row in bundle_reports))
require(all(validate_checkpoint_report(row, source_root=ROOT)["ok"] is True for row in bundle_reports))
require(bundle_reports[1]["status"] == "checkpoint_registry_consolidation_ready")
require(bundle_reports[1]["details"]["record_count"] == len(records))

source = (ROOT / "conscious_agent/checkpoint_registry.py").read_text(encoding="utf-8")
require("importlib" not in source)
require("subprocess" not in source)
require("eval(" not in source)
require("exec(" not in source)
require("checkpoint_execution_performed" in source)
require("evidence_only_no_authority" in source)

for key, expected in AUTHORITY_FLAGS.items():
    require(expected is False)
    require(manifest[key] is False)
    require(report[key] is False)

result = {"suite": "v1250.4-checkpoint-registry-consolidation", "ok": all(checks), "passed": sum(checks), "total": len(checks)}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
