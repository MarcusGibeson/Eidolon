# v1276.3-v1276.5 Architecture Boundary Integration Review

Status: complete.

Three real extractions were integrated while preserving historical call surfaces:

- `release_evidence_boundary.py` owns canonical release-evidence hashing/building/validation previously embedded in `self_maintenance.py`.
- `dashboard_development_campaign_panel.py` owns the dependency-free static development campaign panel previously embedded in `dashboard.py`.
- `api_request_boundary.py` owns API request/body/path parsing primitives and `ApiError` previously embedded in `api_server.py`.

Authority remains in the original owners. API GET/POST route dispatch remains in `api_server.py`; dashboard HTTP/action handling remains in `dashboard.py`; release/governance actions remain in `self_maintenance.py`. Explicit re-exports preserve existing callers.
