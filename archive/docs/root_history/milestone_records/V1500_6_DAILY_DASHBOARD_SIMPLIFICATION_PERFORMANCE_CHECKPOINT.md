# v1500.6 Daily Dashboard Simplification and Performance Checkpoint

This checkpoint repairs the dashboard bottleneck observed during daily conversation trials.

- The initial chat render does not build attention and recovery state for every conversation.
- Read-only attention and project state use their existing deferred endpoints after first paint.
- The active transcript is loaded once by the realtime conversation panel.
- The initial selector is bounded to 30 sessions; the organizer retains paginated access.
- Daily navigation contains Chat, Memory, Development, Activity, Settings, and Advanced.
- Advanced retains the complete historical engineering and governance route catalog.
- No command, provider, memory, approval, installation, promotion, or release authority changed.
- Historical verification now treats local bytecode as generated runtime state; concrete ZIP privacy verification remains authoritative for package contents.

Live-data profile:

- Before: 41.5 seconds and approximately 803 KB of HTML.
- After: 2.46 seconds cold, approximately 17 ms warm, and approximately 283 KB of HTML.

The next bounded unit is v1500.7 natural association use and conversational coherence.
