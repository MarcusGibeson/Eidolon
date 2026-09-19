"""Observation adapter for frozen reviewers, used only by their detached runner.

The reviewer has no progress API and its digest is pinned. Scoped pass-through
wrappers observe existing boundaries, forward identical arguments/results, and
are restored even on failure. No prompt parsing, model-output storage or changes
to validation. Telemetry failure never changes the reviewed operation.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import logging
from threading import Event, Thread, get_ident

from activity import Activity, TERMINAL

STAGES = ("Preparing", "Observing", "Part Synthesis", "Document Synthesis", "Consolidating", "Final Synthesis", "Verifying")
STAGE_NAMES = {"observe": "Observing", "part": "Part Synthesis", "document": "Document Synthesis",
               "group": "Consolidating", "final": "Final Synthesis"}


class ReviewActivity:
    def __init__(self, job, root):
        self.activity = Activity(job["job_id"], "experiment_review", "Independent experiment review",
                                 job.get("package_id", ""), root=root, stages=STAGES, started=job.get("started"),
                                 identities={k: job.get(k, "") for k in ("job_id", "task_id", "package_id", "reviewer_contract")},
                                 governance={"read_only": True, "non_authoritative": True, "belief_effects": "none",
                                             "mutation_guard": "pending", "execution_authority": "existing_operator_confirmation"})
        self.counts = {"model_calls": 0, "responses_received": 0, "retries": 0, "grounded_observations": 0,
                       "rejected_observations": 0, "synthesis_units": 0}
        self.parts, self.done, self.required = {}, set(), set()
        self.stage_done, self.stage_totals = {}, {}
        self.seen_asks = set()
        self.stopped = Event()
        self.worker = Thread(target=self._heartbeat, daemon=True)
        self.worker.start()
        self.emit("job_started", state="preparing", stage="Preparing")

    def emit(self, event, **kw):
        try:
            self.activity.update(event, **kw)
        except Exception:
            logging.getLogger(__name__).warning("Activity observation unavailable: %s", event)

    def _heartbeat(self):
        while not self.stopped.wait(15):
            self.emit("worker_heartbeat")

    def finish(self, job, artifact=None):
        try:
            self._finish(job, artifact)
        except Exception:
            self.emit("telemetry_projection_failed")
            logging.getLogger(__name__).warning("Review completed; final activity projection unavailable")

    def _finish(self, job, artifact=None):
        self.stopped.set()
        self.worker.join(timeout=1)
        artifact = artifact or {}
        state = "failed" if job.get("status") == "failed" else {
            "complete": "complete", "mutation_guard_failed": "failed"}.get(artifact.get("status"), "incomplete")
        checks = artifact.get("mutation_guard") or {}
        self.counts["missing_required_parts"] = sum(key not in self.done for key in self.required)
        model = (artifact.get("provenance") or {}).get("model") or {}
        for missing in (artifact.get("coverage") or {}).get("missing", []):
            level = missing.get("level")
            label = {"part": "Part Synthesis", "document": "Document Synthesis", "intermediate": "Consolidating"}.get(level)
            if missing.get("kind") in {"required_role_absent", "required_part_not_reviewed"}:
                label = "Observing"
            elif missing.get("kind") == "final_synthesis_failed":
                label = "Final Synthesis"
            for row in self.activity.record["stages"]:
                if row["name"] == label:
                    row["state"] = "incomplete"
        self.emit("job_" + state, state=state, metrics=self.counts,
                  result=str(artifact.get("status") or "no_review_artifact"),
                  reason="review_job_failed" if state == "failed" else
                         ("required_review_coverage_or_synthesis_incomplete" if state == "incomplete" else ""),
                  identities={"review_id": job.get("review_id", ""),
                              "provider": model.get("provider", ""), "model": model.get("model", "")},
                  governance={"mutation_guard": "passed" if checks.get("passed") is True else
                              "failed" if checks.get("passed") is False else "unverified"})

    @contextmanager
    def observe(self, reviewer):
        import experiment_review as base
        owner = get_ident()
        originals = []

        def install(module, name, handler):
            original = getattr(module, name)
            @wraps(original)
            def wrapper(*args, **kwargs):
                if get_ident() != owner:
                    return original(*args, **kwargs)
                return handler(original, *args, **kwargs)
            originals.append((module, name, original))
            setattr(module, name, wrapper)

        def safe(fn, *args):
            try:
                fn(*args)
            except Exception:
                self.emit("telemetry_projection_failed")

        def package_loaded(package):
            for doc in package["documents"]:
                n = len(base.chunks(doc["text"]))
                self.parts[doc["doc_id"]] = {"id": doc["doc_id"], "label": doc["role"], "completed": 0, "total": n}
                if doc["required"]:
                    self.required.update((doc["doc_id"], p) for p in range(1, n + 1))
            self.emit("package_validated", units=(0, len(self.required), "required parts"),
                      breakdown=list(self.parts.values()))

        def load(original, *args, **kwargs):
            result = original(*args, **kwargs)
            safe(package_loaded, result)
            return result

        def ask(original, call_model, prompt, max_tokens, accept, ledger, stage, **kwargs):
            def entered():
                name = STAGE_NAMES.get(stage.split(":")[0], "Consolidating")
                stage_args = {"state": "running", "stage": name}
                if stage.startswith("observe:"):
                    pieces = stage.split(":")
                    stage_args["identities"] = {"current_document": pieces[1], "current_part": pieces[2]}
                if name == "Final Synthesis":
                    stage_args["stage_units"] = (self.stage_done.get(name, 0), 2, "halves")
                self.emit("stage_entered", **stage_args)
                if stage in self.seen_asks or ":retry" in stage:
                    self.counts["retries"] += 1
                    self.emit("retry_started", metrics=self.counts)
                self.seen_asks.add(stage)
            safe(entered)
            calls = 0
            def contacting():
                if calls > 1:
                    self.counts["retries"] += 1
                    self.emit("retry_started", metrics=self.counts)
                self.counts["model_calls"] += 1
                self.emit("model_call_started", metrics=self.counts)
            def received():
                self.counts["responses_received"] += 1
                self.emit("model_response_received", metrics=self.counts)
            def model(text, tokens):
                nonlocal calls
                calls += 1
                safe(contacting)
                # The original exception/result propagates exactly as without observation.
                response = call_model(text, tokens)
                safe(received)
                return response
            result = original(model, prompt, max_tokens, accept, ledger, stage, **kwargs)
            def completed():
                if not stage.startswith("observe:"):
                    name = STAGE_NAMES.get(stage.split(":")[0], "Consolidating")
                    self.stage_done[name] = self.stage_done.get(name, 0) + 1
                    self.counts["synthesis_units"] += 1
                    total = 2 if name == "Final Synthesis" else self.stage_totals.get(name)
                    self.emit("synthesis_unit_completed" if result[0] is not None else "synthesis_unit_incomplete",
                              metrics=self.counts, stage_units=(self.stage_done[name], total, "units"))
            safe(completed)
            return result

        def grounded(result, doc_id, part):
            g, r, _ = result
            self.counts["grounded_observations"] += len(g)
            self.counts["rejected_observations"] += len(r)
            if g and (doc_id, part) not in self.done:
                self.done.add((doc_id, part))
                self.parts[doc_id]["completed"] += 1
            self.emit("observations_grounded", metrics=self.counts,
                      identities={"current_document": doc_id, "current_part": part},
                      units=(len(self.done & self.required), len(self.required), "required parts"),
                      stage_units=(len(self.done), sum(p["total"] for p in self.parts.values()), "parts"),
                      breakdown=list(self.parts.values()))
            if r:
                self.emit("observations_rejected")
            if g:
                self.emit("part_completed")

        def ground(original, *args, **kwargs):
            result = original(*args, **kwargs)
            safe(grounded, result, args[2], args[3])
            return result

        snapshots = 0
        def snapshot(original, *args, **kwargs):
            nonlocal snapshots
            snapshots += 1
            if snapshots > 1:
                self.emit("verification_started", stage="Verifying", state="running")
            return original(*args, **kwargs)

        def comparison(original, *args, **kwargs):
            result = original(*args, **kwargs)
            self.emit("mutation_guard_failed" if result else "mutation_guard_passed",
                      governance={"mutation_guard": "failed" if result else "passed"})
            return result

        def plan_handler(label):
            def planned(result):
                self.stage_totals[label] = self.stage_totals.get(label, 0) + len(result)
                self.emit("work_units_planned", stage=label, state="running",
                          stage_units=(self.stage_done.get(label, 0), self.stage_totals[label], "units"))
            def plan(original, *args, **kwargs):
                result = original(*args, **kwargs)
                safe(planned, result)
                return result
            return plan

        def identity(original, *args, **kwargs):
            result = original(*args, **kwargs)
            safe(lambda: self.emit("model_identity_resolved", identities={k: result.get(k, "") for k in ("model", "provider")}))
            return result

        try:
            install(base, "load_package", load)
            install(base, "_ask", ask)
            install(base, "ground_observations", ground)
            install(base, "snapshot_protected", snapshot)
            install(base, "compare_snapshots", comparison)
            install(base, "model_identity", identity)
            install(base, "plan_part_units", plan_handler("Part Synthesis"))
            install(base, "plan_document_units", plan_handler("Document Synthesis"))
            if hasattr(reviewer, "plan_group_units"):
                install(reviewer, "plan_group_units", plan_handler("Consolidating"))
            yield
        finally:
            for module, name, original in reversed(originals):
                setattr(module, name, original)


@contextmanager
def observing_review(job, root, reviewer):
    """Only instrumentation setup may fail open; never retry the operation."""
    observer = None
    try:
        observer = ReviewActivity(job, root)
    except Exception:
        logging.getLogger(__name__).warning("Review activity unavailable; review continues without telemetry")
    if observer is None:
        yield None
        return
    try:
        with observer.observe(reviewer):
            yield observer
    finally:
        observer.stopped.set()
        observer.worker.join(timeout=1)
