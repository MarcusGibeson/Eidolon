from __future__ import annotations

import argparse
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

from conscious_agent.agenda_continuity_checkpoint import build_agenda_continuity_checkpoint
from conscious_agent.autonomous_attention_agenda import AutonomousAttentionAgenda
from conscious_agent.motivation_agenda_arbitration import MotivationAgendaArbitrator


def require(value, detail="assertion failed"):
    if not value:
        raise AssertionError(detail)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(row for row in root.rglob("*") if row.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def fixture():
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1107-2-"))
    source = base / "source" / "Eidolon"
    source.mkdir(parents=True)
    runtime = base / "runtime" / "cognition"
    clock_values = iter([
        "2026-07-27T12:00:00.000Z",
        "2026-07-27T12:00:01.000Z",
        "2026-07-27T12:00:02.000Z",
        "2026-07-27T12:00:03.000Z",
        "2026-07-27T12:00:04.000Z",
        "2026-07-27T12:00:05.000Z",
        "2026-07-27T12:00:06.000Z",
        "2026-07-27T12:00:07.000Z",
        "2026-07-27T12:00:08.000Z",
        "2026-07-27T12:00:09.000Z",
    ])
    clock = lambda: next(clock_values, "2026-07-27T12:00:10.000Z")
    agenda = AutonomousAttentionAgenda(runtime, clock=clock)
    private_subject = "Private conversation subject and evidence text must never appear in inspection."
    first = agenda.upsert_candidate(
        "candidate-1",
        origin_type="inquiry",
        origin_ref="inquiry-private-1",
        subject=private_subject,
        subject_key="inquiry-1",
        salience=0.9,
        urgency=0.8,
        uncertainty=0.9,
        confidence=0.1,
        lineage_refs=["private-evidence-reference"],
        source_revision=1,
    )["result"]["agenda_id"]
    second = agenda.upsert_candidate(
        "candidate-2",
        origin_type="commitment",
        origin_ref="commitment-1",
        subject="Finish a bounded unfinished commitment.",
        subject_key="commitment-1",
        salience=0.4,
        urgency=0.3,
        uncertainty=0.5,
        confidence=0.5,
        source_revision=1,
    )["result"]["agenda_id"]
    third = agenda.upsert_candidate(
        "candidate-3",
        origin_type="memory",
        origin_ref="memory-corrected",
        subject="Corrected private memory text.",
        subject_key="memory-corrected",
        salience=0.5,
        urgency=0.2,
        uncertainty=0.3,
        confidence=0.7,
    )["result"]["agenda_id"]
    agenda.defer_candidate("defer-2", second, reason_code="cooldown", eligible_after="2026-07-28T00:00:00Z")
    agenda.retire_candidate("retire-3", third, outcome="corrected", reason_code="operator_correction", replacement_ref="memory-new")
    arbitrator = MotivationAgendaArbitrator(runtime, agenda=agenda, clock=clock, epoch_clock=lambda: 2_000_000_000.0)
    selected = arbitrator.arbitrate(
        "arbitrate-selected",
        arbitration_key="window-selected",
        gather_candidates=False,
        quiet=False,
        minimum_score=0.1,
        worker_generation=4,
    )
    require(selected["result"]["selected_agenda_id"] == first, selected)
    silent = arbitrator.arbitrate(
        "arbitrate-silent",
        arbitration_key="window-silent",
        gather_candidates=False,
        quiet=True,
        minimum_score=0.1,
        worker_generation=4,
    )
    require(silent["result"]["deliberate_no_selection"] is True, silent)
    return base, runtime, source, private_subject


def test_checkpoint_structural_summary_and_fourteen_checks():
    _, runtime, source, _ = fixture()
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    summary = checkpoint["summary"]
    require(summary["agenda_item_count"] == 3, summary)
    require(summary["active_candidate_count"] == 2, summary)
    require(summary["historical_inactive_count"] == 1, summary)
    require(summary["selection_count"] == 1, summary)
    require(summary["deliberate_no_selection_count"] == 1, summary)
    require(checkpoint["check_count"] == 14, checkpoint)
    require(all(row["status"] == "pass" for row in checkpoint["checks"]), checkpoint["checks"])


def test_checkpoint_is_strictly_read_only():
    _, runtime, source, _ = fixture()
    before = tree_digest(runtime)
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    require(tree_digest(runtime) == before, "checkpoint mutated runtime")
    require(checkpoint["runtime_mutated"] is False and checkpoint["source_modified"] is False, checkpoint)


def test_agenda_persistence_lineage_and_correction_history():
    _, runtime, source, _ = fixture()
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    summary = checkpoint["summary"]
    require(summary["lineage_record_count"] == 3, summary)
    require(summary["update_history_item_count"] == 3, summary)
    require(summary["deferral_count"] == 1, summary)
    require(summary["historical_inactive_count"] == 1, summary)


def test_eligibility_fairness_repetition_and_resource_contracts():
    _, runtime, source, _ = fixture()
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    checks = {row["id"]: row for row in checkpoint["checks"]}
    for name in ("candidate_eligibility", "fairness_and_repetition_suppression", "resource_limits"):
        require(checks[name]["status"] == "pass", checks[name])
    controls = checkpoint["arbitration"]["controls"]
    require(controls["fairness_weight"] > 0, controls)
    require(controls["repetition_penalty_per_attention"] > 0, controls)
    require(controls["max_reflection_steps"] == 1, controls)


def test_quiet_sleep_pause_cooldown_topic_boundaries_are_inspectable():
    _, runtime, source, _ = fixture()
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    row = next(item for item in checkpoint["checks"] if item["id"] == "quiet_sleep_pause_cooldown_topic_boundaries")
    require(row["status"] == "pass", row)
    require(checkpoint["arbitration"]["controls"]["selection_cooldown_seconds"] >= 0, checkpoint)


def test_restart_and_provider_switch_preserve_summary():
    _, runtime, source, _ = fixture()
    previous = os.environ.get("EIDOLON_PROVIDER")
    try:
        os.environ["EIDOLON_PROVIDER"] = "ollama"
        first = build_agenda_continuity_checkpoint(runtime, source_root=source)
        os.environ["EIDOLON_PROVIDER"] = "llama_cpp"
        second = build_agenda_continuity_checkpoint(runtime, source_root=source)
    finally:
        if previous is None:
            os.environ.pop("EIDOLON_PROVIDER", None)
        else:
            os.environ["EIDOLON_PROVIDER"] = previous
    require(first["summary"] == second["summary"], (first["summary"], second["summary"]))
    require(second["provider_contacted"] is False, second)


def test_private_subjects_evidence_and_hidden_reasoning_not_exposed():
    _, runtime, source, private_subject = fixture()
    encoded = json.dumps(build_agenda_continuity_checkpoint(runtime, source_root=source))
    for forbidden in (private_subject, "private-evidence-reference", "Corrected private memory text"):
        require(forbidden not in encoded, forbidden)
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    require(checkpoint["private_subjects_exposed"] is False, checkpoint)
    require(checkpoint["hidden_reasoning_exposed"] is False, checkpoint)
    require(checkpoint["provider_payloads_exposed"] is False, checkpoint)


def test_attention_intention_proposal_authorization_execution_are_separate():
    _, runtime, source, _ = fixture()
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    row = next(item for item in checkpoint["checks"] if item["id"] == "cognitive_state_separation")
    require(row["status"] == "pass", row)
    require(checkpoint["action_authority_changed"] is False, checkpoint)
    require(checkpoint["external_action_executed"] is False, checkpoint)


def test_action_model_release_and_browsing_boundaries_pass():
    _, runtime, source, _ = fixture()
    checkpoint = build_agenda_continuity_checkpoint(runtime, source_root=source)
    for name in ("external_browsing_performed", "file_modification_performed", "model_management_performed", "release_approved", "release_promoted", "release_certified"):
        require(checkpoint[name] is False, (name, checkpoint[name]))


def test_external_runtime_ready_and_in_source_runtime_pending():
    _, runtime, source, _ = fixture()
    external = build_agenda_continuity_checkpoint(runtime, source_root=source)
    require(external["runtime_external"] is True and external["status"] == "ready_for_desktop_verification", external)
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1107-2-inside-"))
    source_inside = base / "Eidolon"
    runtime_inside = source_inside / "data" / "cognition"
    pending = build_agenda_continuity_checkpoint(runtime_inside, source_root=source_inside)
    require(pending["runtime_external"] is False, pending)
    require(pending["status"] == "pending_desktop_verification", pending)
    require(pending["desktop_verification_status"] == "pending", pending)


def test_local_api_surfaces_are_read_only_and_structured():
    from conscious_agent.api_server import dispatch_api
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1107-2-api-"))
    previous = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(base / "runtime")
    try:
        runtime = base / "runtime" / "cognition"
        before = tree_digest(runtime)
        paths = {
            "/api/cognition/attention-agenda": "v1107.0",
            "/api/cognition/attention-arbitration": "v1107.1",
            "/api/cognition/attention-agenda-checkpoint": "v1107.2",
        }
        for path, version in paths.items():
            status, payload = dispatch_api("GET", path)
            require(status == 200, (path, payload))
            require(payload["data"]["contract_version"] == version, payload)
        require(tree_digest(runtime) == before, "read-only API created runtime state")
    finally:
        if previous is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = previous


def test_cli_surfaces_are_provider_free_and_read_only():
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1107-2-cli-"))
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(base / "runtime")
    expected = {
        "attention-agenda": "v1107.0",
        "attention-arbitration": "v1107.1",
        "attention-agenda-checkpoint": "v1107.2",
    }
    runtime = base / "runtime" / "cognition"
    before = tree_digest(runtime)
    for command, version in expected.items():
        run = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), command, "--json"], cwd=ROOT, env=env, capture_output=True, text=True)
        require(run.returncode == 0, (command, run.stderr, run.stdout))
        payload = json.loads(run.stdout)
        require(payload["contract_version"] == version, payload)
        require(payload["provider_contacted"] is False, payload)
    require(tree_digest(runtime) == before, "read-only CLI created runtime state")


def test_dashboard_exposes_restrained_checkpoint_surface():
    from conscious_agent.dashboard_first_use import render_first_use_shell
    html = render_first_use_shell()
    required = [
        "id='attention-agenda-checkpoint-panel'",
        "id='attention-agenda-checkpoint-state'",
        "/api/cognition/attention-agenda-checkpoint",
        "loadAttentionAgendaCheckpoint",
        "@media (max-width:560px)",
    ]
    require(all(token in html for token in required), [token for token in required if token not in html])
    section = html.split("id='attention-agenda-checkpoint-panel'", 1)[1].split("</section>", 1)[0]
    lowered = section.lower()
    require("title=" not in section, section)
    require("chain-of-thought" not in lowered, section)
    require("private conversation subject" not in lowered, section)
    match = re.search(r"<script>(.*)</script>", html, re.S)
    require(match is not None, "dashboard script missing")
    if subprocess.run(["node", "--version"], capture_output=True, text=True).returncode == 0:
        js = Path(tempfile.mkdtemp(prefix="eidolon-v1107-2-js-")) / "dashboard.js"
        js.write_text(match.group(1), encoding="utf-8")
        check = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        require(check.returncode == 0, check.stderr)


def test_release_metadata_identifies_checkpoint_and_next_arc():
    from conscious_agent.release_metadata import NEXT_RECOMMENDED_ARC, RUNTIME_MILESTONE, WORKING_SOURCE_VERSION
    require(tuple(map(int, WORKING_SOURCE_VERSION.split("."))) >= (1107, 2), WORKING_SOURCE_VERSION)
    require(RUNTIME_MILESTONE.startswith(f"v{WORKING_SOURCE_VERSION} "), RUNTIME_MILESTONE)
    require(tuple(map(int, NEXT_RECOMMENDED_ARC.split()[0].removeprefix("v").split("."))) > tuple(map(int, WORKING_SOURCE_VERSION.split("."))), NEXT_RECOMMENDED_ARC)


TESTS = [
    (name.removeprefix("test_"), value)
    for name, value in list(globals().items())
    if name.startswith("test_")
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    rows = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            rows.append({"name": name, "status": "fail", "detail": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            rows.append({"name": name, "status": "pass", "detail": ""})
    report = {
        "suite": "v1107.2-agenda-continuity-inspection-checkpoint",
        "ok": passed == len(TESTS),
        "passed": passed,
        "total": len(TESTS),
        "tests": rows,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
