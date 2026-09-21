from __future__ import annotations

"""Conversational selection and invocation of the governed read-only experiment review (spec 2.25).

Marcus asks which experiments can be reviewed, asks for one, confirms, and asks for status. This module only selects an
already-installed package and invokes the already-authorized operation; it adds no authority and no second reviewer.

- The reviewer is the frozen, qualified ``experiment_review`` capability (v2731.8). Nothing here re-implements it.
- Only packages installed under ``<runtime>/research_packages/`` are eligible, and each must load under the reviewer's
  own rules (manifest, roles, containment, digests). Names from chat are matched against that listing; a path, a glob or
  an unknown name is refused.
- Starting a review needs an explicit operator confirmation: the proposal is saved, and the review begins only when the
  operator executes that one action.
- The review runs as a bounded background job in its own process, so disconnecting the client does not end it. Exactly
  one local-model review job may run at a time; deterministic work (listing, status, other queue kinds) is never blocked.
- Listing and status are read-only and never carry the review's conclusions: a job record and a status reply hold ids,
  digests, counts and coverage only, so conversation memory keeps a minimal operation receipt.
- Reviews stay read-only and non-authoritative. Nothing here changes source, gold, policy, beliefs, memory, configuration
  or releases, nothing schedules, and no shell or model endpoint is reachable from chat.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable, Mapping

from experiment_review import REVIEW_AREA, ReviewPackageError, chunks, load_package, runtime_root
from json_storage import write_text_atomic
import local_research_queue as lrq

CONTRACT_VERSION = "v2731.11"

# The reviewer architecture new reviews run on. v2731.8 stays importable and runnable as the frozen historical
# baseline; jobs already queued keep whatever contract their own record names, so changing this never rewrites a
# review that has already been started or completed.
ACTIVE_REVIEWER_CONTRACT = "v2733.1"
PACKAGE_AREA = "research_packages"
JOB_AREA = "research_jobs"
ACTIVE_JOB_FILE = "active_job.json"
REVIEW_KIND = "independent_experiment_review"
JOB_RUNNER = Path(__file__).resolve().parents[1] / "tools" / "run_review_job.py"
MAX_JOB_SECONDS = 6 * 3600
MAX_CONVERSATION_TARGETS = 12
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 _-]{1,60}$")
FUNCTIONS = ("experiment_review_list", "experiment_review_start", "experiment_review_status")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _root(root: str | Path | None = None) -> Path:
    return runtime_root(root)


def package_area(root: str | Path | None = None) -> Path:
    return _root(root) / PACKAGE_AREA


def job_area(root: str | Path | None = None) -> Path:
    return _root(root) / JOB_AREA


# --- packages ------------------------------------------------------------------------------------------------------------
def eligible_packages(root: str | Path | None = None) -> list[dict[str, Any]]:
    """Every installed package, each verified by the reviewer's own loader. Nothing outside the package area is read."""
    area = package_area(root)
    rows: list[dict[str, Any]] = []
    for directory in sorted(p for p in area.glob("*") if p.is_dir()) if area.is_dir() else []:
        try:
            package = load_package(directory)
        except ReviewPackageError as exc:
            rows.append({"package_id": directory.name, "eligible": False, "reason": str(exc)})
            continue
        except Exception as exc:  # unreadable or malformed manifest: reported, never raised into the conversation
            rows.append({"package_id": directory.name, "eligible": False, "reason": f"unreadable:{type(exc).__name__}"})
            continue
        aliases = package["manifest"].get("selector_aliases", [])
        if (not isinstance(aliases, list) or any(not isinstance(alias, str) or not NAME.fullmatch(alias) for alias in aliases)
                or len(set(alias.casefold() for alias in aliases)) != len(aliases)):
            rows.append({"package_id": package["experiment_id"] or directory.name, "eligible": False,
                         "reason": "package_selector_aliases_invalid"})
            continue
        rows.append({"package_id": package["experiment_id"] or directory.name, "title": package["title"], "directory": directory.name,
                     "selector_aliases": list(aliases),
                     "documents": len(package["documents"]), "parts": sum(len(chunks(d["text"])) for d in package["documents"]),
                     "characters": sum(len(d["text"]) for d in package["documents"]), "manifest_sha256": package["manifest_sha256"],
                     "eligible": True, "reviews": reviews_of(package["manifest_sha256"], root)})
    return rows


def eligible_target_ids(root: str | Path | None = None) -> tuple[str, ...]:
    """The ids of the installed packages a review can name: bounded, sorted, and content free.

    Never a path, never a title and never a review's conclusions. An unreadable package area answers with nothing
    rather than raising into the conversation.
    """
    try:
        rows = eligible_packages(root)
    except Exception:
        return ()
    names = {name for row in rows if row.get("eligible")
             for name in (str(row.get("package_id") or ""), *[str(alias) for alias in row.get("selector_aliases", [])])}
    return tuple(sorted(name for name in names if NAME.match(name)))[:MAX_CONVERSATION_TARGETS]


def reviews_of(manifest_sha256: str, root: str | Path | None = None) -> list[dict[str, Any]]:
    """Existing reviews of one package: ids and status only, never their content."""
    area = _root(root) / REVIEW_AREA
    out = []
    for directory in sorted(p for p in area.glob("*") if p.is_dir()) if area.is_dir() else []:
        artifact = directory / "review.json"
        if not artifact.is_file():
            continue
        try:
            data = json.loads(artifact.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("provenance", {}).get("manifest_sha256") == manifest_sha256:
            out.append({"review_id": data.get("review_id"), "status": data.get("status"), "finished": data.get("provenance", {}).get("finished")})
    return out


def find_package(name: str, root: str | Path | None = None) -> dict[str, Any] | None:
    """Resolve an operator-typed name against the installed listing only. Paths and globs never resolve."""
    value = " ".join(str(name or "").split())
    if not NAME.fullmatch(value):
        return None
    lowered = value.lower()
    rows = [r for r in eligible_packages(root) if r.get("eligible")]
    exact = [row for row in rows if lowered in (
        str(row["package_id"]).lower(), str(row["directory"]).lower(),
        *[str(alias).lower() for alias in row.get("selector_aliases", [])],
    )]
    if len(exact) == 1:
        return exact[0]
    if exact:
        return None
    matches = [r for r in rows if str(r["package_id"]).lower().startswith(lowered) or str(r["title"]).lower().startswith(lowered)]
    return matches[0] if len(matches) == 1 else None


# --- jobs ----------------------------------------------------------------------------------------------------------------
def _process_alive(pid: int) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return exit_code.value == 259  # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    return True


def _job_path(job_id: str, root: str | Path | None = None) -> Path:
    return job_area(root) / f"{job_id}.json"


def _read(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_job(job: Mapping[str, Any], root: str | Path | None = None) -> dict[str, Any]:
    record = dict(job)
    record["updated"] = _now()
    write_text_atomic(_job_path(record["job_id"], root), json.dumps(record, indent=1, ensure_ascii=False))
    active = job_area(root) / ACTIVE_JOB_FILE
    if record["status"] == "running":
        write_text_atomic(active, json.dumps({"job_id": record["job_id"], "started": record["started"]}, indent=1))
    elif _read(active) and _read(active).get("job_id") == record["job_id"]:
        write_text_atomic(active, json.dumps({}, indent=1))
    return record


def _refresh(job: dict[str, Any], root: str | Path | None, alive: Callable[[int], bool]) -> dict[str, Any]:
    """A running record whose process is gone, or which ran past the bound, becomes a recorded failure, never a stuck job."""
    if job.get("status") != "running":
        return job
    started = job.get("started_monotonic_epoch") or 0
    too_long = bool(started) and (time.time() - started) > MAX_JOB_SECONDS
    if too_long or not alive(int(job.get("pid") or 0)):
        job = {**job, "status": "failed", "failure": "job_exceeded_maximum_duration" if too_long else "job_process_ended_without_result",
               "finished": _now()}
        return save_job(job, root)
    return job


def active_job(root: str | Path | None = None, *, alive: Callable[[int], bool] | None = None) -> dict[str, Any] | None:
    alive = alive or ALIVE
    pointer = _read(job_area(root) / ACTIVE_JOB_FILE) or {}
    if not pointer.get("job_id"):
        return None
    job = _read(_job_path(pointer["job_id"], root))
    if not job:
        return None
    job = _refresh(job, root, alive)
    return job if job.get("status") == "running" else None


def latest_job(root: str | Path | None = None) -> dict[str, Any] | None:
    """The running job if there is one, else the most recently started. Ordering uses the start instant, never a
    second-resolution timestamp, so two jobs started in the same second cannot swap places."""
    area = job_area(root)
    jobs = [j for j in (_read(p) for p in sorted(area.glob("*.json")) if p.name != ACTIVE_JOB_FILE) if j]
    if not jobs:
        return None
    running = [j for j in jobs if j.get("status") == "running"]
    return max(running or jobs, key=lambda j: (float(j.get("started_monotonic_epoch") or 0.0), str(j.get("started") or "")))


def start_review(package_id: str, *, confirmed: bool, root: str | Path | None = None, operator_note: str = "",
                 spawn: Callable[[list[str], Path, dict[str, str]], int] | None = None,
                 alive: Callable[[int], bool] | None = None,
                 reviewer_contract: str = "", expected_manifest_sha256: str = "") -> dict[str, Any]:
    """Queue and start one review of one installed package. The operator's confirmation is required; one job at a time."""
    if not confirmed:
        raise PermissionError("operator_confirmation_required")
    reviewer_contract = str(reviewer_contract or ACTIVE_REVIEWER_CONTRACT)
    package = find_package(package_id, root)
    if package is None:
        raise LookupError("package_not_eligible")
    expected_manifest = str(expected_manifest_sha256 or "").lower()
    if expected_manifest and not hmac.compare_digest(expected_manifest, str(package.get("manifest_sha256") or "").lower()):
        raise LookupError("package_manifest_drift")
    if active_job(root, alive=alive) is not None:
        raise RuntimeError("review_job_already_running")
    target = str(package_area(root) / package["directory"])
    task = lrq.add_task(REVIEW_KIND, target, operator_note=str(operator_note)[:300], root=root)
    job_id = "job_" + hashlib.sha256(f"{task['task_id']}|{_now()}".encode()).hexdigest()[:16]
    job_area(root).mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, "-B", str(JOB_RUNNER), str(_job_path(job_id, root))]
    record = {"object": "experiment_review_job", "contract_version": CONTRACT_VERSION, "job_id": job_id, "task_id": task["task_id"],
              "kind": REVIEW_KIND, "package_id": package["package_id"], "package_directory": package["directory"],
              "manifest_sha256": package["manifest_sha256"], "package_dir": target, "runtime_root": str(_root(root)),
              "status": "starting", "started": _now(), "started_monotonic_epoch": time.time(), "argv": argv, "pid": 0,
              "chosen_by": "operator", "authority": "read_only_non_authoritative", "operator_note": str(operator_note)[:300],
              "reviewer_contract": reviewer_contract}
    save_job(record, root)
    launcher = spawn or SPAWN
    pid = int(launcher(argv, JOB_RUNNER.parents[1], {**os.environ, "EIDOLON_DATA_DIR": str(_root(root)), "PYTHONIOENCODING": "utf-8"}))
    return save_job({**record, "status": "running", "pid": pid}, root)


def _spawn_detached(argv: list[str], cwd: Path, env: dict[str, str]) -> int:
    """One fixed argument vector in its own process group, so the review survives the client disconnecting."""
    flags = {}
    if os.name == "nt":
        flags["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    else:
        flags["start_new_session"] = True
    process = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, close_fds=True, **flags)
    return process.pid


SPAWN: Callable[[list[str], Path, dict[str, str]], int] = _spawn_detached  # the launcher; tests replace it, chat never chooses it
ALIVE: Callable[[int], bool] = _process_alive  # how a running job's process is checked; tests replace it, chat never chooses it


def job_status(job_id: str = "latest", root: str | Path | None = None, *, alive: Callable[[int], bool] | None = None) -> dict[str, Any] | None:
    """Status, counts and coverage of one job. It never returns any statement the review made."""
    alive = alive or ALIVE
    job = latest_job(root) if job_id in ("", "latest") else _read(_job_path(job_id, root))
    if not job:
        return None
    job = _refresh(dict(job), root, alive)
    out = {"job_id": job["job_id"], "task_id": job["task_id"], "package_id": job["package_id"], "manifest_sha256": job["manifest_sha256"],
           "status": job["status"], "started": job.get("started"), "finished": job.get("finished"), "review_id": job.get("review_id", ""),
           "review_status": job.get("review_status", ""), "coverage": job.get("coverage", {}), "checks": job.get("checks", {}),
           "failure": job.get("failure", ""), "location": job.get("location", ""),
           "reviewer_contract": job.get("reviewer_contract", ""), "reviewer": job.get("reviewer", {})}
    out["message"] = _status_message(out)
    return out


def _status_message(status: Mapping[str, Any]) -> str:
    package, state = status["package_id"], status["status"]
    if state == "running":
        return f"The review of {package} is running (job {status['job_id']}, started {status['started']})."
    if state == "failed":
        return f"The review of {package} failed: {status.get('failure') or 'see the job record'} (job {status['job_id']})."
    coverage = status.get("coverage") or {}
    parts = coverage.get("required_coverage")
    reviewer = status.get("reviewer") or {}
    # Name the architecture that produced the artifact, so a hierarchical review is never mistaken for a flat one.
    which = str(reviewer.get("contract_version") or status.get("reviewer_contract") or "")
    return (f"The review of {package} finished as {status.get('review_status') or 'unknown'} (review {status.get('review_id')}, job {status['job_id']})."
            + (f" Package coverage {parts:.0%}; {coverage.get('grounded_observations', 0)} grounded observations." if parts is not None else "")
            + (f" Produced by reviewer {which}"
               + (f" ({reviewer['architecture']})." if reviewer.get("architecture") else ".") if which else "")
            + " It is a non-authoritative research artifact; read it before drawing conclusions.")


def receipt(job: Mapping[str, Any]) -> dict[str, Any]:
    """The minimal operation receipt that may enter conversation memory: ids, digests and status only."""
    # Deliberately unchanged by the v2732.0 integration. Reviewer identity belongs in the job record, the status
    # output and the artifact provenance; the receipt is the minimal thing conversation memory may keep, and adding
    # fields to it widens what every review action writes into memory forever.
    return {"job_id": job.get("job_id"), "task_id": job.get("task_id"), "package_id": job.get("package_id"),
            "manifest_sha256": job.get("manifest_sha256"), "status": job.get("status"), "review_id": job.get("review_id", ""),
            "authority": "read_only_non_authoritative"}


# --- what the conversation calls -----------------------------------------------------------------------------------------
def list_message(root: str | Path | None = None) -> str:
    rows = eligible_packages(root)
    if not rows:
        return (f"No experiment packages are installed. An operator installs a built package under {PACKAGE_AREA}/ before I can review it; "
                "I do not build packages or choose experiments.")
    lines = []
    for row in rows:
        if not row.get("eligible"):
            lines.append(f"- {row['package_id']}: not eligible ({row['reason']})")
            continue
        seen = ", ".join(f"{r['review_id']} ({r['status']})" for r in row["reviews"]) or "none yet"
        lines.append(f"- {row['package_id']}: {row['title']} — {row['documents']} documents, {row['parts']} parts; reviews: {seen}")
    return ("I can independently review these installed experiment packages, one at a time and read-only:\n" + "\n".join(lines) +
            "\nAsk me to review one by name; I will propose it and start only after you confirm.")


def propose_message(name: str, root: str | Path | None = None) -> tuple[dict[str, Any] | None, str]:
    package = find_package(name, root)
    if package is None:
        rows = [r["package_id"] for r in eligible_packages(root) if r.get("eligible")]
        return None, (f"I have no installed package called '{name}'. Eligible packages: " + (", ".join(rows) if rows else "none") +
                      ". I only review packages an operator has installed; I cannot choose or build one.")
    running = active_job(root)
    if running is not None:
        return None, (f"A review is already running (job {running['job_id']}, package {running['package_id']}). Only one local-model review runs "
                      "at a time; ask for its status, or start this one after it finishes.")
    return package, (f"I can review {package['package_id']} ({package['title']}): {package['documents']} documents, {package['parts']} parts, "
                     f"manifest {package['manifest_sha256'][:16]}. It runs as a background job on the local model, roughly {package['parts'] * 2 + 12} "
                     "calls, and writes one non-authoritative read-only artifact. Nothing else changes. Confirm to start it.")


def execute_conversational_review_action(function_name: str, args: Mapping[str, Any], *, dry_run: bool = False,
                                         root: str | Path | None = None) -> dict[str, Any]:
    """The only entry point the chat action router executes. Returns receipts and status, never review content."""
    if function_name not in FUNCTIONS:
        return {"ok": False, "message": "unknown_review_function"}
    if function_name == "experiment_review_list":
        return {"ok": True, "message": list_message(root), "packages": [r["package_id"] for r in eligible_packages(root) if r.get("eligible")]}
    if function_name == "experiment_review_status":
        status = job_status(str(args.get("job_id") or "latest"), root)
        return {"ok": bool(status), "message": status["message"] if status else "No review job has been started yet.", "receipt": receipt(status or {})}
    package_id = str(args.get("package_id") or "")
    expected_manifest = str(args.get("manifest_sha256") or "")
    if dry_run:
        package = find_package(package_id, root)
        manifest_matches = bool(package) and (not expected_manifest or hmac.compare_digest(
            expected_manifest.lower(), str((package or {}).get("manifest_sha256") or "").lower()))
        return {"ok": manifest_matches and active_job(root) is None,
                "message": ("Dry run passed. The installed package would be reviewed once, read-only, as a background job."
                            if manifest_matches and active_job(root) is None else "Dry run: the package is not eligible, has drifted, or a review is already running.")}
    try:
        job = start_review(package_id, confirmed=True, root=root, operator_note=str(args.get("operator_note") or ""),
                           expected_manifest_sha256=expected_manifest)
    except PermissionError:
        return {"ok": False, "message": "The review did not start: an explicit operator confirmation is required."}
    except LookupError:
        return {"ok": False, "message": f"The review did not start: '{package_id}' is not an installed, eligible package. "
                                        "Ask me which experiments I can review."}
    except RuntimeError:
        running = active_job(root)
        return {"ok": False, "message": ("The review did not start: a review is already running"
                                         + (f" (job {running['job_id']}, package {running['package_id']})" if running else "")
                                         + ". Only one local-model review runs at a time; ask me for its status.")}
    return {"ok": True, "message": (f"Review job {job['job_id']} started for {job['package_id']} (manifest {job['manifest_sha256'][:16]}). "
                                    "It runs in its own process, so it continues if you disconnect. Ask for the status when you like."),
            "receipt": receipt(job)}


__all__ = ["CONTRACT_VERSION", "FUNCTIONS", "PACKAGE_AREA", "JOB_AREA", "REVIEW_KIND", "MAX_JOB_SECONDS", "package_area", "job_area",
           "eligible_packages", "reviews_of", "find_package", "active_job", "latest_job", "save_job", "start_review", "job_status",
           "receipt", "list_message", "propose_message", "execute_conversational_review_action"]
