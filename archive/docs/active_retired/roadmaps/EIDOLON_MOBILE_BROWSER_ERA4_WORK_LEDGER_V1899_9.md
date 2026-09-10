# Eidolon Mobile Browser Era 4 Work Ledger - v1899.9

## Authority and baseline

- Authoritative input: `Eidolon_v1800_9_era3_desktop_cognitive_gate_source_only.zip`.
- Exact input SHA-256: `343cc4746af89d90afcc36ee50fd37a82adec73839cf8dcdcb72d18968611acb`.
- Input gate status: reviewed/unpromoted; no installation or promotion authority inherited.
- Campaign scope: portable v1801-v1899.9 Memory and World-Model Coherence work.
- Next planned local/operator boundary: v1900 Desktop Era 4 memory/world-model gate.

## Arc 13 - Memory Consolidation and Retrieval

- Added eight explicit memory classes: episodic, semantic, procedural, preference, relationship, project, correction, and temporary working memory.
- Reused the canonical memory store; no second memory database or migration was introduced.
- Added a read-only coherence projection before the existing unified-memory/relevance pipeline on both ordinary conversation provider paths.
- Compatible duplicates are reduced, explicit corrections suppress superseded alternatives, unresolved conflicts remain explicit, weak duplicate evidence may age out, and provenance remains attributable.
- Consolidation never rewrites canonical records or treats assistant-authored text as operator evidence.

## Arc 14 - Time, Identity, and Event Understanding

- Added point and interval time representation, one-sided/uncertain intervals, recurrence, deadlines, anniversaries, ordering, duration boundaries, and uncertainty.
- Added explicit identity continuity using entity identifiers, alias digests, and role history.
- Name similarity alone never merges identities; ambiguous aliases fail closed.
- Repaired a campaign-discovered bug where explicit start/end intervals were incorrectly marked uncertain because an unrelated point timestamp was absent.

## Arc 15 - Revisable World Model and Beliefs

- Reused `belief_revision.BeliefRevisionStore` as the durable owner rather than adding a parallel belief database.
- Added evidence assessment by source type, freshness, independence, contradiction, and source disagreement.
- User, governed action receipt, and attributable external evidence may support review; assistant/Eidolon/generated text is rejected as independent evidence.
- Reviewed belief integration preserves the existing exact-once, contradiction-retaining, non-authorizing store contract.

## Arc 16 - Knowledge Maintenance

- Added freshness classes for stable, versioned, time-sensitive, local-runtime, and externally verifiable knowledge.
- Added bounded stale/unknown-time inspection and provider-neutral refresh proposals.
- Refresh evidence assessment separates private/public evidence and rejects generated or low-quality evidence.
- A refresh proposal never browses, contacts providers, mutates memory, or claims completion.
- Added exact ordinary-chat controls for content-free memory/world-model inspection, stale-knowledge inspection, and digest-bound refresh-proposal preparation through the existing command boundary.

## Production integration

- `conversation_runtime.py` applies Era 4 coherence before existing unified memory and relevance assembly in both provider paths and supplies a bounded policy prompt plus content-free cognitive evidence.
- `ordinary_chat_development_campaign.py` routes the new exact read-only/proposal-only controls without creating a second router.
- Release authority identifies this source as the unreviewed/unpromoted v1899.9 Browser candidate.

## Behavioral outcome

The campaign materially changes ordinary cognition: corrections can remove superseded memory from live prompting without deleting history; unresolved contradictions remain visible; stale knowledge is marked rather than repeated as current truth; identity aliases remain ambiguous unless explicit identity evidence resolves them; and belief support cannot be manufactured from assistant prose.
