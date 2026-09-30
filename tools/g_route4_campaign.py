# forked from g_route3_campaign
from __future__ import annotations

"""G-ROUTE4 R7 certification crash campaign (design §19, ruling 3).

Every filesystem operation, every file read and every child process of the lifecycle goes through the ``Fs``
choke point. ``FaultFs`` counts them and can:

* kill the process (``SimulatedKill``, a BaseException) just before or just after any numbered operation;
* model power loss: every operation not yet made durable by a directory flush is reverted (all of them, or a
  seeded subset, which also models reordering);
* inject sharing violations, failing directory flushes and damage.

A scenario runs commands against a fresh data root until the injected fault, then restarts with fresh objects
(the OS released the lease) and runs the supported recovery commands, optionally killing again during recovery,
until a fixpoint. Oracles: no schedule position is sent to the provider twice within one attempt (J12); no
temporary file is deleted unless identical to its entry; the end state is completed (with fact payloads equal to
the uninterrupted run), or closed with a permitted reason followed by a next attempt that completes, or a declared
refusal; and every committed item still verifies.

    python tools/g_route4_campaign.py [--quick]
"""

import argparse
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_route4_fs as F  # noqa: E402
import g_route4_journal as J  # noqa: E402
import g_route4_lifecycle as L  # noqa: E402
import g_route4_platform as P  # noqa: E402


class SimulatedKill(BaseException):
    """The process dies here. BaseException, so no ``except Exception`` in the lifecycle can swallow it."""


class FaultFs(F.RealFs):
    """RealFs with numbered operations, kills, power-loss bookkeeping and injected faults."""

    def __init__(self, *, kill_at: int | None = None, kill_after: bool = True,
                 flush_fail_at: set[int] | None = None, log_temps: list | None = None,
                 kill_probability: float = 0.0, rng: random.Random | None = None, lose_power: bool = False) -> None:
        super().__init__(hook=self._hook, sleep=lambda seconds: None)
        self.count = 0
        self.kill_at = kill_at
        self.kill_after = kill_after
        self.kill_probability = kill_probability
        self.rng = rng or random.Random(0)
        self.lose_power = lose_power
        self.flush_fail_at = flush_fail_at or set()
        self.pending: list[tuple[str, Any]] = []        # unflushed operations, in order
        self.temp_unlinks = log_temps if log_temps is not None else []
        self.ops: list[str] = []

    def _hook(self, kind: str, detail: str) -> None:
        after = kind.startswith("after_")
        if not after:
            self.count += 1
            self.ops.append(f"{self.count}:{kind}:{detail[-80:]}")
            if self.kill_at is None and self.kill_probability and self.rng.random() < self.kill_probability:
                self.kill_at, self.kill_after = self.count, self.rng.random() < 0.5
            if self.kill_at == self.count and not self.kill_after:
                raise SimulatedKill(f"before:{kind}")
            if kind == "flush_dir" and self.count in self.flush_fail_at:
                raise OSError(5, "injected_flush_failure")
        else:
            if self.kill_at == self.count and self.kill_after:
                raise SimulatedKill(f"after:{kind}")

    # power-loss bookkeeping
    def _write_temp(self, path: Path, data: bytes) -> None:
        super()._write_temp(path, data)
        self.pending.append(("create", Path(path)))

    def _rename_noreplace(self, source: Path, target: Path) -> None:
        super()._rename_noreplace(source, target)
        self.pending.append(("rename", (Path(source), Path(target))))

    def _rename_replace(self, source: Path, target: Path) -> None:
        old = target.read_bytes() if Path(target).exists() else None
        super()._rename_replace(source, target)
        self.pending.append(("replace", (Path(source), Path(target), old)))

    def _unlink(self, path: Path) -> None:
        data = Path(path).read_bytes() if Path(path).is_file() else None
        name = Path(path).name
        if J.TEMP_NAME.match(name) and data is not None:
            number = int(J.TEMP_NAME.match(name).group(1))
            published = Path(path).parent / J.entry_name(number)
            self.temp_unlinks.append((str(path), published.is_file() and published.read_bytes() == data))
        super()._unlink(path)
        self.pending.append(("unlink", (Path(path), data)))

    def _mkdir(self, path: Path) -> None:
        super()._mkdir(path)
        self.pending.append(("mkdir", Path(path)))

    def _flush_dir(self, path: Path) -> None:
        super()._flush_dir(path)
        directory = Path(path).resolve()
        kept = []
        for kind, detail in self.pending:
            touched = _touched_dirs(kind, detail)
            if directory in touched:
                continue
            kept.append((kind, detail))
        self.pending = kept

    def power_loss(self, rng: random.Random | None = None) -> int:
        """Revert unflushed operations (all, or a seeded subset). Returns how many were reverted."""
        chosen = [op for op in self.pending if rng is None or rng.random() < 0.5]
        for kind, detail in reversed(chosen):
            try:
                if kind == "create" and detail.exists():
                    detail.unlink()
                elif kind == "rename":
                    source, target = detail
                    if target.exists() and not source.exists():
                        os.rename(target, source)
                elif kind == "replace":
                    source, target, old = detail
                    if old is not None:
                        target.write_bytes(old)
                elif kind == "unlink":
                    path, data = detail
                    if data is not None and not path.exists():
                        path.write_bytes(data)
                elif kind == "mkdir" and detail.is_dir() and not any(detail.iterdir()):
                    detail.rmdir()
            except OSError:
                pass
        self.pending = []
        return len(chosen)


def _touched_dirs(kind: str, detail: Any) -> set[Path]:
    if kind in ("create", "mkdir"):
        return {Path(detail).resolve().parent}
    if kind == "unlink":
        return {Path(detail[0]).resolve().parent}
    if kind in ("rename", "replace"):
        return {Path(detail[0]).resolve().parent, Path(detail[1]).resolve().parent}
    return set()


# ---------------------------------------------------------------- the small schedule and stubs

def small_schedule() -> tuple[dict, dict]:
    import g_route4_contract as C
    fixtures = {phase: C.runtime_fixtures(phase) for phase in "AB"}
    rows = C.verify_checked_schedule("A")
    coding = next(r for r in rows if fixtures["A"][r["fixture_id"]]["validator_profile"] == "coding.v1")
    plain = [r for r in rows if fixtures["A"][r["fixture_id"]]["validator_profile"] != "coding.v1"][:3]
    chosen = [plain[0], coding, plain[1], plain[2]]
    schedule = {"A": [dict(row, position=index + 1) for index, row in enumerate(chosen)],
                "B": C.verify_checked_schedule("B")[:4]}
    return schedule, fixtures


class StubProvider:
    """Counts calls per (attempt, call id). ``failures`` maps call ids to a failure mode."""

    synthetic_provider = True

    def __init__(self, data_root: Path, counts: dict, failures: Mapping[str, str] | None = None, *,
                 fs: F.RealFs | None = None, violations: list | None = None) -> None:
        self.data_root = data_root
        self.counts = counts
        self.failures = dict(failures or {})
        self.fs = fs
        self.violations = violations if violations is not None else []

    def durable(self, run_id: str) -> bool:
        """No unflushed operation of this process touches the run's journal folder (§11: intent durable first)."""
        pending = getattr(self.fs, "pending", None)
        if not pending:
            return True
        journal = (self.data_root / "phase_a" / "runs" / run_id / "journal").resolve()
        return not any(journal in _touched_dirs(kind, detail) for kind, detail in pending)

    def active_run(self, call_id: str) -> str:
        """The run whose journal ends in a durable call_started for this call id (the one being sent)."""
        runs = self.data_root / "phase_a" / "runs"
        for run in sorted(runs.iterdir()) if runs.is_dir() else []:
            entries = sorted((run / "journal").glob("*.json")) if (run / "journal").is_dir() else []
            if entries:
                envelope = J.parse_entry(entries[-1].read_bytes())
                if envelope and envelope["kind"] == "call_started" and envelope["payload"].get("call_id") == call_id:
                    return run.name
        return "no_durable_call_started"

    def __call__(self, call_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
        import base64
        import hashlib
        key = (self.active_run(call_id), call_id)
        self.counts[key] = self.counts.get(key, 0) + 1
        if key[0] == "no_durable_call_started" or not self.durable(key[0]):
            self.violations.append(f"send_without_durable_call_started:{call_id}")
        mode = self.failures.get(call_id, "")
        if mode == "raise":
            raise ConnectionError("stub_provider_down")
        raw = json.dumps({"path": "app.py", "old": "x", "new": "y"}) if "CODE" in call_id else f"ok:{call_id}"
        envelope = {"model": body["model"], "response": raw, "done": True, "eval_count": 3}
        raw_body = json.dumps(envelope).encode("utf-8")
        return {"requested_model": body["model"], "returned_model": body["model"],
                "raw_body_b64": base64.b64encode(raw_body).decode("ascii"),
                "raw_body_sha256": hashlib.sha256(raw_body).hexdigest(), "raw_output": raw,
                "output_field": "response", "metrics": {"eval_count": 3}, "latency_seconds": 0.01,
                "provider_contacted": True, "error": "HTTPError:500" if mode == "error" else ""}


def stub_worker(fs, failures: set | None = None) -> Callable:
    def call(request: Mapping[str, Any]) -> Mapping[str, Any]:
        fs.hook("child", "worker")
        fs.hook("after_child", "worker")
        if failures and request["fixture_id"] in failures:
            raise L.WorkerFailure("died:1")
        digest = J.sha256_bytes(request["executable_json"].encode("ascii"))
        drift = {"tools/g_route3_worker.py": "0" * 64} if failures and "module_drift" in failures else {}
        return {"evidence": {"stub": digest}, "candidate_error": None, "infrastructure_failure": "",
                "module_digests": drift}
    return call


def stub_scorer(fs, data_root: Path, spec: J.RunSpec) -> Callable:
    def call(request: Mapping[str, Any]) -> Mapping[str, Any]:
        fs.hook("child", "scorer")
        fs.hook("after_child", "scorer")
        directory = Path(request["data_root"]) / f"phase_{request['phase'].lower()}" / "runs" / request["run_id"] / "journal"
        files = {p.name: p.read_bytes() for p in directory.iterdir() if J.ENTRY_NAME.match(p.name)}
        replay = J.replay_run(files, spec)
        facts = [e["payload"].get("raw_output_sha256") for e in replay.entries if e["kind"] == "call_recorded"]
        return {"report": {"facts_digest": J.digest(facts), "attempts": list(request.get("attempts") or [])}}
    return call


# ---------------------------------------------------------------- scenario machinery

SENTENCE = "Authorize G-ROUTE4 phase A execution " + "f" * 64 + " attempt {n}"
DISTINCT = SENTENCE + " after integrity failure of attempt {m}"


class World:
    """One data root, its counters and a way to build a fresh Lifecycle (a fresh process)."""

    def __init__(self, root: Path, *, failures: Mapping[str, str] | None = None,
                 worker_failures: set | None = None) -> None:
        self.root = root
        self.D = root / "D"
        self.counts: dict = {}
        self.temp_unlinks: list = []
        self.failures = dict(failures or {})
        self.worker_failures = set(worker_failures or ())
        self.schedule, self.fixtures = small_schedule()
        self.drift = False
        self.violations: list[str] = []

    def lifecycle(self, fs: F.RealFs) -> L.Lifecycle:
        base = L.standard_guarded_files(self.D, "A")

        def guarded(phase: str) -> dict:
            files = dict(base)
            if self.drift:
                files["tools/g_route3_worker.py"] = "0" * 64
            return files
        spec = J.RunSpec(call_ids=tuple(r["call_id"] for r in self.schedule["A"]),
                         coding=frozenset(r["position"] for r in self.schedule["A"]
                                          if self.fixtures["A"][r["fixture_id"]]["validator_profile"] == "coding.v1"))
        import g_route4_runner as R
        import g_route4_tests as T
        rt = L.Runtime(data_root=self.D, fs=fs, provider=StubProvider(self.D, self.counts, self.failures, fs=fs,
                                                                      violations=self.violations),
                       model_receipts=lambda: T.receipts(), verify_receipts=R.verify_model_receipts,
                       freeze_binding=lambda: "f" * 64, freeze_valid=lambda: True, guarded_files=guarded,
                       worker=stub_worker(fs, self.worker_failures), scorer=stub_scorer(fs, self.D, spec),
                       schedules=self.schedule, fixtures=self.fixtures, synthetic=True, endpoint="synthetic")
        return L.Lifecycle(rt)


def run_command(world: World, fs: F.RealFs, command: str, *args) -> Any:
    lc = world.lifecycle(fs)
    try:
        if command == "setup":
            lc.setup_if_missing()
            return "setup"
        lc.open()
        if command == "prelude":            # J8 steps 1-5 alone: what a refused command leaves behind
            lc.prelude()
            return "prelude"
        method = getattr(lc, "command_" + command)
        return method(*args)
    finally:
        lc.close()


def latest_attempt(world: World) -> tuple[int, str]:
    fs = F.RealFs()
    lc = world.lifecycle(fs)
    lc.open()
    try:
        lc.prelude()                    # what any command does first: recover, then complete pending boundaries
        rows = lc.attempt_table("A")
        if not rows:
            return 0, "none"
        attempt, _, replay, closed = rows[-1]
        return attempt, "closed_at_ledger" if closed else replay.state
    finally:
        lc.close()


def peek_attempt(world: World) -> tuple[int, str, str | None]:
    """A pure status probe: the latest attempt as found on disk. It never verifies, recovers, commits or writes,
    so every recovery is done by a command the campaign can kill (A-N4). Integrity failures found only by
    verification or recovery are not visible here; commands report them by refusing."""
    lc = world.lifecycle(F.RealFs())
    try:
        lc.root_id = json.loads((world.D / "root.json").read_bytes().decode("utf-8"))["root_id"]
        ledger = lc.ledger("A")
        rows = lc.attempt_table("A")
    except Exception:  # noqa: BLE001
        return -1, "unreadable", None
    if not rows:
        return 0, "none", None
    attempt, _, replay, closed = rows[-1]
    return attempt, "closed_at_ledger" if closed else replay.state, ledger.consumed[attempt].get("sentence")


def peek_orphans(world: World) -> list[str]:
    """Run folders with no ledger entry, as found on disk (a pure read, like peek_attempt)."""
    lc = world.lifecycle(F.RealFs())
    try:
        lc.root_id = json.loads((world.D / "root.json").read_bytes().decode("utf-8"))["root_id"]
        return lc.orphan_runs("A")
    except Exception:  # noqa: BLE001
        return []


def drive_to_end(world: World, *, fault: Callable[[], FaultFs] | None = None, max_steps: int = 24,
                 recursive_kills: int = 0, seed: int = 0, power: bool = False) -> str:
    """Supported commands only: resume while possible; declare when an integrity failure needs it; launch the
    next attempt after a closure. Decisions come from a pure peek. Until a command has run its J8 steps without
    being killed, the peek is unverified: a torn, unreadable or failed state, or a completed one, first gets a
    command's J8 steps alone (``prelude``, what a refused command does); other states are acted on directly, so
    recovery and action also run in one process. With ``recursive_kills``, the first commands are themselves
    killed with a per-operation probability, recursively (§19); with ``power``, each such kill also loses the
    unflushed operations. Returns the final outcome label."""
    prefer_distinct = None
    rng = random.Random(seed)
    kills_left = recursive_kills
    verified = False
    force_declare = False
    clear_orphans = False
    last_refusal = None
    for _ in range(max_steps):
        if fault:
            fs = fault()
        elif kills_left > 0:
            kills_left -= 1
            fs = FaultFs(kill_probability=0.02, rng=random.Random(rng.random()), log_temps=world.temp_unlinks,
                         lose_power=power)
        else:
            fs = F.RealFs()
        try:
            if clear_orphans:
                for run_id in peek_orphans(world):
                    run_command(world, fs, "clear_orphan", "A", run_id)
                clear_orphans = False
                verified = True
                continue
            attempt, state, consumed_sentence = peek_attempt(world)
            unsettled = state in ("unreadable", "torn_pending", "torn_tail", "integrity_failure", "absent",
                                  "completed")
            if not verified and unsettled:
                run_command(world, fs, "prelude")
                verified = True
                continue
            if force_declare or (state in ("integrity_failure", "absent") and verified):
                force_declare = False
                run_command(world, fs, "declare", "A", attempt)
            elif attempt == 0:
                run_command(world, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
            elif state == "completed":
                return "completed"
            elif state in ("closed", "closed_at_ledger"):
                distinct = (state == "closed_at_ledger") if prefer_distinct is None else prefer_distinct
                sentence = DISTINCT.format(n=attempt + 1, m=attempt) if distinct else SENTENCE.format(n=attempt + 1)
                if attempt >= 3:
                    return f"stopped_after_{attempt}_attempts"
                run_command(world, fs, "launch", "A", sentence, attempt + 1, distinct)
            else:
                run_command(world, fs, "resume", "A", consumed_sentence or SENTENCE.format(n=attempt))
            verified = True
            last_refusal = None
        except SimulatedKill:
            verified = False
            last_refusal = None                      # a refusal repeated across a kill is progress, not a loop
            if isinstance(fs, FaultFs) and fs.lose_power:
                fs.power_loss(random.Random(rng.random()))
            continue
        except L.PhaseBlocked as exc:
            return f"declared_refusal:{str(exc)[:80]}"
        except F.Unreadable as exc:
            return f"declared_refusal:unreadable:{str(exc)[:60]}"
        except L.Refusal as exc:
            verified = True                          # every refusal below follows the command's J8 steps
            repeated = str(exc) == last_refusal
            last_refusal = str(exc)
            if repeated and "retry_after_verification" not in str(exc):
                return f"refusal:{str(exc)[:120]}"
            if "attempt_not_resumable:integrity_failure" in str(exc) or "attempt_not_resumable:absent" in str(exc):
                force_declare = True                  # found by verification or recovery, not by the peek
                continue
            if "attempt_not_resumable" in str(exc) or "attempt_number_must_be" in str(exc):
                continue                              # the peek predated recovery; peek again
            if "distinct_sentence_required" in str(exc):
                prefer_distinct = True
                continue
            if "distinct_sentence_not_permitted" in str(exc):
                prefer_distinct = False
                continue
            if "retry_after_verification" in str(exc):
                continue                                         # the next command's verification restores it
            if "orphan_run_folder_exists" in str(exc):          # the operator's supported step, next step
                clear_orphans = True
                continue
            return f"refusal:{str(exc)[:120]}"
    return "no_fixpoint"


REFERENCE_FACTS: list = []


def completed_facts(world: World) -> list | None:
    fs = F.RealFs()
    lc = world.lifecycle(fs)
    lc.open()
    try:
        for attempt, run_id, replay, closed in lc.attempt_table("A"):
            if replay.state == "completed":
                return [(e["kind"], e["payload"].get("position"), e["payload"].get("raw_output_sha256"),
                         J.digest(e["payload"].get("evidence"))) for e in replay.entries
                        if e["kind"] in ("call_recorded", "execution_recorded")]
        return None
    finally:
        lc.close()


def check_oracles(world: World) -> list[str]:
    problems = []
    try:
        facts = completed_facts(world)
        if facts is not None and REFERENCE_FACTS and facts != REFERENCE_FACTS[0]:
            problems.append("completed_facts_differ_from_uninterrupted_run")
        lc = world.lifecycle(F.RealFs())
        lc.open()
        try:
            rows = lc.attempts("A")
            ledger = lc.ledger("A")
            if [row["attempt"] for row in rows] != sorted(ledger.consumed):
                problems.append("disclosure_rows_differ_from_ledger")
            for row, (attempt, run_id, replay, closed) in zip(rows, lc.attempt_table("A")):
                expected = "closed_at_ledger" if closed else ("completed" if replay.state == "completed" else
                                                              "closed" if replay.state == "closed" else None)
                if expected and row["outcome"] != expected:
                    problems.append(f"disclosure_outcome_wrong:{attempt}")
                if row["outcome"] != "completed" and not row["optional_stopping_cannot_be_excluded"]:
                    problems.append(f"optional_stopping_flag_missing:{attempt}")
        finally:
            lc.close()
    except (L.Refusal, F.Unreadable):
        pass
    problems.extend(world.violations)
    for (attempt, call_id), count in world.counts.items():
        if count > 1:
            problems.append(f"J12_repeat:{attempt}:{call_id}:{count}")
    for path, identical in world.temp_unlinks:
        if not identical:
            problems.append(f"temp_deleted_not_identical:{path}")
    try:
        fs = F.RealFs()
        lc = world.lifecycle(fs)
        lc.open()                       # verification of every committed item
        lc.close()
    except L.PhaseBlocked:
        pass                            # a declared refusal is a permitted end state
    except Exception as exc:  # noqa: BLE001
        problems.append(f"final_verification:{type(exc).__name__}:{str(exc)[:100]}")
    return problems


def base_world(template: Path, target: Path, **kwargs) -> World:
    if target.exists():
        L._remove_tree(target)
    shutil.copytree(template, target)
    return World(target, **kwargs)


def reference_outcome(workdir: Path) -> tuple[Path, dict]:
    """A pristine set-up data root (the template) and the uninterrupted run's facts."""
    template = workdir / "template"
    if template.exists():
        L._remove_tree(template)
    template.mkdir(parents=True)
    world = World(template)
    run_command(world, F.RealFs(), "setup")
    clean = base_world(template, workdir / "clean")
    outcome = drive_to_end(clean)
    assert outcome == "completed", outcome
    REFERENCE_FACTS[:] = [completed_facts(clean)]
    return template, {"ops": None}


def kill_campaign(workdir: Path, template: Path, *, failures=None, worker_failures=None, power: bool = False,
                  stride: int = 1, label: str = "kills", subset_seed: int | None = None,
                  recursive_kills: int = 2) -> dict:
    """Kill after (and before) every operation of an uninterrupted attempt, then recover to a fixpoint."""
    probe = base_world(template, workdir / "probe", failures=failures, worker_failures=worker_failures)
    fs = FaultFs(log_temps=probe.temp_unlinks)
    try:
        run_command(probe, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
    except L.Refusal:
        pass
    total = fs.count
    results = {"label": label, "operations": total, "cases": 0, "outcomes": {}, "problems": []}
    for index in range(1, total + 1, stride):
        for after in (True, False):
            world = base_world(template, workdir / "case", failures=failures, worker_failures=worker_failures)
            fs = FaultFs(kill_at=index, kill_after=after, log_temps=world.temp_unlinks)
            try:
                run_command(world, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
            except SimulatedKill:
                if power:
                    fs.power_loss(random.Random(subset_seed + index) if subset_seed is not None else None)
            except L.Refusal:
                pass
            outcome = drive_to_end(world, recursive_kills=recursive_kills, seed=index * 2 + int(after), power=power)
            results["cases"] += 1
            results["outcomes"][outcome.split(":")[0]] = results["outcomes"].get(outcome.split(":")[0], 0) + 1
            problems = check_oracles(world)
            persistent = bool(failures or worker_failures)
            permitted = outcome == "completed" or (persistent and outcome.startswith("stopped_after_"))
            if not persistent and outcome == "completed" and len(world.counts) < 4:
                problems = problems + ["completed_without_every_call"]
            if not permitted or problems:
                results["problems"].append({"kill": index, "after": after, "outcome": outcome,
                                            "problems": problems, "op": fs.ops[index - 1] if index <= len(fs.ops) else ""})
    return results


def _latest_file(directory: Path) -> Path | None:
    files = sorted(p for p in directory.glob("*.json")) if directory.is_dir() else []
    return files[-1] if files else None


def damage_campaign(workdir: Path, template: Path, *, stride: int = 1, ledger: bool = False,
                    label: str = "torn_entries") -> dict:
    """§19 torn entries: kill after a publication's rename, then truncate the entry just published (a device
    fault), or the ledger's last entry. Recovery must rename it to .torn and close or re-derive truthfully."""
    probe = base_world(template, workdir / "probe")
    fs = FaultFs()
    run_command(probe, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
    marker = "ledger" if ledger else "journal"
    renames = [i for i, op in enumerate(fs.ops, 1) if ":rename:" in op and marker in op]
    results = {"label": label, "operations": len(fs.ops), "cases": 0, "outcomes": {}, "problems": []}
    for index in renames[::stride]:
        world = base_world(template, workdir / "case")
        fs = FaultFs(kill_at=index, kill_after=True, log_temps=world.temp_unlinks)
        try:
            run_command(world, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
        except SimulatedKill:
            pass
        if ledger:
            target = _latest_file(world.D / "phase_a" / "ledger")
        else:
            runs = sorted((world.D / "phase_a" / "runs").glob("*/journal"))
            target = _latest_file(runs[-1]) if runs else None
        if target is not None:
            data = target.read_bytes()
            target.write_bytes(data[: max(1, len(data) // 2)])
        outcome = drive_to_end(world, recursive_kills=1, seed=index)
        results["cases"] += 1
        key = outcome.split(":")[0]
        results["outcomes"][key] = results["outcomes"].get(key, 0) + 1
        problems = check_oracles(world)
        if key != "completed" or problems:
            results["problems"].append({"kill": index, "outcome": outcome, "problems": problems,
                                        "op": fs.ops[index - 1] if index <= len(fs.ops) else ""})
    return results


def flush_failure_campaign(workdir: Path, template: Path, *, stride: int = 1) -> dict:
    """§19: a directory flush that fails (after its rename) at every flush point."""
    probe = base_world(template, workdir / "probe")
    fs = FaultFs()
    run_command(probe, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
    flushes = [i for i, op in enumerate(fs.ops, 1) if ":flush_dir:" in op]
    results = {"label": "flush_failures", "operations": len(fs.ops), "cases": 0, "outcomes": {}, "problems": []}
    for index in flushes[::stride]:
        world = base_world(template, workdir / "case")
        fs = FaultFs(flush_fail_at={index}, log_temps=world.temp_unlinks)
        try:
            run_command(world, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
        except (F.NotDurable, OSError, L.Refusal):
            pass
        outcome = drive_to_end(world)
        results["cases"] += 1
        key = outcome.split(":")[0]
        results["outcomes"][key] = results["outcomes"].get(key, 0) + 1
        problems = check_oracles(world)
        if key != "completed" or problems:
            results["problems"].append({"flush": index, "outcome": outcome, "problems": problems,
                                        "op": fs.ops[index - 1] if index <= len(fs.ops) else ""})
    return results


def environment_cases(workdir: Path, template: Path) -> dict:
    """§19 environment seeds: leftover git locks, transient read errors, inherited GIT_* and proxy variables."""
    results = {"label": "environment", "cases": 0, "outcomes": {}, "problems": []}

    def record(name: str, outcome: str, problems: list) -> None:
        results["cases"] += 1
        results["outcomes"][name] = outcome
        if outcome != "completed" or problems:
            results["problems"].append({"case": name, "outcome": outcome, "problems": problems})

    world = base_world(template, workdir / "lock")
    (world.D / "evidence.git" / "index.lock").write_bytes(b"")
    (world.D / "evidence.git" / "refs" / "heads" / "evidence.lock").write_bytes(b"")
    record("stale_git_locks", drive_to_end(world), check_oracles(world))

    class Flaky(FaultFs):
        def __init__(self) -> None:
            super().__init__()
            self.failures_left = 5

        def _read(self, path):
            if self.failures_left > 0 and str(path).endswith(".json"):
                self.failures_left -= 1
                raise PermissionError(13, "injected_sharing_violation")
            return super()._read(path)

    import g_route4_platform as platform_module
    original = platform_module.is_transient
    platform_module.is_transient = lambda exc: original(exc) or "injected_sharing_violation" in str(exc)
    try:
        world = base_world(template, workdir / "flaky")
        record("transient_read_errors", drive_to_end(world, fault=Flaky), check_oracles(world))
    finally:
        platform_module.is_transient = original

    saved = {name: os.environ.get(name) for name in ("GIT_OBJECT_DIRECTORY", "GIT_CONFIG_PARAMETERS",
                                                     "GIT_CONFIG_COUNT", "HTTP_PROXY")}
    os.environ.update({"GIT_OBJECT_DIRECTORY": str(workdir / "elsewhere"),
                       "GIT_CONFIG_PARAMETERS": "'core.autocrlf'='true'", "GIT_CONFIG_COUNT": "1",
                       "HTTP_PROXY": "http://127.0.0.1:9"})
    try:
        world = base_world(template, workdir / "gitenv")
        record("inherited_git_environment", drive_to_end(world), check_oracles(world))
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    return results


def gap_cases(workdir: Path, template: Path) -> dict:
    """§19 seeds not covered by the sweeps: unreadable files, a damaged root.json, concurrent first setups,
    interrupts at every safe point."""
    results = {"label": "gap_seeds", "cases": 0, "outcomes": {}, "problems": []}

    def record(name: str, ok: bool, detail: str = "") -> None:
        results["cases"] += 1
        results["outcomes"][name] = "ok" if ok else f"FAILED:{detail}"
        if not ok:
            results["problems"].append({"case": name, "detail": detail})

    # unreadable files: the command refuses (§1.3), then the next command recovers once the file reads again
    class Unreadable(FaultFs):
        def __init__(self, needle: str) -> None:
            super().__init__()
            self.needle = needle

        def _read(self, path):
            if self.needle in str(path):
                raise OSError(1117, "injected_io_device_error")
            return super()._read(path)

        def _listdir(self, path):
            if self.needle in str(path) and self.needle.endswith("journal"):
                raise OSError(1117, "injected_io_device_error")
            return super()._listdir(path)

    for name, needle in (("unreadable_committed_entry", "000001.json"), ("unreadable_tail_entry", "000009.json"),
                         ("unlistable_journal", "journal")):
        world = base_world(template, workdir / name)
        probe = FaultFs()
        try:
            run_command(world, probe, "launch", "A", SENTENCE.format(n=1), 1, False)
        except Exception:  # noqa: BLE001
            pass
        refused = drive_to_end(world, fault=lambda needle=needle: Unreadable(needle), max_steps=2)
        final = drive_to_end(world)
        record(name, refused.startswith(("declared_refusal", "completed")) and final == "completed"
               and not check_oracles(world), f"{refused} then {final}")

    # a damaged root.json is restored from the root commit
    world = base_world(template, workdir / "root_json")
    (world.D / "root.json").write_bytes(b"{broken")
    outcome = drive_to_end(world)
    record("damaged_root_json", outcome == "completed" and J.parse_entry is not None and
           json.loads((world.D / "root.json").read_bytes()).get("experiment") == "G-ROUTE4", outcome)

    # two concurrent first setups: exactly one intact data root
    import subprocess
    target = workdir / "concurrent"
    if target.exists():
        L._remove_tree(target)
    target.mkdir(parents=True)
    script = ("import sys; sys.path.insert(0, %r); import g_route4_campaign as K, g_route4_platform as P; "
              "P.pin_recursion_limit(); from pathlib import Path\n"
              "try:\n    K.run_command(K.World(Path(%r)), K.F.RealFs(), 'setup'); print('setup')\n"
              "except Exception as exc:\n    print('refused', type(exc).__name__)") % (str(TOOLS), str(target))
    procs = [subprocess.Popen([sys.executable, "-B", "-c", script], stdout=subprocess.PIPE, text=True)
             for _ in range(2)]
    outputs = [proc.communicate(timeout=300)[0].strip() for proc in procs]
    world = World(target)
    record("concurrent_setup", drive_to_end(world) == "completed" and not check_oracles(world), str(outputs))

    # an interrupt at every safe point closes as operator_interrupt before collected, or exits after it
    probe = base_world(template, workdir / "interrupt_probe")
    counting = probe.lifecycle(F.RealFs())
    seen = {"n": 0}

    def count() -> bool:
        seen["n"] += 1
        return False
    counting.rt.interrupted = count
    counting.open()
    try:
        counting.command_launch("A", SENTENCE.format(n=1), 1, False)
    finally:
        counting.close()
    safe_points = seen["n"]
    for point in range(1, safe_points + 2):
        world = base_world(template, workdir / f"interrupt_{point}")
        lc = world.lifecycle(F.RealFs())
        counter = {"n": 0}

        def interrupted(counter=counter, point=point):
            counter["n"] += 1
            return counter["n"] == point
        lc.rt.interrupted = interrupted
        lc.open()
        try:
            out = lc.command_launch("A", SENTENCE.format(n=1), 1, False)
        finally:
            lc.close()
        if point > safe_points:
            ok = out["state"] == "completed"
        else:
            ok = (out["state"] == "closed" and out["reason"] == "operator_interrupt") or \
                (out["state"] in ("collected", "scoring_interrupted", "scored")
                 and out["reason"] == "interrupted_after_collection")
        final = drive_to_end(world)
        record(f"interrupt_at_safe_point_{point}", ok and final == "completed" and not check_oracles(world),
               f"{out['state']}:{out.get('reason')} then {final}")
    return results


def resumed_interrupt_cases(workdir: Path, template: Path) -> dict:
    """Ruling 12 on resumed attempts. The first attempt is killed after a plain call_recorded (collecting) and
    after the coding call_recorded (awaiting_execution, the pending-sandbox safe point). The resume is then
    interrupted at its k-th check. Before the first new call it must exit open, having added only the
    execution entries of a sandbox run that finished before the interrupt;
    after one it must close as operator_interrupt, or, from collected on, exit with interrupted_after_collection.
    Either way the attempt must then complete with clean oracles."""
    results = {"label": "resumed_interrupts", "cases": 0, "outcomes": {}, "problems": []}
    probe = base_world(template, workdir / "resumed_probe")
    probe_fs = FaultFs(log_temps=probe.temp_unlinks)
    run_command(probe, probe_fs, "launch", "A", SENTENCE.format(n=1), 1, False)
    ops = probe_fs.ops
    for label, entry in (("collecting", "000003.json"), ("awaiting_execution", "000005.json")):
        kill = next(i for i, op in enumerate(ops, 1) if ":rename:" in op and "journal" in op and entry in op)
        for k in range(1, 9):
            name = f"resumed_{label}_interrupt_at_check_{k}"
            world = base_world(template, workdir / "resumed_case")
            try:
                run_command(world, FaultFs(kill_at=kill, kill_after=True), "launch", "A", SENTENCE.format(n=1), 1,
                            False)
            except SimulatedKill:
                pass
            run_command(world, F.RealFs(), "prelude")
            journal = next((world.D / "phase_a" / "runs").iterdir()) / "journal"
            before, calls_before = sorted(p.name for p in journal.iterdir()), dict(world.counts)
            lc = world.lifecycle(F.RealFs())
            seen = {"n": 0}

            def interrupted(seen=seen, k=k):
                seen["n"] += 1
                return seen["n"] == k
            lc.rt.interrupted = interrupted
            lc.open()
            try:
                out = lc.command_resume("A", SENTENCE.format(n=1))
            finally:
                lc.close()
            new_calls = sum(world.counts.values()) - sum(calls_before.values())
            if out["state"] == "completed":
                ok = seen["n"] < k                                   # the flag was never raised
            elif new_calls == 0:
                # the interrupt itself writes nothing; a sandbox run that finished before it may have added its
                # own execution entries, and nothing else
                added = [J.parse_entry((journal / n).read_bytes()) for n in
                         sorted(set(p.name for p in journal.iterdir()) - set(before))]
                ok = (out["state"], out["reason"]) == ("open", "interrupted_before_first_new_call") and \
                    all(e is not None and e["kind"] in ("execution_started", "execution_recorded") for e in added)
            else:
                ok = (out["state"], out["reason"]) == ("closed", "operator_interrupt") or \
                    out["reason"] == "interrupted_after_collection"
            final = drive_to_end(world)
            problems = check_oracles(world)
            passed = ok and final == "completed" and not problems
            results["cases"] += 1
            results["outcomes"][name] = "ok" if passed else f"FAILED:{out['state']}:{out.get('reason')}:{final}"
            if not passed:
                results["problems"].append({"case": name, "out": out, "new_calls": new_calls, "final": final,
                                            "problems": problems})
    return results


def review_seeds(workdir: Path, template: Path) -> dict:
    """Seeds from implementation review 1 (A-F12): read corruption of committed entries (A-O3), ledger twins
    (A-O7), declaration then further commands (A-F3), pending ledger closures (A-F4), a failed refs flush (A-O9),
    worker module drift (C-O3/C-O4), abandon, and a kill during setup."""
    results = {"label": "review_seeds", "cases": 0, "outcomes": {}, "problems": []}

    def record(name: str, ok: bool, detail: str = "") -> None:
        results["cases"] += 1
        results["outcomes"][name] = "ok" if ok else f"FAILED:{detail}"
        if not ok:
            results["problems"].append({"case": name, "detail": detail})

    class CorruptAfterFirstRead(FaultFs):
        """Returns damaged bytes for a target file on every read after the first one in this command."""
        def __init__(self, needle: str) -> None:
            super().__init__()
            self.needle, self.seen = needle, 0

        def _read(self, path):
            data = super()._read(path)
            if self.needle in str(path).replace("\\", "/"):
                self.seen += 1
                if self.seen > 1:
                    return data[: len(data) // 2]
            return data

    def ops_of(world, command, *args):
        probe = FaultFs()
        run_command(world, probe, command, *args)
        return probe.ops

    # A-O3 / exp4: a protected attempt (killed during scoring) and read corruption of its committed ledger entry
    probe_world = base_world(template, workdir / "probe_rs")
    ops = ops_of(probe_world, "launch", "A", SENTENCE.format(n=1), 1, False)
    scorer_op = next(i for i, op in enumerate(ops, 1) if ":child:scorer" in op)
    for name, needle, command in (("read_corruption_ledger_on_launch2", "phase_a/ledger/000001.json", "launch2"),
                                  ("read_corruption_completed_on_resume", "journal/000014.json", "resume")):
        world = base_world(template, workdir / name)
        if command == "launch2":
            try:
                run_command(world, FaultFs(kill_at=scorer_op, kill_after=False), "launch", "A",
                            SENTENCE.format(n=1), 1, False)
            except SimulatedKill:
                pass
            try:
                run_command(world, CorruptAfterFirstRead(needle), "launch", "A", SENTENCE.format(n=2), 2, False)
                outcome = "launched_attempt_2"
            except (L.Refusal, F.Unreadable) as exc:
                outcome = f"refused:{str(exc)[:60]}"
            final = drive_to_end(world)
            attempt, state = latest_attempt(world)
            record(name, outcome != "launched_attempt_2" and final == "completed" and attempt == 1
                   and not check_oracles(world), f"{outcome}; final {final}; latest {attempt}:{state}")
        else:
            run_command(world, F.RealFs(), "launch", "A", SENTENCE.format(n=1), 1, False)
            try:
                run_command(world, CorruptAfterFirstRead(needle), "resume", "A", SENTENCE.format(n=1))
            except (L.Refusal, F.Unreadable):
                pass
            final = drive_to_end(world)
            record(name, final == "completed" and latest_attempt(world) == (1, "completed")
                   and not check_oracles(world), final)

    # A-O7 for ledgers: an identical .torn twin of a committed ledger entry is quarantined
    world = base_world(template, workdir / "ledger_twin")
    run_command(world, F.RealFs(), "launch", "A", SENTENCE.format(n=1), 1, False)
    ledger = world.D / "phase_a" / "ledger"
    (ledger / "000001.torn").write_bytes((ledger / "000001.json").read_bytes())
    final = drive_to_end(world)
    record("ledger_twin", final == "completed" and not (ledger / "000001.torn").exists()
           and not check_oracles(world), final)

    # A-F3 / exp1: consumption-only 000001 damaged, declared, then more commands must still work
    world = base_world(template, workdir / "declare_then_more")
    ops = ops_of(base_world(template, workdir / "probe_d"), "launch", "A", SENTENCE.format(n=1), 1, False)
    after_consumption = next(i for i, op in enumerate(ops, 1) if ":rename:" in op and "000002.json" in op)
    try:
        run_command(world, FaultFs(kill_at=after_consumption, kill_after=False), "launch", "A",
                    SENTENCE.format(n=1), 1, False)
    except SimulatedKill:
        pass
    run_dir = next((world.D / "phase_a" / "runs").iterdir())
    (run_dir / "journal" / "000001.json").write_bytes(b"damaged")
    final = drive_to_end(world)
    record("declare_then_more_commands", final == "completed" and not check_oracles(world), final)

    # A-F4 / exp2: attempt 2's declaration killed before its commit; the closure is still committed later
    world = base_world(template, workdir / "pending_closure")
    for attempt in (1, 2):
        sentence = SENTENCE.format(n=1) if attempt == 1 else DISTINCT.format(n=2, m=1)
        index = kill_index(world, "launch", ("A", sentence, attempt, attempt == 2),
                           lambda op: ":rename:" in op and "journal" in op and "000002.json" in op)
        try:
            run_command(world, FaultFs(kill_at=index, kill_after=False), "launch", "A", sentence, attempt,
                        attempt == 2)
        except SimulatedKill:
            pass
        run_dir = sorted((world.D / "phase_a" / "runs").iterdir(), key=lambda p: p.stat().st_mtime)[-1]
        (run_dir / "journal" / "000001.json").write_bytes(b"damaged")
        if attempt == 1:
            run_command(world, F.RealFs(), "declare", "A", 1)
        else:
            index = kill_index(world, "declare", ("A", 2),
                               lambda op: ":child:" in op, after=lambda op: ":rename:" in op and "ledger" in op)
            try:
                run_command(world, FaultFs(kill_at=index, kill_after=False), "declare", "A", 2)
            except SimulatedKill:
                pass
    run_command(world, F.RealFs(), "launch", "A", DISTINCT.format(n=3, m=2), 3, True)
    lc = world.lifecycle(F.RealFs())
    lc.open()
    try:
        tree = lc.tree()
        closure_entries = [e for e in lc.ledger("A").entries if e["kind"] == "attempt_closed_at_ledger"]
        all_committed = all(f"phase_a/ledger/{J.entry_name(e['entry'])}" in tree for e in closure_entries)
    finally:
        lc.close()
    record("pending_ledger_closure", all_committed and len(closure_entries) == 2
           and not check_oracles(world), f"closures {len(closure_entries)} committed {all_committed}")

    # A-O9: the refs/heads flush fails after update-ref; the next command flushes before trusting the ref
    world = base_world(template, workdir / "refs_flush")
    ops = ops_of(base_world(template, workdir / "probe_r"), "launch", "A", SENTENCE.format(n=1), 1, False)
    refs_flush = next(i for i, op in enumerate(ops, 1) if ":flush_dir:" in op and "refs" in op and "heads" in op)
    try:
        run_command(world, FaultFs(flush_fail_at={refs_flush}), "launch", "A", SENTENCE.format(n=1), 1, False)
    except (F.NotDurable, OSError, L.Refusal):
        pass
    final = drive_to_end(world)
    record("refs_flush_failure", final == "completed" and not check_oracles(world), final)

    # C-O3/C-O4: the worker reports a drifted module; the attempt closes truthfully as infrastructure
    world = base_world(template, workdir / "module_drift", worker_failures={"module_drift"})
    out = run_command(world, F.RealFs(), "launch", "A", SENTENCE.format(n=1), 1, False)
    record("worker_module_drift", out["state"] == "closed" and out["reason"] == "infrastructure_failure"
           and not check_oracles(world), str(out))

    # abandon: refused while preflight passes; allowed on a persistent receipt mismatch
    world = base_world(template, workdir / "abandon")
    ops = ops_of(base_world(template, workdir / "probe_ab"), "launch", "A", SENTENCE.format(n=1), 1, False)
    mid = next(i for i, op in enumerate(ops, 1) if ":rename:" in op and "000003.json" in op)
    try:
        run_command(world, FaultFs(kill_at=mid), "launch", "A", SENTENCE.format(n=1), 1, False)
    except SimulatedKill:
        pass
    try:
        run_command(world, F.RealFs(), "abandon", "A", 1)
        refused = False
    except L.Refusal:
        refused = True
    lc = world.lifecycle(F.RealFs())
    lc.rt.verify_receipts = lambda receipts: {"valid": False, "reasons": ["provider_version_mismatch:x"]}
    lc.open()
    try:
        out = lc.command_abandon("A", 1)
    finally:
        lc.close()
    record("abandon_only_on_failing_preflight", refused and out["state"] == "closed"
           and not check_oracles(world), str(out))

    # a kill at every operation of setup leaves either no data root or an intact one
    failures = []
    setup_ops = FaultFs()
    target = workdir / "setup_probe"
    if target.exists():
        L._remove_tree(target)
    target.mkdir(parents=True)
    run_command(World(target), setup_ops, "setup")
    for index in range(1, setup_ops.count + 1):
        target = workdir / "setup_kill"
        if target.exists():
            L._remove_tree(target)
        target.mkdir(parents=True)
        try:
            run_command(World(target), FaultFs(kill_at=index), "setup")
        except SimulatedKill:
            pass
        world = World(target)
        if drive_to_end_with_setup(world) != "completed":
            failures.append(index)
    record("kill_during_setup", not failures, str(failures[:10]))
    return results


def kill_index(world: World, command: str, args: tuple, match, after=None) -> int:
    """Probe a copy of the world's current state to find the operation index of the first matching operation
    (optionally after the last operation matching ``after``) for this command."""
    shadow = workdir_shadow(world)
    probe = FaultFs()
    run_command(shadow, probe, command, *args)
    start = 0
    if after is not None:
        start = max(i for i, op in enumerate(probe.ops, 1) if after(op))
    return next(i for i, op in enumerate(probe.ops, 1) if i > start and match(op))


def workdir_shadow(world: World) -> World:
    shadow = world.root.parent / (world.root.name + "_shadow")
    if shadow.exists():
        L._remove_tree(shadow)
    shutil.copytree(world.root, shadow)
    return World(shadow)


def drive_to_end_with_setup(world: World) -> str:
    try:
        run_command(world, F.RealFs(), "setup")
    except Exception as exc:  # noqa: BLE001
        return f"setup_failed:{type(exc).__name__}:{exc}"
    return drive_to_end(world)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", default=str(Path(os.environ.get("TEMP", "/tmp")) / "g_route4_campaign"))
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--only", default="")
    args = parser.parse_args(argv)
    P.pin_recursion_limit()
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    template, _ = reference_outcome(workdir)
    stride = 7 if args.quick else args.stride
    report = []
    started = time.time()
    for label, kwargs in (("clean_kills", {}),
                          ("clean_power_loss", {"power": True}),
                          ("transport_failure_kills", {"failures": {small_schedule()[0]["A"][2]["call_id"]: "error"}}),
                          ("sandbox_failure_kills", {"worker_failures": {small_schedule()[0]["A"][1]["fixture_id"]}})):
        if args.only and label not in args.only.split(","):
            continue
        result = kill_campaign(workdir, template, stride=stride, label=label, **kwargs)
        report.append(result)
        print(json.dumps({k: v for k, v in result.items() if k != "problems"}), "problems:", len(result["problems"]))
        for problem in result["problems"][:5]:
            print("   ", problem)
    for label, run in (("torn_entries", lambda: damage_campaign(workdir, template, stride=1 if stride == 1 else 3)),
                       ("torn_ledger", lambda: damage_campaign(workdir, template, ledger=True, label="torn_ledger")),
                       ("flush_failures", lambda: flush_failure_campaign(workdir, template,
                                                                         stride=1 if stride == 1 else 5)),
                       ("environment", lambda: environment_cases(workdir, template)),
                       ("gap_seeds", lambda: gap_cases(workdir, template)),
                       ("review_seeds", lambda: review_seeds(workdir, template)),
                       ("resumed_interrupts", lambda: resumed_interrupt_cases(workdir, template)),
                       ("power_loss_subsets", lambda: kill_campaign(workdir, template, power=True, subset_seed=7,
                                                                    stride=stride, label="power_loss_subsets"))):
        if args.only and label not in args.only.split(","):
            continue
        result = run()
        report.append(result)
        print(json.dumps({k: v for k, v in result.items() if k != "problems"}), "problems:", len(result["problems"]))
        for problem in result["problems"][:5]:
            print("   ", problem)
    print("seconds", round(time.time() - started, 1))
    (workdir / "campaign_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if all(not r["problems"] for r in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
