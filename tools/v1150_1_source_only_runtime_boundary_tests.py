from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1150-1-boundary-runtime-"))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from conscious_agent.package_integrity import (
    SOURCE_DATA_ALLOWLIST,
    package_privacy_summary,
    package_privacy_summary_for_root,
    package_privacy_summary_for_zip,
)
from conscious_agent.release_packaging import _is_source_data_file

ROOT = Path(__file__).resolve().parents[1]
forbidden_samples = [
    "Eidolon/data/settings.json",
    "Eidolon/data/workspaces/projects.json",
    "Eidolon/data/conversation_runtime/session/turns.json",
    "Eidolon/data/memories.json",
    "Eidolon/data/cognition/private_evidence.json",
    "Eidolon/data/provider_payloads/request.json",
]
summary = package_privacy_summary(forbidden_samples)
root_summary = package_privacy_summary_for_root(ROOT)
with tempfile.TemporaryDirectory() as temporary:
    archive = Path(temporary) / "private.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Eidolon/README.md", "source")
        zf.writestr("Eidolon/data/workspaces/projects.json", '{"projects":[{"id":"private"}]}')
    zip_summary = package_privacy_summary_for_zip(archive)

checks = [
    SOURCE_DATA_ALLOWLIST == (),
    summary["forbidden_count"] == len(forbidden_samples),
    not summary["ok"] and not summary["source_only"],
    not _is_source_data_file("data/settings.json"),
    not _is_source_data_file("data/workspaces/projects.json"),
    not _is_source_data_file("data/workspaces/command_profiles/eidolon.json"),
    root_summary["ok"] and root_summary["source_only"],
    not zip_summary["ok"] and not zip_summary["source_only"],
    "Eidolon/data/workspaces/projects.json" in zip_summary["forbidden_entries"],
]
assert all(checks), {"summary": summary, "root": root_summary, "zip": zip_summary}
print(json.dumps({"suite": "v1150.1-source-only-boundary", "passed": len(checks), "total": len(checks)}))
