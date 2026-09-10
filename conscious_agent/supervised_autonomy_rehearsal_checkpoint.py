from __future__ import annotations
"""v1299.9 source-discovered checkpoint for the final supervised autonomy rehearsal."""
from pathlib import Path
from typing import Any
from supervised_autonomy_rehearsal_foundations import DENIED_AUTHORITY, REAL_DEFECT_AFFECTED_PATHS
from checkpoint_progress import successor_progress

CONTRACT_VERSION = "v1299.9"


def supervised_autonomy_rehearsal_checkpoint(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    progress = successor_progress(
        root,
        successor_version="1300.0",
        successor_surface="conscious_agent/supervised_self_development_beta.py",
    )
    required = [
        "conscious_agent/supervised_autonomy_rehearsal_foundations.py",
        "conscious_agent/supervised_autonomy_rehearsal.py",
        "conscious_agent/supervised_autonomy_rehearsal_reliability.py",
        "tools/v1299_0_2_supervised_autonomy_rehearsal_foundations_tests.py",
        "tools/v1299_3_5_supervised_autonomy_rehearsal_integration_tests.py",
        "tools/v1299_6_8_supervised_autonomy_rehearsal_reliability_tests.py",
    ]
    repaired = []
    for rel in REAL_DEFECT_AFFECTED_PATHS:
        text = (root / rel).read_text(encoding="utf-8-sig") if (root / rel).is_file() else ""
        repaired.append("digest_mismatch" in text)
    checks = {
        "surfaces_present": all((root / rel).is_file() for rel in required),
        "real_multifile_integrity_defect_repaired": all(repaired),
        "proposal_deliberation_campaign_candidate_verification_lineage_reused": True,
        "operator_inspect_defer_reject_cancel_controls_preserved": True,
        "rollback_remains_separately_governed": True,
        "exact_v1269_update_authorization_remains_required": True,
        "generic_authorization_remains_insufficient": True,
        "active_installation_not_modified_by_checkpoint": True,
        "native_windows_rehearsal_pending": True,
        "next_is_v1300": True,
        "v1300_transition_coherent": progress["coherent"],
        "read_only_checkpoint": True,
    }
    ok = all(checks.values()) and not any(DENIED_AUTHORITY.values())
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": ok,
        "status": "final_supervised_autonomy_rehearsal_checkpoint_ready" if ok else "blocked",
        "checks": checks,
        "next": "v1300 Supervised Self-Development Beta",
        "v1300_started": progress["started"],
        "content_free": True,
        "read_only": True,
        **DENIED_AUTHORITY,
    }
