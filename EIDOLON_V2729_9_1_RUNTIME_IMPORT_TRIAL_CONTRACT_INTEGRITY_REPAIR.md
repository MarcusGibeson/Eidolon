# Eidolon v2729.9.1 Runtime Import and Trial Contract Integrity Repair

Parent checkpoint: **v2729.9 Combined Trial Campaign Preparation Checkpoint**  
Parent archive SHA-256: `E06CA51E39882018767064A94E7FBDC72BC009E709CD427EF2A15C4BF0A13556`

## Release-blocking repair

The shipped launch environment and the release verifier had diverged. Newer modules use package-qualified imports such as `conscious_agent.x`, while direct `conscious_agent/main.py` launch historically exposed only the `conscious_agent/` directory as the import root. The release verifier masked this by injecting repository-root `PYTHONPATH` into runtime-status.

v2729.9.1 repairs both sides:

- `conscious_agent/main.py` adds the repository root to `sys.path` before dashboard/general imports while preserving the retained top-level import convention.
- `tools/release_verify.py` uses a dedicated production-launcher runtime environment for `runtime-status` and deliberately omits repository-root `PYTHONPATH`.
- Clean-environment `python conscious_agent/main.py --status` and `python eidolon.py status` are regression-tested.

## Combined-trial contract hardening

- Unknown trial dependencies fail closed.
- Trial evidence is accepted only in the canonical v2722 schema, with exact field set and digest verification. Extra/raw fields and digest tampering are rejected.
- Campaign readiness requires exact catalog/plan membership, uniqueness, dependency identity, and dependency order rather than equal counts alone.
- A not-ready campaign cannot be persisted as `prepared_not_started`.
- Persisted prepared campaign state is schema- and digest-bound. Tampering returns `corrupt_state_rejected` and never appears started.
- Observability surfaces corrupted prepared state instead of silently treating it as an ordinary missing snapshot.

## Authority

The combined trial campaign remains **not started**. This repair grants no provider, tool, source mutation, installation, promotion, trial start, or independent authority.

Next bounded unit remains **v2730.0 - Operator-Selected Combined Trial Campaign Review and Start Boundary**.
