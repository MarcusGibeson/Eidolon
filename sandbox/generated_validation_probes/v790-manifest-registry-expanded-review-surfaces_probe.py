# Generated sandbox validation probe
# v865.0 Operator-Approved Sandbox Probe File Generation Trial v1
# Deterministic content produced from manifest-guided dry-run evidence.
# Written only by a separate explicit operator-approved sandbox generation trial.
from __future__ import annotations

PROBE_METADATA = {
    "api_route": "not_exposed_review_only",
    "authority_level": "review_only",
    "builder_function": "build_manifest_registry_expanded_review_surfaces_review",
    "cli_flag": "--manifest-registry-expanded-review-surfaces",
    "dashboard_route": "/self-development-smoke-debt",
    "sandbox_relative_path": "sandbox/generated_validation_probes/v790-manifest-registry-expanded-review-surfaces_probe.py",
    "smoke_check": "manifest-registry-expanded-review-surfaces-v1",
    "smoke_segment": "install-dashboard",
    "surface_id": "v790-manifest-registry-expanded-review-surfaces",
    "text_function": "manifest_registry_expanded_review_surfaces_review_text"
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
