# v1252.0-v1252.2 Bundle A Review

Conversation metadata listing is index-backed after explicit migration or canonical session writes. Cross-session prompt continuity is capped at six selected transcripts, and bounded private summaries/topics update with canonical session writes. Read-only inspection never creates/rebuilds the derivative index. Canonical transcript JSON remains authoritative and rebuildable.
