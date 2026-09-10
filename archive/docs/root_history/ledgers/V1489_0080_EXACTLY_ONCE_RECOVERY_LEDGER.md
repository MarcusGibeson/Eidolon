# v1489.0080 Exactly-Once / Recovery Ledger

Content-free checkpoint. Browser, desktop, API and runtime views derive one opaque operation identity; repeated acceptance converges on one operation, duplicate turn IDs are idempotent, late results cannot overwrite terminal state, cancellation survives detach/restart, and uncertain operations require explicit retry rather than automatic replay.
