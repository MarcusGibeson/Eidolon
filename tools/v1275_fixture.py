from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / 'conscious_agent', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from self_development_alpha_foundations import prepare_self_development_alpha_campaign
from long_running_work_sessions_foundations import prepare_long_running_work_session
from restart_crash_recovery_foundations import prepare_restart_crash_recovery
from ownership_concurrency_foundations import prepare_ownership_concurrency
from environment_awareness_foundations import prepare_environment_awareness
from environment_awareness import refresh_development_environment
from v1274_fixture import deterministic_windows_probes
from v1270_fixture import fixture, evidence, priority_context


def prepared_dependency_environment_chain(base: Path, *, now: float = 1000.0):
    source = fixture(base)
    (source / 'requirements.txt').write_text('-r requirements-core.txt\n', encoding='utf-8')
    (source / 'requirements-core.txt').write_text('requests>=2.31,<3\n', encoding='utf-8')
    (source / 'requirements-test.txt').write_text('pytest>=8,<9\n', encoding='utf-8')
    (source / 'requirements-empty.txt').write_text('# deterministic offline clean-install fixture\n', encoding='utf-8')
    runtime = base / 'runtime'
    campaign = prepare_self_development_alpha_campaign(source, external_evidence=evidence(), priority_context=priority_context(), runtime_root=runtime)
    session = prepare_long_running_work_session(campaign['campaign_id'], runtime_root=runtime, now=now)
    recovery = prepare_restart_crash_recovery(session['session_id'], runtime_root=runtime, now=now)
    ownership = prepare_ownership_concurrency(recovery['recovery_id'], runtime_root=runtime, now=now)
    environment = prepare_environment_awareness(ownership['ownership_id'], runtime_root=runtime, now=now)
    refreshed = refresh_development_environment(
        environment['environment_id'], source, runtime_root=runtime,
        probes=deterministic_windows_probes(), now=now,
    )
    return {'source': source, 'runtime': runtime, 'campaign': campaign, 'session': session, 'recovery': recovery, 'ownership': ownership, 'environment': environment, 'refreshed': refreshed}
