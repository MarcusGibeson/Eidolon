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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1900-9-"))

from active_conversation_facts import _facts_from_text  # noqa: E402
from checkpoint_registry import lookup_checkpoint  # noqa: E402
from conversation_entity_associations import resolve_conversation_association_query  # noqa: E402
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


require("version", WORKING_SOURCE_VERSION == "1900.9")
require("previous", PREVIOUS_WORKING_SOURCE_VERSION == "1899.9")
require("milestone", MILESTONE == "v1900.9 Era 4 Desktop Memory and World-Model Gate")
require("next", NEXT_BOUNDED_UNIT == "v1901.0 - Discourse and Conversational Flow foundations")
require("review_state", CODEX_REVIEW_STATE == "v1900_9_desktop_memory_world_model_gate_reviewed_unpromoted")
require("authority_denied", not any(bool(value) for value in AUTHORITY_FLAGS.values()))

checkpoint = lookup_checkpoint("1900.9")
require("canonical_registry_selector", checkpoint is not None and checkpoint.test_selector == f"tools/{Path(__file__).name}")
require("question_not_fact", not _facts_from_text("What is my fiancee's name?", offset=0))

unsupported = resolve_conversation_association_query("What provider does Project Neptune use?", [], [])
require("unsupported_provider_grounded", unsupported.state == "association_uncertain")
require("unsupported_provider_uncertain", "don't have enough attributable" in unsupported.response.lower())

ledger = ROOT / "docs/roadmaps/EIDOLON_V1900_9_DESKTOP_MEMORY_WORLD_MODEL_GATE_LEDGER.md"
ledger_text = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
require("gate_ledger", "81/81" in ledger_text and "unpromoted and not installed" in ledger_text)

result = {
    "suite": "v1900.9-era4-desktop-memory-world-model-gate",
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
