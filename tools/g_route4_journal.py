# forked from g_route3_journal
from __future__ import annotations

"""Journal entries, seals and the pure replay procedure of the G-ROUTE4 R7 lifecycle (design §4, §5, §9.1).

Nothing here touches the disk, git or the clock. ``replay_run`` and ``replay_ledger`` take the bytes of the
``NNNNNN.json`` / ``NNNNNN.torn`` files of one directory and return a state; they are pure, total functions
(J4). The lifecycle reads the files (through ``g_route4_fs``) and acts on the state.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping

ENTRY_NAME = re.compile(r"^(\d{6})\.(json|torn)$")
TEMP_NAME = re.compile(r"^\.tmp-(\d{6})-[0-9a-f]+$")
ORPHAN_TEMP = re.compile(r"^\.orphan-tmp-\d{6}-[0-9a-f]+$")

EXECUTION_KINDS = ("execution_started", "execution_recorded")      # forbidden in G-ROUTE4 (coding excluded)
RUN_KINDS = ("run_created", "call_started", "call_recorded", "execution_started", "execution_recorded",
             "scoring_started", "scored", "completed", "closed")
DERIVED_KINDS = ("scoring_started", "scored", "completed")
LEDGER_KINDS = ("attempt_consumed", "attempt_closed_at_ledger", "ledger_torn_acknowledged")
CLOSED_REASONS_FIXED = ("transport_failure", "infrastructure_failure", "execution_interrupted",
                        "call_outcome_unknown", "durability_uncertain", "operator_interrupt")
ABANDON_PREFIX = "abandoned_preflight_failed:"
LEDGER_CLOSURE_REASONS = ("integrity_failure", "journal_missing", "durability_uncertain")


# ---------------------------------------------------------------- canonical form (§4.4)

def safe_value(value: Any) -> Any:
    """Everything sealed passes through here (J6): lone surrogates replaced, huge integers and non-finite floats
    turned into strings, tuples into lists. Keys must be strings."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return str(value) if abs(value) >= 10 ** 30 else value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    if isinstance(value, str):
        return value.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
    if isinstance(value, (list, tuple)):
        return [safe_value(item) for item in value]
    if isinstance(value, Mapping):
        return {safe_value(str(key)): safe_value(item) for key, item in value.items()}
    raise TypeError(f"unsealable_value:{type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_to_b64(text: str) -> tuple[str, str]:
    """Lossless storage of model text (§4.2): base64 of UTF-8 with surrogatepass, and the sha256 of those bytes."""
    import base64
    raw = str(text).encode("utf-8", "surrogatepass")
    return base64.b64encode(raw).decode("ascii"), sha256_bytes(raw)


def b64_to_text(encoded: str) -> str:
    import base64
    return base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8", "surrogatepass")


def genesis_seal(phase: str, root_id: str) -> str:
    return digest({"genesis": "g-route4-ledger", "phase": phase, "root_id": root_id})


def entry_name(number: int, torn: bool = False) -> str:
    return f"{number:06d}.{'torn' if torn else 'json'}"


def make_entry(number: int, kind: str, owner: str, previous: str, payload: Mapping[str, Any], *,
               acknowledges: Iterable[Mapping[str, Any]] = (), orphans: Iterable[Mapping[str, Any]] = ()
               ) -> tuple[dict[str, Any], bytes]:
    """Build and seal one entry. Returns (envelope, file bytes)."""
    envelope = safe_value({"entry": int(number), "kind": kind, "run_id": owner, "previous_entry_sha256": previous,
                           "acknowledges": [dict(row) for row in acknowledges],
                           "orphans": [dict(row) for row in orphans], "payload": dict(payload)})
    envelope["record_sha256"] = digest(envelope)
    return envelope, canonical_bytes(envelope) + b"\n"


def parse_entry(data: bytes) -> dict[str, Any] | None:
    """The sealed envelope, or None if the bytes do not parse, are not canonical, or do not seal."""
    try:
        if not data.endswith(b"\n"):
            return None
        envelope = json.loads(data[:-1].decode("utf-8"))
        if not isinstance(envelope, dict) or canonical_bytes(envelope) + b"\n" != data:
            return None
        if set(envelope) != {"entry", "kind", "run_id", "previous_entry_sha256", "acknowledges", "orphans",
                             "payload", "record_sha256"}:
            return None
        body = {key: value for key, value in envelope.items() if key != "record_sha256"}
        if digest(body) != envelope["record_sha256"]:
            return None
        return envelope
    except (ValueError, UnicodeDecodeError, RecursionError, TypeError):
        return None


# ---------------------------------------------------------------- the schedule a run journal is checked against

@dataclass(frozen=True)
class RunSpec:
    """What replay needs to know about the fixed schedule: call ids by position. Coding is excluded (design "Coding
    exclusion in the R7 fork"): ``coding`` must be empty, so the coding replay states are unreachable."""
    call_ids: tuple[str, ...]
    coding: frozenset[int]

    def __post_init__(self) -> None:
        if self.coding:
            raise ValueError("coding_positions_forbidden")

    @property
    def calls(self) -> int:
        return len(self.call_ids)


# ---------------------------------------------------------------- replay result

@dataclass
class Replay:
    state: str                                   # see §5; "integrity_failure" carries ``reason``
    reason: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)     # valid entries, in order
    tear: list[tuple[int, str]] = field(default_factory=list)       # trailing .torn entries (number, sha256)
    torn_tail: int | None = None                  # R5: the highest .json that fails to parse or seal
    predicted: str = ""                           # R6: predicted kind of the trailing tear
    predicted_class: str = ""                     # provider | closure | derived | special
    position: int = 0                             # position of the last record, or of the in-doubt call
    pair_to_unlink: list[int] = field(default_factory=list)          # n.json identical to n.torn
    temps: list[str] = field(default_factory=list)                   # .tmp-* names
    orphan_temps: list[str] = field(default_factory=list)            # .orphan-tmp-* names
    foreign: list[str] = field(default_factory=list)

    @property
    def last(self) -> dict[str, Any] | None:
        return self.entries[-1] if self.entries else None

    @property
    def head(self) -> str | None:
        return self.entries[-1]["record_sha256"] if self.entries else None

    def first(self, kind: str) -> dict[str, Any] | None:
        return next((row for row in self.entries if row["kind"] == kind), None)


def _classify_names(files: Mapping[str, bytes], extra_names: Iterable[str], result: Replay
                    ) -> tuple[dict[int, bytes], dict[int, bytes]] | None:
    jsons: dict[int, bytes] = {}
    torns: dict[int, bytes] = {}
    for name, data in files.items():
        match = ENTRY_NAME.match(name)
        if not match:
            continue
        (jsons if match.group(2) == "json" else torns)[int(match.group(1))] = data
    for name in extra_names:
        if ENTRY_NAME.match(name):
            continue
        if TEMP_NAME.match(name):
            result.temps.append(name)
        elif ORPHAN_TEMP.match(name):
            result.orphan_temps.append(name)
        else:
            result.foreign.append(name)
    for number in sorted(set(jsons) & set(torns)):
        if jsons[number] != torns[number]:
            result.state, result.reason = "integrity_failure", f"json_and_torn_differ:{number}"
            return None
        result.pair_to_unlink.append(number)
        del jsons[number]
    return jsons, torns


def _failure_reason(entry: Mapping[str, Any]) -> str:
    payload = entry["payload"]
    if entry["kind"] == "call_recorded" and payload.get("transport_failure"):
        return "transport_failure"
    if entry["kind"] == "execution_recorded" and payload.get("infrastructure_failure"):
        return ("execution_interrupted" if payload["infrastructure_failure"] == "execution_interrupted"
                else "infrastructure_failure")
    return ""


class _RunGrammar:
    """Walks valid entries in order and enforces §4.2 and the R3 checks. Raises ValueError(reason)."""

    def __init__(self, spec: RunSpec) -> None:
        self.spec = spec
        self.last: dict[str, Any] | None = None
        self.run_id: str | None = None
        self.position = 0            # last recorded position
        self.collected = False
        self.terminal = False
        self.orphan_names: set[str] = set()
        self.run_created: dict[str, Any] | None = None
        self.scored: dict[str, Any] | None = None

    def _is_clean_record(self, entry: Mapping[str, Any]) -> bool:
        return entry["kind"] in ("call_recorded", "execution_recorded") and not _failure_reason(entry)

    def expected_closed_reason(self, acknowledges: list) -> tuple[str, ...] | None:
        """The permitted closed reasons after the current prefix (R3), or None if closed is forbidden."""
        last = self.last
        if last is None or self.terminal or self.collected:
            return None
        failure = _failure_reason(last)
        if failure:
            return (failure,)
        if acknowledges:
            return ("durability_uncertain",)
        if last["kind"] == "call_started":
            return ("call_outcome_unknown",)
        if last["kind"] == "execution_started":
            return None
        if last["kind"] == "run_created" or self._is_clean_record(last):
            return ("operator_interrupt", ABANDON_PREFIX)
        return None

    def accept(self, entry: Mapping[str, Any], acknowledged: list[tuple[int, str]]) -> None:
        kind, payload = entry["kind"], entry["payload"]
        if kind not in RUN_KINDS:
            raise ValueError(f"unknown_kind:{kind}")
        if kind in EXECUTION_KINDS:                 # R7 §5 R3 in this fork: an integrity failure
            raise ValueError(f"execution_kind_forbidden:{kind}")
        if self.run_id is None:
            self.run_id = entry["run_id"]
        elif entry["run_id"] != self.run_id:
            raise ValueError("run_id_changes")
        expected_previous = (self.last["record_sha256"] if self.last is not None
                             else payload.get("claimed_ledger_head"))
        if entry["previous_entry_sha256"] != expected_previous:
            raise ValueError(f"previous_seal_mismatch:{entry['entry']}")
        acks = [(int(row.get("entry", -1)), str(row.get("sha256", ""))) for row in entry["acknowledges"]]
        if acks != acknowledged:
            raise ValueError(f"acknowledges_mismatch:{entry['entry']}")
        if acks and kind not in ("closed", *DERIVED_KINDS):
            raise ValueError(f"acknowledges_on_{kind}")
        for row in entry["orphans"]:
            name = str(row.get("name", ""))
            if not ORPHAN_TEMP.match(name) or name in self.orphan_names:
                raise ValueError(f"orphan_name_invalid_or_repeated:{name}")
            self.orphan_names.add(name)
        if self.terminal:
            raise ValueError("entry_after_terminal")
        last = self.last
        if kind == "closed":
            allowed = self.expected_closed_reason(acks)
            reason = str(payload.get("reason", ""))
            if allowed is None:
                raise ValueError("closed_not_permitted_here")
            if not (reason in allowed or (ABANDON_PREFIX in allowed and reason.startswith(ABANDON_PREFIX)
                                          and len(reason) > len(ABANDON_PREFIX))):
                raise ValueError(f"closed_reason_not_permitted:{reason}")
            self.terminal = True
        elif last is None:
            if kind != "run_created":
                raise ValueError("first_entry_not_run_created")
            self.run_created = dict(payload)
        elif last["kind"] != "call_started" and _failure_reason(last):
            raise ValueError("continuation_after_failure")
        elif kind == "run_created":
            raise ValueError("run_created_not_first")
        elif kind == "call_started":
            k = int(payload.get("position", -1))
            if self.collected or k != self.position + 1 or k > self.spec.calls:
                raise ValueError("call_started_out_of_order")
            if last["kind"] not in ("run_created", "call_recorded", "execution_recorded"):
                raise ValueError("call_started_after_open_call")
            if last["kind"] == "call_recorded" and (self.position in self.spec.coding):
                raise ValueError("call_started_before_execution")
            if payload.get("call_id") != self.spec.call_ids[k - 1]:
                raise ValueError("call_id_mismatch")
        elif kind == "call_recorded":
            k = int(payload.get("position", -1))
            if last["kind"] != "call_started" or k != last["payload"]["position"]:
                raise ValueError("call_recorded_without_its_call_started")
            if payload.get("call_id") != last["payload"]["call_id"]:
                raise ValueError("call_id_mismatch")
            self.position = k
            if not _failure_reason(entry) and k == self.spec.calls and k not in self.spec.coding:
                self.collected = True
        elif kind == "execution_started":
            k = int(payload.get("position", -1))
            if (last["kind"] != "call_recorded" or k != last["payload"]["position"] or k not in self.spec.coding
                    or _failure_reason(last)):
                raise ValueError("execution_started_out_of_place")
            text = str(payload.get("executable_json", ""))
            if sha256_bytes(text.encode("ascii", "strict")) != payload.get("executable_sha256"):
                raise ValueError("executable_sha256_mismatch")
        elif kind == "execution_recorded":
            k = int(payload.get("position", -1))
            if last["kind"] != "execution_started" or k != last["payload"]["position"]:
                raise ValueError("execution_recorded_without_its_execution_started")
            if not _failure_reason(entry) and k == self.spec.calls:
                self.collected = True
        elif kind == "scoring_started":
            if not self.collected or last["kind"] not in ("call_recorded", "execution_recorded"):
                raise ValueError("scoring_started_before_collected")
            if payload.get("fact_prefix_sha256") != last["record_sha256"]:
                raise ValueError("scoring_started_prefix_mismatch")
        elif kind == "scored":
            if last["kind"] != "scoring_started":
                raise ValueError("scored_out_of_place")
            self.scored = dict(entry)
        elif kind == "completed":
            if last["kind"] != "scored":
                raise ValueError("completed_out_of_place")
            expected = {"run_created_sha256": self._first_seal, "scored_sha256": last["record_sha256"],
                        "freeze_binding": (self.run_created or {}).get("freeze_binding"),
                        "guarded_digest": (self.run_created or {}).get("guarded_digest"),
                        "calls": self.spec.calls}
            if dict(payload) != expected:
                raise ValueError("completed_receipt_does_not_match_chain")
            self.terminal = True
        if self.last is None:
            self._first_seal = entry["record_sha256"]
        self.last = dict(entry)

    _first_seal: str = ""

    def predict(self) -> tuple[str, str]:
        """Predicted kind and class of a trailing tear (§5 table)."""
        last = self.last
        if last is None:
            return "run_created", "special"
        if self.terminal:
            return "", "terminal"
        kind = last["kind"]
        if kind in ("call_recorded", "execution_recorded") and _failure_reason(last):
            return "closed", "closure"
        if kind == "scoring_started":
            return "scored", "derived"
        if kind == "scored":
            return "completed", "derived"
        if self.collected:
            return "scoring_started", "derived"
        if kind == "call_started":
            return "call_recorded", "provider"
        if kind == "call_recorded" and last["payload"]["position"] in self.spec.coding:
            return "execution_started", "provider"
        if kind == "execution_started":
            return "execution_recorded", "provider"
        return "call_started", "provider"


def replay_run(files: Mapping[str, bytes], spec: RunSpec, *, extra_names: Iterable[str] = ()) -> Replay:
    """§5 as a pure, total, ordered function over one run journal directory.

    ``files`` maps every ``NNNNNN.json`` / ``NNNNNN.torn`` name to its bytes (an unreadable entry never reaches
    here: the caller refuses first, R−1). ``extra_names`` lists the directory's other names.
    """
    result = Replay(state="")
    split = _classify_names(files, extra_names, result)
    if split is None:
        return result
    jsons, torns = split
    numbers = sorted(set(jsons) | set(torns))
    if not numbers:
        result.state = "absent"                                                       # R0
        return result
    if numbers != list(range(1, numbers[-1] + 1)):
        return _integrity(result, "entry_numbers_not_contiguous")                     # R1
    highest = numbers[-1]
    parsed: dict[int, dict[str, Any]] = {}
    for number, data in jsons.items():
        envelope = parse_entry(data)
        if envelope is None:
            if number != highest:
                return _integrity(result, f"unsealed_entry_before_tail:{number}")     # R2
            result.torn_tail = number
            continue
        if envelope["entry"] != number:
            return _integrity(result, f"entry_number_differs_from_name:{number}")
        parsed[number] = envelope
    trailing: list[int] = []
    for number in reversed([n for n in numbers if n != result.torn_tail]):
        if number in torns:
            trailing.append(number)
        else:
            break
    trailing.reverse()
    grammar = _RunGrammar(spec)
    pending: list[tuple[int, str]] = []
    for number in numbers:
        if number in torns:
            if number == 1 and len(numbers) > 1 and any(n in parsed for n in numbers):
                return _integrity(result, "torn_entry_1_with_later_entries")          # R4
            pending.append((number, sha256_bytes(torns[number])))
            continue
        if number == result.torn_tail:
            continue
        envelope = parsed[number]
        try:
            grammar.accept(envelope, pending)                                          # R3
        except ValueError as exc:
            return _integrity(result, f"grammar:{exc}")
        pending = []
        result.entries.append(envelope)
    if pending and [n for n, _ in pending] != trailing:
        return _integrity(result, "torn_entry_not_acknowledged")                       # R4
    result.position = grammar.position
    if result.torn_tail is not None:                                                    # R5
        result.state = "torn_tail"
        return result
    if trailing:                                                                        # R6
        result.tear = pending
        kind, klass = grammar.predict()
        if klass == "terminal":
            return _integrity(result, "tear_after_terminal_entry")
        result.state, result.predicted, result.predicted_class = "torn_pending", kind, klass
        return result
    last = grammar.last
    assert last is not None
    kind = last["kind"]
    if kind == "completed":
        result.state = "completed"                                                      # R7
    elif kind == "closed":
        result.state = "closed"                                                         # R8
    elif kind == "scored":
        result.state = "scored"                                                         # R9
    elif kind == "scoring_started":
        result.state = "scoring_interrupted"                                            # R10
    elif kind == "execution_started":
        result.state, result.position = "execution_in_doubt", int(last["payload"]["position"])   # R11
    elif kind == "call_started":
        result.state, result.position = "in_doubt", int(last["payload"]["position"])              # R12
    elif _failure_reason(last):
        result.state = "faulted"                                                        # R13
    elif kind == "call_recorded" and last["payload"]["position"] in spec.coding:
        result.state = "awaiting_execution"                                             # R14
    elif grammar.collected:
        result.state = "collected"                                                      # R15
    elif kind in ("call_recorded", "execution_recorded"):
        result.state = "collecting"                                                     # R16
    else:
        result.state = "created"                                                        # R17
    return result


def _integrity(result: Replay, reason: str) -> Replay:
    result.state, result.reason = "integrity_failure", reason
    result.entries = []
    return result


def closed_reason_for(replay: Replay, spec: RunSpec, *, acknowledging: bool, requested: str = "") -> str:
    """The reason R3 requires for a closed entry published now (used by recovery and commands)."""
    grammar = _RunGrammar(spec)
    for entry in replay.entries:
        grammar.last = entry
    grammar.position = replay.position
    grammar.collected = replay.state in ("collected", "scoring_interrupted", "scored")
    grammar.terminal = replay.state in ("completed", "closed")
    allowed = grammar.expected_closed_reason([1] if acknowledging else [])
    if allowed is None:
        raise ValueError("closed_not_permitted_here")
    if requested and (requested in allowed or (ABANDON_PREFIX in allowed and requested.startswith(ABANDON_PREFIX))):
        return requested
    if len(allowed) == 1:
        return allowed[0]
    raise ValueError("closed_reason_requires_operator_choice")


# ---------------------------------------------------------------- facts helpers used by the lifecycle

def sealed_protective(files: Mapping[str, bytes], spec: RunSpec) -> bool:
    """§9.4, file by file and independent of the chain: a clean non-coding call_recorded of position N, a clean
    execution_recorded of position N, or any derived entry. Temporary files are excluded (only NNNNNN.json)."""
    for name, data in files.items():
        if not ENTRY_NAME.match(name):
            continue                          # temporary files are excluded; .json and sealing .torn count
        envelope = parse_entry(data)
        if envelope is None:
            continue
        kind, payload = envelope["kind"], envelope["payload"]
        if kind in DERIVED_KINDS:
            return True
        if kind in ("call_recorded", "execution_recorded") and not _failure_reason(envelope) \
                and payload.get("position") == spec.calls:
            if kind == "execution_recorded" or spec.calls not in spec.coding:
                return True
    return False


# ---------------------------------------------------------------- ledger (§9.1)

@dataclass
class LedgerReplay:
    state: str                      # ok | absent | torn_tail | torn_pending | integrity_failure
    reason: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)
    tear: list[tuple[int, str]] = field(default_factory=list)
    torn_tail: int | None = None
    pair_to_unlink: list[int] = field(default_factory=list)
    temps: list[str] = field(default_factory=list)
    orphan_temps: list[str] = field(default_factory=list)
    foreign: list[str] = field(default_factory=list)
    consumed: dict[int, dict[str, Any]] = field(default_factory=dict)       # attempt -> attempt_consumed payload
    closed_at_ledger: dict[int, dict[str, Any]] = field(default_factory=dict)

    @property
    def head(self) -> str | None:
        return self.entries[-1]["record_sha256"] if self.entries else None

    @property
    def next_number(self) -> int:
        return len(self.entries) + len(self.tear) + (1 if self.torn_tail else 0) + 1


def replay_ledger(files: Mapping[str, bytes], phase: str, root_id: str, *, extra_names: Iterable[str] = ()
                  ) -> LedgerReplay:
    probe = Replay(state="")
    split = _classify_names(files, extra_names, probe)
    result = LedgerReplay(state="", temps=probe.temps, orphan_temps=probe.orphan_temps, foreign=probe.foreign,
                          pair_to_unlink=probe.pair_to_unlink)
    if split is None:
        result.state, result.reason = "integrity_failure", probe.reason
        return result
    jsons, torns = split
    numbers = sorted(set(jsons) | set(torns))
    if not numbers:
        result.state = "absent"
        return result
    if numbers != list(range(1, numbers[-1] + 1)):
        return _ledger_integrity(result, "ledger_numbers_not_contiguous")
    highest = numbers[-1]
    owner = f"ledger-{phase}"
    previous = genesis_seal(phase, root_id)
    pending: list[tuple[int, str]] = []
    for number in numbers:
        if number in torns:
            pending.append((number, sha256_bytes(torns[number])))
            continue
        envelope = parse_entry(jsons[number])
        if envelope is None:
            if number != highest:
                return _ledger_integrity(result, f"ledger_unsealed_before_tail:{number}")
            result.torn_tail = number
            continue
        try:
            _ledger_accept(result, envelope, number, owner, previous, pending)
        except ValueError as exc:
            return _ledger_integrity(result, f"ledger_grammar:{exc}")
        previous = envelope["record_sha256"]
        pending = []
        result.entries.append(envelope)
    if result.torn_tail is not None:
        result.state = "torn_tail"
    elif pending:
        result.tear, result.state = pending, "torn_pending"
    else:
        result.state = "ok"
    return result


def _ledger_accept(result: LedgerReplay, envelope: Mapping[str, Any], number: int, owner: str, previous: str,
                   pending: list[tuple[int, str]]) -> None:
    if envelope["entry"] != number or envelope["run_id"] != owner:
        raise ValueError("ledger_identity")
    if envelope["previous_entry_sha256"] != previous:
        raise ValueError("ledger_previous_seal")
    acks = [(int(row.get("entry", -1)), str(row.get("sha256", ""))) for row in envelope["acknowledges"]]
    if acks != pending:
        raise ValueError("ledger_acknowledges_mismatch")
    kind, payload = envelope["kind"], envelope["payload"]
    if kind not in LEDGER_KINDS:
        raise ValueError(f"ledger_kind:{kind}")
    if acks and kind != "ledger_torn_acknowledged":
        raise ValueError("ledger_acknowledges_on_wrong_kind")
    if kind == "attempt_consumed":
        attempt = int(payload.get("attempt", -1))
        if attempt != len(result.consumed) + 1:
            raise ValueError("ledger_attempt_number")
        result.consumed[attempt] = dict(payload)
    elif kind == "attempt_closed_at_ledger":
        attempt = int(payload.get("attempt", -1))
        if attempt not in result.consumed or attempt in result.closed_at_ledger:
            raise ValueError("ledger_closure_of_unknown_or_closed_attempt")
        if payload.get("reason") not in LEDGER_CLOSURE_REASONS:
            raise ValueError("ledger_closure_reason")
        result.closed_at_ledger[attempt] = dict(payload)
    else:
        if not acks:
            raise ValueError("ledger_ack_without_tear")
        consumed = payload.get("consumed_and_closed")
        if consumed is not None:
            attempt = int(consumed.get("attempt", -1))
            if attempt != len(result.consumed) + 1:
                raise ValueError("ledger_ack_attempt_number")
            result.consumed[attempt] = dict(consumed)
            result.closed_at_ledger[attempt] = {"attempt": attempt, "reason": "durability_uncertain",
                                                "via": "ledger_torn_acknowledged"}


def _ledger_integrity(result: LedgerReplay, reason: str) -> LedgerReplay:
    result.state, result.reason = "integrity_failure", reason
    result.entries = []
    return result


__all__ = ["ENTRY_NAME", "TEMP_NAME", "ORPHAN_TEMP", "RUN_KINDS", "DERIVED_KINDS", "LEDGER_KINDS", "ABANDON_PREFIX",
           "safe_value", "canonical_bytes", "digest", "sha256_bytes", "text_to_b64", "b64_to_text", "genesis_seal",
           "entry_name", "make_entry", "parse_entry", "RunSpec", "Replay", "replay_run", "closed_reason_for",
           "sealed_protective", "LedgerReplay", "replay_ledger"]
