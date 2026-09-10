from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v2100-9-"))

from background_cognition_scheduler_v2000 import configure_scheduler, upsert_background_job  # noqa: E402
from checkpoint_registry import lookup_checkpoint  # noqa: E402
from native_background_host_v2100 import run_native_background_host_tick  # noqa: E402
from release_authority import (  # noqa: E402
    AUTHORITY_FLAGS,
    CODEX_REVIEW_STATE,
    MILESTONE,
    NEXT_BOUNDED_UNIT,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
)
from resource_cooperative_governance_v2000 import assess_resource_pressure  # noqa: E402

checks: dict[str, bool] = {}


def require(name: str, value: object) -> None:
    checks[name] = bool(value)
    assert checks[name], name


require("version", WORKING_SOURCE_VERSION == "2100.9")
require("previous", PREVIOUS_WORKING_SOURCE_VERSION == "2099.9")
require("milestone", MILESTONE == "v2100.9 Era 6 Desktop Attention and Initiative Gate")
require("next", NEXT_BOUNDED_UNIT == "v2101.0 - Local System and Application Tool Contracts")
require("review_state", CODEX_REVIEW_STATE == "v2100_9_desktop_attention_initiative_gate_reviewed_unpromoted")
require("authority_denied", not any(bool(value) for value in AUTHORITY_FLAGS.values()))

checkpoint = lookup_checkpoint("2100.9")
require("canonical_registry_selector", checkpoint is not None and checkpoint.test_selector == f"tools/{Path(__file__).name}")

runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2100-host-"))
disabled = run_native_background_host_tick(runtime_root=runtime, resource_measurements={"cpu_percent": 1, "memory_percent": 1})
require("native_host_disabled_by_default", disabled["status"] == "native_background_scheduler_disabled")

configure_scheduler(event_id="gate-config", enabled=True, quiet_start_hour=0, quiet_end_hour=0, runtime_root=runtime)
upsert_background_job(
    job_id="gate-plan-review",
    work_kind="plan_review",
    interval_minutes=15,
    priority_class="normal",
    evidence_digest="a" * 64,
    event_id="gate-job",
    runtime_root=runtime,
)
now = time.time()
first = run_native_background_host_tick(
    runtime_root=runtime,
    now_epoch=now,
    resource_measurements={"cpu_percent": 1, "memory_percent": 1},
)
replay = run_native_background_host_tick(
    runtime_root=runtime,
    now_epoch=now,
    resource_measurements={"cpu_percent": 1, "memory_percent": 1},
)
require("native_host_prepares_bounded_ticket", first["tickets_prepared"] == 1)
require("native_host_replay_exactly_once", replay["tickets_prepared"] == 0 and replay["scheduler_status"] == "scheduler_tick_replayed")
require("native_host_nonexecuting", first["background_work_executed"] is False and first["provider_contacted"] is False)

missing = assess_resource_pressure({}, runtime_root=runtime)
invalid = assess_resource_pressure({"cpu_percent": "invalid"}, runtime_root=runtime)
require("missing_resource_evidence_suspends", missing["mode"] == "suspend" and missing["measurement_evidence_sufficient"] is False)
require("invalid_resource_evidence_suspends", invalid["mode"] == "suspend" and invalid["invalid_dimensions"] == ["cpu_percent"])

service_source = (ROOT / "conscious_agent/proactive_communication.py").read_text(encoding="utf-8")
require("existing_cognitive_service_hosts_era6", service_source.count("run_native_background_host_tick(") == 1)

ledger = ROOT / "docs/roadmaps/EIDOLON_V2100_9_DESKTOP_ATTENTION_INITIATIVE_GATE_LEDGER.md"
ledger_text = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
require("gate_ledger", "79/79" in ledger_text and "unpromoted and not installed" in ledger_text)

result = {
    "suite": "v2100.9-era6-desktop-attention-initiative-gate",
    "ok": all(checks.values()),
    "passed": sum(checks.values()),
    "total": len(checks),
    "checks": checks,
    "installed": False,
    "promoted": False,
    "authority_expanded": False,
}
print(result)
raise SystemExit(0 if result["ok"] else 1)
