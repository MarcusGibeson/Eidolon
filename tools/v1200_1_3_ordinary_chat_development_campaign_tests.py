from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
MASTER_RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v1200-1-3-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(MASTER_RUNTIME)

from conscious_agent.conversation_runtime import run_conversation_turn, stream_conversation_turn
from conscious_agent.dashboard import EidolonDashboardHandler, render_chat_console, render_development_campaigns
from conscious_agent.developer_alpha_runtime import (
    create_development_proposal as create_calculator_proposal,
    execute_development_proposal as execute_calculator_proposal,
)
from conscious_agent.natural_language_action_routing import build_natural_language_action_projection
from conscious_agent.ordinary_chat_development_campaign import (
    _approval_path,
    _atomic_json,
    _proposal_path,
    _read_json,
    _seal,
    approve_development_campaign_proposal,
    cancel_development_campaign_proposal,
    create_or_resume_development_proposal,
    list_development_campaign_proposals,
    load_development_campaign_proposal,
    process_ordinary_chat_development_turn,
    public_development_campaign_proposal,
    reject_development_campaign_proposal,
    revise_development_campaign_proposal,
)

started = time.monotonic()
checks: list[bool] = []
sections: dict[str, float] = {}


def require(value: object, detail: object = None) -> None:
    checks.append(bool(value))
    assert value, detail


def mark(name: str, section_started: float) -> None:
    sections[name] = round(time.monotonic() - section_started, 4)


def source_signature() -> str:
    digest = hashlib.sha256()
    excluded = {".git", ".venv", "venv", "data", "__pycache__"}
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if path.is_file() and not excluded.intersection(relative.parts):
            digest.update(relative.as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def contains_private_key(value: object) -> bool:
    forbidden = {
        "request", "user_request", "request_text", "private_path", "path", "session_id",
        "conversation", "memory", "prompt", "provider_payload", "credentials", "command",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).casefold()
            if lowered in forbidden or lowered.endswith("_path") and lowered != "path_digest":
                return True
            if contains_private_key(item):
                return True
    elif isinstance(value, list):
        return any(contains_private_key(item) for item in value)
    return False


before = source_signature()

try:
    section = time.monotonic()
    request = "Build me a to-do webpage"
    routing = build_natural_language_action_projection(request)
    require(routing["intent"]["category"] == "action_request", routing)
    require(routing["grounding"]["grounding_status"] == "matched", routing)
    require(routing["grounding"]["capability_id"] == "software_development", routing)
    mark("classification", section)

    section = time.monotonic()
    persistence_root = MASTER_RUNTIME / "persistence"
    project = {"id": "project-private-id", "name": "Todo Demo", "path": "C:/Users/FixtureUser/Private Todo Project"}
    first = create_or_resume_development_proposal(
        request, session_id="private-session-id", project_state=project, runtime_root=persistence_root,
    )
    second = create_or_resume_development_proposal(
        request, session_id="another-tab", project_state=project, runtime_root=persistence_root,
    )
    require(first["operation_status"] == "created", first)
    require(second["operation_status"] == "resumed", second)
    require(first["proposal_id"] == second["proposal_id"], (first, second))
    require(first["revision"] == second["revision"] == 1)
    persisted = load_development_campaign_proposal(first["proposal_id"], runtime_root=persistence_root)
    require(persisted["request"] == request)
    require(persisted["target"]["private_path"] == project["path"])
    public = public_development_campaign_proposal(persisted)
    require(public["request_digest"] == persisted["request_digest"])
    require(not contains_private_key(public), public)
    require(request not in json.dumps(public))
    require(project["path"] not in json.dumps(public))
    require(project["name"] not in json.dumps(public))
    require(public["target"]["project_name_digest"] == hashlib.sha256(project["name"].encode()).hexdigest())
    intake_indexes = list((persistence_root / "development_campaigns" / "intake-index").glob("*.json"))
    require(len(intake_indexes) == 1, intake_indexes)
    intake_index = json.loads(intake_indexes[0].read_text(encoding="utf-8"))
    require(intake_index["proposal_id"] == first["proposal_id"], intake_index)
    require(intake_index["content_free"] is True, intake_index)
    require(intake_index["private_request_included"] is False, intake_index)
    require(intake_index["private_path_included"] is False, intake_index)
    require(request not in json.dumps(intake_index), intake_index)
    require(project["path"] not in json.dumps(intake_index), intake_index)
    require(project["name"] not in json.dumps(intake_index), intake_index)
    mark("persistent_create_resume", section)

    section = time.monotonic()
    race_root = MASTER_RUNTIME / "races"
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        created_rows = list(pool.map(
            lambda tab: create_or_resume_development_proposal(
                "Build me a shared notes webpage", session_id=f"tab-{tab}", runtime_root=race_root,
            ),
            range(24),
        ))
    require(len({row["proposal_id"] for row in created_rows}) == 1)
    require(sum(row["operation_status"] == "created" for row in created_rows) == 1, created_rows)
    require(list_development_campaign_proposals(runtime_root=race_root)["proposal_count"] == 1)
    race_proposal = created_rows[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        approvals = list(pool.map(
            lambda _: approve_development_campaign_proposal(
                race_proposal["proposal_id"], revision=1, revision_digest=race_proposal["revision_digest"], runtime_root=race_root,
            ),
            range(24),
        ))
    require(sum(row.get("approval_consumed_now") is True for row in approvals) == 1, approvals)
    require(all(row.get("approval_consumption_count") == 1 for row in approvals), approvals)
    require(all(row.get("status") in {"approval_consumed", "approval_already_consumed"} for row in approvals), approvals)
    receipt_files = list((race_root / "development_campaigns" / "approvals").rglob("revision-1.json"))
    require(len(receipt_files) == 1, receipt_files)
    approved_retry = process_ordinary_chat_development_turn(
        "Build me a shared notes webpage",
        action_projection=build_natural_language_action_projection("Build me a shared notes webpage"),
        runtime_root=race_root,
    )
    require(approved_retry["event"] == "proposal_resumed", approved_retry)
    require("remains consumed exactly once" in approved_retry["conversation_response"], approved_retry)
    require("To approve this exact revision" not in approved_retry["conversation_response"], approved_retry)

    process_race_root = MASTER_RUNTIME / "process-races"
    process_env = {**os.environ, "EIDOLON_DATA_DIR": str(process_race_root), "PYTHONDONTWRITEBYTECODE": "1"}
    create_code = (
        "import json; from conscious_agent.ordinary_chat_development_campaign import create_or_resume_development_proposal; "
        "print(json.dumps(create_or_resume_development_proposal('Build me a process-safe notes webpage')))"
    )
    create_processes = [subprocess.Popen(
        [sys.executable, "-c", create_code], cwd=ROOT, env=process_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) for _ in range(8)]
    process_create_rows = []
    for process in create_processes:
        stdout, stderr = process.communicate(timeout=30)
        require(process.returncode == 0, stderr)
        process_create_rows.append(json.loads(stdout))
    require(len({row["proposal_id"] for row in process_create_rows}) == 1, process_create_rows)
    require(sum(row["operation_status"] == "created" for row in process_create_rows) == 1, process_create_rows)
    process_proposal = process_create_rows[0]
    approve_code = (
        "import json; from conscious_agent.ordinary_chat_development_campaign import approve_development_campaign_proposal; "
        f"print(json.dumps(approve_development_campaign_proposal('{process_proposal['proposal_id']}', revision=1, revision_digest='{process_proposal['revision_digest']}')))"
    )
    approval_processes = [subprocess.Popen(
        [sys.executable, "-c", approve_code], cwd=ROOT, env=process_env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) for _ in range(8)]
    process_approval_rows = []
    for process in approval_processes:
        stdout, stderr = process.communicate(timeout=30)
        require(process.returncode == 0, stderr)
        process_approval_rows.append(json.loads(stdout))
    require(sum(row.get("approval_consumed_now") is True for row in process_approval_rows) == 1, process_approval_rows)
    require(all(row.get("approval_consumption_count") == 1 for row in process_approval_rows), process_approval_rows)
    mark("duplicate_multitab_exactly_once", section)

    section = time.monotonic()
    revision_root = MASTER_RUNTIME / "revision"
    revision_one = create_or_resume_development_proposal("Build me a timer webpage", runtime_root=revision_root)
    revision_two = revise_development_campaign_proposal(
        revision_one["proposal_id"], expected_revision=1, request="Build me a timer webpage with lap tracking", runtime_root=revision_root,
    )
    require(revision_two["ok"] is True and revision_two["revision"] == 2, revision_two)
    revised_resume = create_or_resume_development_proposal(
        "Build me a timer webpage with lap tracking", runtime_root=revision_root,
    )
    require(revised_resume["operation_status"] == "resumed", revised_resume)
    require(revised_resume["proposal_id"] == revision_one["proposal_id"], revised_resume)
    require(revised_resume["revision"] == 2, revised_resume)
    old_wording_new_generation = create_or_resume_development_proposal(
        "Build me a timer webpage", runtime_root=revision_root,
    )
    require(old_wording_new_generation["operation_status"] == "created", old_wording_new_generation)
    require(old_wording_new_generation["proposal_id"] != revision_one["proposal_id"], old_wording_new_generation)
    require(old_wording_new_generation["revision"] == 1, old_wording_new_generation)
    conflict_target = create_or_resume_development_proposal("Build me a stopwatch webpage", runtime_root=revision_root)
    conflict_revision = revise_development_campaign_proposal(
        old_wording_new_generation["proposal_id"], expected_revision=1,
        request="Build me a stopwatch webpage", runtime_root=revision_root,
    )
    require(conflict_revision["status"] == "revision_target_conflict", conflict_revision)
    require(conflict_revision["conflicting_proposal_id"] == conflict_target["proposal_id"], conflict_revision)
    stale_save = revise_development_campaign_proposal(
        revision_one["proposal_id"], expected_revision=1, request="A stale tab tries to save", runtime_root=revision_root,
    )
    require(stale_save["status"] == "stale_save_rejected", stale_save)
    empty_revision = revise_development_campaign_proposal(
        revision_one["proposal_id"], expected_revision=2, request="", runtime_root=revision_root,
    )
    require(empty_revision["status"] == "invalid_request", empty_revision)
    stale_approval = approve_development_campaign_proposal(
        revision_one["proposal_id"], revision=1, revision_digest=revision_one["revision_digest"], runtime_root=revision_root,
    )
    require(stale_approval["status"] == "stale_approval_rejected", stale_approval)
    exact_approval = approve_development_campaign_proposal(
        revision_two["proposal_id"], revision=2, revision_digest=revision_two["revision_digest"], runtime_root=revision_root,
    )
    require(exact_approval["status"] == "approval_consumed", exact_approval)
    require(exact_approval["implementation_started"] is False)
    require(exact_approval["source_modified"] is False)
    mark("revision_binding_stale_rejection", section)

    section = time.monotonic()
    decision_root = MASTER_RUNTIME / "decisions"
    cancel_row = create_or_resume_development_proposal("Build me a kanban webpage", runtime_root=decision_root)
    cancelled = cancel_development_campaign_proposal(
        cancel_row["proposal_id"], revision=1, revision_digest=cancel_row["revision_digest"], runtime_root=decision_root,
    )
    require(cancelled["status"] == "cancelled", cancelled)
    require(approve_development_campaign_proposal(cancel_row["proposal_id"], revision=1, runtime_root=decision_root)["status"] == "approval_blocked")
    reject_row = create_or_resume_development_proposal("Build me a bookmark webpage", runtime_root=decision_root)
    rejected = reject_development_campaign_proposal(
        reject_row["proposal_id"], revision=1, revision_digest=reject_row["revision_digest"], runtime_root=decision_root,
    )
    require(rejected["status"] == "rejected", rejected)
    require(approve_development_campaign_proposal(reject_row["proposal_id"], revision=1, runtime_root=decision_root)["status"] == "approval_blocked")
    mark("cancellation_rejection", section)

    section = time.monotonic()
    recovery_root = MASTER_RUNTIME / "recovery"
    interrupted = create_or_resume_development_proposal("Build me a habit tracker webpage", runtime_root=recovery_root)
    interrupted_path = _proposal_path(interrupted["proposal_id"], recovery_root)
    interrupted_state = _read_json(interrupted_path)
    interrupted_state["lifecycle_state"] = "approval_processing"
    _seal(interrupted_state)
    _atomic_json(interrupted_path, interrupted_state)
    preview_before_persist = list_development_campaign_proposals(runtime_root=recovery_root)
    require(preview_before_persist["recovery_preview_count"] == 1, preview_before_persist)
    require(preview_before_persist["recovery_preview_persisted"] is False, preview_before_persist)
    require(preview_before_persist["proposals"][0]["lifecycle_state"] == "awaiting_approval", preview_before_persist)
    require(_read_json(interrupted_path)["lifecycle_state"] == "approval_processing")
    recovered = load_development_campaign_proposal(interrupted["proposal_id"], runtime_root=recovery_root)
    require(recovered["lifecycle_state"] == "awaiting_approval", recovered)
    require(recovered["approval_consumption_count"] == 0, recovered)
    stale_lock = recovery_root / "development_campaigns" / "locks" / f"{interrupted['proposal_id']}.lock"
    stale_lock.mkdir(parents=True)
    (stale_lock / "owner.json").write_text('{"pid": 999999, "created_at": "stale"}', encoding="utf-8")
    stale_timestamp = time.time() - 60
    os.utime(stale_lock, (stale_timestamp, stale_timestamp))
    stale_lock_resume = create_or_resume_development_proposal("Build me a habit tracker webpage", runtime_root=recovery_root)
    require(stale_lock_resume["operation_status"] == "resumed", stale_lock_resume)
    require(not stale_lock.exists())

    receipt_recovery = create_or_resume_development_proposal("Build me a meal planner webpage", runtime_root=recovery_root)
    consumed = approve_development_campaign_proposal(
        receipt_recovery["proposal_id"], revision=1, revision_digest=receipt_recovery["revision_digest"], runtime_root=recovery_root,
    )
    require(consumed["status"] == "approval_consumed", consumed)
    receipt_recovery_path = _proposal_path(receipt_recovery["proposal_id"], recovery_root)
    receipt_processing = _read_json(receipt_recovery_path)
    receipt_processing["lifecycle_state"] = "approval_processing"
    receipt_processing["approval_consumed"] = False
    receipt_processing["approval_receipt_digest"] = ""
    receipt_processing["approval_consumption_count"] = 0
    _seal(receipt_processing)
    _atomic_json(receipt_recovery_path, receipt_processing)
    receipt_preview = list_development_campaign_proposals(runtime_root=recovery_root)
    receipt_preview_row = next(row for row in receipt_preview["proposals"] if row["proposal_id"] == receipt_recovery["proposal_id"])
    require(receipt_preview_row["lifecycle_state"] == "approved_pending_grounded_specification", receipt_preview_row)
    require(receipt_preview_row["approval_consumption_count"] == 1, receipt_preview_row)
    receipt_recovered = load_development_campaign_proposal(receipt_recovery["proposal_id"], runtime_root=recovery_root)
    require(receipt_recovered["lifecycle_state"] == "approved_pending_grounded_specification", receipt_recovered)
    require(receipt_recovered["approval_consumed"] is True, receipt_recovered)
    require(receipt_recovered["approval_consumption_count"] == 1, receipt_recovered)

    finalized_tamper = create_or_resume_development_proposal("Build me a pantry webpage", runtime_root=recovery_root)
    finalized_tamper_consumed = approve_development_campaign_proposal(
        finalized_tamper["proposal_id"], revision=1, revision_digest=finalized_tamper["revision_digest"], runtime_root=recovery_root,
    )
    require(finalized_tamper_consumed["status"] == "approval_consumed", finalized_tamper_consumed)
    finalized_tamper_receipt_path = _approval_path(finalized_tamper["proposal_id"], 1, recovery_root)
    finalized_tamper_receipt = _read_json(finalized_tamper_receipt_path)
    finalized_tamper_receipt["receipt_digest"] = "f" * 64
    _atomic_json(finalized_tamper_receipt_path, finalized_tamper_receipt)
    finalized_tamper_preview = list_development_campaign_proposals(runtime_root=recovery_root)
    finalized_tamper_row = next(row for row in finalized_tamper_preview["proposals"] if row["proposal_id"] == finalized_tamper["proposal_id"])
    require(finalized_tamper_row["lifecycle_state"] == "approval_receipt_invalid", finalized_tamper_row)
    require(finalized_tamper_preview["recovery_preview_persisted"] is False, finalized_tamper_preview)
    require(_read_json(_proposal_path(finalized_tamper["proposal_id"], recovery_root))["lifecycle_state"] == "approved_pending_grounded_specification")
    finalized_tamper_loaded = load_development_campaign_proposal(finalized_tamper["proposal_id"], runtime_root=recovery_root)
    require(finalized_tamper_loaded["lifecycle_state"] == "approval_receipt_invalid", finalized_tamper_loaded)
    require(approve_development_campaign_proposal(finalized_tamper["proposal_id"], revision=1, runtime_root=recovery_root)["status"] == "approval_blocked")

    tampered = create_or_resume_development_proposal("Build me a recipe webpage", runtime_root=recovery_root)
    tampered_consumed = approve_development_campaign_proposal(
        tampered["proposal_id"], revision=1, revision_digest=tampered["revision_digest"], runtime_root=recovery_root,
    )
    require(tampered_consumed["status"] == "approval_consumed", tampered_consumed)
    tampered_receipt_path = _approval_path(tampered["proposal_id"], 1, recovery_root)
    tampered_receipt = _read_json(tampered_receipt_path)
    tampered_receipt["receipt_digest"] = "0" * 64
    _atomic_json(tampered_receipt_path, tampered_receipt)
    tampered_proposal_path = _proposal_path(tampered["proposal_id"], recovery_root)
    tampered_processing = _read_json(tampered_proposal_path)
    tampered_processing["lifecycle_state"] = "approval_processing"
    tampered_processing["approval_consumed"] = False
    tampered_processing["approval_receipt_digest"] = ""
    tampered_processing["approval_consumption_count"] = 0
    _seal(tampered_processing)
    _atomic_json(tampered_proposal_path, tampered_processing)
    tampered_preview = list_development_campaign_proposals(runtime_root=recovery_root)
    tampered_preview_row = next(row for row in tampered_preview["proposals"] if row["proposal_id"] == tampered["proposal_id"])
    require(tampered_preview_row["lifecycle_state"] == "approval_receipt_invalid", tampered_preview_row)
    tampered_recovered = load_development_campaign_proposal(tampered["proposal_id"], runtime_root=recovery_root)
    require(tampered_recovered["lifecycle_state"] == "approval_receipt_invalid", tampered_recovered)
    require(approve_development_campaign_proposal(tampered["proposal_id"], revision=1, runtime_root=recovery_root)["status"] == "approval_blocked")

    refresh = list_development_campaign_proposals(runtime_root=recovery_root)
    require(refresh["proposal_count"] == 4)
    env = {**os.environ, "EIDOLON_DATA_DIR": str(recovery_root), "PYTHONDONTWRITEBYTECODE": "1"}
    restart = subprocess.run(
        [sys.executable, "-c", (
            "import json; from conscious_agent.ordinary_chat_development_campaign import list_development_campaign_proposals; "
            "print(json.dumps(list_development_campaign_proposals()))"
        )],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    require(restart.returncode == 0, restart.stderr)
    restart_payload = json.loads(restart.stdout)
    require(restart_payload["proposal_count"] == 4, restart_payload)
    require({row["lifecycle_state"] for row in restart_payload["proposals"]} == {
        "awaiting_approval", "approved_pending_grounded_specification", "approval_receipt_invalid",
    }, restart_payload)
    require(sum(row["lifecycle_state"] == "approval_receipt_invalid" for row in restart_payload["proposals"]) == 2, restart_payload)
    mark("refresh_restart_interruption", section)

    section = time.monotonic()
    unsupported_root = MASTER_RUNTIME / "unsupported"
    unsupported_text = "Build a native accounting suite application"
    unsupported_routing = build_natural_language_action_projection(unsupported_text)
    unsupported_turn = process_ordinary_chat_development_turn(
        unsupported_text, action_projection=unsupported_routing, runtime_root=unsupported_root,
    )
    require(unsupported_turn["event"] == "proposal_created", unsupported_turn)
    require(unsupported_turn["proposal"]["lifecycle_state"] == "unsupported_request", unsupported_turn)
    require(unsupported_turn["proposal"]["approval_required"] is False)
    require("unavailable" in unsupported_turn["proposal"]["approval_requirement"].casefold())
    require("unsupported" in unsupported_turn["conversation_response"].casefold())
    require(unsupported_turn["proposal"]["implementation_started"] is False)
    for blocked_text, expected_status in (
        ("Modify Eidolon source to make it autonomous", "unsupported_authority_request"),
        ("Install a new model for Eidolon", "unsupported_authority_request"),
        ("Build a browser extension", "unsupported_current_scope"),
        ("Build me a mobile app", "unsupported_current_scope"),
    ):
        blocked_routing = build_natural_language_action_projection(blocked_text)
        blocked_turn = process_ordinary_chat_development_turn(
            blocked_text, action_projection=blocked_routing, runtime_root=unsupported_root,
        )
        require(blocked_turn["active"] is True, (blocked_text, blocked_routing, blocked_turn))
        require(blocked_turn["proposal"]["support_status"] == expected_status, (blocked_text, blocked_turn))
        require(blocked_turn["proposal"]["approval_required"] is False, blocked_turn)
        require(blocked_turn["proposal"]["lifecycle_state"] == "unsupported_request", blocked_turn)
    project_source_text = "Modify the source code in my selected website project"
    project_source_turn = process_ordinary_chat_development_turn(
        project_source_text,
        action_projection=build_natural_language_action_projection(project_source_text),
        runtime_root=unsupported_root,
    )
    require(project_source_turn["active"] is True, project_source_turn)
    require(project_source_turn["proposal"]["support_status"] == "supported_for_supervised_proposal", project_source_turn)
    require(project_source_turn["proposal"]["approval_required"] is True, project_source_turn)
    mark("unsupported_behavior", section)

    section = time.monotonic()
    chat_root = MASTER_RUNTIME / "ordinary-chat"
    # DATA_DIR is fixed at import time, so use the master runtime for the actual conversation integration.
    # This is a small-project lifecycle trial, not a copy of the entire Eidolon
    # checkout. Select a real disposable project through the production registry.
    from conscious_agent.project_manager import save_projects_data
    chat_root.mkdir(parents=True, exist_ok=True)
    (chat_root / "main.py").write_text("def main():\n    return 'fixture'\n", encoding="utf-8")
    save_projects_data({"active_project_id": "chat-fixture", "active_project": "Chat Fixture",
                        "projects": [{"id": "chat-fixture", "name": "Chat Fixture", "root": str(chat_root)}]})
    chat_result = run_conversation_turn("Build me a grocery-list webpage", use_ai=True)
    require(chat_result.success is True, chat_result.to_dict())
    require(chat_result.completion_state == "development_campaign_lifecycle", chat_result.to_dict())
    require(chat_result.provider_request_count == 0, chat_result.to_dict())
    require("Approve development proposal" in chat_result.response)
    proposals = list_development_campaign_proposals(runtime_root=MASTER_RUNTIME)["proposals"]
    grocery = next(row for row in proposals if row["request_digest"] == hashlib.sha256("Build me a grocery-list webpage".encode()).hexdigest())
    approved_chat = run_conversation_turn(
        f"Approve development proposal {grocery['proposal_id']} revision {grocery['revision']}.", use_ai=True,
    )
    require(approved_chat.success is True)
    require(approved_chat.provider_request_count == 0)
    require("exactly once" in approved_chat.response)
    streamed = list(stream_conversation_turn("Build me a reading-list webpage", use_ai=True))
    require([row["event"] for row in streamed] == ["meta", "context", "status", "replace", "response_complete", "done"], streamed)
    require(streamed[-1]["result"]["provider_request_count"] == 0)
    mark("ordinary_chat_no_provider", section)

    section = time.monotonic()
    dashboard = render_development_campaigns()
    chat_dashboard = render_chat_console()
    require("Supervised Development Proposals" in dashboard)
    require("/api/development-campaign/proposals" in dashboard)
    require("/api/development-campaign/control" in dashboard)
    require("@media(max-width:760px)" in dashboard)
    require("grid-template-columns:1fr" in dashboard)
    require("Realtime Chat Console" in chat_dashboard)
    require("Public cards contain digests and lifecycle state only" in dashboard)
    verification_evidence = (ROOT / "conscious_agent" / "verification_evidence.py").read_text(encoding="utf-8")
    require('"/development-campaigns": 60' in verification_evidence)
    require('"/api/development-campaign/proposals": 60' not in verification_evidence)

    http_server = HTTPServer(("127.0.0.1", 0), EidolonDashboardHandler)
    http_thread = threading.Thread(target=http_server.handle_request, daemon=True)
    http_thread.start()
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{http_server.server_address[1]}/api/development-campaign/proposals", timeout=10,
        ) as response:
            api_payload = json.loads(response.read().decode("utf-8"))
            require(response.status == 200, response.status)
    finally:
        http_thread.join(timeout=10)
        http_server.server_close()
    require(api_payload["ok"] is True, api_payload)
    require(api_payload["public_projection_content_free"] is True, api_payload)
    require(not contains_private_key(api_payload), api_payload)
    require("Build me a grocery-list webpage" not in json.dumps(api_payload), api_payload)
    mark("dashboard_and_narrow_layout", section)

    section = time.monotonic()
    calculator_root = MASTER_RUNTIME / "calculator-regression"
    calculator_request = "Make me a web page with a calculator built into it"
    calculator = create_calculator_proposal(calculator_request, runtime_root=calculator_root)
    calculator_blocked = execute_calculator_proposal(calculator["proposal_id"], operator_approved=False, runtime_root=calculator_root)
    require(calculator_blocked["status"] == "awaiting_approval", calculator_blocked)
    calculator_done = execute_calculator_proposal(calculator["proposal_id"], operator_approved=True, runtime_root=calculator_root)
    require(calculator_done["status"] == "completed", calculator_done)
    require(calculator_done["validation"]["ok"] is True, calculator_done)
    require(calculator_done["source_modified"] is False)
    mark("calculator_regression", section)

    section = time.monotonic()
    require(not (ROOT / "development_campaigns").exists())
    require(not (ROOT / "data" / "development_campaigns").exists())
    runtime_files = [path for path in MASTER_RUNTIME.rglob("*") if path.is_file()]
    require(any("development_campaigns" in path.parts for path in runtime_files), runtime_files[:20])
    require(all(not path.is_relative_to(ROOT) for path in runtime_files))
    intake_index_files = list(MASTER_RUNTIME.rglob("development_campaigns/intake-index/*.json"))
    require(bool(intake_index_files))
    for index_file in intake_index_files:
        value = json.loads(index_file.read_text(encoding="utf-8"))
        require(value["content_free"] is True, value)
        require(value["private_request_included"] is False, value)
        require(value["private_path_included"] is False, value)
        require("request" not in value, value)
        require("path" not in value, value)
    approval_receipts = list(MASTER_RUNTIME.rglob("development_campaigns/approvals/*/revision-*.json"))
    require(bool(approval_receipts))
    for receipt in approval_receipts:
        value = json.loads(receipt.read_text(encoding="utf-8"))
        require(value["content_free"] is True, value)
        require(value["private_request_included"] is False, value)
        require(value["private_path_included"] is False, value)
        require("request" not in value, value)
        require("path" not in value, value)
    release_verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(release_verifier.count("v1200_1_3_ordinary_chat_development_campaign_tests.py") == 1)
    require("v1200.3-ordinary-chat-development-campaign" in release_verifier)
    require(source_signature() == before, "source changed during focused tests")
    mark("runtime_separation_source_immutability", section)

    elapsed = round(time.monotonic() - started, 4)
    print(json.dumps({
        "ok": all(checks),
        "suite": "v1200.1-v1200.3-ordinary-chat-development-campaign",
        "passed": sum(checks),
        "total": len(checks),
        "elapsed_seconds": elapsed,
        "section_elapsed_seconds": sections,
        "ordinary_chat_proposal_persistent": True,
        "approval_revision_bound": True,
        "approval_consumed_exactly_once": True,
        "provider_generation_before_approval": False,
        "implementation_started": False,
        "calculator_regression_passed": True,
        "runtime_data_external": True,
        "source_modified": False,
        "authority_expanded": False,
    }, sort_keys=True))
finally:
    shutil.rmtree(MASTER_RUNTIME, ignore_errors=True)
