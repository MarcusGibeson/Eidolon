# Eidolon v1272.9 Final Validation

v1272 completes Restart and Crash Recovery as a supervised recovery layer around the existing v1270 Self-Development Alpha and v1271 Long-Running Work Sessions pipeline.

The implementation adds a content-minimized write-ahead recovery journal, durable attempt-versus-completion evidence, restart/interruption generations, bounded receipts/summaries, provider outage/return evidence, stale-lease reconciliation, corrupt-projection quarantine/rebuild, operator-visible phase/authorization status, and explicit fail-closed handling of ambiguous in-flight external effects.

The critical crash-after-commit windows are covered deterministically. If v1265 has sealed a candidate or v1267 has passed trusted verification before the parent v1270/v1272 receipt is written, recovery completes only missing higher-level bookkeeping from durable lower lineage and suppresses provider/test replay. If the lower stage is merely `running`, recovery does not guess whether the external effect occurred and does not retry automatically.

The v1272.9 checkpoint is read-only. It performs no provider call, test execution, source mutation, project application, self-update, rollback, installation, promotion, certification, release, autonomous continuation, or authority grant.

Retained governance remains unchanged: exact v1265 mutation authorization, exact v1267 verification/repair authorization, v1268 consideration-only review, fresh v1269 preflight plus exact one-time update authorization, and separately authorized rollback. v1255 application/rollback authority remains distinct.

Remaining limitations: cross-process/browser-tab/queue exactly-once ownership and late-result ownership transfer are deliberately deferred to v1273. A provider/tool process that may have produced an external effect but died before any durable lower-stage commit remains operator-reconciliation-required rather than automatically retried. Native Windows process-kill, machine-restart, NTFS locking/atomic-replace, long-path, and governed-update-running-state behavior remains assigned to Desktop Codex validation.

v1273 has not been started.

## Exact final verification

- v1272.0-v1272.2 foundations: **62/62**.
- v1272.3-v1272.5 integration: **37/37**.
- v1272.6-v1272.8 reliability: **22/22**.
- v1272.9 checkpoint: **11/11**.
- retained v1271.9 checkpoint: **9/9**.
- retained v1270.9 checkpoint: **8/8**.
- retained v1269.9 checkpoint: **8/8**.
- retained v1256.9 checkpoint: **40/40**.
- retained v1244.9 continuity checkpoint: **125/125**.
- release metadata consolidation: **94/94**.
- checkpoint registry consolidation: **118/118**.
- privacy/security/secret-management checkpoint: **59/59**.
- Python parsing: **2,764/2,764**.
- source-only manifest: **3,408 files**.

The final packaging gate must fresh-extract the candidate beneath exactly one `Eidolon/` root, compare every packaged source file with the final source manifest, rerun the v1272.9 checkpoint and privacy/security gate from that fresh extraction, and compute the candidate SHA-256.
