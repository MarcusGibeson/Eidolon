from __future__ import annotations

"""The G-ROUTE3 R7 run lifecycle: one journal per run, pure replay, recovery, boundary evidence (design R7).

Every command follows J8: take the lease, verify committed evidence (§13.4), replay the ledgers and runs,
recover to a fixpoint (§6), complete pending boundaries (§13.3), then act, running the drift check before any
derivation, sandbox run or call, and commit any boundary the action reached before returning.

This module never builds a provider. ``Runtime`` is assembled by the launcher (governed) or by tests
(synthetic, against a temporary data root only).
"""

from dataclasses import dataclass, field
import json
import re
import secrets
from pathlib import Path
from typing import Any, Callable, Mapping

import g_route3_evidence as ev
import g_route3_fs as fsmod
import g_route3_journal as J
import g_route3_platform as platform

CONTRACT_VERSION = "g-route3.lifecycle.r7"
PHASES = ("A", "B")
TABLE_NAME = "QUALIFICATION_TABLE.json"
AUDIT_NAME = "QUALIFICATION_AUDIT_DOCUMENT"
R7_MODULES = ("tools/g_route3_platform.py", "tools/g_route3_fs.py", "tools/g_route3_journal.py",
              "tools/g_route3_evidence.py", "tools/g_route3_lifecycle.py", "tools/g_route3_worker.py",
              "tools/g_route3_scorer.py", "tools/g_route3_launch.py")
WORKER_TIMEOUT_SECONDS = 180
SCORER_TIMEOUT_SECONDS = 1800
RECEIPT_WAIT_SECONDS = 600


class Refusal(RuntimeError):
    """The command refuses and changes nothing further. The message names the reason."""


class PhaseBlocked(Refusal):
    """A declared §1.3 exception: the phase waits for an operator ruling."""


class Interrupted(Exception):
    """Raised internally after an operator interrupt has been closed through the normal path."""


# ---------------------------------------------------------------- runtime

@dataclass
class Runtime:
    """Everything a command needs from the outside world. Built by the launcher or by tests."""
    data_root: Path
    fs: Any
    provider: Callable[[str, Mapping[str, Any]], Any]
    model_receipts: Callable[[], list]
    verify_receipts: Callable[[list], Mapping[str, Any]]
    freeze_binding: Callable[[], str]
    freeze_valid: Callable[[], bool]
    guarded_files: Callable[[str], dict]        # phase -> {relative path: sha256}
    worker: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    scorer: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    schedules: Mapping[str, list]
    fixtures: Mapping[str, Mapping[str, Any]]
    synthetic: bool
    endpoint: str
    interrupted: Callable[[], bool] = lambda: False
    frozen_artifact_digests: Callable[[], set] = lambda: set()
    table_on_main: Callable[[bytes], bool] = lambda table_bytes: True
    receipt_wait_seconds: float = RECEIPT_WAIT_SECONDS
    sleep: Callable[[float], None] = lambda seconds: None
    log: list = field(default_factory=list)


def guarded_digest(files: Mapping[str, str]) -> str:
    return J.digest(sorted(files.items()))


# ---------------------------------------------------------------- the lifecycle

class Lifecycle:
    def __init__(self, runtime: Runtime) -> None:
        self.rt = runtime
        self.fs = runtime.fs
        self.D = Path(runtime.data_root)
        self.repo = ev.EvidenceRepo(self.D / "evidence.git", self.fs)
        self.lease = platform.OsLease(self.D / ".lease")
        self.root_id = ""
        self.integrity_runs: dict[tuple[str, str], str] = {}
        self._tree: dict[str, str] | None = None
        self._specs: dict[str, J.RunSpec] = {}

    # ------------------------------------------------------------ paths
    def phase_dir(self, phase: str) -> Path:
        return self.D / f"phase_{phase.lower()}"

    def ledger_dir(self, phase: str) -> Path:
        return self.phase_dir(phase) / "ledger"

    def runs_dir(self, phase: str) -> Path:
        return self.phase_dir(phase) / "runs"

    def journal_dir(self, phase: str, run_id: str) -> Path:
        return self.runs_dir(phase) / run_id / "journal"

    def spec(self, phase: str) -> J.RunSpec:
        if phase not in self._specs:
            schedule = self.rt.schedules[phase]
            fixtures = self.rt.fixtures[phase]
            self._specs[phase] = J.RunSpec(
                call_ids=tuple(row["call_id"] for row in schedule),
                coding=frozenset(int(row["position"]) for row in schedule
                                 if fixtures[row["fixture_id"]]["validator_profile"] == "coding.v1"))
        return self._specs[phase]

    def log(self, message: str) -> None:
        self.rt.log.append(message)
        try:
            with open(self.D / "recovery.log", "a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except OSError:
            pass            # the log is non-authoritative (J10)

    # ------------------------------------------------------------ setup (§3.1) and opening (J8 steps 1-2)
    def setup_if_missing(self) -> None:
        """Atomic setup of D under the setup lock, only when D does not exist (or is empty)."""
        parent = self.D.parent
        self.fs.ensure_dir(parent)
        setup_lock = platform.OsLease(parent / (self.D.name + ".setup.lock"))
        setup_lock.acquire({"purpose": "setup"})
        try:
            names = self.fs.list_names(self.D)
            if names == []:
                self.fs._retrying(lambda: __import__("os").rmdir(self.D))
                names = None
            for leftover in self.fs.list_names(parent) or []:
                if leftover.startswith(self.D.name + ".setup-"):
                    _remove_tree(parent / leftover)
            if names is not None:
                return
            ev.EvidenceRepo.check_git_version(self.fs)
            build = parent / f"{self.D.name}.setup-{fsmod.token()}"
            self.fs.ensure_dir(build)
            root = {"experiment": "G-ROUTE3", "root_id": secrets.token_hex(16)}
            root_bytes = J.canonical_bytes(root) + b"\n"
            self.fs.publish(build / "root.json", root_bytes, temp_label="root")
            for sub in ("staging", "quarantine", "tables", "disclosure/phase_a", "disclosure/phase_b",
                        "phase_a/ledger", "phase_a/runs", "phase_a/orphans",
                        "phase_b/ledger", "phase_b/runs", "phase_b/orphans"):
                self.fs.ensure_dir(build / sub)
            ev.EvidenceRepo(build / "evidence.git", self.fs).initialize(root_bytes)
            _flush_tree(self.fs, build)
            self.fs._retrying(lambda: self.fs._rename_noreplace(build, self.D))
            self.fs.flush_dir(parent)
        finally:
            setup_lock.release()

    def open(self) -> None:
        """J8 steps 1-2: the lease, the repository health check, stale git locks, then verification."""
        if self.fs.list_names(self.D) is None:
            raise Refusal("data_root_missing")
        self.lease.acquire({"command": "g-route3-r7", "pid": __import__("os").getpid()})
        root_bytes = self.fs.read_bytes(self.D / "root.json")
        try:
            self.repo.check()
        except ev.EvidenceError as exc:
            raise PhaseBlocked(f"evidence_repository_not_intact:{exc}") from exc
        for removed in self.repo.remove_stale_locks():
            self.log(f"removed_stale_git_lock:{removed}")
        committed_root = self.repo.read_blob(self.tree()["root.json"])
        self.root_id = json.loads(committed_root.decode("utf-8"))["root_id"]
        del root_bytes                                   # root.json is verified with every committed item
        self.verify_evidence()

    def close(self) -> None:
        self.lease.release()

    def tree(self, refresh: bool = False) -> dict[str, str]:
        if self._tree is None or refresh:
            self._tree = self.repo.tree()
        return self._tree

    # ------------------------------------------------------------ reading
    def read_dir(self, directory: Path) -> tuple[dict[str, bytes], list[str]] | None:
        names = self.fs.list_names(directory)
        if names is None:
            return None
        files: dict[str, bytes] = {}
        extra: list[str] = []
        for name in names:
            if J.ENTRY_NAME.match(name):
                data = self.fs.read_bytes(directory / name)
                if data is None:
                    raise fsmod.Unreadable(f"entry_vanished:{directory / name}")
                files[name] = data
            else:
                extra.append(name)
        return files, extra

    def ledger(self, phase: str) -> J.LedgerReplay:
        got = self.read_dir(self.ledger_dir(phase))
        files, extra = got if got is not None else ({}, [])
        return J.replay_ledger(files, phase, self.root_id, extra_names=extra)

    def run(self, phase: str, run_id: str) -> tuple[J.Replay, dict[str, bytes]]:
        got = self.read_dir(self.journal_dir(phase, run_id))
        files, extra = got if got is not None else ({}, [])
        replay = J.replay_run(files, self.spec(phase), extra_names=extra)
        reason = self.integrity_runs.get((phase, run_id))
        if reason:
            replay = J.Replay(state="integrity_failure", reason=reason)
        return replay, files

    def run_ids(self, phase: str) -> list[str]:
        return [name for name in (self.fs.list_names(self.runs_dir(phase)) or [])
                if not name.startswith(".")]

    # ------------------------------------------------------------ verification (§13.4)
    def _disk_path(self, tree_path: str) -> Path | None:
        parts = tree_path.split("/")
        if tree_path == "root.json":
            return self.D / "root.json"
        if parts[0] in ("phase_a", "phase_b"):
            return self.D.joinpath(*parts)
        if parts[0] == "tables":
            return self.D / "tables" / "/".join(parts[1:])
        if parts[0] == "disclosure":
            return self.D / "disclosure" / f"phase_{parts[1].lower()}" / "/".join(parts[2:])
        if parts[0] == "quarantine":
            return self.D.joinpath(*parts)
        if parts[0] == "closures":
            phase, attempt_run = parts[1], parts[2]
            run_id = attempt_run.split("-", 1)[1]
            return self.runs_dir(phase).joinpath(run_id, *parts[3:])
        if parts[0] == "orphans":
            phase, run_id = parts[1], parts[2]
            live = self.runs_dir(phase).joinpath(run_id, *parts[3:])
            if (self.runs_dir(phase) / run_id).is_dir():
                return live
            for name in self.fs.list_names(self.phase_dir(phase) / "orphans") or []:
                if name.startswith(run_id + "-"):
                    return (self.phase_dir(phase) / "orphans" / name).joinpath(*parts[3:])
            return live
        return None

    def verify_evidence(self) -> None:
        """Compare every committed file with its disk copy, restoring or refusing as §13.4 says."""
        tree = self.tree(refresh=True)
        committed_runs: dict[tuple[str, str], set[str]] = {}
        for path in tree:
            parts = path.split("/")
            if len(parts) == 5 and parts[0] in ("phase_a", "phase_b") and parts[1] == "runs" and parts[3] == "journal":
                committed_runs.setdefault((parts[0][-1].upper(), parts[2]), set()).add(parts[4])
        terminal_runs = {key for key, names in committed_runs.items() if self._committed_terminal(key, names, tree)}
        quarantined: dict[str, bytes] = {}
        for path, blob in sorted(tree.items()):
            disk = self._disk_path(path)
            if disk is None:
                raise PhaseBlocked(f"unknown_committed_path:{path}")
            data = self.fs.read_bytes(disk)
            if data is not None and ev.blob_id(data) == blob:
                continue
            parts = path.split("/")
            is_journal = len(parts) == 5 and parts[1] == "runs" and parts[3] == "journal"
            name = parts[-1]
            if is_journal and name == "000001.json":
                key = (parts[0][-1].upper(), parts[2])
                if committed_runs.get(key) == {"000001.json"} and not self._ledger_closed(key):
                    self.integrity_runs[key] = "consumption_only_000001_missing_or_damaged"
                    continue
            sealed = bool(J.ENTRY_NAME.match(name)) and name.endswith(".json") and not path.startswith("quarantine/")
            if data is not None and sealed and J.parse_entry(data) is not None:
                raise PhaseBlocked(f"committed_entry_differs:{path}")
            if data is not None:
                quarantined.update(self._quarantine(disk))
            self._restore(disk, self.repo.read_blob(blob))
            self.log(f"restored_from_evidence:{path}")
        for (phase, run_id) in terminal_runs:
            listing = self.fs.list_names(self.journal_dir(phase, run_id)) or []
            names = committed_runs[(phase, run_id)]
            for extra in listing:
                if J.ENTRY_NAME.match(extra) and extra not in names:
                    raise PhaseBlocked(f"extra_entry_in_committed_terminal_journal:{phase}:{run_id}:{extra}")
        for (phase, run_id), names in committed_runs.items():
            listing = self.fs.list_names(self.journal_dir(phase, run_id)) or []
            for extra in listing:
                match = J.ENTRY_NAME.match(extra)
                if match and match.group(2) == "torn" and f"{match.group(1)}.json" in names:
                    quarantined.update(self._quarantine(self.journal_dir(phase, run_id) / extra))
        if quarantined:
            self._commit(quarantined, "restore boundary", include_ledgers=False)

    def _committed_terminal(self, key: tuple[str, str], names: set[str], tree: Mapping[str, str]) -> bool:
        phase, run_id = key
        highest = max((n for n in names if n.endswith(".json")), default=None)
        if highest is None:
            return False
        blob = tree[f"phase_{phase.lower()}/runs/{run_id}/journal/{highest}"]
        envelope = J.parse_entry(self.repo.read_blob(blob))
        return envelope is not None and envelope["kind"] in ("completed", "closed")

    def _ledger_closed(self, key: tuple[str, str]) -> bool:
        phase, run_id = key
        try:
            ledger = self.ledger(phase)
        except fsmod.Unreadable:
            return False
        attempt = next((a for a, row in ledger.consumed.items() if row.get("run_id") == run_id), None)
        return attempt is not None and attempt in ledger.closed_at_ledger

    def _quarantine(self, disk: Path) -> dict[str, bytes]:
        data = self.fs.read_bytes(disk)
        if data is None:
            return {}
        token = fsmod.token()
        relative = disk.resolve().relative_to(self.D.resolve()).as_posix()
        target = self.D / "quarantine" / token / relative
        self.fs.ensure_dir(target.parent)
        self.fs.rename(disk, target)
        return {f"quarantine/{token}/{relative}": data}

    def _restore(self, disk: Path, data: bytes) -> None:
        staging = self.D / "staging" / f".tmp-restore-{fsmod.token()}"
        self.fs._write_temp(staging, data)
        self.fs.ensure_dir(disk.parent)
        self.fs.rename(staging, disk)

    # ------------------------------------------------------------ committing (§13.1)
    def _uncommitted_ledger(self, phase: str) -> dict[str, bytes]:
        tree = self.tree()
        got = self.read_dir(self.ledger_dir(phase))
        out = {}
        for name, data in (got[0] if got else {}).items():
            path = f"phase_{phase.lower()}/ledger/{name}"
            if path not in tree:
                out[path] = data
        return out

    def _commit(self, additions: dict[str, bytes], message: str, *, include_ledgers: bool = True,
                disclosure_phase: str | None = None) -> str:
        additions = dict(additions)
        if include_ledgers:
            for phase in PHASES:
                additions.update(self._uncommitted_ledger(phase))
            tree = self.tree()
            for directory, _dirs, files in __import__("os").walk(self.D / "quarantine"):
                for name in files:
                    disk = Path(directory) / name
                    path = disk.resolve().relative_to(self.D.resolve()).as_posix()
                    if path not in tree:
                        data = self.fs.read_bytes(disk)
                        if data is not None:
                            additions[path] = data
        if disclosure_phase is not None:
            path, record = self._disclosure_record(disclosure_phase)
            additions[path] = record
        head = self.repo.commit(additions, message, staging=self.D / "staging")
        self.tree(refresh=True)
        if disclosure_phase is not None:
            disk = self._disk_path(path)
            existing = self.fs.read_bytes(disk)
            if existing != record:
                if existing is not None:
                    self._quarantine(disk)
                self._restore(disk, record)
        return head

    # ------------------------------------------------------------ disclosure records (§12, gold-free)
    def attempts(self, phase: str) -> list[dict[str, Any]]:
        """Gold-free disclosure rows for every consumed attempt of a phase, under every freeze."""
        ledger = self.ledger(phase)
        rows = []
        for attempt, consumed in sorted(ledger.consumed.items()):
            run_id = str(consumed.get("run_id"))
            row = {"attempt": attempt, "run_id": run_id, "freeze_binding": consumed.get("freeze_binding"),
                   "operator_confirmation": consumed.get("sentence")}
            closure = ledger.closed_at_ledger.get(attempt)
            replay, _ = self.run(phase, run_id)
            counts = _counts(replay)
            if closure is not None:
                row.update(outcome="closed_at_ledger", reason=closure.get("reason"),
                           counts="unknown", lower_bounds=counts)
            elif replay.state == "completed":
                row.update(outcome="completed", reason="completed_and_scored", counts=counts)
            elif replay.state == "closed":
                row.update(outcome="closed", reason=replay.last["payload"]["reason"], counts=counts)
            else:
                row.update(outcome="in_progress" if replay.state != "integrity_failure" else "integrity_failure",
                           reason=replay.state, counts=counts)
            row["optional_stopping_cannot_be_excluded"] = row["outcome"] != "completed"
            row["raw_output_sha256"] = {str(e["payload"]["position"]): e["payload"].get("raw_output_sha256")
                                        for e in replay.entries if e["kind"] == "call_recorded"}
            rows.append(row)
        identity: dict[str, dict[str, Any]] = {}
        for row in rows:
            for position, sha in row["raw_output_sha256"].items():
                identity.setdefault(position, {})[str(row["attempt"])] = sha
        for row in rows:
            row["cross_attempt_identity"] = {
                position: len({sha for sha in by_attempt.values()}) == 1
                for position, by_attempt in identity.items()
                if position in row["raw_output_sha256"] and len(by_attempt) > 1}
        return rows

    def _disclosure_record(self, phase: str) -> tuple[str, bytes]:
        tree = self.tree()
        prefix = f"disclosure/{phase}/"
        sequence = 1 + sum(1 for path in tree if path.startswith(prefix))
        orphans = sorted({path.split("/")[2] for path in tree if path.startswith(f"orphans/{phase}/")})
        record = {"phase": phase, "sequence": sequence, "attempts": self.attempts(phase),
                  "orphans_cleared": orphans, "evidence_head_before": self.repo.head(),
                  "contains_gold": False}
        return f"{prefix}{sequence:06d}.json", J.canonical_bytes(J.safe_value(record)) + b"\n"

    # ------------------------------------------------------------ publishing entries
    def _publish_run_entry(self, phase: str, run_id: str, replay: J.Replay, kind: str,
                           payload: Mapping[str, Any], *, acknowledging: bool = False,
                           previous_override: str | None = None) -> dict[str, Any]:
        directory = self.journal_dir(phase, run_id)
        numbers = [e["entry"] for e in replay.entries] + [n for n, _ in replay.tear]
        number = max(numbers, default=0) + 1
        previous = previous_override if previous_override is not None else replay.head
        acks = [{"entry": n, "sha256": sha} for n, sha in replay.tear] if acknowledging else []
        named = {row["name"] for e in replay.entries for row in e["orphans"]}
        orphans = []
        for name in sorted(set(replay.orphan_temps) - named):
            data = self.fs.read_bytes(directory / name)
            if data is None:
                raise fsmod.Unreadable(f"orphan_temp_vanished:{name}")
            orphans.append({"name": name, "sha256": J.sha256_bytes(data)})
        envelope, data = J.make_entry(number, kind, run_id, previous, payload, acknowledges=acks, orphans=orphans)
        self.fs.publish(directory / J.entry_name(number), data, temp_label=f"{number:06d}")
        return envelope

    def _publish_ledger_entry(self, phase: str, kind: str, payload: Mapping[str, Any], *,
                              acknowledging: bool = False) -> dict[str, Any]:
        ledger = self.ledger(phase)
        if ledger.state not in ("ok", "absent", "torn_pending"):
            raise PhaseBlocked(f"ledger_not_appendable:{ledger.state}:{ledger.reason}")
        numbers = [e["entry"] for e in ledger.entries] + [n for n, _ in ledger.tear]
        number = max(numbers, default=0) + 1
        previous = ledger.head or J.genesis_seal(phase, self.root_id)
        acks = [{"entry": n, "sha256": sha} for n, sha in ledger.tear] if acknowledging else []
        envelope, data = J.make_entry(number, kind, f"ledger-{phase}", previous, payload, acknowledges=acks)
        self.fs.publish(self.ledger_dir(phase) / J.entry_name(number), data, temp_label=f"{number:06d}")
        return envelope

    def _publish_closed(self, phase: str, run_id: str, replay: J.Replay, files: Mapping[str, bytes],
                        *, requested: str = "", acknowledging: bool = False, detail: str = "") -> None:
        if J.sealed_protective(files, self.spec(phase)):
            raise PhaseBlocked(f"protected_attempt_would_close:{phase}:{run_id}")
        reason = J.closed_reason_for(replay, self.spec(phase), acknowledging=acknowledging, requested=requested)
        payload = {"reason": reason}
        if detail:
            payload["exception"] = detail[:500]
        self._publish_run_entry(phase, run_id, replay, "closed", payload, acknowledging=acknowledging)

    # ------------------------------------------------------------ recovery (§6)
    def recover(self) -> None:
        for _ in range(10_000):
            if not self._recover_step():
                return
        raise PhaseBlocked("recovery_did_not_reach_a_fixpoint")

    def _recover_step(self) -> bool:
        for phase in PHASES:
            if self._recover_ledger(phase):
                return True
            ledger = self.ledger(phase)
            by_run = {row.get("run_id"): attempt for attempt, row in ledger.consumed.items()}
            for run_id in self.run_ids(phase):
                attempt = by_run.get(run_id)
                if attempt is not None and attempt in ledger.closed_at_ledger:
                    continue                                   # frozen
                if self._recover_run(phase, run_id, attempt):
                    return True
            for attempt, row in ledger.consumed.items():       # consumed runs whose folder is gone
                run_id = str(row.get("run_id"))
                if attempt in ledger.closed_at_ledger or run_id in self.run_ids(phase):
                    continue
                if not self._consumption_committed(phase, attempt, run_id):
                    self._ledger_close(phase, attempt, run_id, "durability_uncertain", "run_folder_absent")
                    return True
        return False

    def _recover_ledger(self, phase: str) -> bool:
        directory = self.ledger_dir(phase)
        ledger = self.ledger(phase)
        if ledger.state == "integrity_failure":
            raise PhaseBlocked(f"ledger_integrity_failure:{phase}:{ledger.reason}")
        if self._handle_pairs_and_temps(directory, ledger.pair_to_unlink, ledger.temps):
            return True
        if ledger.state == "torn_tail":
            return self._rename_torn(directory, ledger.torn_tail)
        if ledger.state == "torn_pending":
            claimed = ledger.head or J.genesis_seal(phase, self.root_id)
            consumed_runs = {row.get("run_id") for row in ledger.consumed.values()}
            claimant = None
            for run_id in self.run_ids(phase):
                if run_id in consumed_runs:
                    continue
                first = self.fs.read_bytes(self.journal_dir(phase, run_id) / "000001.json")
                envelope = J.parse_entry(first) if first else None
                if envelope and envelope["kind"] == "run_created" and \
                        envelope["payload"].get("claimed_ledger_head") == claimed:
                    claimant = (run_id, envelope)
            payload: dict[str, Any] = {}
            if claimant is not None:
                run_id, envelope = claimant
                payload["consumed_and_closed"] = {
                    "attempt": len(ledger.consumed) + 1, "run_id": run_id,
                    "run_created_sha256": envelope["record_sha256"],
                    "sentence_sha256": envelope["payload"].get("sentence_sha256"),
                    "freeze_binding": envelope["payload"].get("freeze_binding")}
            self._publish_ledger_entry(phase, "ledger_torn_acknowledged", payload, acknowledging=True)
            self.log(f"ledger_torn_acknowledged:{phase}")
            return True
        return False

    def _handle_pairs_and_temps(self, directory: Path, pairs: list[int], temps: list[str]) -> bool:
        for number in pairs:
            self.fs.unlink(directory / J.entry_name(number))
            return True
        for name in temps:
            data = self.fs.read_bytes(directory / name)
            if data is None:
                continue
            number = int(J.TEMP_NAME.match(name).group(1))
            published = self.fs.read_bytes(directory / J.entry_name(number))
            if published == data:
                self.fs.unlink(directory / name)
            else:
                self.fs.rename(directory / name, directory / f".orphan-tmp-{number:06d}-{fsmod.token()}")
            return True
        return False

    def _rename_torn(self, directory: Path, number: int) -> bool:
        path = directory / J.entry_name(number)
        again = self.fs.read_bytes(path)
        if again is not None and J.parse_entry(again) is not None:
            raise Refusal(f"transient_read_disagreement:{path}")     # A-O3: re-read before renaming
        torn = directory / J.entry_name(number, torn=True)
        if self.fs.read_bytes(torn) == again:
            self.fs.unlink(path)
        else:
            self.fs.rename(path, torn)
        return True

    def _consumption_committed(self, phase: str, attempt: int, run_id: str) -> bool:
        tree = self.tree()
        return f"phase_{phase.lower()}/runs/{run_id}/journal/000001.json" in tree and any(
            path.startswith(f"phase_{phase.lower()}/ledger/") for path in tree) and \
            self._ledger_entry_committed(phase, attempt)

    def _ledger_entry_committed(self, phase: str, attempt: int) -> bool:
        ledger = self.ledger(phase)
        tree = self.tree()
        for envelope in ledger.entries:
            if envelope["kind"] == "attempt_consumed" and envelope["payload"].get("attempt") == attempt:
                return f"phase_{phase.lower()}/ledger/{J.entry_name(envelope['entry'])}" in tree
        return False

    def _recover_run(self, phase: str, run_id: str, attempt: int | None) -> bool:
        directory = self.journal_dir(phase, run_id)
        replay, files = self.run(phase, run_id)
        if replay.state == "integrity_failure":
            return False
        if self._handle_pairs_and_temps(directory, replay.pair_to_unlink, replay.temps):
            return True
        state = replay.state
        if attempt is None:
            return False                                       # an orphan: only --clear-orphan acts on it
        if state == "torn_tail":
            return self._rename_torn(directory, replay.torn_tail)
        if state == "torn_pending":
            if replay.predicted_class in ("provider", "closure"):
                self._publish_closed(phase, run_id, replay, files, acknowledging=True)
                return True
            if replay.predicted_class == "special":
                if not self._consumption_committed(phase, attempt, run_id):
                    self._ledger_close(phase, attempt, run_id, "durability_uncertain", "torn_run_created")
                    return True
                self.integrity_runs[(phase, run_id)] = "torn_run_created_after_consumption"
                return False
            return False                                       # derived: left for §7
        if state == "absent":
            if not self._consumption_committed(phase, attempt, run_id):
                self._ledger_close(phase, attempt, run_id, "durability_uncertain", "journal_absent")
                return True
            self.integrity_runs[(phase, run_id)] = "journal_missing"
            return False
        if state == "in_doubt":
            self._publish_closed(phase, run_id, replay, files)
            return True
        if state == "execution_in_doubt":
            self._publish_run_entry(phase, run_id, replay, "execution_recorded",
                                    {"position": replay.position, "evidence": None, "candidate_error": None,
                                     "infrastructure_failure": "execution_interrupted", "module_digests": {}})
            return True
        if state == "faulted":
            self._publish_closed(phase, run_id, replay, files)
            return True
        return False

    def _ledger_close(self, phase: str, attempt: int, run_id: str, reason: str, observed: str) -> None:
        """Automatic (no call possible) or declared ledger-level closure with its snapshot and commit."""
        snapshot = self._snapshot(phase, run_id)
        self._publish_ledger_entry(phase, "attempt_closed_at_ledger", {
            "attempt": attempt, "run_id": run_id, "reason": reason, "observed": observed,
            "snapshot_path": f"closures/{phase}/{attempt}-{run_id}/",
            "snapshot_digest": J.digest(sorted((path, ev.blob_id(data)) for path, data in snapshot.items()))})
        additions = {f"closures/{phase}/{attempt}-{run_id}/{path}": data for path, data in snapshot.items()}
        self._commit(additions, f"ledger closure {phase} attempt {attempt}", disclosure_phase=phase)

    def _snapshot(self, phase: str, run_id: str) -> dict[str, bytes]:
        """The run folder's files as found (relative path -> bytes). Unreadable files refuse (§1.3)."""
        base = self.runs_dir(phase) / run_id
        out: dict[str, bytes] = {}
        if not base.is_dir():
            return out
        for directory, _dirs, files in __import__("os").walk(base):
            for name in files:
                path = Path(directory) / name
                data = self.fs.read_bytes(path)
                if data is None:
                    continue
                out[path.relative_to(base).as_posix()] = data
        return out

    # ------------------------------------------------------------ pending boundaries (§13.3)
    def sync(self) -> None:
        for phase in PHASES:
            ledger = self.ledger(phase)
            tree = self.tree()
            for attempt, row in sorted(ledger.consumed.items()):
                run_id = str(row.get("run_id"))
                if attempt in ledger.closed_at_ledger:
                    closure = ledger.closed_at_ledger[attempt]
                    prefix = f"closures/{phase}/{attempt}-{run_id}/"
                    ledger_uncommitted = self._uncommitted_ledger(phase)
                    if ledger_uncommitted or (closure.get("via") == "ledger_torn_acknowledged"
                                              and not any(p.startswith(prefix) for p in tree)):
                        snapshot = self._snapshot(phase, run_id)
                        self._commit({prefix + p: d for p, d in snapshot.items()},
                                     f"ledger closure {phase} attempt {attempt}", disclosure_phase=phase)
                    continue
                replay, files = self.run(phase, run_id)
                if replay.state in ("integrity_failure", "absent", "torn_tail"):
                    continue
                if replay.state == "torn_pending" and replay.predicted_class == "special":
                    continue
                journal = f"phase_{phase.lower()}/runs/{run_id}/journal/"
                if not self._consumption_committed(phase, attempt, run_id):
                    self._commit({journal + "000001.json": files["000001.json"]},
                                 f"consumption {phase} attempt {attempt}", disclosure_phase=phase)
                    tree = self.tree()
                later = replay.state in ("collected", "scoring_interrupted", "scored", "completed", "closed") or \
                    (replay.state == "torn_pending" and replay.predicted_class == "derived")
                if later:
                    missing = {journal + name: data for name, data in files.items() if journal + name not in tree}
                    got = self.read_dir(self.journal_dir(phase, run_id))
                    extras = {journal + name: self.fs.read_bytes(self.journal_dir(phase, run_id) / name)
                              for name in (got[1] if got else []) if J.ORPHAN_TEMP.match(name)
                              and journal + name not in tree}
                    missing.update({k: v for k, v in extras.items() if v is not None})
                    if missing:
                        label = "terminal" if replay.state in ("completed", "closed") else "collection"
                        self._commit(missing, f"{label} {phase} attempt {attempt}", disclosure_phase=phase)
                        tree = self.tree()
            if self._uncommitted_ledger(phase):
                self._commit({}, f"ledger {phase}", disclosure_phase=phase)

    # ------------------------------------------------------------ the J8 prelude
    def prelude(self) -> None:
        self.recover()
        self.sync()

    # ------------------------------------------------------------ guard, receipts, sentences
    def guard(self, phase: str, run_created: Mapping[str, Any]) -> None:
        files = self.rt.guarded_files(phase)
        if guarded_digest(files) != run_created.get("guarded_digest"):
            recorded = run_created.get("guarded_files") or {}
            changed = sorted(path for path in set(files) | set(recorded) if files.get(path) != recorded.get(path))
            raise Refusal("guarded_dependency_drift:" + ",".join(changed))

    def receipts_or_refuse(self) -> list:
        receipts = self.rt.model_receipts()
        check = self.rt.verify_receipts(receipts)
        if not check.get("valid"):
            raise Refusal("model_receipts_invalid:" + ",".join(check.get("reasons") or []))
        return receipts

    # ------------------------------------------------------------ attempt policy (§9.3)
    def attempt_table(self, phase: str) -> list[tuple[int, str, J.Replay, bool]]:
        ledger = self.ledger(phase)
        rows = []
        for attempt, row in sorted(ledger.consumed.items()):
            run_id = str(row.get("run_id"))
            replay, _ = self.run(phase, run_id)
            rows.append((attempt, run_id, replay, attempt in ledger.closed_at_ledger))
        return rows

    def committed_completed(self, phase: str, run_id: str) -> bool:
        tree = self.tree()
        prefix = f"phase_{phase.lower()}/runs/{run_id}/journal/"
        names = sorted(path for path in tree if path.startswith(prefix) and path.endswith(".json"))
        if not names:
            return False
        envelope = J.parse_entry(self.repo.read_blob(tree[names[-1]]))
        return envelope is not None and envelope["kind"] == "completed"

    def protected(self, phase: str, run_id: str, table_attempt_run: str | None = None) -> bool:
        if self.committed_completed(phase, run_id):
            return True
        _, files = self.run(phase, run_id)
        if J.sealed_protective(files, self.spec(phase)):
            return True
        tree = self.tree()
        paths = {path: blob for path, blob in tree.items()
                 if path.startswith(f"phase_{phase.lower()}/runs/{run_id}/journal/")}
        contents = self.repo.read_blobs(paths.values())
        committed = {path.rsplit("/", 1)[1]: contents[blob] for path, blob in paths.items()}
        if J.sealed_protective(committed, self.spec(phase)):
            return True
        return phase == "A" and table_attempt_run == run_id

    def orphan_runs(self, phase: str) -> list[str]:
        consumed = {str(row.get("run_id")) for row in self.ledger(phase).consumed.values()}
        return [run_id for run_id in self.run_ids(phase) if run_id not in consumed]

    def check_launch_policy(self, phase: str, attempt: int, distinct: bool) -> None:
        rows = self.attempt_table(phase)
        if attempt != len(rows) + 1:
            raise Refusal(f"attempt_number_must_be_{len(rows) + 1}")
        if self.orphan_runs(phase):
            raise Refusal("orphan_run_folder_exists_clear_it_first")
        for number, run_id, replay, ledger_closed in rows:
            if replay.state == "completed" or self.committed_completed(phase, run_id):
                raise Refusal(f"attempt_{number}_completed")
            if not ledger_closed and replay.state != "closed":
                raise Refusal(f"attempt_{number}_not_closed:{replay.state}")
        previous_needs_distinct = bool(rows) and rows[-1][3] and \
            self.ledger(phase).closed_at_ledger[rows[-1][0]].get("reason") in ("integrity_failure", "journal_missing")
        if previous_needs_distinct != distinct:
            raise Refusal("distinct_sentence_required" if previous_needs_distinct else "distinct_sentence_not_permitted")

    # ------------------------------------------------------------ collection (§8)
    def collect(self, phase: str, run_id: str) -> str:
        """Collect from the replayed state until collected, closed or interrupted. Returns the state."""
        spec = self.spec(phase)
        schedule = self.rt.schedules[phase]
        fixtures = self.rt.fixtures[phase]
        while True:
            replay, files = self.run(phase, run_id)
            state = replay.state
            run_created = replay.entries[0]["payload"] if replay.entries else {}
            if state in ("collected", "scoring_interrupted", "scored", "completed", "closed"):
                return state
            if state == "torn_pending" and replay.predicted_class == "derived":
                return state
            if state not in ("created", "collecting", "awaiting_execution"):
                raise Refusal(f"not_collectable:{state}")
            attempt = self._attempt_of(phase, run_id)
            if not self._consumption_committed(phase, attempt, run_id):
                raise Refusal("consumption_boundary_not_committed")
            self.guard(phase, run_created)
            if state == "awaiting_execution":
                self._execute(phase, run_id, replay, files)
                continue
            if self.rt.interrupted():
                self._publish_closed(phase, run_id, replay, files, requested="operator_interrupt")
                self._terminal_commit(phase)
                return "closed"
            position = replay.position + 1
            scheduled = schedule[position - 1]
            fixture = fixtures[scheduled["fixture_id"]]
            from g_route3_contract import request_body
            body = request_body(fixture, scheduled)
            started = self._publish_run_entry(phase, run_id, replay, "call_started", {
                "position": position, "call_id": scheduled["call_id"], "request_sha256": J.digest(body),
                "guarded_digest": run_created.get("guarded_digest")})
            payload = self._call(scheduled, body, position)
            replay2, _ = self.run(phase, run_id)
            self._publish_run_entry(phase, run_id, replay2, "call_recorded", payload)
            replay3, files3 = self.run(phase, run_id)
            if replay3.state == "faulted":
                self._publish_closed(phase, run_id, replay3, files3)
                self._terminal_commit(phase)
                return "closed"
            if replay3.state == "awaiting_execution":
                self._execute(phase, run_id, replay3, files3)
                replay3, files3 = self.run(phase, run_id)
                if replay3.state == "faulted":
                    self._publish_closed(phase, run_id, replay3, files3)
                    self._terminal_commit(phase)
                    return "closed"
            if replay3.state == "collected":
                self.sync()                                         # A-O10: collection boundary now
                return "collected"
            if self.rt.interrupted():
                self._publish_closed(phase, run_id, replay3, files3, requested="operator_interrupt")
                self._terminal_commit(phase)
                return "closed"
            del started

    def _attempt_of(self, phase: str, run_id: str) -> int:
        for attempt, row in self.ledger(phase).consumed.items():
            if row.get("run_id") == run_id:
                return attempt
        raise Refusal("run_has_no_ledger_entry")

    def _call(self, scheduled: Mapping[str, Any], body: Mapping[str, Any], position: int) -> dict[str, Any]:
        """One request (J14) and R6's provider-failure rule, carried verbatim (§8 step 4)."""
        base = {"position": position, "call_id": scheduled["call_id"], "requested_model": scheduled["model"]}
        try:
            result = self.rt.provider(scheduled["call_id"], body)
            result = result.as_dict() if hasattr(result, "as_dict") else dict(result)
        except Exception as exc:  # noqa: BLE001 - R6: provider_boundary_exception closes the attempt
            output_b64, output_sha = J.text_to_b64("")
            return {**base, "returned_model": "", "raw_body_b64": "", "raw_body_sha256": "",
                    "raw_output_b64": output_b64, "raw_output_sha256": output_sha, "output_field": "none",
                    "metrics": {}, "latency_seconds": 0.0, "provider_contacted": True, "error": "",
                    "transport_failure": f"provider_boundary_exception:{type(exc).__name__}:{exc}"[:500]}
        failure = str(result.get("error") or "")
        if result.get("returned_model") != scheduled["model"]:
            failure = failure or "provider_model_fallback_or_mismatch"
        output_b64, output_sha = J.text_to_b64(str(result.get("raw_output") or ""))
        return {**base, "returned_model": str(result.get("returned_model") or ""),
                "raw_body_b64": str(result.get("raw_body_b64") or ""),
                "raw_body_sha256": str(result.get("raw_body_sha256") or ""),
                "raw_output_b64": output_b64, "raw_output_sha256": output_sha,
                "output_field": str(result.get("output_field") or ""),
                "metrics": J.safe_value(dict(result.get("metrics") or {})),
                "latency_seconds": float(result.get("latency_seconds") or 0.0),
                "provider_contacted": bool(result.get("provider_contacted")), "error": str(result.get("error") or ""),
                "transport_failure": failure}

    def _execute(self, phase: str, run_id: str, replay: J.Replay, files: Mapping[str, bytes]) -> None:
        """Derive (holder), write-ahead execution_started, run the worker once, record (§8 step 5)."""
        from g_route3_worker import derive_executable
        recorded = replay.last
        position = int(recorded["payload"]["position"])
        scheduled = self.rt.schedules[phase][position - 1]
        fixture = self.rt.fixtures[phase][scheduled["fixture_id"]]
        executable_json = derive_executable(fixture, J.b64_to_text(recorded["payload"]["raw_output_b64"]))
        run_created = replay.entries[0]["payload"]
        self.guard(phase, run_created)
        self._publish_run_entry(phase, run_id, replay, "execution_started", {
            "position": position, "executable_json": executable_json,
            "executable_sha256": J.sha256_bytes(executable_json.encode("ascii"))})
        try:
            result = dict(self.rt.worker({"phase": phase, "fixture_id": scheduled["fixture_id"],
                                          "executable_json": executable_json}))
            infrastructure = str(result.get("infrastructure_failure") or "")
            recorded_files = run_created.get("guarded_files") or {}
            drifted = sorted(path for path, sha in (result.get("module_digests") or {}).items()
                             if recorded_files.get(path) != sha)
            if drifted:
                infrastructure = "sandbox_worker_failure:guarded_module_drift"
                result.setdefault("drifted_modules", drifted)
        except WorkerFailure as exc:
            result = {"evidence": None, "candidate_error": None}
            infrastructure = f"sandbox_worker_failure:{exc}"[:200]
        replay2, _ = self.run(phase, run_id)
        self._publish_run_entry(phase, run_id, replay2, "execution_recorded", {
            "position": position, "evidence": result.get("evidence"), "candidate_error": result.get("candidate_error"),
            "infrastructure_failure": infrastructure, "module_digests": result.get("module_digests") or {}})

    # ------------------------------------------------------------ scoring (§7, §4.3)
    def score(self, phase: str, run_id: str) -> None:
        while True:
            replay, files = self.run(phase, run_id)
            state = replay.state
            if state == "completed":
                self._terminal_commit(phase)
                self._project(phase, run_id, replay)
                return
            if state not in ("collected", "scoring_interrupted", "scored", "torn_pending"):
                raise Refusal(f"not_scorable:{state}")
            run_created = replay.entries[0]["payload"]
            self.guard(phase, run_created)
            target = replay.predicted if state == "torn_pending" else \
                {"collected": "scoring_started", "scoring_interrupted": "scored", "scored": "completed"}[state]
            payload = self._derive(phase, run_id, replay, target)
            self._check_against_committed(phase, run_id, target, payload)
            self._publish_run_entry(phase, run_id, replay, target, payload, acknowledging=bool(replay.tear))

    def _derive(self, phase: str, run_id: str, replay: J.Replay, kind: str) -> dict[str, Any]:
        facts = [e for e in replay.entries if e["kind"] not in J.DERIVED_KINDS]
        if kind == "scoring_started":
            ledger = self.ledger(phase)
            earlier = {}
            for attempt, row in sorted(ledger.consumed.items()):
                if row.get("run_id") == run_id:
                    break
                other, _ = self.run(phase, str(row.get("run_id")))
                earlier[str(attempt)] = other.head
            return {"fact_prefix_sha256": facts[-1]["record_sha256"],
                    "disclosure_inputs": {"ledger_head": ledger.head, "earlier_attempt_heads": earlier}}
        if kind == "scored":
            current = self._attempt_of(phase, run_id)
            rows = [row for row in self.attempts(phase) if row["attempt"] < current]
            rows.append({"attempt": current, "run_id": run_id, "outcome": "this_attempt"})
            result = self.rt.scorer({"mode": "score_run", "phase": phase, "run_id": run_id,
                                     "data_root": str(self.D), "attempts": rows})
            if result.get("error"):
                raise Refusal(f"scorer_failed:{result['error']}")
            return {"report": result["report"]}
        if kind == "completed":
            scored = next(e for e in reversed(replay.entries) if e["kind"] == "scored")
            first = replay.entries[0]
            return {"run_created_sha256": first["record_sha256"], "scored_sha256": scored["record_sha256"],
                    "freeze_binding": first["payload"].get("freeze_binding"),
                    "guarded_digest": first["payload"].get("guarded_digest"), "calls": self.spec(phase).calls}
        raise Refusal(f"not_derivable:{kind}")

    def _check_against_committed(self, phase: str, run_id: str, kind: str, payload: Mapping[str, Any]) -> None:
        tree = self.tree()
        prefix = f"phase_{phase.lower()}/runs/{run_id}/journal/"
        blobs = [blob for path, blob in tree.items() if path.startswith(prefix) and path.endswith(".json")]
        for data in self.repo.read_blobs(blobs).values():
            envelope = J.parse_entry(data)
            if envelope and envelope["kind"] == kind and envelope["payload"] != J.safe_value(dict(payload)):
                raise PhaseBlocked(f"rederived_{kind}_differs_from_committed")

    def _terminal_commit(self, phase: str) -> None:
        self.sync()

    def _project(self, phase: str, run_id: str, replay: J.Replay) -> None:
        scored = next(e for e in reversed(replay.entries) if e["kind"] == "scored")
        base = self.runs_dir(phase) / run_id
        self.fs.replace_projection(base / "score.json",
                                   J.canonical_bytes(J.safe_value(scored["payload"]["report"])) + b"\n")
        self.fs.replace_projection(base / "receipt.json",
                                   J.canonical_bytes(J.safe_value(replay.last["payload"])) + b"\n")

    # ------------------------------------------------------------ commands (§7)
    def command_launch(self, phase: str, sentence: str, attempt: int, distinct: bool,
                       phase_b: Mapping[str, Any] | None = None) -> dict[str, Any]:
        self.prelude()
        if not self.rt.freeze_valid():
            raise Refusal("execution_freeze_does_not_verify")
        self.check_launch_policy(phase, attempt, distinct)
        receipts = self.receipts_or_refuse()
        files = self.rt.guarded_files(phase)
        ledger = self.ledger(phase)
        if ledger.state not in ("ok", "absent"):
            raise Refusal(f"ledger_not_ready:{ledger.state}")
        claimed = ledger.head or J.genesis_seal(phase, self.root_id)
        run_id = f"groute3{phase.lower()}-{attempt:03d}-{fsmod.token()}"
        payload = {"phase": phase, "attempt": attempt, "sentence_sha256": J.sha256_bytes(sentence.encode("utf-8")),
                   "authorization_sha256": J.digest({"sentence": sentence, "phase": phase, "attempt": attempt}),
                   "claimed_ledger_head": claimed, "freeze_binding": self.rt.freeze_binding(),
                   "schedule_sha256": J.digest(self.rt.schedules[phase]), "guarded_digest": guarded_digest(files),
                   "guarded_files": files, "root_id": self.root_id, "synthetic": bool(self.rt.synthetic),
                   "endpoint": self.rt.endpoint, "model_receipts": receipts,
                   "transport_contract": "one POST /api/generate per call; max_retries=0; proxies stripped",
                   "gold_loaded_during_collection": False, **dict(phase_b or {})}
        directory = self.journal_dir(phase, run_id)
        self.fs.ensure_dir(directory)
        envelope, data = J.make_entry(1, "run_created", run_id, claimed, payload)
        self.fs.publish(directory / J.entry_name(1), data, temp_label="000001")
        self._publish_ledger_entry(phase, "attempt_consumed", {
            "attempt": attempt, "sentence": sentence, "freeze_binding": payload["freeze_binding"],
            "authorization_sha256": payload["authorization_sha256"], "run_id": run_id,
            "run_created_sha256": envelope["record_sha256"]})
        self.sync()                                                 # consumption boundary
        return self._run_to_end(phase, run_id)

    def _run_to_end(self, phase: str, run_id: str) -> dict[str, Any]:
        state = self.collect(phase, run_id)
        if state in ("collected", "scoring_interrupted", "scored", "torn_pending"):
            self.score(phase, run_id)
        replay, _ = self.run(phase, run_id)
        self.sync()
        return {"phase": phase, "run_id": run_id, "state": replay.state,
                "reason": replay.last["payload"].get("reason") if replay.state == "closed" else None}

    def command_resume(self, phase: str, sentence: str) -> dict[str, Any]:
        self.prelude()
        rows = self.attempt_table(phase)
        if not rows:
            raise Refusal("no_attempt_to_resume")
        attempt, run_id, replay, ledger_closed = rows[-1]
        consumed = self.ledger(phase).consumed[attempt]
        if consumed.get("sentence") != sentence:
            raise Refusal("resume_sentence_must_equal_the_consumed_sentence")
        if not self.rt.freeze_valid():
            raise Refusal("execution_freeze_does_not_verify")
        if ledger_closed or replay.state in ("closed", "integrity_failure", "absent"):
            raise Refusal(f"attempt_not_resumable:{replay.state}")
        if replay.state == "completed":
            self._project(phase, run_id, replay)
            return {"phase": phase, "run_id": run_id, "state": "completed"}
        if replay.state in ("created", "collecting", "awaiting_execution"):
            self.receipts_or_refuse()
        return self._run_to_end(phase, run_id)

    def command_abandon(self, phase: str, attempt: int) -> dict[str, Any]:
        self.prelude()
        rows = self.attempt_table(phase)
        if not rows or rows[-1][0] != attempt:
            raise Refusal("abandon_applies_to_the_latest_attempt_only")
        _, run_id, replay, ledger_closed = rows[-1]
        if ledger_closed or replay.state not in ("created", "collecting", "awaiting_execution"):
            raise Refusal(f"abandon_not_permitted_in:{replay.state}")
        failing = self._persistent_preflight_failures()
        if not failing:
            raise Refusal("preflight_passes_abandon_not_permitted")
        _, files = self.run(phase, run_id)
        self._publish_closed(phase, run_id, replay, files,
                             requested=J.ABANDON_PREFIX + ",".join(failing)[:300])
        self.sync()
        return {"phase": phase, "run_id": run_id, "state": "closed", "reason": "abandoned_preflight_failed"}

    def _persistent_preflight_failures(self) -> list[str]:
        waited = 0.0
        while True:
            try:
                receipts = self.rt.model_receipts()
                check = self.rt.verify_receipts(receipts)
                return [] if check.get("valid") else sorted(check.get("reasons") or ["receipts_invalid"])
            except Exception as exc:  # noqa: BLE001 - unreadable receipts only count after the bounded wait
                if waited >= self.rt.receipt_wait_seconds:
                    return [f"receipts_unreadable:{type(exc).__name__}"]
                self.rt.sleep(30.0)
                waited += 30.0

    def frozen_table_run(self) -> str | None:
        """The Phase A run a frozen table names, if a table is committed (§9.4 protection)."""
        if f"tables/{TABLE_NAME}" not in self.tree():
            return None
        data = self.fs.read_bytes(self.D / "tables" / TABLE_NAME) or b"{}"
        return (json.loads(data.decode("utf-8")).get("source") or {}).get("run_id")

    def command_declare(self, phase: str, attempt: int, table_run: str | None = None) -> dict[str, Any]:
        self.prelude()
        table_run = self.frozen_table_run()
        ledger = self.ledger(phase)
        if attempt not in ledger.consumed or attempt in ledger.closed_at_ledger:
            raise Refusal("declare_requires_a_consumed_open_attempt")
        run_id = str(ledger.consumed[attempt].get("run_id"))
        replay, _ = self.run(phase, run_id)
        if replay.state not in ("integrity_failure", "absent"):
            raise Refusal(f"declare_not_permitted_in:{replay.state}")
        if self.protected(phase, run_id, table_run):
            raise PhaseBlocked(f"protected_attempt_integrity_failure:{phase}:{attempt}")
        reason = "journal_missing" if replay.state == "absent" or \
            self.integrity_runs.get((phase, run_id)) == "journal_missing" else "integrity_failure"
        self._ledger_close(phase, attempt, run_id, reason, replay.reason or replay.state)
        return {"phase": phase, "attempt": attempt, "state": "closed_at_ledger", "reason": reason}

    def command_clear_orphan(self, phase: str, run_id: str) -> dict[str, Any]:
        self.prelude()
        if run_id not in self.orphan_runs(phase):
            raise Refusal("not_an_orphan_run")
        snapshot = self._snapshot(phase, run_id)
        for name, data in snapshot.items():
            envelope = J.parse_entry(data) if name.startswith("journal/") else None
            if envelope is not None and envelope["kind"] != "run_created":
                raise Refusal("orphan_has_entries_beyond_run_created")
            if name.startswith("journal/") and J.ENTRY_NAME.match(name.split("/")[-1]) and \
                    name.split("/")[-1] != "000001.json":
                raise Refusal("orphan_has_entries_beyond_run_created")
        self._commit({f"orphans/{phase}/{run_id}/{p}": d for p, d in snapshot.items()},
                     f"orphan {phase} {run_id}", disclosure_phase=phase)
        target = self.phase_dir(phase) / "orphans" / f"{run_id}-{fsmod.token()}"
        self.fs.rename(self.runs_dir(phase) / run_id, target)
        return {"phase": phase, "run_id": run_id, "moved_to": str(target)}

    # ------------------------------------------------------------ Phase A checks (§10 items 1-6) and the table
    def phase_a_checks(self, attempt: int) -> tuple[str, J.Replay]:
        """§10 items 1-6 for a Phase A attempt, shared by --freeze-table and Phase B. Returns (run_id, replay)."""
        import base64
        import hashlib
        from g_route1_provider import extract_output
        from g_route3_contract import request_body
        rows = self.attempt_table("A")
        named = [row for row in rows if row[0] == attempt]
        if not named:
            raise Refusal("phase_a_attempt_not_consumed")
        _, run_id, replay, ledger_closed = named[0]
        reasons = []
        if ledger_closed or replay.state != "completed" or not self.committed_completed("A", run_id):
            reasons.append("phase_a_attempt_not_completed_and_committed")
        for number, other_id, other, other_closed in rows:
            if number == attempt:
                continue
            if other.state == "completed" or self.committed_completed("A", other_id):
                reasons.append("phase_a_attempt_is_not_the_only_completed_attempt")
            elif not other_closed and other.state != "closed":
                reasons.append("phase_a_attempt_in_progress")
        if reasons:
            raise Refusal(",".join(sorted(set(reasons))))
        run_created = replay.entries[0]["payload"]
        consumed = self.ledger("A").consumed[attempt]
        if (run_created.get("attempt") != attempt
                or run_created.get("authorization_sha256") != consumed.get("authorization_sha256")
                or run_created.get("sentence_sha256") != J.sha256_bytes(str(consumed.get("sentence")).encode("utf-8"))
                or consumed.get("run_created_sha256") != replay.entries[0]["record_sha256"]):
            reasons.append("phase_a_run_created_differs_from_ledger")
        if run_created.get("synthetic") and not self.rt.synthetic:
            reasons.append("phase_a_was_synthetic")
        if run_created.get("freeze_binding") != self.rt.freeze_binding():
            reasons.append("phase_a_ran_under_a_different_freeze")
        if run_created.get("guarded_digest") != guarded_digest(self.rt.guarded_files("A")):
            reasons.append("phase_a_guarded_dependencies_differ_from_now")
        if any(e["payload"].get("guarded_digest") != run_created.get("guarded_digest")
               for e in replay.entries if e["kind"] == "call_started"):
            reasons.append("phase_a_call_guard_differs")
        if not self.rt.verify_receipts(list(run_created.get("model_receipts") or [])).get("valid"):
            reasons.append("phase_a_model_receipts_invalid")
        if run_created.get("endpoint") != self.rt.endpoint:
            reasons.append("phase_a_endpoint_not_the_fixed_endpoint")
        schedule, fixtures = self.rt.schedules["A"], self.rt.fixtures["A"]
        started = {int(e["payload"]["position"]): e["payload"] for e in replay.entries if e["kind"] == "call_started"}
        for entry in replay.entries:
            if entry["kind"] != "call_recorded":
                continue
            payload = entry["payload"]
            scheduled = schedule[int(payload["position"]) - 1]
            try:
                raw = base64.b64decode(payload["raw_body_b64"], validate=True)
                envelope = json.loads(raw.decode("utf-8"))
                if hashlib.sha256(raw).hexdigest() != payload["raw_body_sha256"]:
                    reasons.append("provider_raw_body_digest_mismatch")
                if envelope.get("model") != scheduled["model"] or payload.get("returned_model") != scheduled["model"]:
                    reasons.append("provider_model_differs_from_request")
                if extract_output(envelope)[0] != J.b64_to_text(payload["raw_output_b64"]):
                    reasons.append("raw_output_differs_from_provider_body")
                body = request_body(fixtures[scheduled["fixture_id"]], scheduled)
                if started[int(payload["position"])].get("request_sha256") != J.digest(body):
                    reasons.append("request_body_differs_from_schedule")
            except Exception:  # noqa: BLE001
                reasons.append("provider_evidence_unreadable")
        cells = self.rt.scorer({"mode": "phase_a_cells", "data_root": str(self.D), "run_id": run_id})
        scored = next(e for e in replay.entries if e["kind"] == "scored")
        if cells.get("error") or cells.get("cells") != scored["payload"]["report"].get("cells"):
            reasons.append("sealed_score_differs_from_call_records:" + str(cells.get("error") or ""))
        if reasons:
            raise Refusal(",".join(sorted(set(reasons))))
        return run_id, replay

    def command_freeze_table(self, attempt: int, binding: str, audit_document: Path, auditor: str,
                             verdict: str) -> dict[str, Any]:
        from g_route1_contract import canonical_digest
        self.prelude()
        if binding != self.rt.freeze_binding():
            raise Refusal("freeze_table_sentence_binding_not_in_force")
        tables = self.D / "tables"
        table_path, audit_copy = tables / TABLE_NAME, tables / AUDIT_NAME
        if f"tables/{TABLE_NAME}" in self.tree():
            data = self.fs.read_bytes(table_path) or b"{}"
            return {"table_sha256": json.loads(data.decode("utf-8")).get("table_sha256"), "state": "already_frozen"}
        run_id, replay = self.phase_a_checks(attempt)
        audit_bytes = Path(audit_document).read_bytes()
        if canonical_digest(audit_bytes) in self.rt.frozen_artifact_digests():
            raise Refusal("qualification_audit_document_is_a_frozen_artifact")
        run_created_seal = replay.entries[0]["record_sha256"]
        scored = next(e for e in replay.entries if e["kind"] == "scored")
        text = audit_bytes.decode("utf-8", "replace")
        for needle, label in ((run_id, "run_id"), (scored["record_sha256"], "scored_seal"),
                              (run_created_seal, "run_created_seal")):
            if needle not in text:
                raise Refusal(f"qualification_audit_document_does_not_name_{label}")
        existing_table = self.fs.read_bytes(table_path)
        intact_table = None
        if existing_table is not None:
            try:
                candidate = json.loads(existing_table.decode("utf-8"))
                body = {k: v for k, v in candidate.items() if k != "table_sha256"}
                from g_route3_contract import json_digest
                intact_table = candidate if json_digest(body) == candidate.get("table_sha256") else None
            except (ValueError, UnicodeDecodeError):
                intact_table = None
        existing_audit = self.fs.read_bytes(audit_copy)
        quarantined: dict[str, bytes] = {}
        if existing_audit is not None and existing_audit != audit_bytes:
            recorded = ((intact_table or {}).get("audit") or {}).get("document_sha256")
            if recorded is not None and recorded == canonical_digest(existing_audit):
                raise Refusal("a_different_audit_document_is_already_published")      # intact but different
            quarantined.update(self._quarantine(audit_copy))                          # torn (B-O7)
            existing_audit = None
        for name in self.fs.list_names(tables) or []:
            if name not in (TABLE_NAME, AUDIT_NAME):
                quarantined.update(self._quarantine(tables / name))
        if existing_audit is None:
            self.fs.publish(audit_copy, audit_bytes, temp_label="audit")
        terminal_path = f"phase_a/runs/{run_id}/journal/{J.entry_name(replay.last['entry'])}"
        terminal_commit = self.repo.commit_adding(terminal_path)
        built = self.rt.scorer({"mode": "build_table", "data_root": str(self.D), "run_id": run_id,
                                "cells": scored["payload"]["report"]["cells"],
                                "scored_sha256": scored["record_sha256"], "run_created_sha256": run_created_seal,
                                "terminal_commit": terminal_commit, "freeze_binding": self.rt.freeze_binding(),
                                "audit_copy": str(audit_copy), "auditor": auditor, "verdict": verdict,
                                "attempts": self.attempts("A")})
        if built.get("error"):
            raise Refusal(f"table_build_failed:{built['error']}")
        rendered = (json.dumps(built["table"], indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        if existing_table is not None and existing_table != rendered:
            if intact_table is not None:
                raise Refusal("a_different_table_is_already_published")
            quarantined.update(self._quarantine(table_path))
            existing_table = None
        if existing_table is None:
            self.fs.publish(table_path, rendered, temp_label="table")
        additions = {f"tables/{TABLE_NAME}": rendered, f"tables/{AUDIT_NAME}": audit_bytes, **quarantined}
        self._commit(additions, "table freeze")
        return {"table_sha256": built["table"]["table_sha256"], "state": "frozen", "phase_a_run_id": run_id}

    def phase_b_preconditions(self, phase_a_attempt: int) -> dict[str, Any]:
        """§10: every condition before Corpus B may be contacted. Refuses with the reasons."""
        from g_route1_contract import canonical_digest
        from g_route3_qualification import verify_table
        run_id, replay = self.phase_a_checks(phase_a_attempt)
        table_bytes = self.fs.read_bytes(self.D / "tables" / TABLE_NAME)
        tree = self.tree()
        if table_bytes is None or f"tables/{TABLE_NAME}" not in tree or f"tables/{AUDIT_NAME}" not in tree:
            raise Refusal("qualification_table_not_frozen")
        table = json.loads(table_bytes.decode("utf-8"))
        reasons = list(verify_table(table)["reasons"])
        binding = table.get("r7_binding") or {}
        scored = next(e for e in replay.entries if e["kind"] == "scored")
        if (table.get("source") or {}).get("run_id") != run_id:
            reasons.append("table_run_mismatch")
        if binding.get("run_created_sha256") != replay.entries[0]["record_sha256"] or \
                binding.get("scored_sha256") != scored["record_sha256"]:
            reasons.append("table_seals_differ_from_phase_a")
        if table.get("cells") != scored["payload"]["report"].get("cells"):
            reasons.append("table_cells_differ_from_scored")
        if (table.get("source") or {}).get("execution_freeze_binding") != self.rt.freeze_binding():
            reasons.append("table_bound_to_different_freeze")
        commit = binding.get("terminal_evidence_commit")
        terminal_path = f"phase_a/runs/{run_id}/journal/{J.entry_name(replay.last['entry'])}"
        if not commit or not self.repo.is_ancestor(commit) or self.repo.commit_adding(terminal_path) != commit:
            reasons.append("table_terminal_commit_invalid")
        audit = table.get("audit") or {}
        if audit.get("document_sha256") in self.rt.frozen_artifact_digests():
            reasons.append("qualification_audit_document_is_a_frozen_artifact")
        if canonical_digest(self.fs.read_bytes(self.D / "tables" / AUDIT_NAME) or b"") != audit.get("document_sha256"):
            reasons.append("audit_copy_differs_from_table")
        rows = self.rt.scorer({"mode": "attempt_rows", "phase": "A", "data_root": str(self.D),
                               "attempts": self.attempts("A")})
        if rows.get("error") or json.loads(json.dumps(J.safe_value(rows.get("rows")))) != \
                (table.get("source") or {}).get("phase_a_attempts"):
            reasons.append("table_attempt_disclosure_differs_from_now")
        if not self.rt.table_on_main(table_bytes):
            reasons.append("table_not_on_main_exactly_once")
        if reasons:
            raise Refusal(",".join(sorted(set(reasons))))
        return {"table_sha256": table["table_sha256"], "phase_a_run_id": run_id, "terminal_commit": commit}

    def command_launch_b(self, sentence: str, attempt: int, distinct: bool, table_digest: str,
                         phase_a_attempt: int) -> dict[str, Any]:
        self.prelude()
        pre = self.phase_b_preconditions(phase_a_attempt)
        if pre["table_sha256"] != table_digest:
            raise Refusal("sentence_table_digest_differs_from_frozen_table")
        return self.command_launch("B", sentence, attempt, distinct, phase_b={
            "table_sha256": pre["table_sha256"], "phase_a_run_id": pre["phase_a_run_id"],
            "phase_a_terminal_commit": pre["terminal_commit"]})

    def command_export(self, destination: Path) -> dict[str, Any]:
        """Read-only (A-O6): lease and controlled git, no verification, recovery or commits."""
        self.lease.acquire({"command": "export"})
        try:
            self.repo.git("bundle", "create", str(destination), ev.REF)
            return {"bundle": str(destination), "head": self.repo.head()}
        finally:
            self.lease.release()


class WorkerFailure(RuntimeError):
    """The worker process itself failed (died, timed out, console control or signal): §8 worker-level failure."""


TOOLS = Path(__file__).resolve().parent
CONSOLE_CONTROL_EXITS = {0xC000013A, -1073741510}


def standard_guarded_files(data_root: Path, phase: str) -> dict[str, str]:
    """{relative path: sha256} of every guarded dependency: R6's list, the R7 modules, the execution freeze and,
    in Phase B, the frozen table in D (B-O8)."""
    from g_route1_contract import ROOT, canonical_digest
    from g_route3_contract import EXECUTION_FREEZE_PATH
    from g_route3_runner import GUARDED_PATHS
    files = {}
    for relative in dict.fromkeys((*GUARDED_PATHS, *R7_MODULES)):
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"guarded_dependency_missing:{relative}")
        files[relative] = canonical_digest(path.read_bytes())
    files["execution_freeze"] = (canonical_digest(EXECUTION_FREEZE_PATH.read_bytes())
                                 if EXECUTION_FREEZE_PATH.is_file() else "")
    if phase == "B":
        table = Path(data_root) / "tables" / TABLE_NAME
        if not table.is_file():
            raise FileNotFoundError("guarded_dependency_missing:qualification_table")
        files["D/tables/" + TABLE_NAME] = canonical_digest(table.read_bytes())
    return files


def child_env() -> dict[str, str]:
    """The holder's environment after proxy stripping (A-O13), for the worker and the scorer."""
    import os
    env = dict(os.environ)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def spawn_worker(fs) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    import subprocess
    import sys

    def call(request: Mapping[str, Any]) -> Mapping[str, Any]:
        argv = [sys.executable, "-B", str(TOOLS / "g_route3_worker.py")]
        try:
            result = fs.run_child(argv, env=child_env(), input_bytes=json.dumps(request).encode("utf-8"),
                                  timeout=WORKER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise WorkerFailure("timeout") from exc
        code = result.returncode
        if code in CONSOLE_CONTROL_EXITS or code < 0:
            raise WorkerFailure(f"console_control_or_signal:{code}")
        if code != 0:
            raise WorkerFailure(f"died:{code}")
        try:
            return json.loads(result.stdout.decode("ascii"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise WorkerFailure("unparseable_output") from exc
    return call


def spawn_scorer(fs) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    import subprocess
    import sys

    def call(request: Mapping[str, Any]) -> Mapping[str, Any]:
        argv = [sys.executable, "-B", str(TOOLS / "g_route3_scorer.py")]
        try:
            result = fs.run_child(argv, env=child_env(), input_bytes=json.dumps(request).encode("utf-8"),
                                  timeout=SCORER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return {"error": "scorer_timeout"}
        if result.returncode != 0:
            return {"error": f"scorer_exit:{result.returncode}:"
                             + result.stderr.decode("utf-8", "replace")[-300:]}
        try:
            return json.loads(result.stdout.decode("ascii"))
        except (ValueError, UnicodeDecodeError):
            return {"error": "scorer_output_unparseable"}
    return call


def _counts(replay: J.Replay) -> dict[str, Any]:
    kinds = [e["kind"] for e in replay.entries]
    return {"calls_started": kinds.count("call_started"), "calls_recorded": kinds.count("call_recorded"),
            "executions_started": kinds.count("execution_started"),
            "in_doubt_position": replay.position if replay.state == "in_doubt" else None}


def _flush_tree(fs, root: Path) -> None:
    import os
    for directory, dirs, _files in os.walk(root, topdown=False):
        fs.flush_dir(Path(directory))


def _remove_tree(path: Path) -> None:
    """Remove a setup leftover. Git makes its object files read-only, which rmtree cannot delete on Windows."""
    import os
    import shutil
    import stat

    def writable_then_retry(function, target, _excinfo):
        os.chmod(target, stat.S_IWRITE)
        function(target)
    shutil.rmtree(path, onerror=writable_then_retry)


__all__ = ["CONTRACT_VERSION", "Runtime", "Lifecycle", "Refusal", "PhaseBlocked", "WorkerFailure",
           "guarded_digest", "standard_guarded_files", "spawn_worker", "spawn_scorer", "child_env",
           "R7_MODULES", "TABLE_NAME", "AUDIT_NAME"]
