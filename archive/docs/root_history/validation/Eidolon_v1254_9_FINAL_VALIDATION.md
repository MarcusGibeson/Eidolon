# Eidolon v1254.9 Final Validation

## Candidate

Working source: **v1254.9 Isolated Coding Execution Checkpoint**.

Authoritative v1254 arc input: `Eidolon_v1253_9_2_desktop_codex_windows_coherence_repair_source_only.zip`, SHA-256 `23672742F8FA121E50937C0833CF4066F146F0D0DC46056640CE4E0831B3B19F`.

Authorized continuation baseline for Bundle B/C/checkpoint work: `Eidolon_v1254_2_isolated_coding_execution_bundle_a_source_only.zip`, SHA-256 `0C0F0B9226636C998A2BB1904C42900FCFE6FAAF4F17BDDD68DDAC7000EA5DB4`.

## Exact focused results

- `tools/v1254_0_2_isolated_coding_execution_foundations_tests.py`: **125/125 passed**.
- `tools/v1254_3_5_isolated_coding_execution_integration_tests.py`: **54/54 passed**.
- `tools/v1254_6_8_isolated_coding_execution_reliability_tests.py`: **86/86 passed**.
- `tools/v1254_9_isolated_coding_execution_checkpoint_tests.py`: **33/33 passed**.

## Retained results

- `tools/v1250_3_release_metadata_consolidation_tests.py`: **94/94 passed**.
- `tools/v1250_4_checkpoint_registry_consolidation_tests.py`: **118/118 passed**.
- `tools/v1201_9_small_website_implementation_checkpoint_tests.py`: **89/89 passed**.
- `tools/v1238_9_broader_project_language_adapters_checkpoint_tests.py`: **27/27 passed**.
- `tools/v1247_9_privacy_security_secret_management_audit_checkpoint_tests.py`: **59/59 passed**.
- `tools/v1253_9_2_windows_runtime_coherence_repair_tests.py`: **19/19 passed**.

## Compilation and privacy

All Python source files are compiled in-memory with Python's `compile()` during final validation so the verification itself does not create source-tree bytecode. Final compile count and final source/package privacy counts are recorded in the external release receipt generated alongside the ZIP.

The source-only candidate excludes `data/`, runtime records, workspaces, conversations, memories, prompts, responses, secrets, provider payloads, caches, logs, virtual environments, bytecode, and test/runtime caches. Final archive privacy and fresh-extraction parity are verified after archive construction; the archive SHA-256 is intentionally reported outside this file so the archive does not contain a self-referential hash.

## Remaining limitations

1. Native Windows junction/reparse behavior must still be exercised on a real Windows host; the current environment can validate the Windows-aware contract and symlink/reparse abstractions but cannot reproduce every NTFS junction behavior.
2. Provider-generated implementation is bounded by the existing Python/Node/static verification surfaces. Broader language-specific execution remains future adapter work rather than unrestricted shell access.
3. v1254 can create and review a candidate only in the disposable workspace. It cannot apply, install, promote, certify, or release that candidate.
4. Dependency installation is not authorized in v1254.
5. v1255 Controlled Application and Rollback has not been started.

## Authority conclusion

The v1254.9 candidate is suitable for Desktop Codex review as an isolated coding-execution checkpoint. This validation does not install, promote, certify, release, or apply it, and it grants no permanent or independent authority.
