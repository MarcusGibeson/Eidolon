from __future__ import annotations

"""Supervised read-only experiment self-review (spec 2.18): review_experiment and the local research queue.

Deterministic stub model; no provider contact. Proves that an explicitly selected package is verified before any call,
that only listed documents are read, that every observation is grounded in a verbatim quote, that interpretation cites
existing observation ids, that the artifact is written only in the review area with non-authoritative provenance, that
the mutation guard detects a change to a protected path, a protected runtime root or a git source tree, that failed
synthesis is recorded rather than fabricated, and that the queue admits only operator-chosen READY read-only kinds.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-5-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

import experiment_review as er  # noqa: E402
import local_research_queue as lrq  # noqa: E402

CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_package(base: Path, *, extra: dict | None = None) -> Path:
    pkg = base / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "design.txt").write_text("The experiment asks whether the label stays the same.\nControls: A, B.\n", encoding="utf-8")
    (pkg / "items.txt").write_text("A: gold continuing\nB: gold unresolved\n", encoding="utf-8")
    (pkg / "outputs.txt").write_text("run1 A continuing\nrun2 A continuing\nrun1 B unresolved\nrun2 B event_only\n", encoding="utf-8")
    (pkg / "secret_unlisted.txt").write_text("UNLISTED-SECRET-CONTENT", encoding="utf-8")
    docs = [{"doc_id": "D1", "path": "design.txt", "role": "design", "description": "frozen design", "sha256": sha(pkg / "design.txt")},
            {"doc_id": "D2", "path": "items.txt", "role": "corpus", "description": "items", "sha256": sha(pkg / "items.txt")},
            {"doc_id": "D3", "path": "outputs.txt", "role": "raw_outputs", "description": "raw outputs", "sha256": sha(pkg / "outputs.txt")}]
    manifest = {"experiment_id": "TEST", "title": "Test experiment", "task": "independent_review", "brief": "Review it.", "documents": docs,
                **(extra or {})}
    (pkg / er.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


FIRST = {"experiment_understanding": {"statement": "It checks label stability.", "int_ids": ["I1"]},
         "observations": [{"statement": "B changed between runs", "int_ids": ["I2"]}],
         "passed": [{"statement": "A held", "int_ids": ["I1"]}], "failed": [{"statement": "B moved", "int_ids": ["I2", "I99"]}],
         "failure_clusters": [], "possible_harness_or_measurement_failures": [], "possible_model_or_reasoning_failures": [], "ambiguous_cases": []}
SECOND = {"competing_hypotheses": [{"hypothesis": "B is near a boundary", "evidence_for": ["I2"], "evidence_against": []},
                                   {"hypothesis": "Run noise", "evidence_for": [], "evidence_against": ["I1"]}],
          "unknowns": [{"statement": "why B moved", "int_ids": ["I2"]}], "confidence": {"level": "low", "reason": "two runs", "int_ids": ["I1"]},
          "discriminating_experiments": [{"experiment": "repeat B five times", "distinguishes": [1, 2, 7], "int_ids": ["I2"]}],
          "not_established": [{"statement": "a cause", "int_ids": ["I2"]}]}


class Stub:
    def __init__(self, *, first=FIRST, second=SECOND, bad_first_times=0, hook=None, error_stage=None):
        self.prompts, self.first, self.second, self.bad_first_times, self.hook, self.error_stage = [], first, second, bad_first_times, hook, error_stage

    def __call__(self, prompt: str, max_tokens: int):
        self.prompts.append(prompt)
        if self.hook:
            self.hook(prompt)
        if "List up to" in prompt:
            chunk = prompt.split("---\n", 1)[1].rsplit("\n---\n", 1)[0]
            line = chunk.strip().splitlines()[0]
            return json.dumps({"observations": [{"statement": f"the part says {line}", "quote": line},
                                                {"statement": "an invented fact", "quote": "text that is nowhere in the document"}],
                               "open_questions": ["what next?"]}), {"seconds": 0.0}
        if "Write a bounded synthesis" in prompt:
            ids = re.findall(r"^(O[0-9]+) [(]part [0-9]+[)]: ", prompt, re.M)
            return json.dumps({"statements": [{"statement": "the unit records these observations", "kind": "finding", "obs_ids": ids}]}), {"seconds": 0.0}
        if "first half" in prompt and "second half" not in prompt:
            if self.bad_first_times:
                self.bad_first_times -= 1
                return "{not json", {"seconds": 0.0}
            return json.dumps(self.first) if self.first is not None else "{}", {"seconds": 0.0}
        if self.error_stage == "second":
            return "", {"seconds": 1.0, "error": "LocalModelTimeoutError: Local model request timed out"}
        return json.dumps(self.second), {"seconds": 0.0}


IDENT = {"model": "stub", "provider": "stub", "context_size": 8192, "resolved_config_sha256": "0" * 64}
base = Path(tempfile.mkdtemp(prefix="eidolon-v2731-3-5-case-"))

# --- the package fails closed before any model call ---------------------------------------------------------------------------
for name, mutate in (("digest_mismatch", lambda p: (p / "design.txt").write_text("changed", encoding="utf-8")),
                     ("outside_package", lambda p: _rewrite(p, lambda m: m["documents"][0].update(path="../escape.txt"))),
                     ("unsupported_task", lambda p: _rewrite(p, lambda m: m.update(task="modify_source"))),
                     ("invalid_role", lambda p: _rewrite(p, lambda m: m["documents"][0].update(role="gold_writer")))):
    def _rewrite(p, change):
        m = json.loads((p / er.MANIFEST_NAME).read_text(encoding="utf-8"))
        change(m)
        (p / er.MANIFEST_NAME).write_text(json.dumps(m), encoding="utf-8")
    case = base / f"fail_{name}"
    pkg = make_package(case)
    mutate(pkg)
    stub = Stub()
    try:
        er.review_experiment(pkg, call_model=stub, identity=IDENT)
        raised = False
    except er.ReviewPackageError:
        raised = True
    require(raised and not stub.prompts, f"package_fails_closed_before_any_call:{name}")
require(all(er.load_package(make_package(base / "ok"))["documents"][i]["doc_id"] == f"D{i + 1}" for i in (0, 1)), "a_valid_package_loads_listed_documents")

# --- chunking -----------------------------------------------------------------------------------------------------------------
text = "".join(f"line {i} " + "x" * (i % 50) + "\n" for i in range(3000))
parts = er.chunks(text, 1000)
require("".join(parts) == text and all(len(p) <= 1000 for p in parts), "chunks_are_lossless_and_bounded")
require(er.chunks("y" * 2500, 1000) == ["y" * 1000, "y" * 1000, "y" * 500], "an_overlong_line_is_cut_losslessly")

# --- a complete review ---------------------------------------------------------------------------------------------------------
pkg = make_package(base / "full")
before_pkg = {p.name: sha(p) for p in pkg.iterdir()}
stub = Stub()
art = er.review_experiment(pkg, call_model=stub, identity=IDENT)
require(art["status"] == "complete" and art["mutation_guard"]["passed"], "a_clean_review_completes_with_the_guard_passed")
require(not any("UNLISTED-SECRET-CONTENT" in p for p in stub.prompts), "an_unlisted_file_in_the_package_is_never_read")
require(len(art["grounded_observations"]) == 3 and len(art["rejected_observations"]) == 3
        and all(r["reason"] == "quote_not_found_in_document" for r in art["rejected_observations"]), "every_observation_needs_a_verbatim_quote")
require(not any("an invented fact" in p for p in stub.prompts if "first half" in p or "second half" in p), "rejected_observations_never_reach_synthesis")
require([o["obs_id"] for o in art["grounded_observations"]] == ["O1", "O2", "O3"], "observation_ids_are_sequential")
require(art["unknown_references"] == ["I99"] and art["review"]["failed"][0]["int_ids"] == ["I2"], "references_to_unknown_statements_are_flagged_and_dropped")
require(art["review"]["discriminating_experiments"][0]["distinguishes"] == [1, 2] and art["review"]["discriminating_experiments"][0]["distinguishes_unknown"] == [7],
        "experiments_must_name_existing_hypotheses")
require(art["non_authoritative"] is True and all(v is False for v in art["authority"].values()), "the_review_is_non_authoritative_with_no_authority")
require(art["provenance"]["mutation_authority"] == "none" and art["provenance"]["experiment_id"] == "TEST" and art["provenance"]["model"] == IDENT
        and len(art["provenance"]["documents"]) == 3 and all(len(d["sha256"]) == 64 for d in art["provenance"]["documents"]),
        "provenance_names_the_experiment_model_digests_and_no_mutation_authority")
out = RUNTIME / er.REVIEW_AREA / art["review_id"]
require((out / "review.json").is_file() and (out / "review.md").is_file() and sorted(p.name for p in RUNTIME.rglob("*") if p.is_file()) ==
        ["review.json", "review.md"], "the_only_files_written_are_the_review_artifacts_in_the_review_area")
require({p.name: sha(p) for p in pkg.iterdir()} == before_pkg, "the_package_is_unchanged")
require("cannot change any label, verdict, evidence, belief, memory, policy, configuration or code" in stub.prompts[0]
        and "Do not propose code changes whose purpose is to make a benchmark pass" in stub.prompts[0], "the_prompt_states_the_boundaries")
require(art["runtime_accounting"]["provider_attempts"] == len(stub.prompts) and art["runtime_accounting"]["failed_attempts"] == 0,
        "attempts_are_accounted")
md = (out / "review.md").read_text(encoding="utf-8")
require("Non-authoritative research artifact" in md and "## Competing hypotheses" in md, "the_markdown_rendering_carries_the_status")

# --- repair retry, and failure recorded not fabricated -----------------------------------------------------------------------
art = er.review_experiment(make_package(base / "retry"), call_model=Stub(bad_first_times=1), identity=IDENT)
require(art["status"] == "complete" and art["runtime_accounting"]["retries"] == 1, "one_repair_retry_is_used_and_counted")
art = er.review_experiment(make_package(base / "never"), call_model=Stub(first=None), identity=IDENT)
require(art["status"] == "incomplete" and art["review"] == {} and "final:first_half" in art["runtime_accounting"]["stages_without_accepted_reply"],
        "a_failed_synthesis_is_recorded_and_nothing_is_fabricated")
art = er.review_experiment(make_package(base / "timeout"), call_model=Stub(error_stage="second"), identity=IDENT)
require(art["status"] == "incomplete" and art["runtime_accounting"]["timeout_attempts"] == 2 and art["runtime_accounting"]["failed_attempts"] == 2,
        "timeouts_are_counted_separately")

# --- the mutation guard ---------------------------------------------------------------------------------------------------------
protected = base / "registered"
protected.mkdir()
(protected / "gold.json").write_text('{"A": "continuing"}', encoding="utf-8")
art = er.review_experiment(make_package(base / "guard_path"), call_model=Stub(hook=lambda p: (protected / "gold.json").write_text('{"A": "event_only"}', encoding="utf-8")
                                                                                     if "List up to" in p else None),
                           identity=IDENT, protected_paths=[protected])
require(art["status"] == "mutation_guard_failed" and any("gold.json" in c for c in art["mutation_guard"]["changes"]), "a_change_to_a_protected_path_fails_the_guard")
state_root = base / "real_data"
(state_root / "cognition").mkdir(parents=True)
(state_root / "cognition" / "beliefs.json").write_text("[]", encoding="utf-8")
art = er.review_experiment(make_package(base / "guard_root"), call_model=Stub(hook=lambda p: (state_root / "cognition" / "beliefs.json").write_text('[{"x":1}]', encoding="utf-8")
                                                                                     if "second half" in p else None),
                           identity=IDENT, protected_roots=[state_root])
require(art["status"] == "mutation_guard_failed" and any("beliefs.json" in c for c in art["mutation_guard"]["changes"]), "a_change_to_belief_state_fails_the_guard")
art = er.review_experiment(make_package(base / "guard_runtime"), call_model=Stub(hook=lambda p: (RUNTIME / "settings.json").write_text("{}", encoding="utf-8")
                                                                                        if "first half" in p else None), identity=IDENT)
require(art["status"] == "mutation_guard_failed" and any("settings.json" in c for c in art["mutation_guard"]["changes"]),
        "a_new_file_in_the_runtime_root_outside_the_review_area_fails_the_guard")
(RUNTIME / "settings.json").unlink()
repo = base / "repo"
repo.mkdir()
git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True)  # noqa: E731
git("init", "-q")
(repo / "module.py").write_text("x = 1\n", encoding="utf-8")
git("add", "module.py")
git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init")
art = er.review_experiment(make_package(base / "guard_source"), call_model=Stub(hook=lambda p: (repo / "module.py").write_text("x = 2\n", encoding="utf-8")
                                                                                       if "List up to" in p else None), identity=IDENT, source_root=repo)
require(art["status"] == "mutation_guard_failed" and "source_tree" in " ".join(art["mutation_guard"]["changes"]), "a_source_change_fails_the_guard")
git("checkout", "--", "module.py")
art = er.review_experiment(make_package(base / "guard_clean"), call_model=Stub(), identity=IDENT, source_root=repo, protected_paths=[protected],
                           protected_roots=[state_root])
require(art["status"] == "complete" and art["mutation_guard"]["passed"] and art["mutation_guard"]["protected"]["source_tree"],
        "with_nothing_changed_the_full_guard_passes")

# --- the local research queue ----------------------------------------------------------------------------------------------------
for kind in lrq.REQUIRES_EXTERNAL_OR_OPERATOR_REVIEW:
    try:
        lrq.add_task(kind, "x")
        refused = False
    except PermissionError:
        refused = True
    require(refused, f"queue_refuses:{kind}")
try:
    lrq.add_task("run_anything", "x")
    unknown = False
except ValueError:
    unknown = True
require(unknown, "queue_refuses_unknown_kinds")
later = lrq.add_task("cluster_historical_failures", "all")
try:
    lrq.run_task(later["task_id"], runner=lambda t: {"status": "complete"})
    ran = True
except NotImplementedError:
    ran = False
require(not ran, "a_listed_but_unimplemented_kind_cannot_run")
task = lrq.add_task("independent_experiment_review", str(make_package(base / "queued")), operator_note="first review")
done = lrq.run_task(task["task_id"], runner=lambda target: er.review_experiment(target, call_model=Stub(), identity=IDENT))
require(done["status"] == "completed" and done["chosen_by"] == "operator" and done["review_id"], "an_operator_chosen_review_runs_once_from_the_queue")
try:
    lrq.run_task(task["task_id"], runner=lambda t: {"status": "complete"})
    rerun = True
except ValueError:
    rerun = False
require(not rerun, "a_finished_task_does_not_run_again")
require((RUNTIME / er.REVIEW_AREA / lrq.QUEUE_FILE).is_file() and not any(p.name == "local_queue.json" for p in RUNTIME.iterdir()),
        "the_queue_lives_in_the_review_area")
require(not hasattr(lrq, "schedule") and not hasattr(er, "schedule"), "nothing_schedules_itself")

print(json.dumps({"suite": "v2731.3.5-experiment-review", "passed": len(CHECKS), "total": len(CHECKS), "ok": True}))
