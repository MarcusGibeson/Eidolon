# Eidolon v1338.9 Service Orchestration Checkpoint Validation

This checkpoint completes v1338 on top of the durable v1337.9 Browser Validation checkpoint.

## Completed behavior

- Service orchestration requires a v1333 disposable candidate workspace, sealed satisfied v1332 `service` and `shell` preconditions, and an active workspace-matching standing grant containing both a service command class and an underlying process/shell class.
- Typed service definitions use bounded argument vectors, dependency codes, declared loopback ports, and TCP/HTTP readiness checks. Dependency cycles and missing dependencies are rejected before launch.
- Services start serially in topological order and each dependency must become ready before dependents launch.
- Underlying execution reuses v1336 generation-bound process ownership, bounded logs/timeouts, exact process-tree cancellation, and recovery semantics.
- Restart terminates the exact prior process and uses v1336's content-free invocation discriminator to create a fresh process generation without weakening ordinary duplicate suppression.
- Partial startup/readiness failures stop already-started services in reverse order and report orphan counts.
- Public evidence exposes service codes, dependencies, ports, readiness/process states, process receipt IDs, and definition digests, never raw commands or environment values.
- Ordinary chat can inspect a service-stack receipt but cannot start, restart, or stop services.

## Focused evidence

- v1338.0-v1338.2 foundations: 5/5
- v1338.3-v1338.5 integration: 5/5
- v1338.6-v1338.8 reliability/adversarial: 7/7
- v1338.9 checkpoint: 5/5

Real fixtures start loopback HTTP servers, prove dependency order and readiness, restart into a fresh generation, reject cycles and occupied ports, reverse-clean a failed dependent stack, reject stale/tampered lineage, and finish without orphaned service processes.

## Authority and containment boundary

v1338 declares and validates loopback-local service targets but does not claim kernel/OS network sandbox enforcement. Service evidence grants no external network, selected-source application, release, installation, promotion, provider, or independent authority. Native Windows process/service behavior remains external validation.
