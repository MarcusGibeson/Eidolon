from __future__ import annotations

"""Quick, deterministic R7 lifecycle tests (the normal suite; the exhaustive campaign is g_route3_campaign.py).

    python tools/g_route3_r7_tests.py
"""

import sys
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


if __name__ == "__main__":
    unittest.main(verbosity=1)
