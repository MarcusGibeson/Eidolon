# Eidolon v1251.9 Final Validation

v1251.9 is the read-only Response-Time and Runtime Efficiency Alpha checkpoint. It consolidates v1251.0-v1251.8 latency telemetry, compact model-facing cognition, guarded-action feedback, lightweight terminal startup, provider connection reuse, dashboard prewarming/caching, and static dashboard assets.

## Measured response-time evidence

Measurements use the same container and zero-latency/fixed-latency test providers to separate Eidolon runtime overhead from local-model generation time.

- Terminal chat cold start: approximately **1.41-1.47 seconds**, versus approximately **4.0-4.24 seconds** at the v1250.9 review baseline.
- Terminal chat startup RSS: approximately **130 MB**, versus approximately **428 MB** at the review baseline.
- First social-turn model prompt: approximately **2,292 estimated tokens**, versus approximately **7,400** at the review baseline.
- First ordinary-turn model prompt: approximately **2,500 estimated tokens**.
- Cold first-turn pre-provider runtime: approximately **200 ms** in the measured empty runtime.
- Warm ordinary pre-provider runtime: approximately **14-16 ms** in the measured empty runtime.
- Guarded action test: trusted deterministic feedback appeared at approximately **202 ms**, before a deliberately delayed fake provider finished at approximately **703 ms**.
- Representative dashboard shell: **269,140 bytes -> 213,345 bytes**, a **20.73%** reduction in repeated served HTML.

These numbers are environment-specific engineering evidence, not universal hardware guarantees. The structured budgets live in `docs/release/v1251_response_time_budgets.json`.

## Safety and authority

Prompt compaction changes only model-facing projection. Detailed internal cognitive evidence remains available in runtime records. Immediate action feedback is deterministic and explicitly denies execution or approval. Dashboard caching is read-only and never caches POST results or authority decisions. API prewarming imports local code only. Provider session reuse does not add fallback or provider-selection authority.

The checkpoint does not authorize installation, promotion, certification, release, provider contact, tool execution, project mutation, source mutation, or independent authority. The Desktop Codex review remains postponed until v1253.9.

## Packaging gate

The exact source tree must pass the v1251 focused suites, retained conversation/development checks, source-only privacy checks, Python syntax parsing, and the complete segmented broad verifier before a source-only candidate is packaged. The external segmented-verifier receipt is authoritative for the packaging run rather than being embedded into this source document.
