# v1268.0-v1268.9 Focused Validation

Required focused suites:

- `tools/v1268_0_2_operator_review_handoff_foundations_tests.py`
- `tools/v1268_3_5_operator_review_handoff_integration_tests.py`
- `tools/v1268_6_8_operator_review_handoff_reliability_tests.py`
- `tools/v1268_9_operator_review_handoff_checkpoint_tests.py`

Retained release checks:

- `tools/v1250_3_release_metadata_consolidation_tests.py`
- `tools/v1250_4_checkpoint_registry_consolidation_tests.py`
- retained v1267/v1266/v1265 checkpoints
- `tools/v1247_9_privacy_security_secret_management_audit_tests.py`

The final source-only candidate must compile all Python source, contain exactly one `Eidolon/` root, exclude runtime/private data, match the packaged source byte-for-byte after fresh extraction, and repeat the four v1268 suites from that extraction.
