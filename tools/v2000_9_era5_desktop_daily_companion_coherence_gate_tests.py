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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v2000-9-"))

from checkpoint_registry import lookup_checkpoint  # noqa: E402
from era5_companion_coherence import audit_era5_companion_output  # noqa: E402
from relationship_companion_continuity_v1900 import build_relationship_companion_projection  # noqa: E402
from release_authority import (  # noqa: E402
    AUTHORITY_FLAGS,
    CODEX_REVIEW_STATE,
    MILESTONE,
    NEXT_BOUNDED_UNIT,
    PREVIOUS_WORKING_SOURCE_VERSION,
    WORKING_SOURCE_VERSION,
)

checks: dict[str, bool] = {}


def require(name: str, value: object) -> None:
    checks[name] = bool(value)
    assert checks[name], name


require("version", WORKING_SOURCE_VERSION == "2000.9")
require("previous", PREVIOUS_WORKING_SOURCE_VERSION == "1999.9")
require("milestone", MILESTONE == "v2000.9 Era 5 Desktop Daily-Companion Coherence Gate")
require("next", NEXT_BOUNDED_UNIT == "v2001.0 - Attention and Salience foundations")
require("review_state", CODEX_REVIEW_STATE == "v2000_9_desktop_daily_companion_coherence_gate_reviewed_unpromoted")
require("authority_denied", not any(bool(value) for value in AUTHORITY_FLAGS.values()))

checkpoint = lookup_checkpoint("2000.9")
require("canonical_registry_selector", checkpoint is not None and checkpoint.test_selector == f"tools/{Path(__file__).name}")

nested = {"discourse": {"response_plan": {"maximum_questions": 0}}}
require("nested_zero_question_plan", audit_era5_companion_output("A question?", projection=nested)["question_pressure_exceeded"])
legacy = {"response_plan": {"max_questions": 0}}
require("legacy_zero_question_plan", audit_era5_companion_output("A question?", projection=legacy)["question_pressure_exceeded"])

relationship = build_relationship_companion_projection(
    [{"type": "preference", "content": "Prefers direct answers", "provenance_class": "user"}],
    conversation_history=[],
)
require("relationship_content_not_exposed", "Prefers direct answers" not in relationship["prompt_section"])
require("no_unsolicited_turn", relationship["autonomous_new_turn_permitted"] is False)
require("no_relationship_authority", relationship["authority_granted"] is False)

ledger = ROOT / "docs/roadmaps/EIDOLON_V2000_9_DESKTOP_DAILY_COMPANION_COHERENCE_GATE_LEDGER.md"
ledger_text = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
require("gate_ledger", "116/116" in ledger_text and "unpromoted and not installed" in ledger_text)

result = {
    "suite": "v2000.9-era5-desktop-daily-companion-coherence-gate",
    "ok": all(checks.values()),
    "passed": sum(checks.values()),
    "total": len(checks),
    "checks": checks,
    "source_modified": False,
    "provider_model_changed": False,
    "installed": False,
    "promoted": False,
    "authority_expanded": False,
}
print(result)
raise SystemExit(0 if result["ok"] else 1)
