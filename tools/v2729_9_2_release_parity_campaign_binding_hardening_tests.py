from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / 'conscious_agent'
for value in (str(ROOT), str(AGENT), str(ROOT / 'tools')):
    if value not in sys.path:
        sys.path.insert(0, value)
os.environ.setdefault('EIDOLON_DATA_DIR', tempfile.mkdtemp(prefix='eidolon-v2729-9-2-runtime-'))

from combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog
from combined_trial_campaign_plan_v2721 import build_combined_trial_plan
from combined_trial_campaign_readiness_v2724 import build_combined_trial_campaign_readiness
from combined_trial_campaign_state_v2725 import prepare_combined_trial_campaign_state, load_combined_trial_campaign_state
from combined_trial_evidence_ledger_v2722 import build_trial_evidence_record, build_campaign_evidence_ledger
from checkpoint_registry import checkpoint_registry_manifest
from package_integrity import package_privacy_summary_for_root, package_privacy_summary_for_zip


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def raises(fn):
    try:
        fn()
    except (ValueError, TypeError, KeyError):
        return True
    return False


def run():
    checks = []
    def ck(name, value): checks.append((name, bool(value)))

    cat = build_combined_trial_catalog()
    plan = build_combined_trial_plan(cat)
    ready = build_combined_trial_campaign_readiness(
        cat, plan, current_checkpoint='v2729.9.2', release_certified=True, daily_use_engineering_ready=True
    )

    # 1-2: re-digested catalog and plan semantic forgeries must fail closed.
    badcat = json.loads(json.dumps(cat))
    badcat['trials'][0]['risk_class'] = 'supervised_project_start'
    body = dict(badcat['trials'][0]); body.pop('trial_digest', None); badcat['trials'][0]['trial_digest'] = digest(body)
    body = dict(badcat); body.pop('catalog_digest', None); badcat['catalog_digest'] = digest(body)
    ck('redigested_catalog_semantic_forgery_rejected', raises(lambda: build_combined_trial_plan(badcat)))

    badplan = json.loads(json.dumps(plan))
    badplan['plan'][0]['risk_class'] = 'supervised_project_start'
    body = dict(badplan); body.pop('plan_digest', None); badplan['plan_digest'] = digest(body)
    forged_readiness = build_combined_trial_campaign_readiness(
        cat, badplan, current_checkpoint='v2729.9.2', release_certified=True, daily_use_engineering_ready=True
    )
    ck('redigested_plan_semantic_forgery_rejected', not forged_readiness['ready_for_operator_campaign_review'] and 'trial_plan_catalog_mismatch' in forged_readiness['blockers'])

    # 3: re-digested readiness facts/semantics cannot be persisted as canonical readiness.
    badready = dict(ready)
    badready['state'] = 'not_ready'
    badready['ready_for_operator_campaign_review'] = False
    body = dict(badready); body.pop('readiness_digest', None); badready['readiness_digest'] = digest(body)
    with tempfile.TemporaryDirectory() as td:
        ck('redigested_readiness_forgery_rejected', raises(lambda: prepare_combined_trial_campaign_state(cat, plan, badready, runtime_root=td)))

    # 4: re-digested persisted status tampering is rejected by semantic reconstruction.
    with tempfile.TemporaryDirectory() as td:
        prepare_combined_trial_campaign_state(cat, plan, ready, runtime_root=td)
        path = Path(td) / 'combined_trial_campaign_state_v2725.json'
        state = json.loads(path.read_text(encoding='utf-8'))
        first = sorted(state['status_by_trial'])[0]
        state['status_by_trial'][first] = 'passed'
        body = dict(state); body.pop('state_digest', None); state['state_digest'] = digest(body)
        path.write_text(json.dumps(state), encoding='utf-8')
        loaded = load_combined_trial_campaign_state(td)
        ck('redigested_persisted_state_tamper_rejected', loaded.get('campaign_state') == 'corrupt_state_rejected' and loaded.get('ok') is False)

    # 5-7: evidence is catalog/trial bound and high-risk terminal evidence is checkpoint-bound.
    record = build_trial_evidence_record(trial_id='research', status='passed', evidence_codes=['ok'])
    forged = dict(record); forged['trial_digest'] = '0' * 64
    body = dict(forged); body.pop('evidence_digest', None); forged['evidence_digest'] = digest(body)
    ck('redigested_evidence_trial_binding_tamper_rejected', raises(lambda: build_campaign_evidence_ledger(cat, [forged])))
    ck('high_risk_terminal_requires_checkpoint', raises(lambda: build_trial_evidence_record(trial_id='project_start', status='passed', evidence_codes=['ok'])))
    bound = build_trial_evidence_record(trial_id='project_start', status='passed', evidence_codes=['ok'], checkpoint_digest='a' * 64)
    ck('high_risk_terminal_checkpoint_binding_accepted', build_campaign_evidence_ledger(cat, [bound])['completed_count'] == 1)

    # 8-9: root and final ZIP privacy enforce the same all-data exclusion policy.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / 'Eidolon'; (root / 'data').mkdir(parents=True); (root / 'data' / 'settings.json').write_text('{}\n', encoding='utf-8')
        root_summary = package_privacy_summary_for_root(root)
        archive = Path(td) / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as zf: zf.writestr('Eidolon/data/settings.json', '{}\n')
        zip_summary = package_privacy_summary_for_zip(archive)
        ck('root_privacy_rejects_runtime_data', not root_summary['source_only'] and 'data/settings.json' in root_summary['forbidden_entries'])
        ck('zip_privacy_rejects_runtime_data', not zip_summary['source_only'] and 'Eidolon/data/settings.json' in zip_summary['forbidden_entries'])

    # 10: Unix launchers must be executable in the source used for packaging.
    if os.name == 'nt':
        executable_ok = True
    else:
        executable_ok = all((p.stat().st_mode & stat.S_IXUSR) for p in (ROOT / 'run_eidolon.sh', ROOT / 'setup.sh'))
    ck('unix_launchers_executable', executable_ok)

    # 11-12: internal imports use one convention and production launch loads one source identity.
    relative = package_qualified = 0
    for path in AGENT.rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                relative += int(bool(node.level))
                package_qualified += int(bool(node.level == 0 and node.module and (node.module == 'conscious_agent' or node.module.startswith('conscious_agent.'))))
            elif isinstance(node, ast.Import):
                package_qualified += sum(1 for a in node.names if a.name == 'conscious_agent' or a.name.startswith('conscious_agent.'))
    ck('single_internal_import_convention', relative == 0 and package_qualified == 0)

    env = dict(os.environ); env.pop('PYTHONPATH', None); env['PYTHONDONTWRITEBYTECODE'] = '1'; env['EIDOLON_DATA_DIR'] = tempfile.mkdtemp(prefix='eidolon-module-id-runtime-')
    probe = '''import sys
from pathlib import Path
root=Path.cwd(); agent=(root/'conscious_agent').resolve(); sys.path.insert(0,str(agent)); import main
by={}
for name,m in list(sys.modules.items()):
 p=getattr(m,'__file__',None)
 if not p: continue
 try: rp=Path(p).resolve()
 except Exception: continue
 try: rp.relative_to(agent)
 except ValueError: continue
 by.setdefault(str(rp),[]).append(name)
dups={p:n for p,n in by.items() if len(n)>1}
print(__import__('json').dumps(dups,sort_keys=True)); raise SystemExit(0 if not dups else 7)'''
    cp = subprocess.run([sys.executable, '-c', probe], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    ck('production_import_identity_unique', cp.returncode == 0 and cp.stdout.strip() == '{}')

    # 13: checkpoint registry must have one selector per release checkpoint.
    registry = checkpoint_registry_manifest(source_root=ROOT)
    ck('checkpoint_registry_unique', registry.get('ok') is True and not registry.get('errors'))

    # 14-15: clean launchers work without PYTHONPATH and do not recreate source data.
    source_data = ROOT / 'data'
    before = sorted(p.relative_to(source_data).as_posix() for p in source_data.rglob('*') if p.is_file()) if source_data.exists() else []
    clean_env = dict(os.environ); clean_env.pop('PYTHONPATH', None); clean_env.pop('EIDOLON_DATA_DIR', None); clean_env['PYTHONDONTWRITEBYTECODE'] = '1'
    a = subprocess.run([sys.executable, str(ROOT/'conscious_agent/main.py'), '--status'], cwd=ROOT, env=clean_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=90)
    b = subprocess.run([sys.executable, str(ROOT/'eidolon.py'), 'status'], cwd=ROOT, env=clean_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=90)
    ck('clean_launcher_parity', a.returncode == 0 and b.returncode == 0)
    after = sorted(p.relative_to(source_data).as_posix() for p in source_data.rglob('*') if p.is_file()) if source_data.exists() else []
    ck('clean_launch_does_not_dirty_source', after == before)

    # 16-17: quick release certification must use deterministic production-parity
    # orchestration rather than the old concurrent cold-start shortcuts.
    verifier_text = (ROOT / 'tools' / 'release_verify.py').read_text(encoding='utf-8')
    ck('quick_parallel_core_not_default', 'EIDOLON_VERIFY_PARALLEL_CORE' in verifier_text and '== "1"' in verifier_text)
    ck('dashboard_suite_worker_isolated', '--suite-json' in verifier_text and 'eidolon-dashboard-suite-runtime-' in verifier_text)

    # 18: release-integrity evidence must describe the one-worker dashboard suite,
    # not the retired one-worker-per-route command graph.
    from verification_evidence import expected_stage_commands, required_stage_checks
    dashboard_expected = expected_stage_commands(ROOT, purpose='release')['dashboard-http-probe']
    dashboard_report = {
        'ok': True, 'status': 'pass',
        'routes': {route: {'ok': True} for route in __import__('verification_evidence').DASHBOARD_ROUTE_TIMEOUTS},
        'stage_invocation_count': 1, 'subprocess_execution_count': 1,
    }
    dashboard_checks = required_stage_checks('dashboard-http-probe', dashboard_report)
    ck('dashboard_receipt_contract_matches_suite_worker',
       len(dashboard_expected) == 1 and '--suite-json' in dashboard_expected[0] and all(dashboard_checks.values()))

    result = {'ok': all(v for _, v in checks), 'passed': sum(v for _, v in checks), 'total': len(checks), 'checks': checks}
    print(json.dumps(result, sort_keys=True))
    return result

if __name__ == '__main__':
    raise SystemExit(0 if run()['ok'] else 1)
