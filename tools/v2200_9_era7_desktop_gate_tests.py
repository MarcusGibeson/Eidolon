from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v2200-9-"))

from checkpoint_registry import lookup_checkpoint  # noqa: E402
from era7_interaction_intelligence import prepare_era7_interaction_packet  # noqa: E402
from local_tool_interaction_v2100 import build_tool_preview, prepare_existing_execution_handoff  # noqa: E402
from multimodal_context_v2100 import register_region_observation  # noqa: E402
from release_authority import (  # noqa: E402
    AUTHORITY_FLAGS,
    CODEX_REVIEW_STATE,
    MILESTONE,
    NEXT_BOUNDED_UNIT,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
)
from research_web_intelligence_v2100 import capture_research_evidence, validate_download_receipt  # noqa: E402
from voice_audio_interaction_v2100 import begin_voice_turn, finish_voice_turn  # noqa: E402

checks: dict[str, bool] = {}


def require(name: str, value: object) -> None:
    checks[name] = bool(value)
    assert checks[name], name


require("version", WORKING_SOURCE_VERSION == "2200.9")
require("previous", PREVIOUS_WORKING_SOURCE_VERSION == "2199.9")
require("milestone", MILESTONE == "v2200.9 Era 7 Desktop Tools Research Voice and Multimodal Gate")
require("next", NEXT_BOUNDED_UNIT == "v2201.0 - Fine-Grained Authority and Permissions Policy Model")
require("review_state", CODEX_REVIEW_STATE == "v2200_9_desktop_era7_gate_reviewed_unpromoted")
require("authority_denied", not any(bool(value) for value in AUTHORITY_FLAGS.values()))

checkpoint = lookup_checkpoint("2200.9")
require("canonical_registry_selector", checkpoint is not None and checkpoint.test_selector == f"tools/{Path(__file__).name}")

preview_result = build_tool_preview(
    tool_class="read", operation="file_read", argument_metadata={"target": "workspace_file"},
    target_scope="candidate_workspace", request_id="gate-preview",
)
preview = preview_result["preview"]
tampered = dict(preview)
tampered["target_scope"] = "different_scope"
require("tampered_tool_preview_rejected", not prepare_existing_execution_handoff(tampered)["ok"])
require("malformed_tool_timeout_rejected", not build_tool_preview(
    tool_class="read", operation="file_read", argument_metadata={"target": "workspace_file"},
    target_scope="candidate_workspace", timeout_seconds="invalid", request_id="gate-timeout",
)["ok"])

require("unreceipted_research_rejected", capture_research_evidence(
    plan_digest="a" * 64,
    observations=[{"authoritative": True, "source_observed": True, "source_candidate_digest": "b" * 64,
                   "claim_code": "invented", "stance": "supports", "evidence_digest": "c" * 64,
                   "citation_id": "fake"}],
)["evidence_count"] == 0)
require("malformed_download_rejected", not validate_download_receipt({"size_bytes": "invalid"})["ok"])

visual = register_region_observation(
    item_id="missing", expected_content_digest="d" * 64, region_id="r1", observation_kind="ocr",
    observation_digest="e" * 64, confidence=1.0, bounds={"x": 0, "y": 0, "w": 1, "h": 1},
    event_id="gate-visual", runtime_root=Path(tempfile.mkdtemp(prefix="eidolon-v2200-visual-")),
)
require("unreceipted_visual_observation_rejected", visual["status"] == "authoritative_visual_observation_receipt_required")

voice_root = Path(tempfile.mkdtemp(prefix="eidolon-v2200-voice-"))
begin_voice_turn(turn_id="gate-turn", input_audio_digest="f" * 64, event_id="begin", runtime_root=voice_root)
finish_voice_turn(turn_id="gate-turn", outcome="completed", event_id="complete", runtime_root=voice_root)
rewrite = finish_voice_turn(turn_id="gate-turn", outcome="failed", event_id="rewrite", runtime_root=voice_root)
require("voice_terminal_state_immutable", not rewrite["ok"] and rewrite["turn"]["state"] == "completed")

require("unbound_integrated_component_rejected", not prepare_era7_interaction_packet(
    operation_id="gate-packet", tool_preview={"state": "preview_only", "preview_digest": "1" * 64},
)["ok"])

ledger = ROOT / "docs/roadmaps/EIDOLON_V2200_9_DESKTOP_TOOLS_RESEARCH_VOICE_MULTIMODAL_GATE_LEDGER.md"
ledger_text = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
require("gate_ledger", "107/107" in ledger_text and "unpromoted and not installed" in ledger_text)

result = {
    "suite": "v2200.9-era7-desktop-gate",
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
