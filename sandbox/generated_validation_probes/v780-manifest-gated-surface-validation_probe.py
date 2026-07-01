# Generated sandbox validation probe
# v865.0 Operator-Approved Sandbox Probe File Generation Trial v1
# Deterministic content produced from manifest-guided dry-run evidence.
# Written only by a separate explicit operator-approved sandbox generation trial.
from __future__ import annotations

PROBE_METADATA = {
    "api_route": "not_exposed_review_only",
    "authority_level": "review_only",
    "builder_function": "build_manifest_gated_surface_validation_review",
    "cli_flag": "--manifest-gated-surface-validation",
    "dashboard_route": "/self-development-smoke-debt",
    "sandbox_relative_path": "sandbox/generated_validation_probes/v780-manifest-gated-surface-validation_probe.py",
    "smoke_check": "manifest-gated-surface-validation-v1",
    "smoke_segment": "install-dashboard",
    "surface_id": "v780-manifest-gated-surface-validation",
    "text_function": "manifest_gated_surface_validation_review_text"
}

def probe_preview() -> dict[str, object]:
    return {
        'ok': True,
        'review_only': True,
        'writes_files': False,
        'activates_generated_wiring': False,
        'expands_autonomy': False,
        'metadata': PROBE_METADATA,
    }
