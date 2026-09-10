# v1299.0-v1299.2 Real Defect Evidence

The final supervised-autonomy rehearsal is anchored to a real v1298.9 evidence-integrity defect rather than a synthetic placeholder.

Before the repair, three consumers accepted self-generated evidence records without recomputing the record's own digest from its consumed fields:

- `conscious_agent/canary_self_updates.py` accepted a canary observation whose health fields were changed while retaining the old `observation_digest`.
- `conscious_agent/automated_recovery.py` accepted a recovery trigger whose `trigger_code` was changed while retaining the old `trigger_digest`.
- `conscious_agent/repeated_self_maintenance.py` accepted a test event whose `test_passed` value was changed from false to true while retaining the old `event_digest`, allowing the reducer to skip the repair stage.

The authoritative v1298.9 file identities used for the before/after repair evidence are:

| Path | v1298.9 SHA-256 | repaired SHA-256 at defect repair |
|---|---|---|
| `conscious_agent/canary_self_updates.py` | `3888d933f232154184e5303da176d2234f204790f0a358d97e16b6dc46104133` | `b9175633ee4bb7221269ddf5c414c62620102a6c99c4e1bf33b11aa74733200c` |
| `conscious_agent/automated_recovery.py` | `669b212a3c838368879e6503ffde8638768a09d4b927a2af63964804e6c77687` | `ca7c6b58fea4a04cf4f3d1cc15d68244d5d26b250f9d0204f690a296bfcea28d` |
| `conscious_agent/repeated_self_maintenance.py` | `a9c016a682415476ce65882502d1c920b74fd5886216576a16031d031bf7d624` | `037af2c020f34c96f991a7df7efc8965f67e44192c526492da508fc92a94c621` |

The combined pre/post defect-evidence digest for those three rows is `b36e99c8fc9d71288c18674f91598ad74830909d5fb37e297e180f251fa57821`.

The repair recomputes each self-generated record digest during consumption, excluding only its digest field and the established denied-authority fields that are appended after sealing. A mismatch blocks consumption before the altered evidence can influence canary comparison, automatic recovery, or maintenance-stage progression.

This repair is source work only. It does not modify an installed/operator-active Eidolon environment and it grants no update, release, rollback, provider, tool, command, test, repair, or standing authority.
