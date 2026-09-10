from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.belief_revision import BeliefRevisionStore
from conscious_agent.belief_revision_alpha_checkpoint import build_belief_revision_alpha_checkpoint
from conscious_agent.belief_uncertainty_foundations import build_belief_candidate
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.evidence_grounded_reflection import build_evidence_grounded_reflection
from conscious_agent.reasoning_alpha_checkpoint import build_reasoning_alpha_checkpoint
from conscious_agent.reflection_alpha_checkpoint import build_reflection_alpha_checkpoint

passed = 0


def require(value: object) -> None:
    global passed
    if not value:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def candidate(operation_id: str, user: str, assistant: str, *, prior_reflections=(), prior_candidates=()):
    reflection = build_evidence_grounded_reflection(
        operation_id=operation_id,
        user_message=user,
        assistant_response=assistant,
        thought={"thought": "Compare the available evidence without granting action authority."},
        desires={},
        prior_reflections=list(prior_reflections),
    )
    return reflection, build_belief_candidate(
        reflection=reflection,
        operation_id=operation_id,
        prior_candidates=list(prior_candidates),
    )


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    cognition = runtime / "cognition"
    base_reflection, base_candidate = candidate(
        "checkpoint-base",
        "The PRIVATE BELIEF CHECKPOINT CANARY backup completed successfully on Tuesday.",
        "The available evidence supports a provisional belief that the backup completed.",
    )
    opposite_reflection, opposite_candidate = candidate(
        "checkpoint-opposite",
        "The PRIVATE BELIEF CHECKPOINT CANARY backup did not complete successfully on Tuesday.",
        "The evidence now supports a competing interpretation.",
        prior_reflections=[base_reflection],
        prior_candidates=[base_candidate],
    )
    opposite_candidate = dict(opposite_candidate)
    opposite_candidate.update({
        "belief_candidate_id": "belief-candidate-private-opposite",
        "semantic_subject_key": base_candidate["semantic_subject_key"],
        "subject_terms": list(base_candidate.get("subject_terms") or []),
        "proposition": "The PRIVATE BELIEF CHECKPOINT CANARY backup did not complete successfully on Tuesday.",
        "content": "The PRIVATE BELIEF CHECKPOINT CANARY backup did not complete successfully on Tuesday.",
        "revision_basis": "new_evidence",
        "retires_belief_candidate_ids": [],
        "confidence": 0.61,
    })
    store = BeliefRevisionStore(cognition)
    first = store.integrate_candidate("checkpoint:integrate:base", candidate=base_candidate)
    second = store.integrate_candidate("checkpoint:integrate:opposite", candidate=opposite_candidate)
    first_id = first["result"]["belief_id"]
    evidence_id = next(row["evidence_id"] for row in store.snapshot()["beliefs"] if row["belief_id"] == first_id for row in row["evidence"] if row["active"])
    store.retract_evidence(
        "checkpoint:retract:base",
        belief_id=first_id,
        evidence_id=evidence_id,
        correction_ref="PRIVATE BELIEF CHECKPOINT CANARY evidence was withdrawn.",
    )
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "memories.json").write_text(json.dumps([base_candidate, opposite_candidate]), encoding="utf-8")
    (runtime / "private-canary.txt").write_text("PRIVATE BELIEF CHECKPOINT CANARY", encoding="utf-8")

    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_belief_revision_alpha_checkpoint(runtime, source_root=ROOT)

    require(report["contract_version"] == "v1152.9")
    require(report["checkpoint_id"] == "belief-revision-alpha:v1152.9")
    require(report["ok"] and report["status"] == "belief_revision_alpha_candidate")
    require(report["passed"] == report["total"] == 34)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["summary"]["synthetic_contract_check_count"] == 15)
    require(report["summary"]["registered_checkpoint_count"] >= 179)
    require(report["summary"]["runtime_belief_count"] == 2)
    require(report["summary"]["runtime_contested_belief_count"] == 2)
    require(report["summary"]["runtime_retracted_evidence_count"] == 1)
    require(report["summary"]["runtime_active_conflict_count"] == 1)
    require(report["summary"]["runtime_belief_candidate_count"] == 2)
    require(report["summary"]["maximum_candidate_proposition_chars"] == 420)
    require(report["summary"]["maximum_deliberation_conflicts"] == 2)
    require(report["summary"]["maximum_deliberation_options"] == 3)
    require(report["summary"]["maximum_deliberation_proposition_chars"] == 260)
    require(report["summary"]["privacy_forbidden_entry_count"] == 0)
    require(report["summary"]["privacy_content_finding_count"] == 0)
    require(len(report["remaining_limitations"]) == 5)
    require(report["read_only"] and not report["post_available"] and report["content_free"])
    require(report["authority_preserved"] and report["operator_promotion_required"])
    require(report["desktop_verification_pending"] and report["native_provider_certification_pending"])
    require(not report["consciousness_proven"] and not report["sentience_proven"] and not report["personhood_proven"])
    require(not any(report[key] for key in (
        "provider_contacted", "command_executed", "action_executed", "message_sent",
        "notification_created", "goal_created", "plan_created", "approval_created",
        "authorization_created", "installation_performed", "upgrade_performed",
        "rollback_performed", "packaging_performed", "promotion_performed",
        "certification_performed",
    )))
    serialized = json.dumps(report, sort_keys=True)
    require("PRIVATE BELIEF CHECKPOINT CANARY" not in serialized)
    require("backup" not in serialized.lower() and "tuesday" not in serialized.lower())
    require(not any(report[key] for key in (
        "raw_conversation_exposed", "raw_message_exposed", "prompt_exposed",
        "belief_text_exposed", "memory_text_exposed", "evidence_text_exposed",
        "conflict_identifiers_exposed", "provider_payload_exposed", "hidden_reasoning_exposed",
    )))
    require(report["evidence"]["runtime_belief_health"]["all_content_omitted"])
    require(report["evidence"]["runtime_belief_health"]["belief_bounds_respected"])
    require(report["evidence"]["runtime_belief_health"]["candidate_bounds_respected"])
    require(report["evidence"]["runtime_belief_health"]["conflict_membership_valid"])
    require(report["evidence"]["runtime_belief_health"]["unresolved_conflicts_have_no_preference"])
    require(report["evidence"]["runtime_belief_health"]["processed_events_structurally_valid"])
    require(report["evidence"]["runtime_belief_health"]["all_governance_boundaries_preserved"])
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "belief-revision-alpha-checkpoint",
            source_root=ROOT,
            runtime_root=runtime,
        )
        require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"] and dispatched["checkpoint_summary"]["ok"])

        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/belief-revision-alpha-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1152.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/belief-revision-alpha-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    (runtime / "cognition").mkdir(parents=True)
    (runtime / "cognition" / "belief_revision.json").write_text("{not valid json", encoding="utf-8")
    before = signature(runtime)
    malformed = build_belief_revision_alpha_checkpoint(runtime, source_root=ROOT)
    require(not malformed["ok"] and malformed["evidence"]["runtime_belief_health"]["ledger_parse_valid"] is False)
    require(any(row["check_id"] == "runtime_belief_storage_is_parseable" and row["status"] == "fail" for row in malformed["checks"]))
    require(before == signature(runtime))

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    empty = build_belief_revision_alpha_checkpoint(runtime, source_root=ROOT)
    require(empty["ok"] and empty["summary"]["runtime_belief_count"] == 0)
    require(not runtime.exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "belief-revision-alpha-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=240,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1152.9")
    require(not (Path(td) / "runtime").exists())

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    imported = subprocess.run(
        [sys.executable, "-c", "import conscious_agent.belief_revision; import conscious_agent.belief_deliberation"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(imported.returncode == 0 and not (Path(td) / "runtime").exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "belief-revision-alpha-checkpoint"), None)
require(row is not None and row["builder"] == "build_belief_revision_alpha_checkpoint")
require(registry["checkpoint_count"] >= 179)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as td:
    retained_runtime = Path(td) / "runtime"
    retained_runtime.mkdir(parents=True)
    reflection = build_reflection_alpha_checkpoint(retained_runtime, source_root=ROOT)
    reasoning = build_reasoning_alpha_checkpoint(retained_runtime, source_root=ROOT)
    require(reflection["ok"] and reflection["passed"] == reflection["total"] == 24)
    require(reasoning["ok"] and reasoning["passed"] == reasoning["total"] == 22)

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "belief-revision-alpha-checkpoint-panel" in dashboard
    and "/api/cognition/belief-revision-alpha-checkpoint" in dashboard
    and "refreshBeliefRevisionAlphaCheckpoint" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) >= (1152, 9) and tuple(map(int, previous.groups())) >= (1152, 8))
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1152.9 Belief Revision Alpha Read-Only Checkpoint" in history)
require("v1152.6-v1152.8 Belief Revision Reliability and Deliberation" in history)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
require(
    "v1153.0-v1153.2 Multi-Step Deliberation Foundations" in next_steps
    or "v1154.0-v1154.2 Deliberation Outcome and Decision-Boundary Foundations" in next_steps
    or "v1155.0-v1155.2" in next_steps
    or "v1156.0-v1156.2" in next_steps
)
require((ROOT / "tools" / "v1152_9_full_registry_validation.py").exists())

print(json.dumps({"passed": passed, "total": passed, "suite": "v1152.9"}))
