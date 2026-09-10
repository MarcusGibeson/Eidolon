from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from v1097_bundle_c_test_support import prepare_certified_fixture
from release_certification_history import create_certification_history_reconciliation_preview
from release_certification_policy import BUILTIN_POLICY_ID, create_policy_migration_preview, select_certification_policy
from release_authority_readiness import create_release_authority_readiness_preview


def prepare_ready_fixture(base: Path) -> dict[str, Any]:
    fixture = prepare_certified_fixture(base)
    runtime_root = Path(fixture["handoff_runtime"])
    history = create_certification_history_reconciliation_preview(runtime_root=runtime_root)
    assert history.get("ok"), history
    policy = select_certification_policy(built_in_policy_id=BUILTIN_POLICY_ID, runtime_root=runtime_root)
    assert policy.get("ok"), policy
    migration = create_policy_migration_preview(runtime_root=runtime_root)
    assert migration.get("ok"), migration
    readiness = create_release_authority_readiness_preview(runtime_root=runtime_root)
    assert readiness.get("ok"), readiness
    fixture["runtime_root"] = runtime_root
    fixture["initial_readiness"] = readiness
    return fixture


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
