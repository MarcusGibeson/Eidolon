from __future__ import annotations

"""Hierarchical experiment reviewer (contract v2732.0): bounded intermediate synthesis.

A NEW reviewer, not a change to the qualified one. ``experiment_review`` (v2731.8) stays byte-for-byte as the
historical baseline and is imported here for every primitive this version does not change: package loading, chunking,
observation grounding, statement validation, part and document planning, the mutation guard and the ledger.

Why this exists
---------------
In v2731.8 the final synthesis receives every document statement plus every uncaptured input, so its input block grows
roughly linearly with part count. The capacity qualification measured that block at 98.9% of its 12,000-character
budget at 34 parts, with the hard 8,192-token context ceiling only a few parts beyond.

What changes
------------
One level is inserted between document synthesis and final synthesis::

    part review -> document synthesis -> bounded intermediate synthesis -> final synthesis -> mechanical verification

The intermediate level is a **bounded fan-in reduction tree**, not a single pass. Inputs are partitioned in stable
order into groups of at most ``GROUP_MAX_INPUTS``; each group emits at most ``GROUP_MAX_STATEMENTS`` statements;
inputs no group cited are carried forward unchanged and re-enter the next round, where they get another chance to be
captured. Rounds repeat until the surviving input count is at most ``FINAL_MAX_INPUTS``.

Carry-forward alone does not converge. A model that cites little leaves most inputs uncited every round, and the
surviving count approaches a fixed point above the cap - the first build of this module stalled at exactly that.
So each round has a floor: it must shrink to at most ``MIN_REDUCTION`` of its input count, and when it would not,
the **minimum** number of uncited inputs needed to make progress is folded into one deterministic register for that
round. A register keeps the folded inputs' identifiers and their full observation lineage, so the accounting is
untouched and the artifact still lists every one of them; what stops travelling onward is only their prose. Which
inputs are folded is decided by how many rounds they have already gone uncited and then by stable position, never
by what they say.

Three things therefore fail closed rather than degrade:

* the round limit (``intermediate_synthesis_did_not_converge``) and the round width (``intermediate_round_too_wide``);
* a round that still fails to shrink (``intermediate_synthesis_did_not_reduce``);
* and, because a bounded review is not automatically a meaningful one, a final synthesis that would receive less
  than ``MIN_SYNTHESISED_REPRESENTATION`` of the evidence as prose rather than as register pointers
  (``final_representation_below_floor``).

That last check is stricter than the baseline. Where v2731.8 would carry a thin review through to a final object,
this version refuses it. The difference is deliberate and is reported in the qualification record.

Nothing is dropped to achieve the bound. Every observation accepted upstream is, at every level, either cited by a
statement or explicitly carried forward, and the closing accounting recomputes that from the artifact rather than
trusting the loop.
"""

from collections import Counter
import contextlib
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
import uuid

import experiment_review as base
from json_storage import write_text_atomic

CONTRACT_VERSION = "v2732.0"
BASELINE_CONTRACT = base.CONTRACT_VERSION
REVIEW_AREA = base.REVIEW_AREA
MANIFEST_NAME = base.MANIFEST_NAME

# --- the bound -------------------------------------------------------------------------------------------------------
# Both limits in requirement 10 are explicit: how big one group may be, and how many groups a round may have.
GROUP_MAX_INPUTS = 12          # inputs one intermediate group may synthesise
GROUP_MAX_STATEMENTS = 4       # statements one intermediate group may emit
GROUP_INPUT_BUDGET_CHARS = 6000  # a group prompt stays inside the same per-unit budget the document level uses
MAX_GROUPS_PER_ROUND = 32      # a round wider than this fails closed rather than fanning out without limit
FINAL_MAX_INPUTS = 32          # the structural cap on final synthesis input
MAX_ROUNDS = 12                # reduction rounds before the review fails closed (see the bound below)
MIN_REDUCTION = 0.80           # a round must shrink to at most this share, or uncited inputs are folded
MIN_SYNTHESISED_REPRESENTATION = 0.5  # share of observations that must reach the final as prose, not as a pointer
GROUP_MAX_TOKENS = 2048

# Worst-case rounds to reach the cap from N surviving inputs is ceil(log(FINAL_MAX_INPUTS / N) / log(MIN_REDUCTION)),
# because every round is guaranteed to shrink by at least MIN_REDUCTION. At MIN_REDUCTION = 0.80 and a cap of 32 that
# is 11 rounds from 320 inputs, which is the document-level input count of a 64-part package at 5 observations per
# part. MAX_ROUNDS = 12 therefore covers the qualification envelope with one round to spare, and anything beyond it
# fails closed rather than running unbounded.
#
# Final input block bound, independent of part count:
#     FINAL_MAX_INPUTS * (MAX_STATEMENT_CHARS + FINAL_LINE_OVERHEAD_CHARS + 1)
#   = 32 * (200 + 40 + 1) = 7,712 characters
# against base.FINAL_INPUT_BUDGET_CHARS (12,000) and the measured hard context ceiling of 13,488 characters at the
# binding final:second_half stage on an 8,192-token window. See docs/REVIEWER_CAPACITY_QUALIFICATION.md.
FINAL_INPUT_BOUND_CHARS = FINAL_MAX_INPUTS * (base.MAX_STATEMENT_CHARS + base.FINAL_LINE_OVERHEAD_CHARS + 1)

GROUP_PROMPT = (
    base.FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Below are syntheses and uncaptured evidence drawn from across the package, group {group} of {groups} in "
    "consolidation round {round}. Each has an id and, in brackets, where it came from:\n"
    "{inputs}\n"
    "Write a consolidated synthesis of these inputs for the final review. " + base._PRESERVE +
    "Each statement must cite the ids of the inputs it rests on (input_ids, at most {max_ids}). Inputs you leave out "
    "are carried forward unchanged, so cite only what a statement actually rests on. Give at most {max_statements} "
    "statements, each at most {max_chars} characters, and label each with one kind: {kinds}.\n"
    'Return only JSON: {{"statements": [{{"statement": "...", "kind": "finding", "input_ids": ["DS1"]}}]}}'
)
FINAL_A_PROMPT = base.FINAL_A_PROMPT.replace(
    "These are syntheses of the package's grounded observations: document-level statements (DS ids) and, marked as "
    "uncaptured, part-level statements (PS ids) and observations (O ids) that no higher-level statement captured.",
    "These are consolidated syntheses of the package's grounded observations: group statements (GS ids), document "
    "statements (DS ids) and, marked as uncaptured, part statements (PS ids) and observations (O ids) that no higher "
    "statement captured.")
FINAL_B_PROMPT = base.FINAL_B_PROMPT


# --- the review-id vocabulary ----------------------------------------------------------------------------------------
# The baseline treats a token with letters and digits as a factual identifier that must be supported by the evidence,
# and exempts its own bookkeeping labels O1 / PS1 / DS1 because they name inputs rather than assert anything. This
# version mints two more label kinds, GS (group statement) and U (uncaptured register), which the baseline's exemption
# does not know about - so a statement that legitimately wrote "GS1 and DS4 disagree" would be rejected for an
# unsupported identifier.
#
# The fix extends the exemption to exactly those two prefixes and nothing else. It is deliberately not a general
# relaxation: every genuinely unknown identifier is still rejected, and the baseline's own vocabulary is unchanged
# when the baseline runs. The extension is scoped to one v2732.0 review by the context manager below and is always
# restored, so a v2731.8 review in the same process keeps the stricter vocabulary.
_REVIEW_ID = re.compile(r"(?:gs|u)[0-9]+")


def _identifiers(text: Any) -> set[str]:
    """The baseline's identifier extraction, less this version's two extra label kinds."""
    return {token for token in _BASE_IDENTIFIERS(text) if not _REVIEW_ID.fullmatch(token)}


_BASE_IDENTIFIERS = base._identifiers


@contextlib.contextmanager
def review_id_vocabulary():
    """Make GS and U count as review labels for the duration of one v2732.0 review, then put the baseline back."""
    if base._identifiers is _identifiers:
        raise RuntimeError("review_id_vocabulary_is_not_reentrant")
    original = base._identifiers
    base._identifiers = _identifiers
    try:
        yield
    finally:
        base._identifiers = original


def _input_line(item: Mapping[str, Any], level: str) -> str:
    """Render one input for the next level. Group statements are new; everything else defers to the baseline."""
    if item["type"] == "group_statement":
        return f"{item['id']} [round {item['round']}, {item['kind']}]: {item['statement']}"
    return base.input_line(item, level)


def _block(ids: Sequence[str], items: Mapping[str, Mapping[str, Any]], level: str) -> str:
    return "\n".join(_input_line(items[i], level) for i in ids)


def plan_group_units(inputs: Sequence[str], items: Mapping[str, Mapping[str, Any]], round_no: int) -> list[dict[str, Any]]:
    """Partition inputs into deterministic consecutive groups, in stable order, bounded by count and characters.

    Order is the order the inputs already have, which derives from document order and then part order. No input is
    chosen for what it says, so grouping cannot select evidence for a desired conclusion.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    size = 0
    for input_id in inputs:
        chars = len(_input_line(items[input_id], "group")) + 1
        if current and (len(current) + 1 > GROUP_MAX_INPUTS or size + chars > GROUP_INPUT_BUDGET_CHARS):
            groups.append(current)
            current, size = [], 0
        current.append(input_id)
        size += chars
    if current:
        groups.append(current)
    return [{"unit_id": f"GU{round_no}.{n + 1}", "stage": f"group:r{round_no}:g{n + 1}", "round": round_no,
             "group": n + 1, "groups": len(groups), "inputs": list(g), "required": True,
             "max_statements": min(GROUP_MAX_STATEMENTS, max(1, math.ceil(len(g) / 2)))}
            for n, g in enumerate(groups)]


def review_experiment(package_dir: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Review one package with bounded intermediate synthesis, under this version's review-id vocabulary."""
    with review_id_vocabulary():
        return _review_experiment(package_dir, **kwargs)


def _review_experiment(package_dir: str | Path, *, call_model: Callable[[str, int], tuple[str, dict[str, Any]]] | None = None,
                       runtime_root_path: str | Path | None = None, source_root: str | Path | None = None,
                       protected_paths: Iterable[str | Path] = (), protected_roots: Iterable[str | Path] = (),
                       identity: Mapping[str, Any] | None = None, clock: Callable[[], str] = base._now) -> dict[str, Any]:
    package = base.load_package(package_dir)
    root = base.runtime_root(runtime_root_path)
    area = root / REVIEW_AREA
    started = clock()
    review_id = hashlib.sha256(f"{package['manifest_sha256']}|{started}|{uuid.uuid4().hex}".encode()).hexdigest()[:16]
    out_dir = area / review_id
    if out_dir.exists():
        raise FileExistsError(f"review directory already exists: {out_dir}")
    guarded_roots = [root, *[Path(r).expanduser().resolve() for r in protected_roots]]
    guarded_paths = [Path(p).expanduser().resolve() for p in protected_paths]
    src = Path(source_root).expanduser().resolve() if source_root is not None else None
    before = base.snapshot_protected(source_root=src, package_dir=package["dir"], protected_paths=guarded_paths,
                                     protected_roots=guarded_roots, review_area=out_dir)
    call_model = call_model or base.production_call_model()
    ident = dict(identity) if identity is not None else base.model_identity()
    context_size = ident.get("context_size") if isinstance(ident.get("context_size"), int) else None

    ledger: list[dict[str, Any]] = []
    grounded: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    parts_coverage: list[dict[str, Any]] = []

    # --- level 0: package parts -> grounded observations ---------------------------------------------------------
    absent_roles = [r for r in base.REQUIRED_ROLES if r not in {d["role"] for d in package["documents"]}]
    if not absent_roles:
        for doc in package["documents"]:
            parts, offset = base.chunks(doc["text"]), 0
            for part, chunk_text in enumerate(parts, 1):
                stage = f"observe:{doc['doc_id']}:{part}"
                prompt = base.OBSERVE_PROMPT.format(
                    title=package["title"], brief=package["brief"], doc_id=doc["doc_id"], role=doc["role"],
                    description=doc["description"], part=part, parts=len(parts), chunk=chunk_text,
                    max_obs=base.MAX_OBSERVATIONS_PER_CHUNK, max_quotes=base.MAX_QUOTES_PER_OBSERVATION,
                    max_quote=base.MAX_QUOTE_CHARS)
                parsed, reason = base._ask(call_model, prompt, base.OBSERVE_MAX_TOKENS,
                                           lambda p: isinstance(p.get("observations"), list), ledger, stage,
                                           context_size=context_size)
                g: list[dict[str, Any]] = []
                r: list[dict[str, Any]] = []
                if parsed is not None:
                    g, r, q = base.ground_observations(parsed, chunk_text, doc["doc_id"], part, len(grounded) + 1,
                                                       doc_text=doc["text"], chunk_offset=offset,
                                                       rejected_start=len(rejected) + 1)
                    grounded += g
                    rejected += r
                    questions += [{"doc_id": doc["doc_id"], "part": part, "question": x} for x in q]
                    reason = None if g else "no_grounded_observations"
                parts_coverage.append({"stage": stage, "doc_id": doc["doc_id"], "role": doc["role"], "part": part,
                                       "parts": len(parts), "required": doc["required"], "reviewed": reason is None,
                                       "reason": reason, "attempts": sum(x["stage"] == stage for x in ledger),
                                       "grounded_observations": len(g), "rejected_observations": len(r)})
                offset += len(chunk_text)

    required = [p for p in parts_coverage if p["required"]]
    optional = [p for p in parts_coverage if not p["required"]]
    missing: list[dict[str, Any]] = [
        {"kind": "required_role_absent", "role": role, "reason": "the package lists no document with this required role"}
        for role in absent_roles]
    missing += [{"kind": "required_part_not_reviewed", "stage": p["stage"], "doc_id": p["doc_id"], "part": p["part"],
                 "reason": p["reason"]} for p in required if not p["reviewed"]]
    rejected_ids = {o["rej_id"] for o in rejected}

    items: dict[str, dict[str, Any]] = {
        o["obs_id"]: {"id": o["obs_id"], "type": "observation", "doc_id": o["doc_id"], "part": o["part"],
                      "statement": o["statement"], "lineage": [o["obs_id"]],
                      "meta": base._metadata_label(o["provenance"]["metadata"])} for o in grounded}
    evidence = {o["obs_id"]: base.observation_evidence(o) for o in grounded}

    part_units: list[dict[str, Any]] = []
    doc_units: list[dict[str, Any]] = []
    group_rounds: list[dict[str, Any]] = []
    uncaptured_registers: list[str] = []
    carry_counts: dict[str, int] = {}
    part_statements: list[str] = []
    doc_statements: list[str] = []
    group_statements: list[str] = []
    rejected_statements: list[dict[str, Any]] = []
    carried_to_document: list[str] = []
    carried_to_intermediate: list[str] = []
    final_inputs: list[str] = []
    dropped_refs: list[str] = []

    def run_unit(unit: dict[str, Any], prompt: str, max_tokens: int, ids_key: str, prefix: str, kind: str,
                 extra: Callable[[dict], dict]) -> str | None:
        parsed, reason = base._ask(call_model, prompt, max_tokens, base._accept_statements, ledger, unit["stage"],
                                   context_size=context_size)
        unit["attempts"] = sum(x["stage"] == unit["stage"] for x in ledger)
        if parsed is None:
            unit.update(status=f"failed:{reason}", cited=[], uncited=list(unit["inputs"]), statements=[])
            return reason
        kept, dropped = base.validate_statements(parsed, unit, items, evidence, ids_key=ids_key)
        cited = {i for s in kept for i in s["cites"]}
        unit.update(status="accepted", cited=[i for i in unit["inputs"] if i in cited],
                    uncited=[i for i in unit["inputs"] if i not in cited], statements=[],
                    rejected_statements=len(dropped))
        for s in kept:
            sid = f"{prefix}{sum(1 for x in items.values() if x['type'] == kind) + 1}"
            items[sid] = {"id": sid, "type": kind, "unit_id": unit["unit_id"], "kind": s["kind"],
                          "statement": s["statement"], "cites": s["cites"], "dropped_cites": s["dropped_cites"],
                          "lineage": base.lineage_of(s["cites"], items), **extra(s)}
            unit["statements"].append(sid)
        rejected_statements.extend({"level": unit["stage"].split(":")[0], "unit_id": unit["unit_id"], **d}
                                   for d in dropped)
        dropped_refs.extend(i for s in kept + dropped for i in s["dropped_cites"])
        return None

    # --- level 1: grounded observations -> per-part synthesis ----------------------------------------------------
    if not missing:
        part_units = base.plan_part_units(package, grounded)
        for unit in part_units:
            reason = run_unit(unit, base.part_prompt(package, unit, items), base.PART_MAX_TOKENS, "obs_ids", "PS",
                              "part_statement", lambda s, unit=unit: {"part": unit["part"], "doc_id": unit["doc_id"]})
            if reason and unit["required"]:
                missing.append({"kind": "synthesis_stage_failed", "level": "part", "unit_id": unit["unit_id"],
                                "stage": unit["stage"], "doc_id": unit["doc_id"], "parts": [unit["part"]],
                                "reason": reason, "inputs_lost_at_stage": unit["inputs"]})
        part_statements = [i for u in part_units for i in u.get("statements", [])]
        carried_to_document = [i for u in part_units if u.get("status") == "accepted" or not u["required"]
                               for i in u["uncited"]]

    # --- level 2: per-document synthesis -------------------------------------------------------------------------
    if not missing:
        part_inputs = {(u["doc_id"], u["part"]): u["statements"] + u["uncited"] for u in part_units}
        doc_units = base.plan_document_units(package, part_units, items, part_inputs)
        for unit in doc_units:
            unit["max_statements"] = max(1, math.ceil(len(unit["inputs"]) / 2))
        for unit in doc_units:
            reason = run_unit(unit, base.document_prompt(package, unit, items), base.DOCUMENT_MAX_TOKENS,
                              "input_ids", "DS", "document_statement",
                              lambda s, unit=unit: {"parts": unit["parts"], "doc_id": unit["doc_id"]})
            if reason and unit["required"]:
                missing.append({"kind": "synthesis_stage_failed", "level": "document", "unit_id": unit["unit_id"],
                                "stage": unit["stage"], "doc_id": unit["doc_id"], "parts": unit["parts"],
                                "reason": reason, "inputs_lost_at_stage": unit["inputs"]})
        doc_statements = [i for u in doc_units for i in u.get("statements", [])]
        carried_to_intermediate = [i for u in doc_units if u.get("status") == "accepted" or not u["required"]
                                   for i in u["uncited"]]

    # --- level 2.5: bounded intermediate synthesis ---------------------------------------------------------------
    # Reduce until the surviving count fits the structural final cap, or fail closed. Never bypass, never fall back.
    surviving: list[str] = []
    if not missing:
        order = {u["unit_id"]: n for n, u in enumerate(doc_units)}
        surviving = doc_statements + sorted(
            carried_to_intermediate,
            key=lambda i: (next(order[u["unit_id"]] for u in doc_units if i in u["inputs"]), i))
        round_no = 0
        while len(surviving) > FINAL_MAX_INPUTS and not missing:
            round_no += 1
            if round_no > MAX_ROUNDS:
                missing.append({"kind": "intermediate_synthesis_did_not_converge", "rounds": MAX_ROUNDS,
                                "surviving_inputs": len(surviving), "cap": FINAL_MAX_INPUTS,
                                "reason": "consolidation did not reach the final input cap within the round limit"})
                break
            # Registers are already minimal; they pass through untouched rather than being re-consolidated.
            groupable = [i for i in surviving if items[i]["type"] != "uncaptured_register"]
            registers_in = [i for i in surviving if items[i]["type"] == "uncaptured_register"]
            units = plan_group_units(groupable, items, round_no)
            if len(units) > MAX_GROUPS_PER_ROUND:
                missing.append({"kind": "intermediate_round_too_wide", "round": round_no, "groups": len(units),
                                "limit": MAX_GROUPS_PER_ROUND, "inputs": len(surviving),
                                "reason": "a consolidation round exceeded the group-count limit"})
                break
            produced: list[str] = []
            carried: list[str] = []
            for unit in units:
                prompt = GROUP_PROMPT.format(
                    title=package["title"], brief=package["brief"], group=unit["group"], groups=unit["groups"],
                    round=round_no, inputs=_block(unit["inputs"], items, "group"), max_ids=base.MAX_IDS_PER_STATEMENT,
                    max_statements=unit["max_statements"], max_chars=base.MAX_STATEMENT_CHARS,
                    kinds=", ".join(base.SYNTHESIS_KINDS))
                reason = run_unit(unit, prompt, GROUP_MAX_TOKENS, "input_ids", "GS", "group_statement",
                                  lambda s, unit=unit: {"round": unit["round"], "group": unit["group"],
                                                        "doc_id": f"round {unit['round']}"})
                if reason:
                    missing.append({"kind": "synthesis_stage_failed", "level": "intermediate",
                                    "unit_id": unit["unit_id"], "stage": unit["stage"], "round": round_no,
                                    # doc_id and parts keep the baseline's missing-coverage renderer working; an
                                    # intermediate group spans documents, so it is labelled by its round.
                                    "doc_id": f"round {round_no}", "parts": [],
                                    "reason": reason, "inputs_lost_at_stage": unit["inputs"]})
                    break
                produced += unit["statements"]
                carried += unit["uncited"]
            if missing:
                break
            for input_id in carried:
                carry_counts[input_id] = carry_counts.get(input_id, 0) + 1
            nxt = produced + carried + registers_in
            folded: list[str] = []
            kept_verbatim = list(carried)
            # Convergence guarantee. Verbatim carry-forward is kept while it is affordable, exactly as the baseline
            # does. When a round does not shrink enough, only the MINIMUM number of uncited inputs needed to make
            # progress is folded into a single deterministic register: identifiers and full lineage are preserved,
            # so every observation still has an explicit downstream state and the artifact keeps the complete list.
            # Only their prose stops travelling to the final prompt, which is what makes the bound hold.
            #
            # Which ones are folded is decided by how many rounds an input has already gone uncited, then by stable
            # position - never by what it says. Evidence the model keeps declining to cite is folded before evidence
            # it has only just seen.
            target = int(MIN_REDUCTION * len(surviving))
            room = max(0, target - len(produced) - len(registers_in) - 1)
            if carried and len(nxt) > target and room < len(carried):
                order_index = {input_id: n for n, input_id in enumerate(carried)}
                ranked = sorted(carried, key=lambda i: (-carry_counts.get(i, 0), order_index[i]))
                kept_verbatim = sorted(ranked[:room], key=lambda i: order_index[i])
                folded = sorted(ranked[room:], key=lambda i: order_index[i])
                register_id = f"U{round_no}"
                lineage = base.lineage_of(folded, items)
                docs = sorted({items[i].get("doc_id", "") for i in folded} - {""})
                items[register_id] = {
                    "id": register_id, "type": "uncaptured_register", "round": round_no, "kind": "unknown",
                    "doc_id": f"round {round_no}", "covers": list(folded), "lineage": lineage, "cites": [],
                    "statement": (f"{len(folded)} input(s) resting on {len(lineage)} observation(s) from "
                                  f"{', '.join(docs) or 'the package'} that no synthesis statement cited across "
                                  f"{round_no} round(s); unrepresented above, not discarded")}
                nxt = produced + kept_verbatim + [register_id] + registers_in
            group_rounds.append({"round": round_no, "units": len(units), "inputs": len(surviving),
                                 "statements": len(produced), "carried": len(carried), "folded": len(folded),
                                 "kept_verbatim": len(kept_verbatim),
                                 "registers_in": len(registers_in), "surviving": len(nxt),
                                 "reduction": round(len(nxt) / len(surviving), 4) if surviving else 0.0,
                                 "accepted": sum(u.get("status") == "accepted" for u in units),
                                 "unit_ids": [u["unit_id"] for u in units]})
            group_statements += produced
            if folded:
                uncaptured_registers.append(register_id)
            if len(nxt) >= len(surviving):
                missing.append({"kind": "intermediate_synthesis_did_not_reduce", "round": round_no,
                                "inputs": len(surviving), "surviving": len(nxt),
                                "reason": "a consolidation round did not reduce the surviving input count"})
                break
            surviving = nxt
        final_inputs = list(surviving)

    # --- level 3: final synthesis --------------------------------------------------------------------------------
    first = second = None
    first_half: dict[str, Any] = {}
    second_half: dict[str, Any] = {}
    final_rejected: list[dict[str, Any]] = []
    final_unknown: list[str] = []
    final_state = {"first_half": "skipped:earlier_coverage_incomplete", "second_half": "skipped:earlier_coverage_incomplete"}
    block = ""
    if not missing:
        block = _block(final_inputs, items, "final")
        if len(final_inputs) > FINAL_MAX_INPUTS:
            missing.append({"kind": "final_input_count_exceeds_bound", "inputs": len(final_inputs),
                            "bound": FINAL_MAX_INPUTS, "reason": "the structural final input cap was not honoured"})
        elif len(block) > base.FINAL_INPUT_BUDGET_CHARS:
            missing.append({"kind": "final_input_exceeds_budget", "chars": len(block),
                            "budget": base.FINAL_INPUT_BUDGET_CHARS,
                            "reason": "the final input block exceeded the configured budget"})
    if not missing:
        known = set(final_inputs)
        first, reason_a = base._ask(call_model, FINAL_A_PROMPT.format(title=package["title"], brief=package["brief"],
                                                                     inputs=block),
                                    base.FINAL_A_MAX_TOKENS, base._accept_final_first, ledger, "final:first_half",
                                    context_size=context_size)
        if first is None:
            final_state = {"first_half": f"failed:{reason_a}", "second_half": "skipped:first_half_failed"}
            missing.append({"kind": "final_synthesis_failed", "stage": "final:first_half", "reason": reason_a})
        else:
            first_half, rej, unk = base.validate_final_first(first, known, items, evidence)
            final_rejected += rej
            final_unknown += unk
            second, reason_b = base._ask(
                call_model, FINAL_B_PROMPT.format(title=package["title"], brief=package["brief"], inputs=block,
                                                  first_half=base.first_half_summary(first_half)),
                base.FINAL_B_MAX_TOKENS, base._accept_final_second, ledger, "final:second_half",
                context_size=context_size)
            final_state = {"first_half": "accepted", "second_half": "accepted" if second else f"failed:{reason_b}"}
            if second is None:
                missing.append({"kind": "final_synthesis_failed", "stage": "final:second_half", "reason": reason_b})
            else:
                second_half, rej, unk = base.validate_final_second(second, known, items, evidence)
                final_rejected += rej
                final_unknown += unk
    review = {**first_half, **second_half}

    # --- mechanical verification ---------------------------------------------------------------------------------
    represented = set(base.lineage_of(final_inputs, items))
    # Bounded is not the same as meaningful. A register entry keeps an observation accounted for, but the final
    # synthesis cannot reason about prose it never sees. If too little of the evidence reaches the final as an
    # actual statement, the review is not a finished analysis and must fail closed rather than emit a thin object.
    synthesised_inputs = [i for i in final_inputs if items[i]["type"] != "uncaptured_register"]
    synthesised_lineage = set(base.lineage_of(synthesised_inputs, items))
    register_only = sorted(represented - synthesised_lineage)
    representation = round(len(synthesised_lineage) / len(grounded), 4) if grounded else 0.0
    if final_inputs and not missing and representation < MIN_SYNTHESISED_REPRESENTATION:
        missing.append({"kind": "final_representation_below_floor", "representation": representation,
                        "floor": MIN_SYNTHESISED_REPRESENTATION,
                        "observations_reaching_final_as_statements": len(synthesised_lineage),
                        "observations_reaching_final_only_as_register_pointers": len(register_only),
                        "reason": "too little of the evidence reached the final synthesis as prose"})
    cited_finally = base.final_input_ids(review)
    reached = base.lineage_of(cited_finally, items)
    silently_dropped = [o["obs_id"] for o in grounded if o["obs_id"] not in represented] if final_inputs else []
    after = base.snapshot_protected(source_root=src, package_dir=package["dir"], protected_paths=guarded_paths,
                                    protected_roots=guarded_roots, review_area=out_dir)
    changes = base.compare_snapshots(before, after)
    complete = not missing and first is not None and second is not None and not silently_dropped
    status = "mutation_guard_failed" if changes else "complete" if complete else "incomplete"
    ratio = lambda a, b: round(a / b, 4) if b else 0.0  # noqa: E731
    reviewed_required = sum(p["reviewed"] for p in required)
    captured_by_part = {o for i in part_statements for o in items[i]["cites"]}
    doc_cited = {i for u in doc_units for i in u.get("cited", [])}
    group_units_all = [u for r in group_rounds for u in r["unit_ids"]]
    kinds_preserved = Counter(items[i]["kind"] for i in part_statements + doc_statements + group_statements)

    coverage = {
        "complete": complete, "required_parts": len(required), "reviewed_required_parts": reviewed_required,
        "required_coverage": ratio(reviewed_required, len(required)), "optional_parts": len(optional),
        "reviewed_optional_parts": sum(p["reviewed"] for p in optional), "required_roles": list(base.REQUIRED_ROLES),
        "absent_required_roles": absent_roles, "grounded_observations": len(grounded),
        "levels": {
            "package_parts": {"required": len(required), "reviewed": reviewed_required,
                              "coverage": ratio(reviewed_required, len(required))},
            "part_synthesis": {"units": len(part_units),
                               "accepted": sum(u.get("status") == "accepted" for u in part_units),
                               "statements": len(part_statements), "observations": len(grounded),
                               "observations_cited": len(captured_by_part),
                               "observations_carried_forward": len(carried_to_document)},
            "document_synthesis": {"units": len(doc_units),
                                   "accepted": sum(u.get("status") == "accepted" for u in doc_units),
                                   "statements": len(doc_statements),
                                   "inputs": sum(len(u["inputs"]) for u in doc_units), "inputs_cited": len(doc_cited),
                                   "inputs_carried_forward": len(carried_to_intermediate)},
            "intermediate_synthesis": {"rounds": group_rounds, "round_count": len(group_rounds),
                                       "units": len(group_units_all), "statements": len(group_statements),
                                       "group_max_inputs": GROUP_MAX_INPUTS,
                                       "group_max_statements": GROUP_MAX_STATEMENTS,
                                       "max_groups_per_round": MAX_GROUPS_PER_ROUND, "max_rounds": MAX_ROUNDS,
                                       "min_reduction": MIN_REDUCTION,
                                       "uncaptured_registers": list(uncaptured_registers),
                                       "register_covered_inputs": sum(len(items[r]["covers"]) for r in uncaptured_registers),
                                       "register_covered_observations": len(base.lineage_of(uncaptured_registers, items)) if uncaptured_registers else 0,
                                       "converged": len(final_inputs) <= FINAL_MAX_INPUTS if final_inputs else None},
            "final": {**final_state, "inputs": len(final_inputs), "input_chars": len(block),
                      "input_bound": FINAL_MAX_INPUTS, "input_bound_chars": FINAL_INPUT_BOUND_CHARS,
                      "input_budget": base.FINAL_INPUT_BUDGET_CHARS, "inputs_cited": len(cited_finally),
                      "inputs_not_cited": len([i for i in final_inputs if i not in set(cited_finally)]),
                      "observations_reached": len(reached), "observation_reach": ratio(len(reached), len(grounded)),
                      "rejected_entries": len(final_rejected)},
            "architecture": {"observations": len(grounded),
                             "represented_in_final_inputs": len(represented & set(items)),
                             "coverage": ratio(len(represented), len(grounded)), "silently_dropped": silently_dropped,
                             "synthesised_representation": representation,
                             "representation_floor": MIN_SYNTHESISED_REPRESENTATION,
                             "observations_as_statements": len(synthesised_lineage),
                             "observations_as_register_pointers": len(register_only)},
        },
        "statement_kinds": dict(sorted(kinds_preserved.items())),
        "rejected_statements": dict(Counter(r["reason"] for r in rejected_statements)),
        "missing": missing, "parts": parts_coverage,
    }

    rejections = Counter(x["rejection"] for x in ledger if x["rejection"])
    stage_order = list(dict.fromkeys(x["stage"] for x in ledger))
    accepted_stages = {x["stage"] for x in ledger if x["accepted"]}
    all_refs = dropped_refs + final_unknown
    record = lambda i: {k: v for k, v in items[i].items()}  # noqa: E731
    artifact = {
        "object": "experiment_review", "contract_version": CONTRACT_VERSION, "baseline_contract": BASELINE_CONTRACT,
        "architecture": "hierarchical_bounded_synthesis", "review_id": review_id, "status": status,
        "non_authoritative": True, "authority": dict(base.REVIEW_AUTHORITY), "coverage": coverage,
        "review": review if (first or second) else {},
        "hierarchy": {"part_units": part_units, "part_statements": [record(i) for i in part_statements],
                      "carried_to_document_level": carried_to_document, "document_units": doc_units,
                      "document_statements": [record(i) for i in doc_statements],
                      "carried_to_intermediate": carried_to_intermediate,
                      "intermediate_rounds": group_rounds,
                      "group_statements": [record(i) for i in group_statements],
                      "uncaptured_registers": [record(i) for i in uncaptured_registers],
                      "final_inputs": final_inputs,
                      "final_inputs_not_cited": [i for i in final_inputs if i not in set(cited_finally)],
                      "rejected_statements": rejected_statements},
        "final_rejected_entries": final_rejected,
        "grounded_observations": grounded, "rejected_observations": rejected, "open_questions": questions,
        "unknown_references": sorted(set(final_unknown) - rejected_ids),
        "dropped_references": sorted(set(dropped_refs) - rejected_ids),
        "rejected_observation_references": sorted(set(all_refs) & rejected_ids),
        "integrity_metrics": {
            "multi_quote_observations": sum(len(o["quotes"]) > 1 for o in grounded),
            "omission_quotes": sum(bool(q.get("omission")) for o in grounded for q in o["quotes"]),
            "observations_with_record_metadata": sum(bool(o["provenance"]["metadata"]) for o in grounded),
            "observations_rejected_for_unsupported_identifiers": sum(r["reason"] == "unsupported_identifiers"
                                                                     for r in rejected)},
        "provenance": {
            "experiment_id": package["experiment_id"], "title": package["title"], "package_dir": str(package["dir"]),
            "manifest_sha256": package["manifest_sha256"],
            "documents": [{k: d[k] for k in ("doc_id", "role", "path", "sha256", "required")}
                          for d in package["documents"]],
            "model": ident, "started": started, "finished": clock(), "task": package["manifest"].get("task"),
            "capability": {"contract_version": CONTRACT_VERSION, "baseline_contract": BASELINE_CONTRACT,
                           "module_sha256": base._sha256_file(Path(__file__).resolve()),
                           "baseline_module_sha256": base._sha256_file(Path(base.__file__).resolve()),
                           "source_tree": before.get("source_tree")},
            "limits": registered_limits() | {"context_size": context_size},
            "prompt_templates_sha256": template_digests(), "mutation_authority": "none",
            "review_id_vocabulary": ["O", "PS", "DS", "GS", "U"]},
        "runtime_accounting": {
            "provider_attempts": len(ledger), "failed_attempts": sum(bool(x.get("error")) for x in ledger),
            "timeout_attempts": sum("Timeout" in str(x.get("error", "")) for x in ledger),
            "unparseable_or_rejected_replies": sum(not x["accepted"] and not x.get("error") for x in ledger),
            "truncated_attempts": rejections["truncated_at_output_limit"] + rejections["context_limit_reached"],
            "retries": sum(x["attempt"] > 1 for x in ledger),
            "prompt_tokens": sum(int((x.get("metrics") or {}).get("prompt_eval_count") or 0) for x in ledger),
            "output_tokens": sum(int((x.get("metrics") or {}).get("eval_count") or 0) for x in ledger),
            "recovered_stages": sorted(s for s in accepted_stages
                                       if any(x["stage"] == s and not x["accepted"] for x in ledger)),
            "rejections_by_reason": dict(sorted(rejections.items())),
            "stages_without_accepted_reply": sorted(set(stage_order) - accepted_stages),
            "terminal_stage_failures": [{"stage": s, "reason": [x for x in ledger if x["stage"] == s][-1]["rejection"]}
                                        for s in stage_order if s not in accepted_stages]},
        "mutation_guard": {"passed": not changes, "changes": changes[:50],
                           "protected": {"source_tree": src is not None, "package": True,
                                         "paths": [str(p) for p in guarded_paths],
                                         "roots": [str(r) for r in guarded_roots], "excluded": str(out_dir)}},
        "ledger": ledger,
    }
    write_text_atomic(out_dir / "review.json", json.dumps(artifact, indent=1, ensure_ascii=False))
    write_text_atomic(out_dir / "review.md", render_markdown(artifact))
    return artifact


def render_markdown(artifact: Mapping[str, Any]) -> str:
    """The baseline rendering, with the intermediate level made visible rather than hidden."""
    shim = dict(artifact)
    hierarchy = dict(artifact["hierarchy"])
    hierarchy["document_statements"] = (hierarchy["document_statements"] + hierarchy.get("group_statements", [])
                                        + hierarchy.get("uncaptured_registers", []))
    shim["hierarchy"] = hierarchy
    text = base.render_markdown(shim)
    rounds = artifact["coverage"]["levels"].get("intermediate_synthesis", {}).get("rounds") or []
    if rounds:
        lines = ["", "## Intermediate consolidation", "",
                 f"Bounded fan-in reduction, {len(rounds)} round(s), to a final input cap of {FINAL_MAX_INPUTS}.", ""]
        for r in rounds:
            lines.append(f"- round {r['round']}: {r['inputs']} inputs in {r['units']} group(s) "
                         f"({r['accepted']} accepted) -> {r['statements']} statement(s) + {r['carried']} carried "
                         f"= {r['surviving']} surviving (x{r['reduction']})")
        text += "\n".join(lines) + "\n"
    return text


def registered_limits() -> dict[str, Any]:
    return dict(base.registered_limits()) | {
        "group_max_inputs": GROUP_MAX_INPUTS, "group_max_statements": GROUP_MAX_STATEMENTS,
        "group_input_budget_chars": GROUP_INPUT_BUDGET_CHARS, "max_groups_per_round": MAX_GROUPS_PER_ROUND,
        "final_max_inputs": FINAL_MAX_INPUTS, "max_rounds": MAX_ROUNDS, "min_reduction": MIN_REDUCTION,
        "min_synthesised_representation": MIN_SYNTHESISED_REPRESENTATION,
        "final_input_bound_chars": FINAL_INPUT_BOUND_CHARS}


def template_digests() -> dict[str, str]:
    return dict(base.template_digests()) | {
        "GROUP_PROMPT": hashlib.sha256(GROUP_PROMPT.encode()).hexdigest(),
        "FINAL_A_PROMPT_V2": hashlib.sha256(FINAL_A_PROMPT.encode()).hexdigest()}
