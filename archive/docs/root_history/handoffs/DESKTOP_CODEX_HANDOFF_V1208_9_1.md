# Desktop Codex Handoff: v1208.9.1

This is a repaired development candidate, not an installed or promoted release.

1. Verify the delivered ZIP SHA-256 and extract beneath exactly one `Eidolon/` root.
2. Confirm no `data/`, cache, bytecode, provider payload, conversation, credential, `projects.json`, or private-project content is packaged.
3. Create an external virtual environment and install `requirements-core.txt` plus `requirements-test.txt`.
4. Run the v1206.2, v1206.5, v1206.8, and v1206.9 focused suites.
5. Run the v1207.2, v1207.5, v1207.8, and v1207.9 focused suites.
6. Run the v1208.2, v1208.5, v1208.8, and v1208.9 focused suites.
7. Run `python tools/v1200_0_product_reality_benchmark_tests.py` and `python tools/release_verify.py --profile quick --json`.
8. Confirm browser evidence reports loopback navigation, Node 20 does not receive unsupported concurrency flags, and external-write probes fail without creating their target files.
9. Treat Python audit hooks and Node preload guards as language-runtime policy layers. They are not OS containers and must not be represented as strong hostile-code isolation.
10. Keep passing and failing outcomes as operator-review evidence. Do not install, promote, certify, or apply automatically.
