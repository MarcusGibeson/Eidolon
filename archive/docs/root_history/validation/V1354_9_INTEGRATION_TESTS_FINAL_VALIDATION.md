# Eidolon v1354.9 Integration Tests Final Validation

- Real subprocess boundaries execute only inside disposable candidate workspaces.
- Runtime data is forced into the workspace's isolated runtime-data root.
- Expected artifacts are checked by path/digest without exposing raw content in public receipts.
- Nonzero process results, missing/mismatched artifacts, unsafe paths, and tampered evidence fail closed.
- Mock-only success is explicitly false; no provider/network/release/source-application authority is granted.
