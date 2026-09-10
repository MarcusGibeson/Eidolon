from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for item in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from v1096_bundle_c_test_support import prepare_staged_fixture
from release_installation_transaction import INSTALLATION_APPLY_CONFIRMATION, apply_authorized_installation, preview_installation_apply_authorization
from release_promotion_preview import create_promotion_impact_preview
from release_promotion_plan import create_promotion_plan, preview_promotion_authorization
from release_promotion_transaction import PROMOTION_APPLY_CONFIRMATION, apply_authorized_promotion, promotion_transaction_status


def prepare_promoted_fixture(base: Path) -> dict[str, Any]:
    fixture = prepare_staged_fixture(base)
    install_auth = preview_installation_apply_authorization(runtime_root=fixture["handoff_runtime"])
    installed = apply_authorized_installation(install_auth["authorization_token"], confirm=INSTALLATION_APPLY_CONFIRMATION, runtime_root=fixture["handoff_runtime"])
    assert installed.get("ok"), installed
    assert create_promotion_impact_preview(runtime_root=fixture["handoff_runtime"]).get("ok")
    assert create_promotion_plan(runtime_root=fixture["handoff_runtime"]).get("ok")
    promotion_auth = preview_promotion_authorization(runtime_root=fixture["handoff_runtime"])
    promoted = apply_authorized_promotion(promotion_auth["authorization_token"], confirm=PROMOTION_APPLY_CONFIRMATION, runtime_root=fixture["handoff_runtime"])
    assert promoted.get("ok"), promoted
    fixture["installed"] = installed
    fixture["promoted"] = promoted
    return fixture


def evidence_payload(fixture: dict[str, Any], scope: str, *, environment: dict[str, Any] | None = None, result: str = "passed", complete: bool = True, producer: str = "eidolon-authoritative-verifier") -> dict[str, Any]:
    promoted = promotion_transaction_status(runtime_root=fixture["handoff_runtime"])
    return {
        "schema": "eidolon-certification-evidence-v1",
        "scope": scope,
        "producer": {"tool": producer, "version": "1097.1"},
        "environment": environment or {"os": "posix-fixture", "native": False},
        "candidate_id": promoted["candidate_id"],
        "packaged_version": promoted["packaged_version"],
        "archive_sha256": promoted["archive_sha256"],
        "source_manifest_sha256": promoted["source_manifest_sha256"],
        "archive_manifest_sha256": promoted["archive_manifest_sha256"],
        "installed_receipt_sha256": promoted["installed_receipt_sha256"],
        "promotion_receipt_sha256": promoted["promotion_receipt_sha256"],
        "target_project_id": promoted["target_project_id"],
        "verification_result": result,
        "complete": complete,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "checks": {"passed": 1 if result in {"pass", "passed"} else 0, "failed": 0 if result in {"pass", "passed"} else 1, "total": 1},
    }


def write_evidence(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
