# Eidolon v1250.8 Final Validation

## Candidate status

This is an uninstalled source-only development candidate completing v1250 Bundle C.

Working source version: `1250.8`

Previous working source version: `1250.5`

Milestone: `v1250.6-v1250.8 Architecture Consolidation and Oversized Module Decomposition Bundle C`

Next bounded unit: `v1250.9 Cleanup and Verification Hardening Checkpoint`

The Desktop Codex review remains postponed until the v1250.9 checkpoint produces a trustworthy complete segmented broad-verification result and reconciles remaining cleanup findings.

## Architecture result

| Parent module | Before | After | Parent reduction | Extracted module(s) |
|---|---:|---:|---:|---|
| `self_maintenance.py` | 46,910 | 46,690 | 220 | `release_signature_primitives.py` |
| `dashboard.py` | 18,432 | 17,550 | 882 | `dashboard_layout.py` |
| `api_server.py` | 10,377 | 9,646 | 731 | `api_catalog.py`, `api_http_runtime.py` |
| **Total** | **75,719** | **73,886** | **1,833** | four bounded modules |

The extracted modules do not own approval, installation, promotion, certification, release, provider contact, project mutation, source mutation, or independent action authority.

## Validation results

| Verification | Result |
|---|---:|
| Bundle A focused suites | 298/298 |
| Bundle B focused suites | 311/311 |
| Bundle C focused suites | 250/250 |
| v1147.1 historical registry compatibility | 9/9 |
| v1079.3 conversation runtime reliability | 35/35 |
| v1249.0-v1249.2 retained foundations | 195/195 |
| v1249.3-v1249.5 retained interface stability | 266/266 |
| v1249.6-v1249.8 retained adversarial reliability | 183/183 |
| v1249.9 retained checkpoint | 53/53 |
| segmented dashboard-interface stage | passed, 4/4 suites |
| segmented retained-checkpoints stage | passed, 10/10 suites |
| all-source syntax parse | passed |
| source-tree immutability | passed |
| source-only privacy boundary | passed |

The exact documented working tree passed the selected segmented session in 105.72 seconds: source/privacy 2/2 suites, dashboard/interface 4/4 suites, and retained checkpoints 10/10 suites. All three stages reported zero source-snapshot debris, unchanged authoritative source, and successful runtime cleanup. Fresh-extraction parity remains required before the package checksum is considered final.

## Packaging boundary

The final candidate archive must contain exactly one `Eidolon/` root and exclude:

- runtime `data/`;
- bytecode and cache directories;
- VCS metadata;
- external verifier receipts and logs;
- provider payloads;
- selected-project content;
- credentials, secrets, and private runtime state;
- nested source archives.

The archive SHA-256 is published beside the delivered ZIP rather than embedded recursively inside it.

## Authority boundary

No extracted module, metadata record, checkpoint report, test result, verifier receipt, validation document, or candidate archive authorizes installation, promotion, certification, publication, release, provider contact, model management, project mutation, unattended continuation, or independent authority.
