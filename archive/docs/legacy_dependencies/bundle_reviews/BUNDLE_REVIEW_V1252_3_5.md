# v1252.3-v1252.5 Bundle B Review

Ordinary memory appends no longer reread, deep-copy, and rewrite the complete history. A crash-recoverable append journal preserves the canonical JSON array; SQLite provides bounded retrieval after explicit migration or memory mutation; compaction/rebuild/recovery paths preserve compatibility. Read-only legacy fallback does not mutate derivative index files.
