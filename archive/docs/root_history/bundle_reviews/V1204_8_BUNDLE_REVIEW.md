# v1204.6-v1204.8 Bundle Review

Selected-project application and rollback now use digest-bound phase journals and consumed-authorization recovery. Apply retries cannot re-enter the write loop after authority is consumed. Rollback requests reject changed affected paths, rollback manifests are structurally and cryptographically validated, and interrupted rollback can seal or complete only known original/generated states. Unknown third-state content blocks recovery.

No automatic repair, release promotion, certification, model management, or independent authority was added.
