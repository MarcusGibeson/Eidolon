from __future__ import annotations

"""The private, quiescent review runtime and the widened mutation guard (spec 2.33).

Deterministic; no provider contact and no detached process. A detached review used the live data directory as its
runtime root, and the frozen reviewer always guards its runtime root, so ordinary conversation, cognition and
vector-store writes during a multi-hour review counted as mutations. The review now owns a private runtime nothing
else writes to, while the guard covers strictly more of what matters: the package, the installed package area, the
existing review artifacts, and the source tree, which live runs did not guard at all.

These checks drive the real runner, the real private runtime and the real guard through a stub model, and prove both
directions: live application churn does not trip the guard, and every mutation that should trip it does.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT), str(ROOT / "tools")):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-11-0-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import conversational_experiment_review as adapter  # noqa: E402
import experiment_review as er  # noqa: E402
import chat_action_router as router  # noqa: E402
import run_review_job  # noqa: E402

CHECKS: list[str] = []
BASELINE_SHA = "d158e253dd88febca8f22ed050beccde2724fd9b604138fa579c5201228b21c8"


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


# --- the frozen reviewer is untouched ------------------------------------------------------------------------------
# The recorded baseline is the digest of the file as stored, with newlines normalised: a Windows checkout rewrites
# line endings, so hashing the working copy byte for byte would report a change that does not exist.
normalised = (AGENT / "experiment_review.py").read_bytes().replace(b"\r\n", b"\n")
require(hashlib.sha256(normalised).hexdigest() == BASELINE_SHA, "the_reviewer_baseline_digest_is_unchanged")

# --- a package to review -------------------------------------------------------------------------------------------
DOCS = {"design.txt": ("design", "The experiment asks whether each item keeps its label across prompt forms.\n"),
        "items.txt": ("corpus", "item=A gold=unresolved\nitem=B gold=continuing\n"),
        "outputs.txt": ("raw_outputs", "form=V1 item=A classification=unresolved\nform=V2 item=A classification=event_only\n")}


def install_package(name: str) -> Path:
    pkg = adapter.package_area() / name
    pkg.mkdir(parents=True, exist_ok=True)
    entries = []
    for n, (file_name, (role, text)) in enumerate(DOCS.items(), 1):
        (pkg / file_name).write_text(text, encoding="utf-8", newline="\n")
        entries.append({"doc_id": f"D{n}", "path": file_name, "role": role, "description": file_name,
                        "sha256": hashlib.sha256((pkg / file_name).read_bytes()).hexdigest()})
    (pkg / er.MANIFEST_NAME).write_text(json.dumps({"experiment_id": name, "title": f"{name} test experiment",
                                                    "task": "independent_review", "brief": "Review it.",
                                                    "documents": entries}), encoding="utf-8")
    return pkg


PACKAGE = install_package("G-GUARD")
adapter.SPAWN = lambda argv, cwd, env: 4242
adapter.ALIVE = lambda pid: pid == 4242

OK_META = {"seconds": 0.0, "metrics": {"eval_count": 40, "prompt_eval_count": 500}}
IDENT = {"model": "stub", "provider": "stub", "context_size": 8192, "resolved_config_sha256": "0" * 64}


def conforming_reply(prompt: str, max_tokens: int):
    """A reviewer stub that satisfies every stage schema, so only the guard decides the outcome."""
    if "List up to" in prompt:
        line = prompt.split("---\n", 1)[1].rsplit("\n---\n", 1)[0].strip().splitlines()[0]
        return json.dumps({"observations": [{"statement": f"the part contains {line}", "quotes": [line]}],
                           "open_questions": []}), dict(OK_META)
    if "Write a part-level synthesis" in prompt or "Write a document-level synthesis" in prompt:
        part = "Write a part-level synthesis" in prompt
        ids = re.findall(r"^(O[0-9]+)(?: \[[^\]]*\])?: " if part else r"^((?:PS|O)[0-9]+) \[", prompt, re.M)
        cap = int(re.search(r"Give at most ([0-9]+) statements", prompt).group(1))
        groups = [ids[i:i + er.MAX_IDS_PER_STATEMENT] for i in range(0, len(ids), er.MAX_IDS_PER_STATEMENT)][:cap]
        return json.dumps({"statements": [{"statement": "these inputs are recorded", "kind": "finding",
                                           ("obs_ids" if part else "input_ids"): g} for g in groups]}), dict(OK_META)
    if "second half" in prompt:
        return json.dumps({"competing_hypotheses": [], "unknowns": [],
                           "confidence": {"level": "low", "reason": "small", "input_ids": ["DS1"]},
                           "discriminating_experiments": [], "not_established": []}), dict(OK_META)
    return json.dumps({"experiment_understanding": {"statement": "the forms disagree about item A", "input_ids": ["DS1"]},
                       **{k: [] for k in er.SECTIONS_A[1:]}}), dict(OK_META)


CURRENT: dict = {}


def run_review(*, during=None) -> dict:
    """Start a review the way the operator does, then run its job. ``during`` mutates something mid-review."""
    fired = {"done": False}

    def model(prompt: str, max_tokens: int):
        if during is not None and not fired["done"]:
            fired["done"] = True
            during()
        return conforming_reply(prompt, max_tokens)

    job = adapter.start_review("G-GUARD", confirmed=True)
    CURRENT["job"] = job
    run_review_job.CALL_MODEL = model
    run_review_job.IDENTITY = IDENT
    try:
        record = run_review_job.run_job(adapter.job_area() / f"{job['job_id']}.json")
    finally:
        run_review_job.CALL_MODEL = None
        run_review_job.IDENTITY = None
    require(during is None or fired["done"], "the_mid_review_mutation_actually_happened")
    return record


def guard_of(record: dict) -> dict:
    return json.loads((Path(record["location"]) / "review.json").read_text(encoding="utf-8"))["mutation_guard"]


# --- 1. a clean review, and what it guards ---------------------------------------------------------------------------
clean = run_review()
clean_guard = guard_of(clean)
require(clean["status"] == "completed" and clean["review_status"] == "complete", "a_clean_review_completes")
require(clean_guard["passed"] is True, "a_clean_review_passes_its_guard")
require(clean_guard["protected"]["source_tree"] is True, "the_source_tree_is_guarded")
require(clean["checks"]["source_tree_guarded"] is True, "the_job_record_reports_that_source_was_guarded")
require(clean_guard["protected"]["package"] is True, "the_package_is_guarded")

guarded_roots = [Path(r) for r in clean_guard["protected"]["roots"]]
private_root = RUNTIME / run_review_job.PRIVATE_RUNTIME_AREA / clean["job_id"]
require(private_root in guarded_roots, "the_private_runtime_is_guarded")
require(RUNTIME / adapter.PACKAGE_AREA in guarded_roots, "the_installed_package_area_is_guarded")
require(RUNTIME not in guarded_roots, "the_live_data_directory_is_not_guarded_as_a_whole")
# Earlier reviews are guarded one directory at a time: the research queue keeps local_queue.json beside them, and
# other deterministic queue work is allowed to continue while a review runs.
require(RUNTIME / er.REVIEW_AREA not in guarded_roots, "the_review_area_itself_is_not_guarded_as_a_whole")
require(str(clean["private_runtime_root"]) == str(private_root), "the_job_record_names_the_private_runtime")
require(Path(clean["location"]) == RUNTIME / er.REVIEW_AREA / clean["review_id"],
        "the_artifact_is_published_into_the_live_review_area")

# Nothing of the live application was copied into the private runtime.
private_entries = {p.name for p in private_root.iterdir()}
require(private_entries == {er.REVIEW_AREA}, "the_private_runtime_holds_only_the_review_output")
for churn in ("cognition", "conversation_runtime", "conversation_sessions", "chroma", "dashboard_chat"):
    require(not (private_root / churn).exists(), f"live_state_is_not_copied_into_the_private_runtime:{churn}")


# --- 2. live application churn must not trip the guard ---------------------------------------------------------------
def write_live_churn() -> None:
    """Exactly the categories that failed the live G-INVAR run."""
    for relative, payload in (("cognition/cognitive_cycle_state.json", '{"cycle": 41}'),
                              ("cognition/belief_revision.json", '{"revisions": []}'),
                              ("conversation_runtime/operations/conversation_probe.json", '{"op": "probe"}'),
                              ("conversation_sessions/session_probe.json", '{"session": "probe"}'),
                              ("conversation_policy_state/operations/policy_probe.json", '{"policy": "probe"}'),
                              ("dashboard_chat/dash_chat_probe.json", '{"turn": "probe"}'),
                              ("chroma/chroma.sqlite3", "not really a database, but it changes")):
        path = RUNTIME / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    # Other deterministic queue work continues during a review, and writes local_queue.json beside the artifacts.
    import local_research_queue as lrq

    lrq.add_task("cluster_historical_failures", "all")


churn = run_review(during=write_live_churn)
require(guard_of(churn)["passed"] is True, "live_runtime_churn_does_not_trip_the_review_guard")
require(churn["checks"]["mutation_guard_passed"] is True, "the_job_record_reports_the_guard_passed_through_churn")
require((RUNTIME / "cognition" / "cognitive_cycle_state.json").exists(), "the_live_churn_really_was_written")

# A second review's arrival in the live area is not a mutation of the first one's world either.
published = sorted(p.name for p in (RUNTIME / er.REVIEW_AREA).iterdir() if p.is_dir())
require(published == sorted([clean["review_id"], churn["review_id"]]), "both_reviews_are_published")
require((RUNTIME / er.REVIEW_AREA / "local_queue.json").exists(), "the_queue_really_was_written_during_the_review")

# The earlier review is guarded by the next one, as its own directory.
second_roots = [Path(r) for r in guard_of(churn)["protected"]["roots"]]
require(RUNTIME / er.REVIEW_AREA / clean["review_id"] in second_roots,
        "an_existing_review_artifact_is_guarded_by_the_next_review")
require(RUNTIME / er.REVIEW_AREA not in second_roots, "the_queue_file_is_never_guarded")


# --- 3. every mutation that should trip the guard does ---------------------------------------------------------------
def mutate_package() -> None:
    (PACKAGE / "items.txt").write_text("item=A gold=CHANGED\n", encoding="utf-8", newline="\n")


def mutate_source() -> None:
    (ROOT / ".v2731_11_0_guard_probe.tmp").write_text("an untracked source-tree change\n", encoding="utf-8")


def mutate_existing_review() -> None:
    artifact = Path(clean["location"]) / "review.json"
    artifact.write_text(artifact.read_text(encoding="utf-8") + "\n", encoding="utf-8")


def mutate_private_runtime() -> None:
    """A stray file in the runtime this very review owns, outside its own output directory."""
    running = RUNTIME / run_review_job.PRIVATE_RUNTIME_AREA / CURRENT["job"]["job_id"]
    (running / "not_a_review_output.json").write_text('{"stray": true}', encoding="utf-8")


package_before = (PACKAGE / "items.txt").read_bytes()
existing_before = (Path(clean["location"]) / "review.json").read_bytes()

try:
    mutated = run_review(during=mutate_package)
    package_guard = guard_of(mutated)
    require(package_guard["passed"] is False, "package_mutation_trips_the_guard")
    require(any(c.startswith("package:") for c in package_guard["changes"]), "the_guard_names_the_package_change")
finally:
    (PACKAGE / "items.txt").write_bytes(package_before)

try:
    mutated = run_review(during=mutate_source)
    source_guard = guard_of(mutated)
    require(source_guard["passed"] is False, "source_mutation_trips_the_guard")
    require(any(c.startswith("source_tree:") for c in source_guard["changes"]), "the_guard_names_the_source_change")
finally:
    (ROOT / ".v2731_11_0_guard_probe.tmp").unlink(missing_ok=True)

mutated = run_review(during=mutate_existing_review)
review_guard = guard_of(mutated)
require(review_guard["passed"] is False, "protected_review_artifact_mutation_trips_the_guard")
require(any(er.REVIEW_AREA in c for c in review_guard["changes"]), "the_guard_names_the_review_artifact_change")
(Path(clean["location"]) / "review.json").write_bytes(existing_before)

mutated = run_review(during=mutate_private_runtime)
private_guard = guard_of(mutated)
require(private_guard["passed"] is False, "private_runtime_mutation_outside_review_output_is_detected")
require(any("not_a_review_output.json" in c for c in private_guard["changes"]), "the_guard_names_the_stray_private_file")

# The package and the earlier artifact survived every adversarial run byte for byte.
require((PACKAGE / "items.txt").read_bytes() == package_before, "the_package_is_restored_and_unchanged")
require((Path(clean["location"]) / "review.json").read_bytes() == existing_before,
        "the_existing_review_artifact_is_unchanged")
require(not (ROOT / ".v2731_11_0_guard_probe.tmp").exists(), "the_source_probe_left_nothing_behind")


# --- 4. the operator workflow still works ------------------------------------------------------------------------------
action = router.propose_chat_action("Review G-GUARD independently.", save=False, save_unknown=False)
require(action["intent"] == "experiment_review_start" and action["function_name"] == "experiment_review_start",
        "chat_invocation_still_routes_to_the_review")
require(router.propose_chat_action("What experiments can you review?", save=False, save_unknown=False)["intent"]
        == "experiment_review_list", "chat_listing_still_routes")

detached = adapter.start_review("G-GUARD", confirmed=True)
require(detached["status"] == "running" and detached["pid"] == 4242, "a_confirmed_review_starts_detached")
require(adapter.active_job()["job_id"] == detached["job_id"], "a_running_job_is_found_again_after_reconnection")
status = adapter.job_status(detached["job_id"])
require(status["status"] == "running" and status["package_id"] == "G-GUARD", "status_reports_the_running_job")
receipt = adapter.receipt(status)
require(set(receipt) == {"job_id", "task_id", "package_id", "manifest_sha256", "status", "review_id", "authority"},
        "the_receipt_carries_ids_and_status_only")
require("the forms disagree about item A" not in json.dumps(receipt), "the_receipt_carries_no_review_conclusion")

finished = adapter.job_status(clean["job_id"])
require(finished["status"] == "completed" and finished["review_id"] == clean["review_id"],
        "a_finished_job_is_still_reported_from_the_published_artifact")
require("the forms disagree about item A" not in json.dumps(finished), "job_status_carries_no_review_conclusion")

require(hashlib.sha256((AGENT / "experiment_review.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == BASELINE_SHA,
        "the_reviewer_baseline_digest_is_still_unchanged_after_every_run")

shutil.rmtree(RUNTIME, ignore_errors=True)
print(json.dumps({"suite": "v2731.11.0-private-review-runtime", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
