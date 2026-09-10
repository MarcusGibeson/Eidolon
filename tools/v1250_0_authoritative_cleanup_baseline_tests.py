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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-0-"))

from release_authority import (  # noqa: E402
    AUTHORITY_FLAGS,
    AUTHORITATIVE_BASELINE_ARCHIVE_SHA256,
    CHECKPOINT_HISTORY,
    CODEX_REVIEW_STATE,
    CONTRACT_VERSION,
    LEGACY_DOCUMENT_HASHES,
    MILESTONE,
    NEXT_BOUNDED_UNIT,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
    release_authority_record,
    validate_release_authority,
)
import release_metadata as active_metadata  # noqa: E402

checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


record = release_authority_record()
validation = validate_release_authority(source_root=ROOT)
require(record["contract_version"] == CONTRACT_VERSION == "v1250.0")
require(record["working_source_version"] == WORKING_SOURCE_VERSION)
require(record["previous_working_source_version"] == PREVIOUS_WORKING_SOURCE_VERSION)
require(record["milestone"] == MILESTONE)
require(record["next_bounded_unit"] == NEXT_BOUNDED_UNIT)
require(record["codex_review_state"] == CODEX_REVIEW_STATE)
require(record["authoritative_baseline_archive_sha256"] == AUTHORITATIVE_BASELINE_ARCHIVE_SHA256)
require(record["history_count"] == len(CHECKPOINT_HISTORY))
require(record["history_chronological"] is True)
require(record["history"][0]["version"] == "1200.0")
require(record["history"][-1]["version"] == WORKING_SOURCE_VERSION)
require(any(row["version"] == "1250.2" for row in record["history"]))
require(len({row["version"] for row in record["history"]}) == len(record["history"]))
require(len(record["authority_digest"]) == 64)
require(validation["ok"] is True)
require(validation["passed"] == validation["total"] == 17)
require(validation["working_source_version"] == WORKING_SOURCE_VERSION)
require(validation["previous_working_source_version"] == PREVIOUS_WORKING_SOURCE_VERSION)
visible_versions = validation["visible_history_versions"]
require(visible_versions[:1] == [WORKING_SOURCE_VERSION])
require(len(visible_versions) == len(set(visible_versions)))
require("1249.9" in visible_versions)
require(validation["legacy_archive_checks"] == {key: True for key in LEGACY_DOCUMENT_HASHES})
require(active_metadata.WORKING_SOURCE_VERSION == WORKING_SOURCE_VERSION)
require(active_metadata.PREVIOUS_WORKING_SOURCE_VERSION == PREVIOUS_WORKING_SOURCE_VERSION)
require(active_metadata.RUNTIME_VERSION == WORKING_SOURCE_VERSION)
require(active_metadata.RUNTIME_MILESTONE == MILESTONE)
require(active_metadata.NEXT_RECOMMENDED_ARC == NEXT_BOUNDED_UNIT)

for relative, expected in LEGACY_DOCUMENT_HASHES.items():
    path = ROOT / relative
    require(path.is_file())
    require(hashlib.sha256(path.read_bytes()).hexdigest() == expected)

manifest_path = ROOT / "docs/legacy/pre_v1250_document_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
require(manifest["contract_version"] == "v1250.0")
require(manifest["working_source_version"] == "1250.5")
require(manifest["previous_working_source_version"] == "1250.2")
require(set(manifest["documents"]) >= set(LEGACY_DOCUMENT_HASHES))
for relative, expected in LEGACY_DOCUMENT_HASHES.items():
    row = manifest["documents"][relative]
    require(row["sha256"] == expected)
    require(row["size"] == (ROOT / relative).stat().st_size)
extra_facade = manifest["documents"]["docs/legacy/release_metadata_v1250_2_facade.py.txt"]
require(extra_facade["sha256"] == hashlib.sha256((ROOT / "docs/legacy/release_metadata_v1250_2_facade.py.txt").read_bytes()).hexdigest())
require(extra_facade["size"] == (ROOT / "docs/legacy/release_metadata_v1250_2_facade.py.txt").stat().st_size)

document_expectations = {
    "README.md": ("v1250.9", "v1250.6-v1250.8"),
    "README_NEXT_STEPS.md": ("v1250.9", "ready_for_postponed_desktop_codex_review"),
    "README_RELEASE_HISTORY.md": ("## v1250.9",),
    "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md": ("v1250.6-v1250.8", "v1250.9"),
}
for name, expected_markers in document_expectations.items():
    text = (ROOT / name).read_text(encoding="utf-8")
    visible = text.split('<details id="retained-pre-v1250-compatibility">', 1)[0]
    if name != "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md":
        require(f"v{WORKING_SOURCE_VERSION}" in visible)
    for marker in expected_markers:
        require(marker in visible)
    require("retained-pre-v1250-compatibility" in text)

next_text = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
next_visible = next_text.split('<details id="retained-pre-v1250-compatibility">', 1)[0]
require(len(re.findall(r"^# ", next_visible, flags=re.MULTILINE)) == 1)
require(CODEX_REVIEW_STATE in next_visible)
require(NEXT_BOUNDED_UNIT in next_visible)
require("Desktop-reviewed" in next_visible)

history_text = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
history_visible = history_text.split('<details id="retained-pre-v1250-compatibility">', 1)[0]
versions = re.findall(r"^## v([0-9]+(?:\.[0-9]+)+)\b", history_visible, flags=re.MULTILINE)
require(versions[:1] == [WORKING_SOURCE_VERSION])
require(len(versions) == len(set(versions)))
require(history_visible.count("## v1249.9") == 1)
require("Current source: v1190.9" not in history_visible)

agent_metadata_text = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
require(re.search(rf'^WORKING_SOURCE_VERSION = "{re.escape(WORKING_SOURCE_VERSION)}"$', agent_metadata_text, flags=re.MULTILINE))
require(re.search(rf'^PREVIOUS_WORKING_SOURCE_VERSION = "{re.escape(PREVIOUS_WORKING_SOURCE_VERSION)}"$', agent_metadata_text, flags=re.MULTILINE))
require('WORKING_SOURCE_VERSION = "1249.9"' in agent_metadata_text)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1247.9"' in agent_metadata_text)
require("Desktop Codex review postponed" in agent_metadata_text)
require("conscious_agent.release_authority" in agent_metadata_text)
require(f"Active source marker: {WORKING_SOURCE_VERSION}" in (ROOT / "release_metadata.py").read_text(encoding="utf-8"))

for key, expected in AUTHORITY_FLAGS.items():
    require(record.get(key) is expected)
    require(validation.get(key) is expected)

result = {
    "suite": "v1250.0-authoritative-cleanup-baseline",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
