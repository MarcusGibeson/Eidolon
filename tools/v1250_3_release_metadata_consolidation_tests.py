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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-3-"))

from checkpoint_registry import validate_checkpoint_report  # noqa: E402
from release_authority import (  # noqa: E402
    CHECKPOINT_HISTORY,
    CODEX_REVIEW_STATE,
    MILESTONE,
    NEXT_BOUNDED_UNIT,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
    release_authority_record,
    validate_release_authority,
)
from release_metadata_consolidation import (  # noqa: E402
    CONTRACT_VERSION,
    REGISTRY_RELATIVE_PATH,
    render_agent_release_metadata,
    render_root_release_metadata,
    validate_release_metadata_consolidation,
)
from release_metadata_consolidation_checkpoint import build_release_metadata_consolidation_checkpoint  # noqa: E402
import release_metadata as metadata  # noqa: E402

checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


record = release_authority_record()
authority_validation = validate_release_authority(source_root=ROOT)
validation = validate_release_metadata_consolidation(source_root=ROOT)
checkpoint = build_release_metadata_consolidation_checkpoint(source_root=ROOT)
checkpoint_validation = validate_checkpoint_report(checkpoint, source_root=ROOT)

require(CONTRACT_VERSION == "v1250.3")
require(bool(WORKING_SOURCE_VERSION))
require(bool(PREVIOUS_WORKING_SOURCE_VERSION))
require(bool(MILESTONE))
require(bool(NEXT_BOUNDED_UNIT))
require(bool(CODEX_REVIEW_STATE))
require(record["working_source_version"] == WORKING_SOURCE_VERSION)
require(record["previous_working_source_version"] == PREVIOUS_WORKING_SOURCE_VERSION)
require(record["history_count"] == len(CHECKPOINT_HISTORY))
require(any(row["version"] == "1250.3" for row in record["history"]))
require(any(row["version"] == "1250.4" for row in record["history"]))
require(record["history"][-1]["version"] == WORKING_SOURCE_VERSION)
require(record["history_chronological"] is True)
require(authority_validation["ok"] is True)
require(authority_validation["passed"] == authority_validation["total"])

require(validation["ok"] is True)
require(validation["status"] == "release_metadata_consolidated")
require(validation["passed"] == validation["total"] == 12)
require(validation["working_source_version"] == WORKING_SOURCE_VERSION)
require(validation["previous_working_source_version"] == PREVIOUS_WORKING_SOURCE_VERSION)
require(validation["generated_facade"] is True)
require(validation["active_authority_count"] == 1)
require(validation["agent_facade_line_count"] <= 25)
require(len(validation["agent_facade_sha256"]) == 64)
require(len(validation["root_facade_sha256"]) == 64)
require(len(validation["validation_digest"]) == 64)
require(all(validation["checks"].values()))

agent_path = ROOT / "conscious_agent/release_metadata.py"
root_path = ROOT / "release_metadata.py"
agent_text = agent_path.read_text(encoding="utf-8")
root_text = root_path.read_text(encoding="utf-8")
legacy_text = (ROOT / "docs/legacy/release_metadata_v1250_2_facade.py.txt").read_text(encoding="utf-8")
active_prefix = agent_text.split("LEGACY_COMPATIBILITY_TEXT", 1)[0]
require(agent_text == render_agent_release_metadata(source_root=ROOT))
require(root_text == render_root_release_metadata(source_root=ROOT))
require(len(agent_text.splitlines()) <= 25)
require(len(legacy_text.splitlines()) == 608)
require(len(agent_text.splitlines()) < len(legacy_text.splitlines()) // 10)
require(len(re.findall(r'^WORKING_SOURCE_VERSION = "[^"]+"$', agent_text, flags=re.MULTILINE)) == 1)
require(len(re.findall(r'^PREVIOUS_WORKING_SOURCE_VERSION = "[^"]+"$', agent_text, flags=re.MULTILINE)) == 1)
require(f'WORKING_SOURCE_VERSION = "{WORKING_SOURCE_VERSION}"' in active_prefix)
require(f'PREVIOUS_WORKING_SOURCE_VERSION = "{PREVIOUS_WORKING_SOURCE_VERSION}"' in active_prefix)
require(f'RUNTIME_MILESTONE = "{MILESTONE}"' in active_prefix)
require(f'NEXT_RECOMMENDED_ARC = "{NEXT_BOUNDED_UNIT}"' in active_prefix)
require('METADATA_SCHEMA_VERSION = "2"' in active_prefix)
require(REGISTRY_RELATIVE_PATH in active_prefix)
require("# Compatibility marker: WORKING_SOURCE_VERSION" not in active_prefix)
require("# Completed arc:" not in active_prefix)
require("LEGACY_COMPATIBILITY_TEXT = '''" in agent_text)
require(agent_text.count(f'WORKING_SOURCE_VERSION = "{WORKING_SOURCE_VERSION}"') == 1)
require(root_text.count(f"Active source marker: {WORKING_SOURCE_VERSION}") == 1)
require(hashlib.sha256(agent_text.encode()).hexdigest() == validation["agent_facade_sha256"])
require(hashlib.sha256(root_text.encode()).hexdigest() == validation["root_facade_sha256"])

require(metadata.WORKING_SOURCE_VERSION == WORKING_SOURCE_VERSION)
require(metadata.RUNTIME_VERSION == WORKING_SOURCE_VERSION)
require(metadata.RUNTIME_VERSION_TAG == f"v{WORKING_SOURCE_VERSION}")
require(metadata.PREVIOUS_WORKING_SOURCE_VERSION == PREVIOUS_WORKING_SOURCE_VERSION)
require(metadata.PREVIOUS_RUNTIME_VERSION == PREVIOUS_WORKING_SOURCE_VERSION)
require(metadata.RUNTIME_MILESTONE == MILESTONE)
require(metadata.NEXT_RECOMMENDED_ARC == NEXT_BOUNDED_UNIT)
require(metadata.METADATA_SCHEMA_VERSION == "2")
require(metadata.RELEASE_AUTHORITY_MODULE == "conscious_agent.release_authority")
require(metadata.COMPATIBILITY_REGISTRY_PATH == REGISTRY_RELATIVE_PATH)

manifest = json.loads((ROOT / "docs/release/release_metadata_manifest.json").read_text(encoding="utf-8"))
require(manifest["schema"] == "eidolon.release-metadata-manifest.v1")
require(manifest["contract_version"] == "v1250.3")
require(manifest["working_source_version"] == WORKING_SOURCE_VERSION)
require(manifest["previous_working_source_version"] == PREVIOUS_WORKING_SOURCE_VERSION)
require(manifest["authority_module"] == "conscious_agent.release_authority")
require(manifest["generated_agent_facade"] == "conscious_agent.release_metadata")
require(manifest["compatibility_registry"] == REGISTRY_RELATIVE_PATH)
require(manifest["agent_facade_sha256"] == validation["agent_facade_sha256"])
require(manifest["root_facade_sha256"] == validation["root_facade_sha256"])
require(manifest["release_authorized"] is False)
require(len(manifest["manifest_digest"]) == 64)

document_expectations = {
    "README.md": ("v1250.9", "v1250.3-v1250.5", "v1250.6-v1250.8", "ready_for_postponed_desktop_codex_review"),
    "README_NEXT_STEPS.md": ("v1250.9", "v1250.6", "v1250.7", "v1250.8", "ready_for_postponed_desktop_codex_review"),
    "README_RELEASE_HISTORY.md": ("v1250.3", "v1250.4", "v1250.5", "v1250.6", "v1250.7", "v1250.8", "v1250.9"),
    "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md": ("v1250.3-v1250.5", "v1250.6-v1250.8", "v1250.9", "ready_for_postponed_desktop_codex_review"),
}
for name, expected_tokens in document_expectations.items():
    text = (ROOT / name).read_text(encoding="utf-8")
    visible = text.split('<details id="retained-pre-v1250-compatibility">', 1)[0]
    require(all(token in visible for token in expected_tokens))

require(checkpoint["ok"] is True)
require(checkpoint["checkpoint_version"] == "1250.3")
require(checkpoint["status"] == "release_metadata_consolidation_ready")
require(checkpoint["passed"] == checkpoint["total"] == 3)
require(checkpoint_validation["ok"] is True)
require(checkpoint_validation["passed"] == checkpoint_validation["total"])
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
    require(validation[key] is False)
    require(checkpoint[key] is False)

result = {"suite": "v1250.3-release-metadata-consolidation", "ok": all(checks), "passed": sum(checks), "total": len(checks)}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
