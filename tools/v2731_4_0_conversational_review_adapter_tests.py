from __future__ import annotations

"""Conversational selection and invocation of the governed read-only experiment review (spec 2.25).

Deterministic; no provider contact and no detached process. Proves the routing of the three operator phrases, that a
review starts only on an explicit confirmation, that exactly one local-model review job runs at a time while
deterministic work continues, that status reports ids, counts and coverage but never the review's conclusions, that a
job whose process died or ran past its bound becomes a recorded failure instead of a stuck job, that the stored
conversation memory holds only an operation receipt, and that the adapter adds no authority: no path or unknown name
resolves, no other queue kind is reachable, nothing schedules, and no shell or model endpoint is exposed.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-4-0-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import conversational_experiment_review as adapter  # noqa: E402
import experiment_review as er  # noqa: E402
import local_research_queue as lrq  # noqa: E402
import chat_action_router as router  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
import run_review_job  # noqa: E402

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


DOCS = {"design.txt": ("design", "The experiment asks whether each item keeps its label across prompt forms.\nForms: V1, V2.\n"),
        "items.txt": ("corpus", "item=A gold=unresolved\nitem=B gold=continuing\n"),
        "outputs.txt": ("raw_outputs", "form=V1 item=A classification=unresolved\nform=V1 item=B classification=continuing\n"
                                       "form=V2 item=A classification=event_only\nform=V2 item=B classification=continuing\n")}


def install_package(name: str, *, break_digest: bool = False) -> Path:
    pkg = adapter.package_area() / name
    pkg.mkdir(parents=True, exist_ok=True)
    entries = []
    for n, (file_name, (role, text)) in enumerate(DOCS.items(), 1):
        (pkg / file_name).write_text(text, encoding="utf-8", newline="\n")
        entries.append({"doc_id": f"D{n}", "path": file_name, "role": role, "description": file_name, "sha256": sha(pkg / file_name)})
    (pkg / er.MANIFEST_NAME).write_text(json.dumps({"experiment_id": name, "title": f"{name} test experiment", "task": "independent_review",
                                                    "brief": "Review it.", "documents": entries}), encoding="utf-8")
    if break_digest:
        (pkg / "items.txt").write_text("item=A gold=changed\n", encoding="utf-8", newline="\n")
    return pkg


install_package("G-TEST")
install_package("G-BROKEN", break_digest=True)
OK_META = {"seconds": 0.0, "metrics": {"eval_count": 40, "prompt_eval_count": 500}}
IDENT = {"model": "stub", "provider": "stub", "context_size": 8192, "resolved_config_sha256": "0" * 64}
CONCLUSION = "the forms disagree about item A"


def stub_model(prompt: str, max_tokens: int):
    """A conforming reviewer stub whose final synthesis carries a recognisable conclusion sentence."""
    if "List up to" in prompt:
        line = prompt.split("---\n", 1)[1].rsplit("\n---\n", 1)[0].strip().splitlines()[0]
        return json.dumps({"observations": [{"statement": f"the part contains {line}", "quotes": [line]}], "open_questions": []}), dict(OK_META)
    if "Write a part-level synthesis" in prompt or "Write a document-level synthesis" in prompt:
        part = "Write a part-level synthesis" in prompt
        ids = re.findall(r"^(O[0-9]+)(?: \[[^\]]*\])?: " if part else r"^((?:PS|O)[0-9]+) \[", prompt, re.M)
        cap = int(re.search(r"Give at most ([0-9]+) statements", prompt).group(1))
        groups = [ids[i:i + er.MAX_IDS_PER_STATEMENT] for i in range(0, len(ids), er.MAX_IDS_PER_STATEMENT)][:cap]
        return json.dumps({"statements": [{"statement": "these inputs are recorded", "kind": "finding", ("obs_ids" if part else "input_ids"): g}
                                          for g in groups]}), dict(OK_META)
    if "second half" in prompt:
        return json.dumps({"competing_hypotheses": [], "unknowns": [], "confidence": {"level": "low", "reason": "small", "input_ids": ["DS1"]},
                           "discriminating_experiments": [], "not_established": []}), dict(OK_META)
    return json.dumps({"experiment_understanding": {"statement": CONCLUSION, "input_ids": ["DS1"]},
                       **{k: [] for k in er.SECTIONS_A[1:]}}), dict(OK_META)


spawned: list[dict] = []


def fake_spawn(argv, cwd, env):
    spawned.append({"argv": list(argv), "cwd": str(cwd), "data_dir": env.get("EIDOLON_DATA_DIR")})
    return 4242


adapter.SPAWN = fake_spawn
adapter.ALIVE = lambda pid: pid == 4242  # the fake launcher's process; the real check is untouched in production

# --- eligibility and name resolution ------------------------------------------------------------------------------------------
rows = {r["package_id"]: r for r in adapter.eligible_packages()}
require(rows["G-TEST"]["eligible"] and rows["G-TEST"]["documents"] == 3 and rows["G-TEST"]["parts"] == 3 and rows["G-TEST"]["reviews"] == []
        and not rows["G-BROKEN"]["eligible"] and rows["G-BROKEN"]["reason"] == "package_document_digest_mismatch",
        "the_listing_verifies_each_installed_package_with_the_reviewers_own_loader")
require(adapter.find_package("g-test")["package_id"] == "G-TEST" and adapter.find_package("G-TEST")["package_id"] == "G-TEST",
        "a_package_resolves_by_name_case_insensitively")
for bad in ("G-MISSING", "../escape", "research_packages/G-TEST", "conscious_agent/memory.py", "G-*", "", "it"):
    require(adapter.find_package(bad) is None, f"no_resolution_for:{bad or 'empty'}")
require(adapter.find_package("G-BROKEN") is None, "an_ineligible_package_never_resolves")

# --- routing ----------------------------------------------------------------------------------------------------------------
listing = router.propose_chat_action("What experiments can you review?", save=False)
status_action = router.propose_chat_action("What's the status of the review?", save=False)
start = router.propose_chat_action("Review G-TEST independently.", save=False)
unknown = router.propose_chat_action("Review G-NOPE independently.", save=False)
file_review = router.propose_chat_action("review conscious_agent/memory.py", save=False)
require(listing["intent"] == "experiment_review_list" and listing["execution_mode"] == router.INFO and "G-TEST" in listing["summary"]
        and "not eligible" in listing["summary"], "the_listing_phrase_answers_read_only_with_the_installed_packages")
require(status_action["intent"] == "experiment_review_status" and status_action["execution_mode"] == router.INFO
        and "No review job" in status_action["summary"], "the_status_phrase_answers_read_only")
require(start["intent"] == "experiment_review_start" and start["execution_mode"] == router.DIRECT_FUNCTION
        and start["function_name"] == "experiment_review_start" and start["function_args"] == {"package_id": "G-TEST"}
        and start["status"] == "proposed", "a_review_request_becomes_a_proposal_for_the_governed_capability")
require(unknown["intent"] == "experiment_review_unavailable" and unknown["execution_mode"] == router.BLOCKED and "G-TEST" in unknown["blocked_reason"],
        "an_unknown_name_is_blocked_with_the_eligible_list")
require(not str(file_review["intent"]).startswith("experiment_review"), "a_file_path_request_is_not_an_experiment_review")
require("independent read-only review of an installed experiment package" in router.supervised_capability_summary(),
        "the_capability_is_registered_in_the_supervised_catalog")

# --- confirmation is required -------------------------------------------------------------------------------------------------
require(not list(adapter.job_area().glob("*.json")) and not lrq.load_queue()["tasks"], "proposing_a_review_starts_nothing")
try:
    adapter.start_review("G-TEST", confirmed=False)
    unconfirmed = False
except PermissionError:
    unconfirmed = True
require(unconfirmed and not list(adapter.job_area().glob("*.json")), "a_review_never_starts_without_the_operators_confirmation")

# --- starting one job ---------------------------------------------------------------------------------------------------------
job = adapter.start_review("G-TEST", confirmed=True)
task = lrq.load_queue()["tasks"][0]
require(job["status"] == "running" and job["pid"] == 4242 and job["package_id"] == "G-TEST" and job["kind"] == adapter.REVIEW_KIND
        and task["kind"] == adapter.REVIEW_KIND and task["chosen_by"] == "operator" and task["status"] == "queued"
        and job["manifest_sha256"] == rows["G-TEST"]["manifest_sha256"], "a_confirmed_review_queues_the_operator_chosen_task_and_starts_one_job")
require(spawned[0]["argv"] == [sys.executable, "-B", str(adapter.JOB_RUNNER), str(adapter.job_area() / f"{job['job_id']}.json")]
        and spawned[0]["data_dir"] == str(RUNTIME) and not any("G-TEST" in a for a in spawned[0]["argv"][:3]),
        "the_job_is_one_fixed_argument_vector_with_no_text_from_chat")
require(adapter.active_job()["job_id"] == job["job_id"], "the_running_job_is_the_active_one")

# --- exactly one model review at a time, without blocking deterministic work ------------------------------------------------------
try:
    adapter.start_review("G-TEST", confirmed=True)
    second = False
except RuntimeError as exc:
    second = str(exc) == "review_job_already_running"
blocked = adapter.execute_conversational_review_action("experiment_review_start", {"package_id": "G-TEST"})
package, message = adapter.propose_message("G-TEST")
require(second and blocked["ok"] is False and "already running" in blocked["message"] and package is None and "already running" in message,
        "a_second_review_is_refused_while_one_runs")
other = lrq.add_task("cluster_historical_failures", "all")
require(adapter.eligible_packages() and adapter.job_status()["status"] == "running" and other["status"] == "queued"
        and len(list(adapter.job_area().glob("*.json"))) == 2, "deterministic_work_continues_while_a_review_runs")

# --- the job runs to completion in its own process ----------------------------------------------------------------------------
record = run_review_job.run_job(adapter.job_area() / f"{job['job_id']}.json",
                                review=lambda target: er.review_experiment(target, call_model=stub_model, identity=IDENT, runtime_root_path=RUNTIME))
status = adapter.job_status(job["job_id"])
review = json.loads((Path(record["location"]) / "review.json").read_text(encoding="utf-8"))
require(record["status"] == "completed" and record["review_status"] == "complete" and status["status"] == "completed"
        and status["review_id"] == review["review_id"] and status["coverage"]["required_coverage"] == 1.0
        and status["checks"]["mutation_guard_passed"] is True and status["checks"]["authority_flags_all_false"] is True,
        "a_finished_job_records_the_review_id_coverage_and_its_mechanical_checks")
require(review["non_authoritative"] is True and all(v is False for v in review["authority"].values())
        and lrq.load_queue()["tasks"][0]["status"] == "completed", "the_artifact_stays_read_only_and_non_authoritative")
second_job = adapter.start_review("G-TEST", confirmed=True) if adapter.active_job() is None else None
require(second_job is not None and second_job["status"] == "running" and adapter.latest_job()["job_id"] == second_job["job_id"],
        "the_next_review_may_start_once_the_job_has_finished_and_is_the_one_latest_resolves_to")
running_again = adapter.job_status(second_job["job_id"])

# --- status and receipts carry no conclusion ------------------------------------------------------------------------------------
payload = json.dumps([status, adapter.receipt(record), adapter.execute_conversational_review_action("experiment_review_status", {})], ensure_ascii=False)
require(CONCLUSION in json.dumps(review, ensure_ascii=False) and CONCLUSION not in payload and CONCLUSION not in json.dumps(record, ensure_ascii=False),
        "status_and_receipts_report_ids_counts_and_coverage_but_never_the_reviews_conclusions")
require(set(adapter.receipt(record)) == {"job_id", "task_id", "package_id", "manifest_sha256", "status", "review_id", "authority"},
        "the_receipt_is_the_minimal_operation_record")

# --- conversation memory keeps only the receipt ------------------------------------------------------------------------------------
stored: list[dict] = []
original_store, router.store_memory = router.store_memory, lambda entry, **kwargs: stored.append(entry)
try:
    refused = router.propose_chat_action("Review G-TEST independently.", save=True)
    refused_execution = router.execute_chat_action(refused["id"])
    adapter.save_job({**running_again, "status": "failed", "failure": "test_teardown"}, RUNTIME)
    saved = router.propose_chat_action("Review G-TEST independently.", save=True)
    executed = router.execute_chat_action(saved["id"])
finally:
    router.store_memory = original_store
require(refused["intent"] == "experiment_review_unavailable" and refused["execution_mode"] == router.BLOCKED
        and "already running" in refused["blocked_reason"] and not refused_execution.ok and not refused_execution.result
        and "already running" in str(refused_execution.error), "while_one_runs_a_second_review_is_refused_at_proposal_time_and_never_executes")
require(executed.ok and executed.status == "executed" and set(executed.result) == {"ok", "message", "receipt"},
        "confirming_the_proposal_starts_the_review_through_the_router")
memory = json.dumps(stored, ensure_ascii=False)
require(stored and any(e["type"] == "chat_action_executed" and e.get("status") == "executed" for e in stored)
        and all(e["source"] == "chat_action_router" and str(e.get("intent", "")).startswith("experiment_review") for e in stored)
        and CONCLUSION not in memory and "Review job" in memory and "grounded_observations" not in memory and "observations" not in memory,
        "the_stored_conversation_memory_holds_only_an_operation_receipt")

# --- a job whose process is gone, or which runs past its bound, is a recorded failure ---------------------------------------------
dead = adapter.job_status("latest", alive=lambda pid: False)
require(dead["status"] == "failed" and dead["failure"] == "job_process_ended_without_result" and adapter.active_job() is None,
        "a_job_whose_process_ended_without_a_result_is_recorded_as_failed")
stale = adapter.start_review("G-TEST", confirmed=True)
adapter.save_job({**stale, "started_monotonic_epoch": time.time() - adapter.MAX_JOB_SECONDS - 1}, RUNTIME)
timed_out = adapter.job_status(stale["job_id"], alive=lambda pid: True)
require(timed_out["status"] == "failed" and timed_out["failure"] == "job_exceeded_maximum_duration",
        "a_job_past_its_bound_is_recorded_as_failed_rather_than_left_running")

# --- the adapter adds no authority -------------------------------------------------------------------------------------------------
source = (AGENT / "conversational_experiment_review.py").read_text(encoding="utf-8")
code = "\n".join(line for line in source.splitlines() if not line.strip().startswith("#"))
require("shell=True" not in code and "ollama" not in code.lower() and "11434" not in code and "os.system" not in code
        and code.count("Popen") == 1 and not any(hasattr(adapter, name) for name in ("schedule", "schedule_review", "run_periodically", "cron")),
        "no_shell_no_model_endpoint_and_nothing_schedules")
require(re.findall(r"add_task\(([A-Za-z_]+)", source) == ["REVIEW_KIND"] and adapter.REVIEW_KIND in lrq.IMPLEMENTED
        and adapter.REVIEW_KIND in lrq.READY_LOCAL_READ_ONLY, "only_the_already_authorized_review_kind_is_ever_queued")
for kind in sorted(lrq.REQUIRES_EXTERNAL_OR_OPERATOR_REVIEW):
    try:
        lrq.add_task(kind, "x")
        refused = False
    except PermissionError:
        refused = True
    require(refused, f"queue_still_refuses:{kind}")
require(adapter.execute_conversational_review_action("experiment_review_delete", {})["ok"] is False,
        "an_unknown_review_function_is_refused")
require(json.loads((RUNTIME / er.REVIEW_AREA / review["review_id"] / "review.json").read_text(encoding="utf-8"))["review_id"] == review["review_id"],
        "the_preserved_review_artifact_is_untouched_by_the_adapter")

print(json.dumps({"suite": "v2731.4.0-conversational-review-adapter", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
