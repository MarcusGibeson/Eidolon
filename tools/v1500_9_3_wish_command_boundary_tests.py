from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from natural_language_action_routing import build_natural_language_action_projection
from ordinary_chat_development_campaign import (
    list_development_campaign_proposals,
    load_development_campaign_proposal,
    process_ordinary_chat_development_turn,
)
from unified_companion_developer import actionable_clauses, understand_mixed_intent


CHECKS: list[str] = []


def require(value: bool, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if "__pycache__" in relative or relative.endswith((".pyc", ".pyo")) or relative.startswith("data/"):
            continue
        rows.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def route(text: str, runtime: Path) -> dict:
    return process_ordinary_chat_development_turn(
        text,
        action_projection=build_natural_language_action_projection(text),
        session_id="v1500-9-3-boundary",
        runtime_root=runtime,
    )


before = source_signature()
with tempfile.TemporaryDirectory(prefix="eid-v1500-9-3-") as directory:
    runtime = Path(directory) / "runtime"
    non_actions = (
        "I wish you could build a calculator app.",
        "I hope you can build a calculator app someday.",
        "Someday you could build a calculator app.",
        "What if you built a calculator app?",
        "Could you explain how to build a calculator app?",
        "Maybe you should build a calculator someday.",
    )
    for text in non_actions:
        understanding = understand_mixed_intent(text)
        require(understanding["payload"]["actionable_count"] == 0, f"non_action_clause_inactive:{text}")
        require(actionable_clauses(text) == [], f"non_action_text_not_extracted:{text}")
        result = route(text, runtime)
        require(result["active"] is False, f"non_action_proposal_inactive:{text}")
    require(list_development_campaign_proposals(runtime_root=runtime, public=False)["proposal_count"] == 0, "non_actions_create_no_proposals")

    direct = route("Build me a responsive calculator webpage.", runtime)
    require(direct["event"] == "proposal_created", "direct_request_creates_proposal")
    require(list_development_campaign_proposals(runtime_root=runtime, public=False)["proposal_count"] == 1, "direct_request_creates_exactly_one_proposal")

with tempfile.TemporaryDirectory(prefix="eid-v1500-9-3-mixed-") as directory:
    runtime = Path(directory) / "runtime"
    mixed = "I wish you could build a calculator app. Build me a responsive notes webpage."
    require(actionable_clauses(mixed) == ["Build me a responsive notes webpage."], "mixed_turn_extracts_only_live_command")
    result = route(mixed, runtime)
    require(result["event"] == "proposal_created", "mixed_turn_creates_proposal")
    proposals = list_development_campaign_proposals(runtime_root=runtime, public=False)
    require(proposals["proposal_count"] == 1, "mixed_turn_creates_exactly_one_proposal")
    stored = load_development_campaign_proposal(result["proposal"]["proposal_id"], runtime_root=runtime)
    require(stored["request"] == "Build me a responsive notes webpage.", "proposal_contains_only_live_command")

require(source_signature() == before, "suite_preserves_source")
print(json.dumps({
    "ok": True,
    "suite": "v1500.9.3-wish-command-boundary",
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "provider_contacted": False,
    "source_modified": False,
    "authority_granted": False,
}, indent=2, sort_keys=True))
