# G-ROUTE3 contamination and independence analysis

## A versus B

Both corpora are new. Neither reuses a G-ROUTE1 fixture template, entity, number or answer.

### What "out of sample" means here

The operator set the standard after the round-1 external review: **same construct, fresh instance.** Corpus B
tests whether a model qualified on one instance of a task construct also succeeds on a *fresh instance of
that construct*, with new entities, new facts, new answers and a different reasoning problem wherever the
class allows one. It does not claim that B poses new *kinds* of problem. For planning, B deliberately poses
the same kind of problem, as declared below. The primary result is read at that scope.

### Measured independence

Measured by `tools/g_route3_independence.py`, and frozen as `INDEPENDENCE_REPORT.json`.

| Check | Bound | Result |
|---|---|---|
| Highest cross-corpus word-trigram overlap, same task class, shared boilerplate removed | ≤ 0.20 | **0.055** (ordinary_conversation); every other class ≤ 0.042 |
| Mean cross-corpus overlap | — | ≤ 0.005 per class |
| Shared named entities and identifiers | 0 | **0** |
| Shared planning actions in gold | 0 | **0** |
| Shared coding function names | 0 | **0** |
| Shared extraction string values | 0 | **0** |
| Shared research source lineages | 0 | **0** |
| Same **gold-answer structure** in A and B within a cell (research fine and coarse, synthesis, extraction, planning), outside a declared single-template class | 0 | **0** |
| Author-assigned reasoning-pattern label shared within a cell | 0 | **0 of 24 cells** |

**Why a structural check was added.** In round 1 the reasoning-pattern check rested only on labels the
author had assigned, and the trigram check removes shared boilerplate. So a renamed copy of the same
template passed both. The external reviewer found seven routed cells where that had happened. The
tool now also compares the *shape* of each gold answer within each cell:

- **research**: claim statuses with their citation and lineage counts, the recommendation's position in the
  allowed list, the uncertainty codes, the source count and the decision-rule form;
- **synthesis**: the sorted roles and the conclusion;
- **extraction**: the schema's field types;
- **planning**: the step, action, evidence and uncertainty counts.

The research signature is checked twice.

- The fine version is the shape above.
- The coarse version keeps only three things: the claim statuses, the recommendation, and why a claim is
  unresolved (conflict, scope or unaddressed). It ignores lineage counts, so two fixtures posing the same
  problem cannot differ in a lineage count alone.

The coarse check found A-RESEARCH-R1-1 and B-RESEARCH-R1-2 in round 3; B-RESEARCH-R1-2 was changed.
Extraction field types are abstracted: enum sets become `enumN`, and dates and times are one type. A
relabelled enum therefore cannot hide a shared shape. The report also lists, as information only, answer
shapes shared between A and B in *different* cells. It lists 61 such pairs, 48 of them from the
declared planning template. Qualification and validation are per cell, so these are not findings. The
extraction signature also counts derived fields, so copying a value and computing one are different
shapes.

A match between A and B in the same cell is a finding. Conversation and coding have no structural
signature. For those two classes, independence rests on two things: the rewritten fixtures, whose
operation within each cell is stated below, and the external reviews' reading.

**Conversation operations by cell (round 3):**

| Cell | Corpus A | Corpus B |
|---|---|---|
| R1 | two-condition slot filter; whole-number division | maximum with unit conversion; conditional count |
| R2 | date difference against a review window; time difference against a threshold | month arithmetic for expiry; percentage fee |
| R3 | lockout expiry by time addition; precondition absent | three same-month age differences against a threshold; partial-result lookup |
| R4 | dual-control refusal; role-reserved override | legal-hold prohibition; remaining-capacity computation |

### Research: one sub-skill per cell, never the same in A and B

Research uses one prompt in every risk class, so risk cannot separate its fixtures. Instead each fixture
exercises one of eight declared sub-skills:

| Code | Sub-skill |
|---|---|
| S1 | positive lineage-count rule |
| S2 | direct contradiction |
| S3 | other subject, so the claim is unaddressed |
| S4 | same-lineage repetition |
| S5 | conflict left unresolved |
| S6 | narrower scope |
| S7 | conflict settled by a stated rule |
| S8 | quantitative contradiction |

Each corpus uses each sub-skill exactly once:

| Cell | A | B |
|---|---|---|
| R1 | S2, S3 | S1, S8 |
| R2 | S4, S5 | S6, S7 |
| R3 | S1, S6 | S2, S5 |
| R4 | S8, S7 | S3, S4 |

A research cell qualified on A is therefore validated on B against *different* sub-skills of the same
construct. This is a harder transfer than instance-level reuse, and it is declared.

### Planning is a declared single-template construct

Every planning fixture in both corpora has the same shape:

- four included steps in a total order, each consecutive pair linked by an evidence line stating the
  precedence;
- one excluded action, named by a stated prefix;
- five evidence items;
- two uncertainty codes, of which exactly one holds.

That shape is the construct being qualified: exact rule-following over stated precedences, exclusions and
conditions. It is declared in `SINGLE_TEMPLATE_TASK_CLASSES`, and the independence report lists all 16
same-cell A/B planning pairs, so the reuse is visible rather than hidden. Planning in B tests fresh
instances of exactly this template. A planning result says nothing about open-ended planning.

### Difficulty matching

Round 1 had within-cell difficulty mismatches: B's extraction R1 computed values while A only copied them;
B's plans were larger; one B research fixture was trivially easy; one B coding fixture was much easier. They
were repaired:

- Each corpus's extraction R1 cell has one copy-only fixture and one fixture with a computed field.
- Extraction R2 and R3 each have one derived computation per fixture in both corpora. A-EXTRACT-R2-2 gained a
  date addition, B-EXTRACT-R2-2 was reduced to one multiplication, and B-EXTRACT-R3-2 derives retention
  days from two dates.
- Conversation R1 pairs a filter or comparison with one arithmetic operation in both corpora. Conversation
  R2 is two computations in both corpora. Conversation R3 pairs one computation with one lookup in both
  corpora. Round 3 corrected a wrong statement here, made A-CONV-R1-1 a two-condition filter and kept
  B-CONV-R3-1's date differences within one month.
- Planning is normalized to one size.
- B-RESEARCH-R1-1 applies a two-lineage rule.
- B-CODE-R3-2 is now a redirect-safety check of comparable difficulty to A's R3 coding fixtures.

Difficulty matching is still the author's judgment. It was not measured on any model.

**Declared shared vocabulary.** Some vocabulary is shared by design, because it defines the task class
being qualified rather than any fixture's content:

- research status and uncertainty codes;
- synthesis conclusion rules and codes;
- the planning exclusion prefixes;
- the coding whitelist text.

The independence tool excludes these explicitly and lists the exclusions in its report.

**Also declared.** Four broad domains appear in both corpora, but in different task classes and cells:
`backup_operations`, `laboratory_safety`, `network_security` and `web_security`. No entity or answer is
shared.

## Corpus B cannot influence qualification

- separate files, separate gold, disjoint `A-` and `B-` namespaces, disjoint seeds and call ids;
- both corpora and both gold files frozen by digest before any model contact;
- collection never loads gold for either corpus;
- Phase A scoring loads only gold A, and a test runs a complete Phase A with gold B made unloadable and
  confirms it succeeds;
- the table is written once, before Phase B, and verifies only if derived from Corpus A alone;
- the table sits inside Phase B's mutation guard;
- thresholds are frozen before contact.

## Model exposure

The three models are static local weights, pinned by digest, and every call runs in a fresh session with no
state carried between calls. Neither corpus has ever been sent to any model. Seeds do not overlap with each
other or with G-ROUTE1's or G-ROUTE2's ranges. Ollama does not attest seed honoring.

## Designer contamination

The designer has seen G-ROUTE1 and G-ROUTE2 outcomes. What that knowledge was used for:

- **Architecture** — the two-corpus design and qualification-gated stopping come from G-ROUTE2's pointer, as
  the task permits.
- **The derivability rule** — this comes from a diagnostic over G-ROUTE2 records. It is a construction
  property, checkable without any model output, and it moves fixtures toward being answerable rather than
  toward any particular outcome.
- **Trigger retirement** — reasons are argued from the G-ROUTE3 design, and recorded.
- **Round-1 external review** — its findings concern fixture construction and code boundaries, checked without model output. No review finding was based on, or tuned against, model behavior.

What it was not used for: no G-ROUTE2 cell verdict, pass rate or threshold is carried into G-ROUTE3. Fixture
difficulty was not tuned against any observed model behavior, and no fixture was tested on a model.
Thresholds are argued from the pilot-scale denominator, not from prior observed rates.

## G-ROUTE1 and G-ROUTE2

Untouched. G-ROUTE3 reads their frozen artifacts only for three things:

- to reuse the semantic validators, the non-conversation operational checks, the transport normalization and
  the prompt profiles, byte-for-byte;
- to wrap G-ROUTE1's validators, in separate modules, with the conversation two-line frame and the coding
  trailing-newline canonicalization;
- to produce the labelled derivability diagnostic.
