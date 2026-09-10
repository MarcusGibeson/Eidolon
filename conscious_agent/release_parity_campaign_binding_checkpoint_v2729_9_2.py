from __future__ import annotations

"""v2729.9.2 cumulative release-parity/campaign-binding hardening checkpoint."""

import ast
import os
import stat
import tempfile
from pathlib import Path

from checkpoint_registry import checkpoint_registry_manifest
from combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog
from combined_trial_campaign_plan_v2721 import build_combined_trial_plan
from combined_trial_campaign_readiness_v2724 import build_combined_trial_campaign_readiness
from combined_trial_campaign_state_v2725 import prepare_combined_trial_campaign_state, load_combined_trial_campaign_state
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v2729.9.2"


def build_checkpoint(source_root: str | Path | None = None) -> dict:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    agent = root / "conscious_agent"

    privacy = package_privacy_summary_for_root(root)
    registry = checkpoint_registry_manifest(source_root=root)

    relative = 0
    package_qualified = 0
    for path in agent.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                relative += int(bool(node.level))
                package_qualified += int(
                    bool(node.level == 0 and node.module and (node.module == "conscious_agent" or node.module.startswith("conscious_agent.")))
                )
            elif isinstance(node, ast.Import):
                package_qualified += sum(
                    1 for alias in node.names if alias.name == "conscious_agent" or alias.name.startswith("conscious_agent.")
                )

    cat = build_combined_trial_catalog()
    plan = build_combined_trial_plan(cat)
    ready = build_combined_trial_campaign_readiness(
        cat,
        plan,
        current_checkpoint="v2729.9.2",
        release_certified=True,
        daily_use_engineering_ready=True,
    )
    with tempfile.TemporaryDirectory() as td:
        prepared = prepare_combined_trial_campaign_state(cat, plan, ready, runtime_root=td)
        loaded = load_combined_trial_campaign_state(td)

    executable = True
    if os.name != "nt":
        executable = all((root / name).stat().st_mode & stat.S_IXUSR for name in ("run_eidolon.sh", "setup.sh"))

    checks = {
        "source_only_root": privacy.get("ok") is True and privacy.get("source_only") is True and int(privacy.get("forbidden_count") or 0) == 0,
        "checkpoint_registry_unique": registry.get("ok") is True and not registry.get("errors"),
        "single_internal_import_identity": relative == 0 and package_qualified == 0,
        "campaign_binding_roundtrip": prepared.get("campaign_state") == "prepared_not_started" and loaded.get("ok") is True and loaded.get("state_digest") == prepared.get("state_digest"),
        "unix_launchers_executable": bool(executable),
        "campaign_still_not_started": loaded.get("campaign_state") == "prepared_not_started" and loaded.get("authority_granted") is False and loaded.get("automatic_transition_permitted") is False,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "passed": sum(bool(v) for v in checks.values()),
        "total": len(checks),
    }


__all__ = ["CONTRACT_VERSION", "build_checkpoint"]
