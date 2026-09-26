from __future__ import annotations

"""G-ROUTE3 R7 certification crash campaign (design §19, ruling 3).

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

    python tools/g_route3_campaign.py [--quick]
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

import g_route3_fs as F  # noqa: E402
import g_route3_journal as J  # noqa: E402
import g_route3_lifecycle as L  # noqa: E402
import g_route3_platform as P  # noqa: E402


class SimulatedKill(BaseException):
    """The process dies here. BaseException, so no ``except Exception`` in the lifecycle can swallow it."""


class FaultFs(F.RealFs):
    """RealFs with numbered operations, kills, power-loss bookkeeping and injected faults."""

    def __init__(self, *, kill_at: int | None = None, kill_after: bool = True,
                 flush_fail_at: set[int] | None = None, log_temps: list | None = None) -> None:
        super().__init__(hook=self._hook, sleep=lambda seconds: None)
        self.count = 0
        self.kill_at = kill_at
        self.kill_after = kill_after
        self.flush_fail_at = flush_fail_at or set()
        self.pending: list[tuple[str, Any]] = []        # unflushed operations, in order
        self.temp_unlinks = log_temps if log_temps is not None else []
        self.ops: list[str] = []

    def _hook(self, kind: str, detail: str) -> None:
        after = kind.startswith("after_")
        if not after:
            self.count += 1
            self.ops.append(f"{self.count}:{kind}:{detail[-80:]}")
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
    import g_route3_contract as C
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

    def __init__(self, data_root: Path, counts: dict, failures: Mapping[str, str] | None = None) -> None:
        self.data_root = data_root
        self.counts = counts
        self.failures = dict(failures or {})

    def attempt(self) -> int:
        ledger = self.data_root / "phase_a" / "ledger"
        consumed = 0
        for path in sorted(ledger.glob("*.json")) if ledger.is_dir() else []:
            envelope = J.parse_entry(path.read_bytes())
            if envelope and (envelope["kind"] == "attempt_consumed" or
                             (envelope["payload"] or {}).get("consumed_and_closed")):
                consumed += 1
        return consumed

    def __call__(self, call_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
        import base64
        import hashlib
        key = (self.attempt(), call_id)
        self.counts[key] = self.counts.get(key, 0) + 1
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
        return {"evidence": {"stub": digest}, "candidate_error": None, "infrastructure_failure": "",
                "module_digests": {}}
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

SENTENCE = "Authorize G-ROUTE3 phase A execution " + "f" * 64 + " attempt {n}"
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
        import g_route3_runner as R
        import g_route3_tests as T
        rt = L.Runtime(data_root=self.D, fs=fs, provider=StubProvider(self.D, self.counts, self.failures),
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


def drive_to_end(world: World, *, fault: Callable[[], FaultFs] | None = None, max_steps: int = 12) -> str:
    """Supported commands only: resume while possible; declare when an integrity failure needs it; launch the
    next attempt after a closure. Returns the final outcome label."""
    prefer_distinct = None
    for _ in range(max_steps):
        fs = fault() if fault else F.RealFs()
        try:
            attempt, state = latest_attempt(world)
            if attempt == 0:
                run_command(world, fs, "launch", "A", SENTENCE.format(n=1), 1, False)
            elif state == "completed":
                return "completed"
            elif state in ("closed", "closed_at_ledger"):
                distinct = (state == "closed_at_ledger") if prefer_distinct is None else prefer_distinct
                sentence = DISTINCT.format(n=attempt + 1, m=attempt) if distinct else SENTENCE.format(n=attempt + 1)
                if attempt >= 3:
                    return f"stopped_after_{attempt}_attempts"
                run_command(world, fs, "launch", "A", sentence, attempt + 1, distinct)
            elif state in ("integrity_failure", "absent"):
                run_command(world, fs, "declare", "A", attempt, None)
            else:
                run_command(world, fs, "resume", "A", SENTENCE.format(n=attempt))
        except SimulatedKill:
            if isinstance(fs, FaultFs):
                fs.power_loss() if getattr(fs, "lose_power", False) else None
            continue
        except L.PhaseBlocked as exc:
            return f"declared_refusal:{str(exc)[:80]}"
        except L.Refusal as exc:
            if "distinct_sentence_required" in str(exc):
                prefer_distinct = True
                continue
            if "distinct_sentence_not_permitted" in str(exc):
                prefer_distinct = False
                continue
            if "orphan_run_folder_exists" in str(exc):          # the operator's supported step
                clear = world.lifecycle(F.RealFs())
                clear.open()
                try:
                    for run_id in clear.orphan_runs("A"):
                        clear.close()
                        run_command(world, F.RealFs(), "clear_orphan", "A", run_id)
                        clear.open()
                finally:
                    clear.close()
                continue
            return f"refusal:{str(exc)[:120]}"
    return "no_fixpoint"


def check_oracles(world: World) -> list[str]:
    problems = []
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
    return template, {"ops": None}


def kill_campaign(workdir: Path, template: Path, *, failures=None, worker_failures=None, power: bool = False,
                  stride: int = 1, label: str = "kills") -> dict:
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
                    fs.power_loss()
            except L.Refusal:
                pass
            outcome = drive_to_end(world)
            results["cases"] += 1
            results["outcomes"][outcome.split(":")[0]] = results["outcomes"].get(outcome.split(":")[0], 0) + 1
            problems = check_oracles(world)
            persistent = bool(failures or worker_failures)
            permitted = outcome == "completed" or (persistent and outcome.startswith("stopped_after_"))
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
        outcome = drive_to_end(world)
        results["cases"] += 1
        key = outcome.split(":")[0]
        results["outcomes"][key] = results["outcomes"].get(key, 0) + 1
        problems = check_oracles(world)
        if key not in ("completed", "declared_refusal") or problems:
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

    import g_route3_platform as platform_module
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", default=str(Path(os.environ.get("TEMP", "/tmp")) / "g_route3_campaign"))
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
                       ("environment", lambda: environment_cases(workdir, template))):
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
