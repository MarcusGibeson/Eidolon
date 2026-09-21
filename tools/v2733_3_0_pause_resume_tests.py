"""v2733.3.0 - adversarial tests for cooperative pause, durable checkpoints and integrity-checked resume.

A paused review must be the same review when it comes back: no repeated provider call, no skipped work, no duplicated
or renamed observation, no altered synthesis input, and no quietly reconciled drift. The decisive test is the last
one: an uninterrupted run and a run paused and resumed several times must produce mechanically equivalent lineage
under a deterministic model.

    python tools/v2733_3_0_pause_resume_tests.py
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import cooperative_pause as pause  # noqa: E402
import experiment_review as base  # noqa: E402
import experiment_review_hierarchical as hier  # noqa: E402
import reviewer_capacity_qualification as q  # noqa: E402

CHECKS: list[tuple[str, bool]] = []
IDENT = {"model": "stub", "provider": "test", "context_size": 8192, "resolved_config_sha256": "0" * 64}


def require(condition: bool, name: str) -> None:
    CHECKS.append((name, bool(condition)))


class Recorder:
    """A deterministic model that records every prompt and can raise a pause request at a chosen moment."""

    def __init__(self, controls: Path, work_id: str, *, pause_at=None, cancel_at=None):
        self.inner = q.deterministic_stub()
        self.prompts: list[str] = []
        self.controls, self.work_id = controls, work_id
        self.pause_at, self.cancel_at = pause_at, cancel_at
        self.requested = False

    def __call__(self, prompt: str, max_tokens: int):
        self.prompts.append(hashlib.sha256(prompt.encode()).hexdigest()[:16])
        reply = self.inner(prompt, max_tokens)
        if not self.requested:
            trigger = self.pause_at or self.cancel_at
            if trigger and trigger(prompt, len(self.prompts)):
                pause.request(self.work_id, "pause" if self.pause_at else "cancel", self.controls,
                              note="adversarial test")
                self.requested = True
        return reply


def controls_for(pkg: Path, runtime: Path, work_id: str) -> Path:
    manifest = base._sha256_file(pkg / base.MANIFEST_NAME)
    return hier.control_root_for(runtime, manifest, work_id)


def fresh(tmp: Path, name: str, parts: int = 19):
    pkg = tmp / f"pkg-{name}"
    if not pkg.exists():
        q.build_package(pkg, parts)
    runtime = tmp / f"rt-{name}"
    runtime.mkdir(parents=True, exist_ok=True)
    return pkg, runtime


def run_to_completion(pkg: Path, runtime: Path, work_id: str, trigger, *, cycles: int = 8,
                      every_cycle: bool = False):
    """Start, pause when the trigger fires, resume, repeat. Returns the artifact and every prompt seen.

    ``every_cycle`` keeps arming the trigger so the work is interrupted over and over; otherwise it is armed once,
    which is the single pause-and-resume each level test wants.
    """
    controls = controls_for(pkg, runtime, work_id)
    seen: list[str] = []
    result = None
    for cycle in range(cycles):
        armed = trigger if (cycle == 0 or every_cycle) else None
        recorder = Recorder(controls, work_id, pause_at=armed)
        pause.clear(work_id, controls)
        if cycle:
            result = hier.resume_review(pkg, work_id=work_id, call_model=recorder,
                                        runtime_root_path=runtime, identity=IDENT, release_model=False)
        else:
            result = hier.review_experiment(pkg, work_id=work_id, call_model=recorder,
                                            runtime_root_path=runtime, identity=IDENT, release_model=False)
        seen += recorder.prompts
        if result.get("object") != "experiment_review_paused":
            return result, seen, cycle + 1
    return result, seen, cycles


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="v2733-pause-") as tmp:
        work = Path(tmp)

        # --- baseline: an uninterrupted run ------------------------------------------------------------------
        pkg, runtime = fresh(work, "base")
        baseline = hier.review_experiment(pkg, work_id="base", call_model=q.deterministic_stub(),
                                          runtime_root_path=runtime, identity=IDENT, release_model=False)
        require(baseline["status"] == "complete", "the_uninterrupted_baseline_completes")

        # --- 1. pause at each level ---------------------------------------------------------------------------
        levels = {
            "observation": lambda p, n: '"observations"' in p and n == 3,
            "after_observation": lambda p, n: '"obs_ids"' in p and n >= 1,
            "document_synthesis": lambda p, n: "document-level synthesis" in p,
            "between_groups": lambda p, n: "consolidation round" in p,
            "before_final": lambda p, n: "first half of your review" in p,
        }
        artifacts = {}
        for name, trigger in levels.items():
            pkg_l, rt_l = fresh(work, name)
            result, seen, cycles = run_to_completion(pkg_l, rt_l, name, trigger)
            artifacts[name] = result
            require(result.get("status") == "complete", f"a_review_paused_at_{name}_resumes_and_completes")
            require(cycles >= 2, f"the_run_really_paused_at_{name}")
            require(len(seen) == len(set(seen)), f"no_provider_call_is_repeated_after_resume:{name}")

        # --- 2. equivalence with the uninterrupted run --------------------------------------------------------
        for name, art in artifacts.items():
            require(len(art["grounded_observations"]) == len(baseline["grounded_observations"]),
                    f"the_same_number_of_observations_survives:{name}")
            require([o["obs_id"] for o in art["grounded_observations"]] ==
                    [o["obs_id"] for o in baseline["grounded_observations"]],
                    f"observation_ids_are_unchanged:{name}")
            require([o["statement"] for o in art["grounded_observations"]] ==
                    [o["statement"] for o in baseline["grounded_observations"]],
                    f"observation_content_is_unchanged:{name}")
            require(len({o["obs_id"] for o in art["grounded_observations"]}) ==
                    len(art["grounded_observations"]), f"no_observation_is_duplicated:{name}")
            require(art["coverage"]["required_coverage"] == baseline["coverage"]["required_coverage"],
                    f"coverage_matches_the_uninterrupted_run:{name}")
            require([s["cites"] for s in art["hierarchy"]["part_statements"]] ==
                    [s["cites"] for s in baseline["hierarchy"]["part_statements"]],
                    f"synthesis_inputs_are_unchanged:{name}")
            require([s["lineage"] for s in art["hierarchy"]["document_statements"]] ==
                    [s["lineage"] for s in baseline["hierarchy"]["document_statements"]],
                    f"lineage_is_mechanically_equivalent:{name}")
            require(art["hierarchy"]["final_inputs"] == baseline["hierarchy"]["final_inputs"],
                    f"the_final_inputs_are_unchanged:{name}")
            require(len(art["hierarchy"].get("uncaptured_registers", [])) ==
                    len(baseline["hierarchy"].get("uncaptured_registers", [])),
                    f"uncaptured_registers_survive_the_pause:{name}")
            require(art["mutation_guard"]["passed"], f"the_mutation_guard_passes_across_a_pause:{name}")

        # --- 3. multiple pause/resume cycles ------------------------------------------------------------------
        pkg_m, rt_m = fresh(work, "many")
        result, seen, cycles = run_to_completion(pkg_m, rt_m, "many",
                                                 lambda p, n: n % 2 == 1, cycles=120, every_cycle=True)
        require(result.get("status") == "complete", "a_review_paused_many_times_still_completes")
        require(cycles > 3, "the_run_really_paused_repeatedly")
        require(len(seen) == len(set(seen)), "no_provider_call_is_repeated_across_many_cycles")
        require([o["obs_id"] for o in result["grounded_observations"]] ==
                [o["obs_id"] for o in baseline["grounded_observations"]],
                "many_cycles_do_not_change_observation_ids")

        # --- 4. refusals -------------------------------------------------------------------------------------
        pkg_r, rt_r = fresh(work, "refuse")
        controls = controls_for(pkg_r, rt_r, "refuse")
        rec = Recorder(controls, "refuse", pause_at=lambda p, n: n == 2)
        paused = hier.review_experiment(pkg_r, work_id="refuse", call_model=rec, runtime_root_path=rt_r,
                                        identity=IDENT, release_model=False)
        require(paused.get("object") == "experiment_review_paused", "a_pause_returns_a_paused_record_not_an_artifact")
        require(paused.get("resumable") is True, "the_paused_record_says_it_is_resumable")
        require(not (rt_r / base.REVIEW_AREA / paused["review_id"] / "review.json").exists(),
                "a_paused_review_writes_no_review_artifact")

        # A pause request left standing would make the next resume pause again instead of refusing, so clear it
        # before every refusal case: what is under test is integrity, not the stop signal.
        pause.clear("refuse", controls)

        def refusal(fn) -> str:
            """Return the refusal reason, or a marker naming what happened instead."""
            try:
                fn()
            except pause.ResumeRefused as exc:
                return str(exc)
            except Exception as exc:  # noqa: BLE001 - any other failure is itself a finding
                return f"unexpected:{type(exc).__name__}:{exc}"[:120]
            return "no_refusal_at_all"

        # binding drift: the package changes while paused
        # Bytes, not text: write_text translates newlines on Windows, so "restoring" the file would change it and
        # every later case would fail on package digest instead of on what it is meant to test.
        doc = pkg_r / "corpus.txt"
        original = doc.read_bytes()
        doc.write_bytes(original + b"\ndrifted line\n")
        reason = refusal(lambda: hier.resume_review(pkg_r, work_id="refuse", call_model=q.deterministic_stub(),
                                                    runtime_root_path=rt_r, identity=IDENT))
        require(reason.startswith("binding_drift") or reason.startswith("unexpected:ReviewPackageError"),
                "package_drift_while_paused_refuses_resume")
        doc.write_bytes(original)

        # model/config drift
        drifted_identity = {**IDENT, "resolved_config_sha256": "1" * 64}
        pause.clear("refuse", controls)
        reason = refusal(lambda: hier.resume_review(pkg_r, work_id="refuse", call_model=q.deterministic_stub(),
                                                    runtime_root_path=rt_r, identity=drifted_identity))
        require(reason.startswith("binding_drift"), "model_configuration_drift_while_paused_refuses_resume")

        # checkpoint corruption
        cp = pause.checkpoint_path("refuse", controls)
        good = cp.read_text(encoding="utf-8")
        record = json.loads(good)
        record["state"]["grounded"] = []
        cp.write_text(json.dumps(record), encoding="utf-8")
        pause.clear("refuse", controls)
        reason = refusal(lambda: hier.resume_review(pkg_r, work_id="refuse", call_model=q.deterministic_stub(),
                                                    runtime_root_path=rt_r, identity=IDENT))
        require(reason == "checkpoint_digest_mismatch", "a_tampered_checkpoint_refuses_resume")
        cp.write_text("{not json", encoding="utf-8")
        pause.clear("refuse", controls)
        reason = refusal(lambda: hier.resume_review(pkg_r, work_id="refuse", call_model=q.deterministic_stub(),
                                                    runtime_root_path=rt_r, identity=IDENT))
        require(reason.startswith("checkpoint_unreadable"), "an_unreadable_checkpoint_refuses_resume")
        cp.write_text(good, encoding="utf-8")

        # missing checkpoint
        pause.clear("refuse", controls)
        reason = refusal(lambda: hier.resume_review(pkg_r, work_id="never-started",
                                                    call_model=q.deterministic_stub(),
                                                    runtime_root_path=rt_r, identity=IDENT))
        require(reason == "no_checkpoint_to_resume", "resuming_work_that_never_started_refuses")

        # --- 5. cancelled is not paused -----------------------------------------------------------------------
        pkg_c, rt_c = fresh(work, "cancel")
        controls_c = controls_for(pkg_c, rt_c, "cancel")
        rec_c = Recorder(controls_c, "cancel", cancel_at=lambda p, n: n == 2)
        cancelled = hier.review_experiment(pkg_c, work_id="cancel", call_model=rec_c, runtime_root_path=rt_c,
                                           identity=IDENT, release_model=False)
        require(cancelled.get("object") == "experiment_review_cancelled", "a_cancel_returns_a_cancelled_record")
        require(cancelled.get("resumable") is False, "a_cancelled_record_says_it_is_not_resumable")
        require(cancelled.get("status") == pause.CANCELLED and pause.CANCELLED != pause.PAUSED,
                "cancelled_is_a_different_state_from_paused")
        pause.clear("cancel", controls_c)
        reason = refusal(lambda: hier.resume_review(pkg_c, work_id="cancel", call_model=q.deterministic_stub(),
                                                    runtime_root_path=rt_c, identity=IDENT))
        require(reason == "work_already_terminal:cancelled", "a_cancelled_review_cannot_be_resumed")

        # --- 6. a finished review cannot be resumed ------------------------------------------------------------
        reason = refusal(lambda: hier.resume_review(pkg, work_id="base", call_model=q.deterministic_stub(),
                                                    runtime_root_path=runtime, identity=IDENT))
        require(reason in ("work_already_terminal:complete", "no_checkpoint_to_resume")
                or reason.startswith("unexpected:FileExistsError"),
                "a_completed_review_is_not_resumable")

        # --- 7. interruption around the checkpoint write -------------------------------------------------------
        cp_r = pause.checkpoint_path("refuse", controls)
        before_bytes = cp_r.read_bytes()
        require(pause.load_checkpoint("refuse", controls) is not None,
                "a_checkpoint_written_before_an_interruption_is_readable_afterwards")
        cp_r.unlink()
        require(pause.load_checkpoint("refuse", controls) is None,
                "an_interruption_before_any_checkpoint_write_leaves_nothing_to_resume_from")
        cp_r.write_bytes(before_bytes)
        record = pause.load_checkpoint("refuse", controls)
        require(record is not None and record["digest"] == pause.digest_of(
            {k: v for k, v in record.items() if k != "digest"}),
            "a_restored_checkpoint_still_verifies_its_own_seal")

        # --- 8. the control signal is cooperative, not an interrupt --------------------------------------------
        require(pause.pending("nobody", controls) == "", "no_request_means_keep_running")
        pause.request("probe", "pause", controls)
        require(pause.pending("probe", controls) == "pause", "a_pause_request_is_visible_to_the_worker")
        pause.request("probe", "resume", controls)
        require(pause.pending("probe", controls) == "", "a_resume_request_clears_the_stop_signal")
        pause.request("probe", "cancel", controls)
        require(pause.pending("probe", controls) == "cancel", "a_cancel_request_is_visible_and_distinct")
        bad = pause.control_path("probe", controls)
        bad.write_text("{corrupt", encoding="utf-8")
        require(pause.pending("probe", controls) == "pause",
                "an_unreadable_control_file_is_treated_as_pause_not_as_keep_running")

        # --- 9. nothing about grounding or acceptance moved ----------------------------------------------------
        require(base.CONTRACT_VERSION == "v2731.8", "the_baseline_reviewer_is_unchanged")
        require(hier.CONTRACT_VERSION == "v2733.0", "the_reviewer_carries_a_new_contract_version")
        require(hier.OBSERVE_GROUNDING_ATTEMPTS == 2, "the_retry_limit_is_unchanged")
        require(hier.MIN_SYNTHESISED_REPRESENTATION == 0.5, "the_representation_floor_is_unchanged")
        require(base.REQUIRED_ROLES == ("design", "corpus", "raw_outputs"), "required_roles_are_unchanged")

    failed = [name for name, ok in CHECKS if not ok]
    print(json.dumps({"suite": "v2733.3.0-pause-resume", "checks": len(CHECKS),
                      "passed": len(CHECKS) - len(failed), "failed": failed[:12]}, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
