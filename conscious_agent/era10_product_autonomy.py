from __future__ import annotations

"""Integrated Era 10 product-maturity and bounded-autonomy status boundary."""

import hashlib
import json
from pathlib import Path
from typing import Any

from product_maturity_v2400 import build_chat_first_shell_projection
from unattended_operation_v2400 import build_health_trend
from autonomous_developer_beta_v2400 import RETAINED_STAGE_OWNERS
from autonomy_benchmark_v2400 import build_autonomy_matrix
from release_authority import WORKING_SOURCE_VERSION, MILESTONE, NEXT_BOUNDED_UNIT

CONTRACT_VERSION = "v2499.9"

_DENIED = {
    "background_work_executed": False,
    "tool_executed": False,
    "provider_contacted": False,
    "source_modified": False,
    "candidate_installed": False,
    "candidate_promoted": False,
    "benchmark_certified": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def build_era10_snapshot(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    shell = build_chat_first_shell_projection(width_px=1280, height_px=800, scaling_percent=100)
    health = build_health_trend(runtime_root=runtime_root) if runtime_root is not None else {"ok": True, "status": "health_runtime_not_supplied", "sample_count": 0, "content_free": True}
    matrix = build_autonomy_matrix()
    result = {
        "ok": bool(shell.get("ok") and health.get("ok") and matrix.get("ok")),
        "status": "era10_product_autonomy_snapshot",
        "contract_version": CONTRACT_VERSION,
        "release": {"working_source_version": WORKING_SOURCE_VERSION, "milestone": MILESTONE, "next_bounded_unit": NEXT_BOUNDED_UNIT},
        "product": {"chat_first": bool(shell.get("chat_first")), "quiet_status": bool(shell.get("quiet_status")), "projection_digest": shell.get("projection_digest")},
        "unattended": {"health_status": health.get("status"), "sample_count": int(health.get("sample_count", 0) or 0), "preparation_not_execution": True},
        "developer_beta": {"stage_count": len(RETAINED_STAGE_OWNERS), "final_state": "review_ready", "installation_out_of_scope": True},
        "benchmark": {"autonomy_matrix_digest": matrix.get("matrix_digest"), "native_certification_required": True, "v2500_gate_preparation_only": True},
        "content_free": True,
        **_DENIED,
    }
    result["snapshot_digest"] = _digest(result); return result


def process_era10_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {
        "show era10 product autonomy status", "inspect era10 product autonomy status",
        "show v2500 benchmark preparation status", "inspect v2500 benchmark preparation status",
        "show bounded autonomy status", "inspect bounded autonomy status",
    }
    if raw in exact:
        return {"active": True, **build_era10_snapshot(runtime_root=runtime_root)}
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era10_read_only_scope_expansion_rejected", "content_free": True, **_DENIED}
    return {"active": False}


__all__ = ["CONTRACT_VERSION", "build_era10_snapshot", "process_era10_control"]
