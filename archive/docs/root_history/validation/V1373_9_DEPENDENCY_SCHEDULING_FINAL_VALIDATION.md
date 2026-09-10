# Eidolon v1373.9 Dependency Scheduling Final Validation

This checkpoint extends **Phase 8: Durable Multi-Step Campaigns** with deterministic dependency scheduling over bounded campaign tasks.

- Task graphs require unique bounded identifiers, known dependencies, valid status/weight fields, and acyclic dependency structure.
- Completed tasks are excluded from dispatch; pending tasks with all dependencies complete are identified as ready; dependency-blocked and paused work remain held with content-minimized reason evidence.
- A remaining critical-path score is computed over unfinished work and used with declared priority for deterministic ready ordering.
- `max_ready` bounds the surfaced ready set without granting task execution or parallelism authority.
- Public evidence stores task/dependency digests, counts, critical-path units, and reason codes rather than raw task content.
- Ordinary-chat inspection is read-only and import-lazy.

Focused verification: foundations 5/5; integration 5/5; reliability/adversarial 7/7; checkpoint 5/5. Retained release metadata passes 94/94 and checkpoint registry passes 118/118. No schedule grants task execution, project/source mutation, network/provider access, release, or independent authority.
