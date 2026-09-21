# Cooperative pause, durable reviewer checkpoints, and the 140-part scale

**Status: implemented and deterministically qualified. No G-CORROB1 review was launched and no provider was contacted.**

## Why

Eidolon's G-CORROB1 review package is 140 parts. A completed review at that scale is roughly 473 model calls, about
26 hours on this host, and the reviewer wrote nothing until the very end — so any interruption lost everything. The
first review attempt already demonstrated the shape of that risk: it spent 7 h 47 m on the observation pass and then
failed closed with no artifact.

Two things had to change before committing to a run that long: the work had to become resumable, and the hierarchy
had to be qualified at the scale it would actually face.

## 1. The pause contract

`conscious_agent/cooperative_pause.py` (`cooperative-pause.v1`) is generic. It knows nothing about reviews,
experiments or G-CORROB1; a worker supplies its own work-unit ids and its own state.

```
running -> pause_requested -> (current atomic unit finishes) -> checkpoint sealed -> paused
        -> [local model released] -> operator resume -> integrity verified -> running
```

**Cooperative, never an interrupt.** Nothing kills a thread or abandons a synchronous provider call. The signal is a
file an operator writes; the worker reads it only at its own safe boundaries, finishes the unit in flight, seals the
result, and only then stops.

**`cancelled` is not `paused`.** A paused activity is alive and expects to come back. A cancelled one is terminal and
is never resumed; its checkpoint is kept as evidence.

**An unreadable control file is read as `pause`,** not as permission to keep running.

## 2. Reviewer checkpoints

`experiment_review_hierarchical` is now **`v2733.0`**. It checkpoints after every completed atomic unit:

| boundary | unit id |
|---|---|
| observation part | `observe:<doc>:<part>` |
| part synthesis unit | `part:PU<n>` |
| document synthesis unit | `document:DU<n>` |
| intermediate group | `group:r<round>:g<n>` |
| completed intermediate round | `round:r<round>` |
| final synthesis half | `final:first_half`, `final:second_half` |

### Where checkpoints live, and why

Inside the review's **own output directory**. The frozen mutation guard excludes exactly one path — this review's
directory — and anywhere else a durable pause would itself trip the guard it is supposed to survive. Both the
checkpoint and the operator's control file live there.

That forced one further change: when work is named, the review id is **derived** from the package manifest and the
work id rather than from a uuid, so a resume can find its own checkpoint before it has read anything.

### Schema (`work-checkpoint.v1`)

```
contract, work_id, sequence, written_at, status,
bindings { package_id, manifest_sha256, package_documents{path: sha256},
           package_contract, rendering, reviewer_contract, baseline_contract,
           reviewer_module_sha256, baseline_module_sha256,
           model{model, provider, context_size, resolved_config_sha256},
           source_tree, limits },
position { level, ... }, completed_units[], completed_unit_count, next_unit,
state { review_id, started, sequence, ledger, grounded, rejected, questions,
        parts_coverage, items, absent_roles, part_units, doc_units, group_rounds,
        group_units_done, uncaptured_registers, carry_counts, part_statements,
        doc_statements, group_statements, carried_to_document, carried_to_intermediate,
        rejected_statements, dropped_refs, surviving, round_no, missing,
        final_inputs, first_half, second_half, final_rejected, final_unknown, final_state },
events[], digest
```

State is **restored wholesale, never recomputed**: identifiers, lineage, citations and synthesis inputs come back
exactly as the earlier segment made them, so no id can be reissued and no input can drift. The `digest` seals
everything the resume will trust.

### Resume fails closed on

package drift · source drift · reviewer or baseline module drift · contract drift · model or configuration drift ·
corrupt, tampered, unreadable or missing checkpoint · ambiguous (duplicated) completed-unit list · terminal work ·
cancelled work. A completed review seals a terminal checkpoint, so it can never be resumed back into life.

### Resource release

On reaching a durable paused state the reviewer asks the local provider to unload the model (`keep_alive: 0`), so a
paused run stops holding GPU and RAM. Best effort and never fatal — the pause is durable because the checkpoint is
sealed, not because the unload succeeded.

### Activity

`activity.py` gains two non-terminal states, `pause_requested` and `paused`; `cancelled` stays terminal and distinct.
The reviewer reports `pause_requested`, `model_released`, `paused`, `resumed` and checkpoint identity through the
caller's `on_state` hook. No prompt, reply or reasoning text is exposed — only operational facts.

## 3. Two bugs the adversarial tests caught

Both were real, and both would have corrupted a resumed review rather than failing loudly:

1. **Round renumbering.** `round_no` was incremented at the top of the consolidation loop, so a pause *inside* a round
   resumed under a *new* round number. That renamed every group stage, re-ran completed groups and produced different
   final inputs. The round number is now derived as `len(group_rounds) + 1`, and a round is appended only when it
   finishes.
2. **Completed groups came back empty.** Group units were re-planned fresh on resume, so a completed group's
   statements and uncited inputs were silently lost. Completed group units are now restored by stage id.

A third, in the test harness rather than the product: `write_text` translates newlines on Windows, so "restoring" a
package file after a drift test changed its bytes and made every later case fail on package digest instead of on what
it meant to test.

## 4. Scale qualification at 140 parts

`MAX_GROUPS_PER_ROUND` **32 → 48**.

Measured, not chosen for comfort. The nominal 140-part case opens consolidation with **491 inputs**, which is
`ceil(491 / 12) = 41` groups. At 32 the review failed closed immediately with `intermediate_round_too_wide` — it
would have spent roughly fourteen hours observing and then produced nothing. 41 is the exact requirement; 48 carries
a first round of up to 576 inputs, about a sixth of headroom for a model that grounds a little more than the
measurement did.

| bound | nominal 140 | pessimistic 140 |
|---|---|---|
| 32 | `intermediate_round_too_wide` | `intermediate_round_too_wide` |
| 41 | complete, 7 rounds | fails closed |
| 44 | complete, 7 rounds (identical) | fails closed |
| **48** | **complete, 7 rounds, 473 calls** | fails closed |

This is reviewer-capacity infrastructure. Nothing scientific moves with it: grounding, identifier support, coverage
requirements, the representation floor, the per-round reduction floor, the group input bound, the group statement
bound, the final input bound, the round limit and the retry limit are all unchanged, and a round wider than 48 still
fails closed.

## 5. Estimated work for G-CORROB1 review attempt 2

| | |
|---|---|
| required parts | 140 |
| observation units | 140 |
| part synthesis units | 140 |
| document synthesis units | ~25 |
| consolidation rounds | 7 |
| intermediate group units | ~160 |
| final halves | 2 |
| **total model calls** | **~473** |
| wall clock at the measured 197 s/call | **~26 hours** |
| checkpoints written | one per unit, ~473 |

With pause/resume this is no longer a single 26-hour commitment: it can be paused at any unit boundary, the GPU
released, and resumed later against verified bindings.

## 6. Known limitations

- **No real-model validation of pause/resume.** Everything here is deterministic-stub qualified. The provider was not
  contacted, by instruction.
- **The 140-part qualification uses a calibrated stub**, not the production model. The pessimistic band still fails
  closed at 140 parts, which is correct but means a genuinely low-citation model cannot be reviewed at this scale.
- **Checkpoints are large.** The full ledger and all accumulated state are sealed each time; at 140 parts the later
  checkpoints are tens of megabytes, written once per unit. This has not been profiled against a 26-hour run.
- **Resume is single-writer.** Concurrent resume of the same work id is not locked beyond the review directory
  already existing; the adapter's one-job-at-a-time rule is what prevents it in practice.
- **`release_local_model` names the model from the run identity.** If the provider is not Ollama, or the identity
  carries no model name, the release is skipped and reported as skipped.

## 7. Pre-existing technical debt, untouched

`tools/g_corrob1_execution_capability_tests.py` fails with **4 failures and 5 errors**, identically on the prior
checkpoint (verified by stashing every change in this work and re-running). It is almost certainly a consequence of
the one-shot execution authorization having been legitimately consumed by the real run. It was not repaired here, and
the consumed authorization was **not** regenerated to make a legacy test green.

## Reproducing

```bash
python tools/v2733_3_0_pause_resume_tests.py
python tools/v2733_2_0_scale_140_qualification_tests.py
```
