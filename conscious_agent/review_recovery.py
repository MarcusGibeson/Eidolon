from __future__ import annotations

"""Governed recovery of the required units an incomplete review failed to observe.

A review that fails one required observation unit currently discards every valid unit it did complete. Attempt 3 of
the G-CORROB1-R2 independent review reached 139 of 140 parts over nine and three quarter hours and then failed closed
on ``observe:D13:63``. Failing closed was right. Throwing the other 139 away to try again was only ever an accident of
having no way to continue.

This is not a second pause/resume. Pause/resume continues *live* work from a sealed checkpoint inside the same
execution. Recovery starts from a review that has already terminated incomplete: it is a new, explicitly governed
operation that names its source, executes only the units that failed, and produces a **new derived artifact**. The
original is opened read-only and never written.

What recovery is not allowed to be is a retry that quietly lowers a bar. So it changes nothing about how a unit is
observed: same package, same documents, same prompts, same grounding and identifier rules, same limits, same model.
Every one of those is verified against what the source review recorded, and any difference in them refuses the
recovery outright rather than executing under altered conditions. If the missing unit still grounds nothing, recovery
fails closed exactly as the original did.

The one binding deliberately treated differently is the reviewer module's whole-file digest. It covers synthesis,
reporting and accounting as well as observation, so an unrelated repair - fixing a wrong retry total, say - would
otherwise make every earlier incomplete review permanently unrecoverable. A difference there never passes silently:
it is reported, it must be acknowledged by exact digest, and it is recorded in the lineage of the derived artifact.
Everything that actually determines how an observation is produced and validated must still match exactly.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Iterable, Mapping

import cooperative_pause as pause
import experiment_review as base
import experiment_review_hierarchical as hier

CONTRACT = "failed-unit-recovery.v1"
LINEAGE_NAME = "recovery_lineage.json"

# Bindings that decide how a missing unit is observed and validated. Every one must match the source review exactly:
# a difference means the unit would be produced under conditions the original review never ran under, which is a new
# review, not a recovery. There is no override for any of these.
EXECUTION_BINDINGS = (
    "package_manifest_sha256",     # the package as a whole
    "package_documents",           # every document, by digest
    "reviewer_contract",           # observation and synthesis semantics
    "baseline_contract",
    "baseline_module_sha256",      # chunking, grounding, identifier support, quote location - the frozen validator
    "prompt_templates_sha256",     # the exact observation prompt and retry preface
    "limits",                      # observation, quote and retry allowances
    "model",                       # model, provider, context size and resolved configuration
    "review_id_vocabulary",
)

# Reported, compared, and never silently ignored - see the module docstring.
ACKNOWLEDGEABLE = ("reviewer_module_sha256",)

RECOVERABLE_KINDS = ("required_part_not_reviewed",)


class RecoveryRefused(Exception):
    """Recovery may not proceed. Raised before anything is written or any provider call is made."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def review_area(root: str | Path) -> Path:
    return Path(root) / base.REVIEW_AREA


def load_source(review_id: str, root: str | Path) -> dict[str, Any]:
    """Read a finished review artifact. Opened read-only; recovery never writes into the source directory."""
    path = review_area(root) / str(review_id) / "review.json"
    if not path.is_file():
        raise RecoveryRefused(f"source_review_not_found:{review_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def source_digest(review_id: str, root: str | Path) -> str:
    return base._sha256_file(review_area(root) / str(review_id) / "review.json")


def missing_required_units(artifact: Mapping[str, Any]) -> list[str]:
    """The required units this review failed to observe, and nothing else."""
    return [str(m["stage"]) for m in (artifact.get("coverage", {}).get("missing") or [])
            if str(m.get("kind")) in RECOVERABLE_KINDS and m.get("stage")]


def unrecoverable_gaps(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Gaps no amount of re-execution can fill, such as a required role the package does not contain at all."""
    return [dict(m) for m in (artifact.get("coverage", {}).get("missing") or [])
            if str(m.get("kind")) not in RECOVERABLE_KINDS]


# --- compatibility ---------------------------------------------------------------------------------------------
def recorded_bindings(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """What the source review says it ran under, read from its own provenance."""
    prov = artifact.get("provenance") or {}
    cap = prov.get("capability") or {}
    return {
        "package_manifest_sha256": str(prov.get("manifest_sha256") or ""),
        "package_documents": {str(d["path"]): str(d["sha256"]) for d in (prov.get("documents") or [])},
        "reviewer_contract": str(cap.get("contract_version") or ""),
        "baseline_contract": str(cap.get("baseline_contract") or ""),
        "baseline_module_sha256": str(cap.get("baseline_module_sha256") or ""),
        "reviewer_module_sha256": str(cap.get("module_sha256") or ""),
        "prompt_templates_sha256": dict(prov.get("prompt_templates_sha256") or {}),
        "limits": dict(prov.get("limits") or {}),
        "model": {k: (prov.get("model") or {}).get(k)
                  for k in ("model", "provider", "context_size", "resolved_config_sha256")},
        "review_id_vocabulary": list(prov.get("review_id_vocabulary") or []),
    }


def current_bindings(package: Mapping[str, Any], ident: Mapping[str, Any]) -> dict[str, Any]:
    """What this environment would run under right now, built from the same sources the reviewer uses."""
    context_size = ident.get("context_size") if isinstance(ident.get("context_size"), int) else None
    return {
        "package_manifest_sha256": str(package["manifest_sha256"]),
        "package_documents": {str(d["path"]): str(d["sha256"]) for d in package["documents"]},
        "reviewer_contract": hier.CONTRACT_VERSION,
        "baseline_contract": hier.BASELINE_CONTRACT,
        "baseline_module_sha256": base._sha256_file(Path(base.__file__).resolve()),
        "reviewer_module_sha256": base._sha256_file(Path(hier.__file__).resolve()),
        "prompt_templates_sha256": hier.template_digests(),
        "limits": hier.registered_limits() | {"context_size": context_size},
        "model": {k: ident.get(k) for k in ("model", "provider", "context_size", "resolved_config_sha256")},
        "review_id_vocabulary": ["O", "PS", "DS", "GS", "U"],
    }


def compatibility(artifact: Mapping[str, Any], package: Mapping[str, Any],
                  ident: Mapping[str, Any]) -> dict[str, Any]:
    """Compare the source review's recorded conditions with this environment's, field by field.

    Reports every difference it finds, not just the first, so an operator sees the whole picture in one read.
    """
    was, now = recorded_bindings(artifact), current_bindings(package, ident)
    differing = [k for k in EXECUTION_BINDINGS if was.get(k) != now.get(k)]
    acknowledgeable = [k for k in ACKNOWLEDGEABLE if was.get(k) != now.get(k)]
    detail = {k: {"source": was.get(k), "current": now.get(k)} for k in differing + acknowledgeable}
    verdict = "incompatible" if differing else ("execution_equivalent" if acknowledgeable else "identical")
    return {"contract": CONTRACT, "verdict": verdict, "execution_bindings_differing": differing,
            "acknowledgeable_differing": acknowledgeable, "detail": detail,
            "verified": [k for k in EXECUTION_BINDINGS if k not in differing]}


# --- planning --------------------------------------------------------------------------------------------------
def work_id_for(source_review_id: str) -> str:
    """Deterministic, so a second recovery of the same review finds the first rather than forking a new one."""
    return f"recovery_{source_review_id}"


def live_checkpoint(job: Mapping[str, Any], private: str | Path) -> bool:
    """Whether this recovery already has checkpointed work, asked of the checkpoint rather than the job's status.

    A resumed job is marked running before its worker starts - that is what stops a second press starting a second
    worker - so the status cannot tell a first run from a continuation. The checkpoint can.
    """
    source = str((job.get("recovery") or {}).get("source_review_id") or "")
    manifest = str(job.get("manifest_sha256") or "")
    if not source or not manifest:
        return False
    work = work_id_for(source)
    try:
        record = pause.load_checkpoint(work, hier.control_root_for(private, manifest, work))
    except Exception:
        return False
    return bool(record) and str(record.get("status")) in (pause.RUNNING, pause.PAUSE_REQUESTED, pause.PAUSED)


def plan(source_review_id: str, *, root: str | Path, package_dir: str | Path | None = None,
         identity: Mapping[str, Any] | None = None, units: Iterable[str] | None = None) -> dict[str, Any]:
    """Everything recovery would do, decided before anything is written or called.

    Raises :class:`RecoveryRefused` for any condition that makes recovery inadmissible.
    """
    artifact = load_source(source_review_id, root)
    if str(artifact.get("status")) == "complete":
        raise RecoveryRefused("source_review_is_already_complete")
    blocked = unrecoverable_gaps(artifact)
    if blocked:
        raise RecoveryRefused("source_has_gaps_execution_cannot_fill:" +
                              ",".join(sorted({str(m.get("kind")) for m in blocked})))
    failed = missing_required_units(artifact)
    if not failed:
        raise RecoveryRefused("source_review_has_no_recoverable_missing_units")

    wanted = sorted(set(units)) if units is not None else sorted(failed)
    if not wanted:
        raise RecoveryRefused("no_units_named")
    # Recovering a unit that already succeeded would re-observe evidence the source review already grounded, and
    # replace it with a fresh answer. Only what failed may run again.
    reviewed = {str(p["stage"]) for p in (artifact.get("coverage", {}).get("parts") or []) if p.get("reviewed")}
    already = sorted(u for u in wanted if u in reviewed)
    if already:
        raise RecoveryRefused("units_already_completed:" + ",".join(already[:8]))
    unknown = sorted(u for u in wanted if u not in set(failed))
    if unknown:
        raise RecoveryRefused("units_not_missing_in_source:" + ",".join(unknown[:8]))

    prov = artifact.get("provenance") or {}
    package = base.load_package(Path(package_dir) if package_dir is not None else Path(str(prov.get("package_dir"))))
    ident = dict(identity) if identity is not None else base.model_identity()
    compat = compatibility(artifact, package, ident)

    work_id = work_id_for(str(source_review_id))
    derived_id = hier.work_review_id(str(package["manifest_sha256"]), work_id)
    observations = list(artifact.get("grounded_observations") or [])
    return {
        "contract": CONTRACT, "source_review_id": str(source_review_id),
        "source_status": str(artifact.get("status")), "source_digest": source_digest(source_review_id, root),
        "package_id": str(package["experiment_id"]), "package_dir": str(package["dir"]),
        "work_id": work_id, "derived_review_id": derived_id,
        "derived_review_dir": str(review_area(root) / derived_id),
        "units_to_execute": wanted, "unit_count": len(wanted),
        "expected_provider_calls": {"minimum": len(wanted),
                                    "maximum": len(wanted) * int(hier.OBSERVE_GROUNDING_ATTEMPTS),
                                    "note": "observation units only; synthesis calls follow if coverage completes"},
        "preserved_units": len(artifact.get("coverage", {}).get("parts") or []) - len(wanted),
        "preserved_observations": len(observations),
        "recovered_observation_ids_begin_after": len(observations),
        "required_parts": int(artifact.get("coverage", {}).get("required_parts") or 0),
        "compatibility": compat,
    }


# --- derived state ---------------------------------------------------------------------------------------------
def derived_state(artifact: Mapping[str, Any], units: Iterable[str], *, review_id: str, started: str) -> dict[str, Any]:
    """The source review's completed work, expressed as the state a resume would have restored.

    Observations, rejections, questions and the provider ledger are carried across exactly as the source recorded
    them - copied, never recomputed, so no identifier is ever reissued and no lineage drifts. Only the failed units'
    coverage rows are withheld, which is what makes the reviewer execute them again and nothing else.

    Synthesis state is deliberately empty. The source never reached synthesis, and even if it had, synthesis over a
    different observation set must be redone rather than reused.
    """
    dropped = set(units)
    coverage = [dict(p) for p in (artifact.get("coverage", {}).get("parts") or []) if str(p["stage"]) not in dropped]
    return {
        "review_id": review_id, "started": started, "sequence": 0,
        "ledger": [dict(x) for x in (artifact.get("ledger") or [])],
        "grounded": [dict(o) for o in (artifact.get("grounded_observations") or [])],
        "rejected": [dict(o) for o in (artifact.get("rejected_observations") or [])],
        "questions": [dict(q) for q in (artifact.get("open_questions") or [])],
        "parts_coverage": coverage,
        "items": {}, "absent_roles": list(artifact.get("coverage", {}).get("absent_required_roles") or []),
        "missing": [],
    }


def completed_units_of(artifact: Mapping[str, Any], units: Iterable[str]) -> list[str]:
    """Observation units the derived run must not execute again - every part the source reviewed."""
    dropped = set(units)
    return [str(p["stage"]) for p in (artifact.get("coverage", {}).get("parts") or [])
            if str(p["stage"]) not in dropped]


# --- execution -------------------------------------------------------------------------------------------------
def recover(source_review_id: str, *, root: str | Path, package_dir: str | Path | None = None,
            identity: Mapping[str, Any] | None = None, units: Iterable[str] | None = None,
            acknowledge_module_change: str = "", call_model: Callable[..., Any] | None = None,
            source_root: str | Path | None = None, protected_roots: Iterable[str | Path] = (),
            on_state: Callable[[str, Mapping[str, Any]], None] | None = None,
            confirmed: bool = False) -> dict[str, Any]:
    """Execute only the failed units of a terminated incomplete review, into a new derived artifact.

    Refuses before touching anything if the plan is inadmissible, if execution conditions differ, or if an
    acknowledgeable difference has not been acknowledged by its exact digest.
    """
    if not confirmed:
        raise RecoveryRefused("recovery_requires_explicit_confirmation")
    proposal = plan(source_review_id, root=root, package_dir=package_dir, identity=identity, units=units)
    compat = proposal["compatibility"]
    if compat["verdict"] == "incompatible":
        raise RecoveryRefused("execution_conditions_differ:" + ",".join(compat["execution_bindings_differing"]))
    if compat["verdict"] == "execution_equivalent":
        expected = str((compat["detail"].get("reviewer_module_sha256") or {}).get("current") or "")
        if acknowledge_module_change.strip() != expected:
            raise RecoveryRefused("reviewer_module_change_not_acknowledged:" + expected)

    artifact = load_source(source_review_id, root)
    prov = artifact.get("provenance") or {}
    package = base.load_package(Path(package_dir) if package_dir is not None else Path(str(prov.get("package_dir"))))
    ident = dict(identity) if identity is not None else base.model_identity()

    derived_id, work_id = str(proposal["derived_review_id"]), str(proposal["work_id"])
    src = Path(source_root).expanduser().resolve() if source_root is not None else None
    out_dir = review_area(root) / derived_id
    if (out_dir / "review.json").is_file():
        # A recovery that reached a terminal artifact is finished, whatever that artifact concluded. Continuing it
        # would need a separately authorized recovery operation, not a second pass at this one.
        raise RecoveryRefused("derived_review_already_exists:" + derived_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    # A recovery that was paused, or whose worker died, already has live checkpointed work. Re-sealing a fresh
    # checkpoint over it would throw that away, so the existing one is continued instead - same work id, same derived
    # review, and the reviewer verifies the seal and every binding exactly as it does for any resume.
    existing = None
    try:
        existing = pause.load_checkpoint(work_id, out_dir)
    except pause.ResumeRefused:
        existing = None
    if existing and str(existing.get("status")) in (pause.RUNNING, pause.PAUSE_REQUESTED, pause.PAUSED):
        pause.clear(work_id, out_dir)
        result = hier.review_experiment(
            package["dir"], work_id=work_id, resume=True, runtime_root_path=root, source_root=src,
            protected_roots=protected_roots, identity=ident, call_model=call_model, on_state=on_state)
        return _summary(proposal, result, out_dir, str(source_review_id), derived_id, compat, continued=True)

    started = _now()
    lineage = {
        "contract": CONTRACT, "recovered_at": started,
        "source_review_id": str(source_review_id), "source_review_digest": proposal["source_digest"],
        "source_status": proposal["source_status"], "source_started": str(prov.get("started") or ""),
        "recovered_units": list(proposal["units_to_execute"]),
        "preserved_observation_count": int(proposal["preserved_observations"]),
        "observations_above_this_index_are_recovered": int(proposal["recovered_observation_ids_begin_after"]),
        "preserved_units": int(proposal["preserved_units"]),
        "compatibility": compat,
        "acknowledged_reviewer_module_change": acknowledge_module_change.strip() or None,
    }

    # The checkpoint is sealed here, inside the derived review's own directory - the one path the mutation guard
    # excludes - and the reviewer then verifies it exactly as it verifies a paused run's. Recovery gets no private
    # entry point into the reviewer and no relaxed verification.
    bindings = hier.execution_bindings(package, ident,
                                       source_tree=base._git_state(src) if src is not None else None)
    checkpointer = pause.Checkpointer(work_id, out_dir, bindings=bindings)
    checkpointer.write(position={"level": "observe", "recovery": True},
                       completed_units=completed_units_of(artifact, proposal["units_to_execute"]),
                       next_unit=proposal["units_to_execute"][0],
                       state=derived_state(artifact, proposal["units_to_execute"],
                                           review_id=derived_id, started=started),
                       status=pause.RUNNING)
    (out_dir / LINEAGE_NAME).write_text(json.dumps(lineage, indent=1, ensure_ascii=False), encoding="utf-8")

    result = hier.review_experiment(
        package["dir"], work_id=work_id, resume=True, runtime_root_path=root, source_root=src,
        protected_roots=protected_roots, identity=ident, call_model=call_model, on_state=on_state,
        continuation_lineage=lineage)
    return _summary(proposal, result, out_dir, str(source_review_id), derived_id, compat, continued=False)


RECOVERY_KIND = "independent_experiment_review_recovery"
JOB_RUNNER = Path(__file__).resolve().parents[1] / "tools" / "run_recovery_job.py"


def start_recovery(source_review_id: str, *, confirmed: bool, root: str | Path,
                   acknowledge_module_change: str = "", units: Iterable[str] | None = None,
                   operator_note: str = "", identity: Mapping[str, Any] | None = None,
                   spawn: Callable[[list[str], Path, dict[str, str]], int] | None = None) -> dict[str, Any]:
    """Start one governed recovery as an ordinary research job, so it has an Activity and an operator control.

    Everything admissibility and compatibility depends on is settled here, before a job record exists: a refusal
    leaves nothing behind to resume, restart or explain away. The worker then performs the same :func:`recover`
    operation this module already defines - the job layer adds visibility and an operator control, never authority.
    """
    import conversational_experiment_review as adapter
    import experiment_review as base_mod
    import run_review_job as runner

    if not confirmed:
        raise RecoveryRefused("recovery_requires_explicit_confirmation")
    if adapter.active_job(root) is not None:
        raise RecoveryRefused("a_research_job_is_already_running")

    ident = dict(identity) if identity is not None else base_mod.model_identity()
    proposal = plan(source_review_id, root=root, identity=ident, units=units)
    compat = proposal["compatibility"]
    if compat["verdict"] == "incompatible":
        raise RecoveryRefused("execution_conditions_differ:" + ",".join(compat["execution_bindings_differing"]))
    if compat["verdict"] == "execution_equivalent":
        expected = str((compat["detail"].get("reviewer_module_sha256") or {}).get("current") or "")
        if acknowledge_module_change.strip() != expected:
            raise RecoveryRefused("reviewer_module_change_not_acknowledged:" + expected)
    if (review_area(root) / str(proposal["derived_review_id"]) / "review.json").is_file():
        raise RecoveryRefused("derived_review_already_exists:" + str(proposal["derived_review_id"]))

    job_id = "job_" + hashlib.sha256(f"recovery|{source_review_id}|{_now()}".encode()).hexdigest()[:16]
    private = runner.private_runtime_root(job_id, root)
    adapter.job_area(root).mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, "-B", str(JOB_RUNNER), str(adapter._job_path(job_id, root))]
    record = {
        "object": "experiment_review_job", "contract_version": adapter.CONTRACT_VERSION, "job_id": job_id,
        "task_id": "", "kind": RECOVERY_KIND, "mode": "failed_unit_recovery",
        "package_id": str(proposal["package_id"]), "package_dir": str(proposal["package_dir"]),
        "manifest_sha256": str((load_source(source_review_id, root).get("provenance") or {}).get("manifest_sha256") or ""),
        "runtime_root": str(adapter._root(root)), "private_runtime_root": str(private),
        "status": "starting", "started": _now(), "started_monotonic_epoch": time.time(), "argv": argv, "pid": 0,
        "chosen_by": "operator", "authority": "read_only_non_authoritative",
        "operator_note": str(operator_note)[:300], "reviewer_contract": hier.CONTRACT_VERSION,
        "recovery": {
            "contract": CONTRACT, "source_review_id": str(source_review_id),
            "source_review_digest": str(proposal["source_digest"]),
            "derived_review_id": str(proposal["derived_review_id"]),
            "units_planned": list(proposal["units_to_execute"]),
            "inherited_units": int(proposal["preserved_units"]),
            "inherited_grounded_observations": int(proposal["preserved_observations"]),
            "required_parts": int(proposal["required_parts"]),
            "compatibility_verdict": compat["verdict"],
            "acknowledged_reviewer_module_change": acknowledge_module_change.strip() or None,
        },
    }
    adapter.save_job(record, root)
    launcher = spawn or adapter.SPAWN
    pid = int(launcher(argv, JOB_RUNNER.parents[1],
                       {**os.environ, "EIDOLON_DATA_DIR": str(adapter._root(root)), "PYTHONIOENCODING": "utf-8"}))
    return adapter.save_job({**record, "status": "running", "pid": pid}, root)


def _summary(proposal: Mapping[str, Any], result: Mapping[str, Any], out_dir: Path, source_review_id: str,
             derived_id: str, compat: Mapping[str, Any], *, continued: bool) -> dict[str, Any]:
    """One content-minimized record of what a recovery did. A pause is reported as a pause, not as a result."""
    status = str(result.get("status") or "")
    summary = {"contract": CONTRACT, "ok": status in ("complete", "incomplete", "paused"),
               "source_review_id": source_review_id, "derived_review_id": derived_id, "status": status,
               "units_executed": list(proposal["units_to_execute"]), "continued_existing_work": bool(continued),
               "lineage_path": str(out_dir / LINEAGE_NAME), "compatibility": compat["verdict"],
               "preserved_observations": int(proposal["preserved_observations"])}
    if status in ("paused", "cancelled"):
        # No artifact exists yet; the checkpoint holds the work and says where it stopped.
        summary["completed_units"] = result.get("completed_units")
        summary["checkpoint_digest"] = result.get("checkpoint_digest")
        summary["resumable"] = bool(result.get("resumable"))
        return summary
    coverage = result.get("coverage") or {}
    summary["coverage"] = {"required_parts": coverage.get("required_parts"),
                           "reviewed_required_parts": coverage.get("reviewed_required_parts"),
                           "required_coverage": coverage.get("required_coverage")}
    summary["total_observations"] = len(result.get("grounded_observations") or [])
    return summary
