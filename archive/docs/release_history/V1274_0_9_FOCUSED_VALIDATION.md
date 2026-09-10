# v1274.0-v1274.9 Focused Validation

v1274 adds an evidence-backed, privacy-minimized environment model above the existing v1273 ownership and v1272 recovery layers. It does not replace their state machines and creates no execution authority.

## Focused suites

- `tools/v1274_0_2_environment_awareness_foundations_tests.py`
- `tools/v1274_3_5_environment_awareness_integration_tests.py`
- `tools/v1274_6_8_environment_awareness_reliability_tests.py`
- `tools/v1274_9_environment_awareness_checkpoint_tests.py`

## Key demonstrated properties

- observed, inferred, assumed, and unknown claims remain distinct;
- inferences require explicit fact lineage;
- unknown facts do not collapse into false observations;
- raw paths, environment-variable values, and provider payloads are not persisted;
- Windows host observation is distinct from Windows-looking path syntax;
- Python/venv, permissions, requested ports, configuration presence, explicit provider availability, process state, and resources can be represented as bounded facts;
- provider and port availability remain unknown unless an explicit probe is supplied;
- stale facts require refresh;
- sensitive preflight uses only current observed facts;
- malformed v1274 state is quarantined instead of reconstructed from guesses;
- v1273 ownership and all lower exact authorization boundaries remain authoritative.

Final aggregate results are recorded in `Eidolon_v1274_9_FINAL_VALIDATION.md` after retained verification and fresh-extraction parity.
