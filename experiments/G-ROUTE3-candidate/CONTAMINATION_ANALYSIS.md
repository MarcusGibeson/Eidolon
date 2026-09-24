# G-ROUTE3 contamination and independence analysis

## A versus B

Both corpora are new. Neither reuses a G-ROUTE1 fixture template, entity, number or answer. Independence
between them is measured, not asserted, by `tools/g_route3_independence.py`, and the result is frozen as
`INDEPENDENCE_REPORT.json`.

| Check | Bound | Result |
|---|---|---|
| Highest cross-corpus word-trigram overlap, same task class, shared boilerplate removed | ≤ 0.20 | **0.058** (conversation R4); every class ≤ 0.058 |
| Mean cross-corpus overlap | — | ≤ 0.004 per class |
| Shared named entities and identifiers | 0 | **0** |
| Shared planning actions in gold | 0 | **0** |
| Shared coding function names | 0 | **0** |
| Shared extraction string values | 0 | **0** |
| Shared research source lineages | 0 | **0** |
| Reasoning pattern shared by A and B within a cell | 0 | **0 of 24 cells** |

Independence is defined at the level of the reasoning problem, not vocabulary. Each fixture carries a pattern
tag in `fixture_design.json` (model-invisible), such as `temporal_precedence_resolution`,
`narrower_scope_source` or `self_approval_detection`. Within every task × risk cell, the A and B pattern sets
are disjoint. Across different cells a structural shape may recur. That is permitted, because qualification
and validation are both per cell.

**Declared, not hidden.** Some vocabulary is shared by design, because it defines the task class being
qualified rather than any fixture's content: research status and uncertainty codes, synthesis conclusion
rules and codes, the planning exclusion prefixes, and the coding whitelist text. The independence tool
excludes these explicitly and lists the exclusions in its report. Two findings were fixed during design:
a planning action shared between A and B in the same cell was renamed, and a trigram overlap caused by a
shared conclusion rule was traced to that rule rather than to fixture content.

**Also declared.** Two broad domains, `backup_operations` and `network_security`, appear in both corpora,
in different task classes and cells. No entity or answer is shared.

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

What it was not used for: no G-ROUTE2 cell verdict, pass rate or threshold is carried into G-ROUTE3. Fixture
difficulty was not tuned against any observed model behavior, and no fixture was tested on a model.
Thresholds are argued from the pilot-scale denominator, not from prior observed rates.

## G-ROUTE1 and G-ROUTE2

Untouched. G-ROUTE3 reads their frozen artifacts only to reuse the validators and prompt profiles
byte-for-byte, and to produce the labelled derivability diagnostic.
