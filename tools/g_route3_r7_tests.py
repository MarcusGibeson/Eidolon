from __future__ import annotations

"""Quick, deterministic R7 lifecycle tests (the normal suite; the exhaustive campaign is g_route3_campaign.py).

    python tools/g_route3_r7_tests.py
"""

import sys
import json
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import g_route3_journal as J  # noqa: E402

SPEC = J.RunSpec(call_ids=("c1", "c2", "c3"), coding=frozenset({2}))
HEAD0 = "0" * 64


class Builder:
    """Builds a run journal entry by entry, as the lifecycle would."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.previous = HEAD0
        self.number = 0

    def add(self, kind: str, payload: dict, *, acks=(), orphans=()) -> dict:
        self.number += 1
        payload = dict(payload)
        if kind == "run_created":
            payload.setdefault("claimed_ledger_head", self.previous)
            payload.setdefault("freeze_binding", "f" * 64)
            payload.setdefault("guarded_digest", "g" * 64)
        envelope, data = J.make_entry(self.number, kind, "run-x", self.previous, payload,
                                      acknowledges=acks, orphans=orphans)
        self.files[J.entry_name(self.number)] = data
        self.previous = envelope["record_sha256"]
        return envelope

    def tear(self, garbage: bytes = b'{"torn') -> None:
        self.number += 1
        self.files[J.entry_name(self.number)] = garbage

    def rename_tail_to_torn(self) -> tuple[int, str]:
        name = J.entry_name(self.number)
        data = self.files.pop(name)
        self.files[J.entry_name(self.number, torn=True)] = data
        return self.number, J.sha256_bytes(data)

    def replay(self) -> J.Replay:
        return J.replay_run(self.files, SPEC)


def executable(text: str = '"x"') -> dict:
    return {"executable_json": text, "executable_sha256": J.sha256_bytes(text.encode("ascii"))}


def full_run(b: Builder) -> None:
    b.add("run_created", {})
    b.add("call_started", {"position": 1, "call_id": "c1"})
    b.add("call_recorded", {"position": 1, "call_id": "c1", "transport_failure": ""})
    b.add("call_started", {"position": 2, "call_id": "c2"})
    b.add("call_recorded", {"position": 2, "call_id": "c2", "transport_failure": ""})
    b.add("execution_started", {"position": 2, **executable()})
    b.add("execution_recorded", {"position": 2, "infrastructure_failure": ""})
    b.add("call_started", {"position": 3, "call_id": "c3"})
    b.add("call_recorded", {"position": 3, "call_id": "c3", "transport_failure": ""})


class JournalReplayTests(unittest.TestCase):
    def test_states_along_a_clean_run(self) -> None:
        b = Builder()
        self.assertEqual(b.replay().state, "absent")
        expected = ["created", "in_doubt", "collecting", "in_doubt", "awaiting_execution", "execution_in_doubt",
                    "collecting", "in_doubt", "collected"]
        steps = [("run_created", {}), ("call_started", {"position": 1, "call_id": "c1"}),
                 ("call_recorded", {"position": 1, "call_id": "c1", "transport_failure": ""}),
                 ("call_started", {"position": 2, "call_id": "c2"}),
                 ("call_recorded", {"position": 2, "call_id": "c2", "transport_failure": ""}),
                 ("execution_started", {"position": 2, **executable()}),
                 ("execution_recorded", {"position": 2, "infrastructure_failure": ""}),
                 ("call_started", {"position": 3, "call_id": "c3"}),
                 ("call_recorded", {"position": 3, "call_id": "c3", "transport_failure": ""})]
        for (kind, payload), state in zip(steps, expected):
            b.add(kind, payload)
            got = b.replay()
            self.assertEqual(got.state, state, (kind, got.reason))
        last = b.previous
        b.add("scoring_started", {"fact_prefix_sha256": last})
        self.assertEqual(b.replay().state, "scoring_interrupted")
        scored = b.add("scored", {"report": {"x": 1}})
        self.assertEqual(b.replay().state, "scored")
        first = J.parse_entry(b.files["000001.json"])["record_sha256"]
        b.add("completed", {"run_created_sha256": first, "scored_sha256": scored["record_sha256"],
                            "freeze_binding": "f" * 64, "guarded_digest": "g" * 64, "calls": 3})
        self.assertEqual(b.replay().state, "completed")

    def test_grammar_is_checked_on_the_last_entry(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        b.add("call_recorded", {"position": 1, "call_id": "WRONG", "transport_failure": ""})
        self.assertEqual(b.replay().state, "integrity_failure")

    def test_nothing_but_closed_after_a_failure(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        b.add("call_recorded", {"position": 1, "call_id": "c1", "transport_failure": "HTTPError:x"})
        self.assertEqual(b.replay().state, "faulted")
        b.add("call_started", {"position": 2, "call_id": "c2"})
        self.assertEqual(b.replay().state, "integrity_failure")

    def test_closed_reason_function(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        self.assertEqual(J.closed_reason_for(b.replay(), SPEC, acknowledging=False), "call_outcome_unknown")
        b.add("closed", {"reason": "operator_interrupt"})
        self.assertEqual(b.replay().state, "integrity_failure")          # wrong reason after call_started

    def test_no_closed_after_collected(self) -> None:
        b = Builder()
        full_run(b)
        with self.assertRaises(ValueError):
            J.closed_reason_for(b.replay(), SPEC, acknowledging=False)
        b.add("closed", {"reason": "operator_interrupt"})
        self.assertEqual(b.replay().state, "integrity_failure")

    def test_no_closed_directly_after_execution_started(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        b.add("call_recorded", {"position": 1, "call_id": "c1", "transport_failure": ""})
        b.add("call_started", {"position": 2, "call_id": "c2"})
        b.add("call_recorded", {"position": 2, "call_id": "c2", "transport_failure": ""})
        b.add("execution_started", {"position": 2, **executable()})
        with self.assertRaises(ValueError):
            J.closed_reason_for(b.replay(), SPEC, acknowledging=False)

    def test_tear_prediction_and_acknowledgement(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        b.tear()
        got = b.replay()
        self.assertEqual((got.state, got.torn_tail), ("torn_tail", 3))
        torn = b.rename_tail_to_torn()
        got = b.replay()
        self.assertEqual((got.state, got.predicted, got.predicted_class), ("torn_pending", "call_recorded", "provider"))
        reason = J.closed_reason_for(got, SPEC, acknowledging=True)
        self.assertEqual(reason, "durability_uncertain")
        b.add("closed", {"reason": reason}, acks=[{"entry": torn[0], "sha256": torn[1]}])
        self.assertEqual(b.replay().state, "closed")

    def test_torn_recovery_publication_extends_the_tear(self) -> None:
        b = Builder()
        full_run(b)
        b.tear()
        first = b.rename_tail_to_torn()
        self.assertEqual(b.replay().predicted, "scoring_started")
        b.tear()                                             # the republication itself tears
        self.assertEqual(b.replay().state, "torn_tail")
        second = b.rename_tail_to_torn()
        got = b.replay()
        self.assertEqual((got.state, got.predicted, [n for n, _ in got.tear]),
                         ("torn_pending", "scoring_started", [first[0], second[0]]))

    def test_tear_after_failure_predicts_closed_with_that_reason(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        b.add("call_recorded", {"position": 1, "call_id": "c1", "transport_failure": "ConnectionError:x"})
        b.tear()
        torn = b.rename_tail_to_torn()
        got = b.replay()
        self.assertEqual((got.predicted, got.predicted_class), ("closed", "closure"))
        self.assertEqual(J.closed_reason_for(got, SPEC, acknowledging=True), "transport_failure")
        b.add("closed", {"reason": "transport_failure"}, acks=[{"entry": torn[0], "sha256": torn[1]}])
        self.assertEqual(b.replay().state, "closed")

    def test_middle_damage_is_integrity_failure(self) -> None:
        b = Builder()
        full_run(b)
        b.files["000003.json"] = b"garbage"
        self.assertEqual(b.replay().state, "integrity_failure")

    def test_identical_json_torn_pair_is_the_torn(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.tear()
        b.files["000002.torn"] = b.files["000002.json"]
        got = b.replay()
        self.assertEqual((got.state, got.pair_to_unlink), ("torn_pending", [2]))

    def test_tear_after_terminal_is_integrity_failure(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("closed", {"reason": "operator_interrupt"})
        b.tear()
        b.rename_tail_to_torn()
        self.assertEqual(b.replay().state, "integrity_failure")

    def test_executable_sha_checked(self) -> None:
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        b.add("call_recorded", {"position": 1, "call_id": "c1", "transport_failure": ""})
        b.add("call_started", {"position": 2, "call_id": "c2"})
        b.add("call_recorded", {"position": 2, "call_id": "c2", "transport_failure": ""})
        b.add("execution_started", {"position": 2, "executable_json": '"a"', "executable_sha256": "0" * 64})
        self.assertEqual(b.replay().state, "integrity_failure")

    def test_per_file_protection(self) -> None:
        b = Builder()
        full_run(b)
        self.assertTrue(J.sealed_protective(b.files, SPEC))
        damaged = dict(b.files)
        damaged["000004.json"] = b"garbage"
        self.assertTrue(J.sealed_protective(damaged, SPEC))
        partial = {name: data for name, data in b.files.items() if name < "000009.json"}
        self.assertFalse(J.sealed_protective(partial, SPEC))

    def test_acknowledges_only_on_closed_and_derived(self) -> None:          # A-O14
        b = Builder()
        b.add("run_created", {})
        b.tear()
        torn = b.rename_tail_to_torn()
        b.add("call_started", {"position": 1, "call_id": "c1"}, acks=[{"entry": torn[0], "sha256": torn[1]}])
        self.assertEqual(b.replay().state, "integrity_failure")

    def test_lossless_text(self) -> None:
        text = "a\ud800b\U0001f600"
        encoded, _ = J.text_to_b64(text)
        self.assertEqual(J.b64_to_text(encoded), text)


class LedgerReplayTests(unittest.TestCase):
    def test_ledger_chain_and_tear(self) -> None:
        genesis = J.genesis_seal("A", "root")
        files = {}
        env, data = J.make_entry(1, "attempt_consumed", "ledger-A", genesis, {"attempt": 1, "run_id": "r1"})
        files["000001.json"] = data
        got = J.replay_ledger(files, "A", "root")
        self.assertEqual((got.state, sorted(got.consumed)), ("ok", [1]))
        files["000002.torn"] = b"xx"
        got = J.replay_ledger(files, "A", "root")
        self.assertEqual(got.state, "torn_pending")
        env2, data2 = J.make_entry(3, "ledger_torn_acknowledged", "ledger-A", env["record_sha256"],
                                   {"consumed_and_closed": {"attempt": 2, "run_id": "r2"}},
                                   acknowledges=[{"entry": 2, "sha256": J.sha256_bytes(b"xx")}])
        files["000003.json"] = data2
        got = J.replay_ledger(files, "A", "root")
        self.assertEqual((got.state, sorted(got.consumed), sorted(got.closed_at_ledger)), ("ok", [1, 2], [2]))


class LifecycleTests(unittest.TestCase):
    """The lifecycle on a four-call schedule with stub provider, worker and scorer (fast, deterministic)."""

    @classmethod
    def setUpClass(cls) -> None:
        import tempfile
        import g_route3_campaign as K
        import g_route3_platform as P
        P.pin_recursion_limit()
        cls.K = K
        cls.work = Path(tempfile.mkdtemp(prefix="g_route3_r7_tests_"))
        template = cls.work / "template"
        template.mkdir()
        K.run_command(K.World(template), K.F.RealFs(), "setup")
        cls.template = template
        probe = K.FaultFs()
        world = K.base_world(template, cls.work / "probe")
        K.run_command(world, probe, "launch", "A", K.SENTENCE.format(n=1), 1, False)
        cls.ops = probe.ops

    @classmethod
    def tearDownClass(cls) -> None:
        import g_route3_lifecycle as L
        L._remove_tree(cls.work)

    def op_index(self, needle: str, *, after: str | None = None) -> int:
        start = 0
        if after is not None:
            start = next(i for i, op in enumerate(self.ops) if ":rename:" in op and after in op) + 1
        return next(i for i, op in enumerate(self.ops[start:], start + 1) if needle in op)

    def world(self, name: str, **kwargs):
        return self.K.base_world(self.template, self.work / name, **kwargs)

    def launch(self, world, n=1, distinct=False, fs=None):
        K = self.K
        sentence = K.DISTINCT.format(n=n, m=n - 1) if distinct else K.SENTENCE.format(n=n)
        return K.run_command(world, fs or K.F.RealFs(), "launch", "A", sentence, n, distinct)

    def killed(self, world, index, after=True):
        with self.assertRaises(self.K.SimulatedKill):
            self.launch(world, fs=self.K.FaultFs(kill_at=index, kill_after=after))

    def test_clean_attempt_completes_and_commits(self) -> None:
        world = self.world("clean")
        self.assertEqual(self.launch(world)["state"], "completed")
        self.assertEqual(self.K.check_oracles(world), [])
        self.assertEqual(max(world.counts.values()), 1)

    def test_transport_failure_closes_truthfully_and_next_attempt_follows(self) -> None:
        call = self.K.small_schedule()[0]["A"][2]["call_id"]
        world = self.world("transport", failures={call: "error"})
        out = self.launch(world)
        self.assertEqual((out["state"], out["reason"]), ("closed", "transport_failure"))
        world.failures.clear()
        with self.assertRaisesRegex(self.K.L.Refusal, "attempt_number_must_be_2"):
            self.launch(world, n=1)
        self.assertEqual(self.launch(world, n=2)["state"], "completed")

    def test_provider_exception_closes(self) -> None:
        call = self.K.small_schedule()[0]["A"][0]["call_id"]
        world = self.world("raise", failures={call: "raise"})
        out = self.launch(world)
        self.assertEqual((out["state"], out["reason"]), ("closed", "transport_failure"))

    def test_worker_failure_is_infrastructure_not_model(self) -> None:
        fixture = self.K.small_schedule()[0]["A"][1]["fixture_id"]
        world = self.world("worker", worker_failures={fixture})
        out = self.launch(world)
        self.assertEqual((out["state"], out["reason"]), ("closed", "infrastructure_failure"))

    def test_completed_attempt_blocks_further_launches(self) -> None:
        world = self.world("blocks")
        self.launch(world)
        with self.assertRaisesRegex(self.K.L.Refusal, "attempt_1_completed"):
            self.launch(world, n=2)

    def test_damaged_committed_entry_is_restored(self) -> None:
        world = self.world("damaged")
        out = self.launch(world)
        journal = world.D / "phase_a" / "runs" / out["run_id"] / "journal"
        original = (journal / "000003.json").read_bytes()
        (journal / "000003.json").write_bytes(b"garbage")
        self.assertEqual(self.K.check_oracles(world), [])
        self.assertEqual((journal / "000003.json").read_bytes(), original)

    def test_changed_sealed_committed_entry_blocks(self) -> None:
        world = self.world("changed")
        out = self.launch(world)
        journal = world.D / "phase_a" / "runs" / out["run_id"] / "journal"
        envelope = J.parse_entry((journal / "000003.json").read_bytes())
        payload = dict(envelope["payload"], latency_seconds=99.0)
        _, data = J.make_entry(envelope["entry"], envelope["kind"], envelope["run_id"],
                               envelope["previous_entry_sha256"], payload)
        (journal / "000003.json").write_bytes(data)
        with self.assertRaises(self.K.L.PhaseBlocked):
            self.K.run_command(world, self.K.F.RealFs(), "resume", "A", self.K.SENTENCE.format(n=1))

    def test_kill_after_call_started_closes_without_repeat(self) -> None:
        world = self.world("killcall")
        self.killed(world, self.op_index("000002.json"))
        self.assertEqual(self.K.drive_to_end(world), "completed")
        self.assertEqual(max(world.counts.values()), 1)
        self.assertEqual(self.K.check_oracles(world), [])
        attempt, state = self.K.latest_attempt(world)
        self.assertEqual((attempt, state), (2, "completed"))       # attempt 1 closed as call_outcome_unknown

    def test_drift_refuses_and_does_not_close(self) -> None:
        world = self.world("drift")
        self.killed(world, self.op_index("000003.json"))
        world.drift = True
        with self.assertRaisesRegex(self.K.L.Refusal, "guarded_dependency_drift"):
            self.K.run_command(world, self.K.F.RealFs(), "resume", "A", self.K.SENTENCE.format(n=1))
        world.drift = False
        self.assertEqual(self.K.drive_to_end(world), "completed")
        self.assertEqual(self.K.latest_attempt(world), (1, "completed"))

    def test_interrupt_before_collected_closes_as_operator_interrupt(self) -> None:
        world = self.world("interrupt")
        lc = world.lifecycle(self.K.F.RealFs())
        calls = {"n": 0}

        def interrupted():
            calls["n"] += 1
            return calls["n"] >= 2
        lc.rt.interrupted = interrupted
        lc.open()
        try:
            out = lc.command_launch("A", self.K.SENTENCE.format(n=1), 1, False)
        finally:
            lc.close()
        self.assertEqual((out["state"], out["reason"]), ("closed", "operator_interrupt"))

    def test_orphan_is_cleared_and_launch_needs_it_cleared(self) -> None:
        world = self.world("orphan")
        self.killed(world, self.op_index("000001.json"))
        run_id = next(p.name for p in (world.D / "phase_a" / "runs").iterdir())
        with self.assertRaisesRegex(self.K.L.Refusal, "orphan_run_folder_exists"):
            self.launch(world)
        self.K.run_command(world, self.K.F.RealFs(), "clear_orphan", "A", run_id)
        self.assertEqual(self.launch(world)["state"], "completed")

    def test_declare_untrusted_in_progress_attempt(self) -> None:           # ruling 11 (B-O3)
        world = self.world("untrusted")
        self.killed(world, self.op_index("000003.json"))
        calls_before = dict(world.counts)
        out = self.K.run_command(world, self.K.F.RealFs(), "declare", "A", 1)
        self.assertEqual((out["state"], out["reason"]), ("closed_at_ledger", "integrity_failure"))
        self.assertEqual(world.counts, calls_before)
        with self.assertRaisesRegex(self.K.L.Refusal, "distinct_sentence_required"):
            self.launch(world, n=2)
        self.assertEqual(self.launch(world, n=2, distinct=True)["state"], "completed")
        self.assertEqual(self.K.check_oracles(world), [])

    def test_extra_table_file_after_freeze_is_quarantined(self) -> None:      # A-O4 (verification row)
        world = self.world("tables")
        self.launch(world)
        lc = world.lifecycle(self.K.F.RealFs())
        lc.open()
        try:
            lc._commit({"tables/QUALIFICATION_TABLE.json": b"{}\n"}, "test table")
        finally:
            lc.close()
        (world.D / "tables" / "QUALIFICATION_TABLE.json").write_bytes(b"{}\n")
        (world.D / "tables" / "stray.json").write_bytes(b"stray")
        self.assertEqual(self.K.check_oracles(world), [])
        self.assertFalse((world.D / "tables" / "stray.json").exists())

    def test_protected_attempt_cannot_be_declared(self) -> None:
        world = self.world("protected")
        self.killed(world, self.op_index(":child:", after="000011.json"), after=False)
        run_dir = next((world.D / "phase_a" / "runs").iterdir())
        (run_dir / "journal" / "000005.json").write_bytes(b"damage")
        with self.assertRaises(self.K.L.PhaseBlocked):
            self.K.run_command(world, self.K.F.RealFs(), "declare", "A", 1)


    def test_resume_refuses_inputs_differing_from_run_created(self) -> None:     # A-N1, B-N3
        world = self.world("binding")
        self.killed(world, self.op_index("000003.json"))
        calls_before = dict(world.counts)
        lc = world.lifecycle(self.K.F.RealFs())
        lc.rt.input_digests = {"experiments/G-ROUTE3-candidate/schedule_a.json": "0" * 64}
        lc.open()
        try:
            with self.assertRaisesRegex(self.K.L.Refusal, "in_memory_inputs_differ_from_run_created"):
                lc.command_resume("A", self.K.SENTENCE.format(n=1))
        finally:
            lc.close()
        self.assertEqual(world.counts, calls_before)
        self.assertEqual(self.K.drive_to_end(world), "completed")
        self.assertEqual(self.K.latest_attempt(world), (1, "completed"))

    def test_resume_interrupt_before_first_new_call_leaves_attempt_open(self) -> None:   # ruling 12
        world = self.world("resume_interrupt")
        self.killed(world, self.op_index("000003.json"))
        lc = world.lifecycle(self.K.F.RealFs())
        lc.open()
        try:
            lc.prelude()
        finally:
            lc.close()
        run_dir = next((world.D / "phase_a" / "runs").iterdir()) / "journal"
        before = sorted(p.name for p in run_dir.iterdir())
        calls_before = dict(world.counts)
        lc = world.lifecycle(self.K.F.RealFs())
        lc.rt.interrupted = lambda: True
        lc.open()
        try:
            out = lc.command_resume("A", self.K.SENTENCE.format(n=1))
        finally:
            lc.close()
        self.assertEqual((out["state"], out["reason"]), ("open", "interrupted_before_first_new_call"))
        self.assertEqual(sorted(p.name for p in run_dir.iterdir()), before)
        self.assertEqual(world.counts, calls_before)
        self.assertEqual(self.K.drive_to_end(world), "completed")
        self.assertEqual(self.K.latest_attempt(world), (1, "completed"))

    def _resume_with(self, world, interrupted):
        lc = world.lifecycle(self.K.F.RealFs())
        lc.rt.interrupted = interrupted
        lc.open()
        try:
            return lc.command_resume("A", self.K.SENTENCE.format(n=1))
        finally:
            lc.close()

    def test_resume_interrupt_at_pending_sandbox_safe_point_leaves_attempt_open(self) -> None:   # ruling 12
        world = self.world("resume_sandbox_interrupt")
        self.killed(world, self.op_index("000005.json"))              # the coding call_recorded
        self.K.run_command(world, self.K.F.RealFs(), "prelude")
        journal = next((world.D / "phase_a" / "runs").iterdir()) / "journal"
        before, calls_before = sorted(p.name for p in journal.iterdir()), dict(world.counts)
        out = self._resume_with(world, lambda: True)
        self.assertEqual((out["state"], out["reason"]), ("open", "interrupted_before_first_new_call"))
        self.assertEqual(sorted(p.name for p in journal.iterdir()), before)     # no sandbox run, nothing written
        self.assertEqual(world.counts, calls_before)
        self.assertEqual(self.K.drive_to_end(world), "completed")
        self.assertEqual(self.K.check_oracles(world), [])

    def test_resumed_attempt_closes_after_its_first_new_call(self) -> None:        # ruling 12, §7
        world = self.world("resume_after_new_call")
        self.killed(world, self.op_index("000003.json"))
        calls_before = sum(world.counts.values())
        out = self._resume_with(world, lambda: sum(world.counts.values()) > calls_before)
        self.assertEqual((out["state"], out["reason"]), ("closed", "operator_interrupt"))
        self.assertEqual(sum(world.counts.values()) - calls_before, 1)
        self.assertEqual(self.K.check_oracles(world), [])

    def test_durable_intent_oracle_fires(self) -> None:                               # A-N4 oracle proof
        class ForgetsFlushes(self.K.FaultFs):
            def _flush_dir(self, path):
                self.K_real_flush(path)                                 # flush, but keep the bookkeeping pending
        ForgetsFlushes.K_real_flush = lambda self, path: self.K.F.RealFs._flush_dir(self, path)
        ForgetsFlushes.K = self.K
        world = self.world("oracle_fires")
        self.launch(world, fs=ForgetsFlushes())
        self.assertTrue(any(v.startswith("send_without_durable_call_started") for v in world.violations))
        clean = self.world("oracle_quiet")
        self.launch(clean, fs=self.K.FaultFs())
        self.assertEqual(clean.violations, [])

    def test_snapshot_flag_is_fixed_by_the_closure_commit(self) -> None:           # MF-1
        world = self.world("snapshot_flag")
        self.killed(world, self.op_index("000003.json"))
        self.K.run_command(world, self.K.F.RealFs(), "declare", "A", 1)

        def flag():
            lc = world.lifecycle(self.K.F.RealFs())
            lc.open()
            try:
                row = lc.attempts("A")[0]
                tree = lc.tree()
                last = sorted(p for p in tree if p.startswith("disclosure/A/"))[-1]
                committed = json.loads(lc.repo.read_blob(tree[last]).decode("utf-8"))["attempts"][0]
                return row["snapshot_matches_recorded_digest"], committed["snapshot_matches_recorded_digest"]
            finally:
                lc.close()
        self.assertEqual(flag(), (True, True))
        run_dir = next((world.D / "phase_a" / "runs").iterdir())
        (run_dir / "desktop.ini").write_bytes(b"[.ShellClassInfo]\r\n")
        self.K.run_command(world, self.K.F.RealFs(), "prelude")
        self.assertEqual(flag(), (True, True))

    def test_scorer_marks_request_body_mismatch_and_unexecuted_coding(self) -> None:   # A-N1, B-N2
        import copy
        import g_route3_scorer as S
        world = self.world("scorer_records")
        out = self.launch(world)
        journal = world.D / "phase_a" / "runs" / out["run_id"] / "journal"
        entries = [J.parse_entry(p.read_bytes()) for p in sorted(journal.glob("*.json"))]
        schedule, fixtures = world.schedule["A"], world.fixtures["A"]
        records, mismatched = S.rebuild_records(entries, "A", schedule, fixtures, check_executables=False)
        self.assertEqual((len(records), mismatched), (len(schedule), {}))
        tampered = copy.deepcopy(entries)
        first_call = next(e for e in tampered if e["kind"] == "call_started")
        first_call["payload"]["request_sha256"] = "0" * 64
        _, mismatched = S.rebuild_records(tampered, "A", schedule, fixtures, check_executables=False)
        self.assertEqual(mismatched, {int(first_call["payload"]["position"]): "request_body_differs_from_call_started"})
        coding = next((int(e["payload"]["position"]) for e in entries if e["kind"] == "execution_recorded"), None)
        if coding is not None:
            unexecuted = [e for e in entries if not (e["kind"] in ("execution_started", "execution_recorded")
                                                     and int(e["payload"]["position"]) == coding)]
            records, _ = S.rebuild_records(unexecuted, "A", schedule, fixtures, check_executables=False)
            row = next(r for r in records if r["schedule_position"] == coding)
            self.assertEqual(row["infrastructure_failure"], "execution_not_run")

    def test_individually_sealed_prefers_json_over_torn_twin(self) -> None:          # B-N5
        import g_route3_lifecycle as L
        import g_route3_scorer as S
        b = Builder()
        b.add("run_created", {})
        b.add("call_started", {"position": 1, "call_id": "c1"})
        files = dict(b.files, **{"000002.torn": b.files["000002.json"]})
        for function in (L._individually_sealed, S._individually_sealed):
            self.assertEqual([e["entry"] for e in function(files)], [1, 2])


class PlatformTests(unittest.TestCase):
    def test_a_killed_holder_leaves_no_live_children(self) -> None:                  # §15, §18
        import subprocess
        import time
        holder = subprocess.Popen(
            [sys.executable, "-B", "-c",
             "import sys, subprocess, time; sys.path.insert(0, %r); import g_route3_platform as P; "
             "P.join_kill_on_close_job(); c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']); "
             "print(c.pid, flush=True); time.sleep(120)" % str(Path(__file__).resolve().parent)],
            stdout=subprocess.PIPE, text=True)
        child = int(holder.stdout.readline().strip())
        self.assertTrue(_alive(child))
        holder.kill()
        holder.wait(timeout=30)
        holder.stdout.close()
        deadline = time.time() + 15
        while _alive(child) and time.time() < deadline:
            time.sleep(0.2)
        self.assertFalse(_alive(child))

    def test_near_limit_bands_are_deterministic_across_depths_and_processes(self) -> None:   # C-O1, C-O5
        import json
        import subprocess
        import g_route3_platform as P
        from g_route3_contract import runtime_fixtures
        from g_route3_worker import derive_executable
        P.pin_recursion_limit()
        fixture = next(f for f in runtime_fixtures("A").values() if f["validator_profile"] == "coding.v1")
        outputs = []
        for terms in (2960, 2976, 2990):
            outputs.append(json.dumps({"path": fixture["input"]["allowed_path"], "old": fixture["input"]["source"],
                                       "new": "value = " + " + ".join(["1"] * terms) + "\n"}))
        for depth in (960, 991, 1000):
            outputs.append("[" * depth + "]" * depth)

        def at_depth(k: int, raw: str) -> str:
            return derive_executable(fixture, raw) if k == 0 else at_depth(k - 1, raw)
        here = [at_depth(0, raw) for raw in outputs]
        deep = [at_depth(300, raw) for raw in outputs]
        self.assertEqual(here, deep)
        script = ("import sys, json; sys.path.insert(0, %r); import g_route3_platform as P; P.pin_recursion_limit(); "
                  "from g_route3_contract import runtime_fixtures; from g_route3_worker import derive_executable, "
                  "classify; f = [x for x in runtime_fixtures('A').values() if x['validator_profile']=='coding.v1'][0]; "
                  "outs = json.loads(sys.stdin.read()); exes = [derive_executable(f, o) for o in outs]; "
                  "print(json.dumps([exes, [P.run_pinned(classify, f, json.loads(e))['candidate_error'] "
                  "for e in exes]]))" % str(Path(__file__).resolve().parent))
        results = [subprocess.run([sys.executable, "-B", "-c", script], input=json.dumps(outputs), text=True,
                                  capture_output=True, check=True).stdout for _ in range(2)]
        self.assertEqual(results[0], results[1])
        self.assertEqual(json.loads(results[0])[0], here)


def _alive(pid: int) -> bool:
    import subprocess
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


if __name__ == "__main__":
    unittest.main(verbosity=1)
