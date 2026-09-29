# Future seal layout (defined and tested; no seal exists)

The seal commit is the single commit on `main` whose parent is the frozen blueprint commit `1156d06`
(`G-ROUTE4_OBLIGATIONS.md` O1). It will add one folder, `experiments/G-ROUTE4-candidate/sealed/`, built by
`seal_layout.build_layout` from the five staging documents and the O2 configuration:

| File | Contents | Who may read it |
|---|---|---|
| `corpus_a.json` | A′ main fixtures (80), model-facing keys only | models, adjudicators |
| `corpus_b.json` | B′ main fixtures (305), model-facing keys only | models, adjudicators |
| `reserve_corpus_a.json` | A′ reserve fixtures (80), model-facing keys only | adjudicators; models if a reserve is used |
| `reserve_corpus_b.json` | B′ reserve fixtures (119), model-facing keys only | adjudicators; models if a reserve is used |
| `gold_a.json`, `gold_b.json` | gold, reference output and rationale for each main fixture | scoring and the operator, never a model or adjudicator |
| `reserve_gold_a.json`, `reserve_gold_b.json` | the same for each reserve fixture | as above |
| `authoring_ledger.json` | every design record: semantic ledgers, name draws, signatures | reviewers |
| `adjudicator_config.json` | the frozen O2 configuration (`adjudicator_config.config()`) | everyone |
| `SEAL_MANIFEST.json` | sha256 of the canonical content of every file above, with counts | everyone |

**Blind separation.** A model-facing fixture has exactly the keys `consequence_risk`, `fixture_id`, `input`,
`prompt`, `task_class`, `title` and `validator_profile`. `seal_layout.verify_blind` rejects any other top-level key,
and any gold-only or ledger-only key at any depth (for example `expected`, `reference_output`, `rationale`,
`required_terms`, `answer`, `message_units`, `research_contract`, `near_miss_option`). Gold files hold exactly
`expected`, `fixture_id`, `rationale` and `reference_output`, and the model-facing and gold files must cover the same
fixture ids part by part. (An observation's `role` is not a leak: the frozen Synthesis input gives each observation
its role.)

**Tests.** `test_repairs_corpus.py` builds the layout from the staged corpus and confirms it is blind. It then plants
a gold key inside a fixture's input and a rationale at a fixture's top level, and both are caught. It also confirms
the adjudicator's rendering equals the models' rendering and refuses a fixture that carries gold.

**Dry run only.** `python -B seal_layout.py --dry-run OUT_DIR` writes the layout outside the repository and refuses
any path inside it. Creating the seal is a separate step that needs the operator's instruction.
