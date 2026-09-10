# v1254.6-v1254.8 Focused Validation

Focused deterministic command:

`python tools/v1254_6_8_isolated_coding_execution_reliability_tests.py`

Result: **86/86 passed**.

Validated surfaces: Windows-portable path rules; casefold/reserved-name rejection; long-path preservation; workspace private/link contamination; existing-test tamper rejection; all-files preflight before mutation; expired-lease recovery without duplicate generation; cancellation/cleanup; stale-source races; read-only health inspection; exact conversational review; operator handoff; and continued denial of application/release/independent authority.

Real Windows junction/reparse creation is not available in the current Linux validation environment and remains a Desktop review item.
