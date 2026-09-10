from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-5-"))

from checkpoint_registry import validate_checkpoint_report  # noqa: E402
from compatibility_registry import (  # noqa: E402
    AUTHORITY_FLAGS,
    CONTRACT_VERSION,
    LEGACY_FACADE_RELATIVE_PATH,
    REGISTRY_RELATIVE_PATH,
    compatibility_text,
    load_compatibility_registry,
    validate_compatibility_registry,
)
from compatibility_registry_migration_checkpoint import build_compatibility_registry_migration_checkpoint  # noqa: E402
from release_metadata_consolidation import render_agent_release_metadata  # noqa: E402

from release_authority import WORKING_SOURCE_VERSION, PREVIOUS_WORKING_SOURCE_VERSION
checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


registry = load_compatibility_registry(source_root=ROOT)
validation = validate_compatibility_registry(source_root=ROOT)
checkpoint = build_compatibility_registry_migration_checkpoint(source_root=ROOT)
checkpoint_validation = validate_checkpoint_report(checkpoint, source_root=ROOT)
facade = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
legacy = (ROOT / LEGACY_FACADE_RELATIVE_PATH).read_text(encoding="utf-8")
active_prefix, _, payload_suffix = facade.partition("LEGACY_COMPATIBILITY_TEXT = '''")
payload = payload_suffix.rsplit("'''", 1)[0]

require(CONTRACT_VERSION == "v1250.5")
require(REGISTRY_RELATIVE_PATH == "docs/compatibility/release_metadata_compatibility_registry.json")
require(LEGACY_FACADE_RELATIVE_PATH == "docs/legacy/release_metadata_v1250_2_facade.py.txt")
require(registry["schema"] == "eidolon.release-metadata-compatibility-registry.v1")
require(registry["contract_version"] == "v1250.5")
require(registry["source_version"] == "1250.2")
require(registry["target_version"] == "1250.5")
require(registry["source_path"] == "conscious_agent/release_metadata.py")
require(registry["entry_count"] == len(registry["entries"]) == 519)
require(registry["categories"]["working_version_marker"] == 159)
require(registry["categories"]["previous_version_marker"] == 66)
require(registry["categories"]["milestone_marker"] == 35)
require(registry["categories"]["next_arc_marker"] == 23)
require(registry["categories"]["completed_arc_marker"] == 63)
require(registry["categories"]["historical_marker"] == 172)
require(registry["migration_state"] == "structured_registry_primary_generated_facade_retained_for_historical_tests")
require(registry["active_authority"] == "conscious_agent.release_authority")
require(registry["generated_facade"] == "conscious_agent.release_metadata")
require(registry["read_only"] is True)
require(registry["content_free"] is True)
require(registry["release_authorized"] is False)
require(registry["source_mutation_authorized"] is False)
require(len(registry["registry_digest"]) == 64)
require(registry["source_sha256"] == hashlib.sha256(legacy.encode()).hexdigest())
require([row["ordinal"] for row in registry["entries"]] == list(range(1, 520)))
require(all(len(row["sha256"]) == 64 for row in registry["entries"]))
require(all(row["sha256"] == hashlib.sha256(row["text"].encode()).hexdigest() for row in registry["entries"]))

require(validation["ok"] is True)
require(validation["status"] == "compatibility_registry_migrated")
require(validation["passed"] == validation["total"] == 15)
require(validation["entry_count"] == 519)
require(validation["category_count"] == 7)
require(validation["structured_registry_primary"] is True)
require(validation["generated_facade_retained"] is True)
require(all(validation["checks"].values()))
require(len(validation["validation_digest"]) == 64)
require(len(validation["compatibility_payload_sha256"]) == 64)

require(payload == compatibility_text(source_root=ROOT))
require(facade == render_agent_release_metadata(source_root=ROOT))
require(len(facade.splitlines()) == 20)
require(len(legacy.splitlines()) == 608)
require(len(facade.splitlines()) < len(legacy.splitlines()) // 10)
require("# Compatibility marker: WORKING_SOURCE_VERSION" not in active_prefix)
require("# Completed arc:" not in active_prefix)
require("# Retained milestone marker:" not in active_prefix)
require(f'WORKING_SOURCE_VERSION = "{WORKING_SOURCE_VERSION}"' in active_prefix)
require(f'PREVIOUS_WORKING_SOURCE_VERSION = "{PREVIOUS_WORKING_SOURCE_VERSION}"' in active_prefix)
require('WORKING_SOURCE_VERSION = "1250.2"' in payload)
require('WORKING_SOURCE_VERSION = "1249.9"' in payload)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1249.9"' in payload)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1247.9"' in payload)
require('RUNTIME_MILESTONE = "v1250.0-v1250.2 Verification Foundation Bundle A"' in payload)
require('NEXT_RECOMMENDED_ARC = "v1250.3-v1250.5 Release Metadata, Checkpoint, and Compatibility Consolidation"' in payload)
require("Desktop Codex review postponed until cleanup and verification hardening are complete." in payload)
require("v1249.9 Feature Freeze and Final Hardening Checkpoint" in payload)
require("v1204.3-v1204.5 Selected-Project Rollback Execution and Apply Recovery" in payload)
require(payload.count('WORKING_SOURCE_VERSION = "1250.2"') == 1)
require(payload.count('PREVIOUS_WORKING_SOURCE_VERSION = "1249.9"') == 1)
require(not re.search(r'^WORKING_SOURCE_VERSION = "1249\.9"$', facade, flags=re.MULTILINE))
require(not re.search(r'^PREVIOUS_WORKING_SOURCE_VERSION = "1249\.9"$', facade, flags=re.MULTILINE))

registry_text = (ROOT / REGISTRY_RELATIVE_PATH).read_text(encoding="utf-8")
require("BEGIN PRIVATE KEY" not in registry_text)
require("provider_payload" not in registry_text.lower())
require("conversation_content" not in registry_text.lower())
require("private_reasoning" not in registry_text.lower())
require("runtime/data" not in registry_text.lower())
require(str(ROOT) not in registry_text)

for old_test in (
    "tools/v1249_9_feature_freeze_final_hardening_checkpoint_tests.py",
    "tools/v1250_0_authoritative_cleanup_baseline_tests.py",
    "tools/v1209_9_general_test_adapter_consolidation_checkpoint_tests.py",
):
    require((ROOT / old_test).is_file())

require(checkpoint["ok"] is True)
require(checkpoint["checkpoint_version"] == "1250.5")
require(checkpoint["status"] == "compatibility_registry_migration_ready")
require(checkpoint["passed"] == checkpoint["total"] == 3)
require(checkpoint["details"]["entry_count"] == 519)
require(checkpoint_validation["ok"] is True)
require(checkpoint_validation["passed"] == checkpoint_validation["total"])

for key, expected in AUTHORITY_FLAGS.items():
    require(expected is False)
    require(validation[key] is False)
    require(checkpoint[key] is False)

result = {"suite": "v1250.5-compatibility-registry-migration", "ok": all(checks), "passed": sum(checks), "total": len(checks)}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
