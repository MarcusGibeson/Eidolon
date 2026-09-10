from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1800-9-"))

from causal_counterfactual_intelligence import create_causal_case, inspect_causal_case, record_probe_observation  # noqa: E402
from checkpoint_registry import lookup_checkpoint  # noqa: E402
from dashboard_first_use import render_first_use_shell  # noqa: E402
from problem_framing_intelligence import build_problem_frame  # noqa: E402
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


require("version", WORKING_SOURCE_VERSION == "1800.9")
require("previous", PREVIOUS_WORKING_SOURCE_VERSION == "1799.9")
require("milestone", MILESTONE == "v1800.9 Era 3 Desktop Cognitive Gate")
require("next", NEXT_BOUNDED_UNIT == "v1801.0 - Memory Consolidation and Retrieval foundations")
require("review_state", CODEX_REVIEW_STATE == "v1800_9_desktop_cognitive_gate_reviewed_unpromoted")
require("authority_denied", not any(bool(value) for value in AUTHORITY_FLAGS.values()))
checkpoint = lookup_checkpoint("1800.9")
require("canonical_registry_selector", checkpoint is not None and checkpoint.test_selector == f"tools/{Path(__file__).name}")

with tempfile.TemporaryDirectory(prefix="eidolon-v1800-privacy-") as directory:
    marker = "ORCHID-NEBULA-7719"
    frame = build_problem_frame(f"Keep {marker} private and prototype a reversible parser.", runtime_root=directory)
    require("problem_frame_ready", frame.get("ok"))
    require("private_request_flag", frame.get("private_request_exposed") is False)
    require("private_request_absent", marker not in json.dumps(frame, sort_keys=True))
    require("public_items_digest_only", all(not row.get("text_exposed") and row.get("text_digest") for row in frame.get("goals") or []))

with tempfile.TemporaryDirectory(prefix="eidolon-v1800-lock-") as directory:
    case = create_causal_case(
        "A service fails after restart.",
        [
            {"id": "state", "predictions": {"restart_probe": "works", "provider_probe": "works"}},
            {"id": "provider", "predictions": {"restart_probe": "fails", "provider_probe": "fails"}},
        ],
        runtime_root=directory,
    )
    barrier = threading.Barrier(2)
    outcomes: list[dict[str, object]] = []

    def writer(probe: str, outcome: str, digest: str) -> None:
        barrier.wait()
        outcomes.append(record_probe_observation(
            case["causal_case_id"], case["causal_case_digest"], probe_code=probe,
            observed_outcome=outcome, evidence_digest=digest, runtime_root=directory,
        ))

    workers = [
        threading.Thread(target=writer, args=("restart_probe", "works", "a" * 64)),
        threading.Thread(target=writer, args=("provider_probe", "works", "b" * 64)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    statuses = sorted(str(row.get("status")) for row in outcomes)
    final_case = inspect_causal_case(case["causal_case_id"], runtime_root=directory)
    require("concurrent_one_winner", statuses == ["causal_observation_recorded", "stale_causal_case_digest"])
    require("concurrent_no_lost_success", final_case.get("observation_count") == 1 and final_case.get("revision") == 2)

shell = render_first_use_shell()
require("first_use_horizontal_clip", "overflow-y:auto; overflow-x:hidden" in shell)
require("first_use_long_token_wrap", ".chat-turn,.chat-bubble" in shell and "word-break:break-word" in shell)
styles = (ROOT / "conscious_agent/dashboard_chat_styles.py").read_text(encoding="utf-8")
require("reusable_chat_wrap", "overflow-wrap:anywhere; word-break:break-word" in styles)
ledger = ROOT / "docs/roadmaps/EIDOLON_V1800_9_DESKTOP_COGNITIVE_GATE_LEDGER.md"
require("gate_ledger", ledger.is_file() and "104/104" in ledger.read_text(encoding="utf-8"))

result = {
    "suite": "v1800.9-era3-desktop-cognitive-gate",
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
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
