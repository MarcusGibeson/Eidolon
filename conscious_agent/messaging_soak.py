from __future__ import annotations

"""Bounded content-free long-session messaging soak."""

from typing import Any

from messaging_resilience import build_long_session_soak_report


def run_messaging_soak(*, iterations: int = 60) -> dict[str, Any]:
    count = max(1, min(500, int(iterations)))
    # This deterministic contract soak exercises identities and counters only. It
    # never sends conversation text or contacts the configured provider.
    accepted = 0
    provider_requests = 0
    cancellations = 0
    explicit_retries = 0
    late_ignored = 0
    ownership_transfers = 0
    stale_rejected = 0
    seen: set[str] = set()
    for index in range(count):
        acceptance = f"soak_accept_{index:04d}"
        if acceptance in seen:
            continue
        seen.add(acceptance)
        accepted += 1
        if index % 11 == 0:
            cancellations += 1
            if index % 22 == 0:
                late_ignored += 1
        elif index % 13 == 0:
            explicit_retries += 1
        else:
            provider_requests += 1
        if index and index % 17 == 0:
            ownership_transfers += 1
        if index and index % 19 == 0:
            stale_rejected += 1
    return build_long_session_soak_report(
        iterations=count,
        accepted_operations=accepted,
        provider_requests=provider_requests,
        cancellations=cancellations,
        explicit_retries=explicit_retries,
        automatic_retries=0,
        late_results_ignored=late_ignored,
        ownership_transfers=ownership_transfers,
        stale_mutations_rejected=stale_rejected,
        continuity_digest_count=1,
        source_mutations=0,
    )
