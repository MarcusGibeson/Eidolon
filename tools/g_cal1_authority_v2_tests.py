"""Offline adversarial tests; authority fixtures exist only in temporary namespaces.

Import the reviewed adapter's audit guard BEFORE importing the new entrypoint.
All HTTP is scripted and sockets/process launches are denied.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).absolute().parent))  # Test-only imports after -I -S startup.
import g_cal1_ollama_transport_tests as mocks
import copy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

# The bootstrap itself is executed from its source bytes, not normal import/pyc.
BOOT_PATH = Path(__file__).absolute().with_name('g_cal1_source_loader_v1.py')
BOOT = {'__file__': str(BOOT_PATH), '__name__': 'gcal_test_verified_bootstrap'}
exec(compile(BOOT_PATH.read_bytes(), str(BOOT_PATH), 'exec', dont_inherit=True), BOOT)
RUNTIME = BOOT['VerifiedRuntime'](BOOT['inventory']())
authority = RUNTIME.module('g_cal1_authority_v2')
LiveRun = RUNTIME.module('g_cal1_live_v4').LiveRun
Package = RUNTIME.module('g_cal1_contract').Package
contract = RUNTIME.module('g_extract1_contract')
canonical, digest, IntegrityError, load = contract.canonical, contract.digest, contract.IntegrityError, contract.load
Journal, write_once = RUNTIME.module('g_extract1_journal').Journal, RUNTIME.module('g_extract1_journal').write_once
from g_extract1_scoring import synthetic_gold


def verified(binding, schedule, provider=None, **kwargs):
    provider = provider or mocks.Provider()
    provider.add(*mocks.metadata_scripts(binding))
    transport = RUNTIME.module('g_cal1_ollama_transport').OllamaLiveTransport(
        binding, schedule, timeout_seconds=30, connection_factory=provider, **kwargs)
    return transport, provider, transport.verify_metadata()


def fixture(root, package):
    registry = authority.Registry(root, test_only=True)
    candidate = registry.candidate(timeout_seconds=30)
    csha = registry.publish('candidates', candidate)
    review = dict(registry.fields(), schema_version='g-cal1.freeze-review.v2', verdict='PASS',
                  candidate_sha256=csha, execution_sha256=candidate['execution_sha256'],
                  reviewer='Sol 6.1', scope='EXECUTION_FREEZE_REVIEW')
    rsha = registry.publish('reviews', review)
    operator = dict(registry.fields(), status='EXPLICIT_OPERATOR_FREEZE_ACTIVATION', candidate_sha256=csha,
                    review_sha256=rsha, predecessor=candidate['predecessor'])
    asha = registry.activate(csha, rsha, operator=operator)
    return registry, candidate, csha, rsha, asha, operator


def grant(registry, run_id):
    current, _ = registry.history()
    a = registry.read('activations', current['activation_sha256'])
    g = dict(registry.fields(), schema_version='g-cal1.cal-grant.v2', experiment='G-CAL1', phase='CAL',
             status='EXPLICIT_OPERATOR_PHASE_AUTHORIZATION', freeze_status='EXECUTION_FREEZE_ACTIVE', run_id=run_id,
             activation_sha256=current['activation_sha256'], candidate_sha256=current['candidate_sha256'],
             generation_head=current['generation_head'], execution_sha256=a['execution_sha256'],
             science_binding=a['science_binding'], synthetic_evidence_allowed=False,
             authority_source='EXPLICIT_OPERATOR_CAL_AUTHORIZATION')
    return registry.publish('grants', g)


def main():
    checks = mocks.Checks()
    protected = mocks.protected_snapshot()
    audit_before = len(mocks.AUDIT)
    production_before = {p.relative_to(authority.NAMESPACE).as_posix(): mocks.file_digest(p)
                         for p in authority.NAMESPACE.rglob('*') if p.is_file()}
    checks.check(all((authority.NAMESPACE / p).is_file() for p in production_before),
                 'isolation', 'existing production authority is read-only evidence')
    checks.check(authority.historical()['binding']['schedule_sha256'] ==
                 'b4d4a5a7ba37961dcfbbe0c6aa6101fbbeb40dcf2dad0c54c8680d216c2e1858', 'preservation', 'frozen schedule')
    # Same verified source facts/schedule as the reviewed transport tests. Remove
    # only their in-memory namespace label; our namespace is explicit in every
    # authority artifact. Production rejects this class, requiring frozen Package.
    package = mocks.TestPackage()
    package.binding.pop('test_only')
    package._derived = canonical(package._state())
    checks.check(len(package.schedule) == 80 and len(package.members) == 40, 'science', '80/40 unchanged')
    binding = authority.historical()['provider_binding']
    with tempfile.TemporaryDirectory(prefix='g-cal1-v2-tests-') as tmp:
        root = Path(tmp)
        reg, c, cs, rs, act, op = fixture(root / 'authority', package)
        checks.check(len(c['executable_sources']) == 18 and len(c['protected_artifacts']) == 107 and c['provider_binding'] == binding,
                     'binding', 'exact executable closure and provider baseline')
        checks.check(reg.history()[0]['activation_sha256'] == act, 'lineage', 'selected v2 activation')
        checks.check(authority.historical()['status'] == 'EXECUTION_FREEZE_CANDIDATE_ONLY',
                     'preservation', 'old evidence unchanged after temporary rollover')
        run_id = 'G-CAL1-CAL-offline-main-0001'
        gs = grant(reg, run_id)
        gate = lambda: reg.authorize(package, run_id, act, gs)
        checks.check(gate()['candidate_sha256'] == cs, 'authority', 'fresh correct grant accepted offline')
        for bad in (authority.ANCHOR['activation_sha256'], authority.ANCHOR['candidate_sha256'], cs, '0' * 64):
            checks.raises(lambda bad=bad: reg.authorize(package, run_id, bad, gs), IntegrityError,
                          'authority', 'old/wrong/candidate-only activation rejected')
        checks.raises(lambda: reg.authorize(package, run_id, act, '0' * 64), IntegrityError,
                      'authority', 'wrong grant hash')
        checks.raises(lambda: reg.authorize(package, authority.BLOCKED_RUN, act, gs), IntegrityError,
                      'run_id', 'blocked historical run ID')
        empty = authority.Registry(root / 'empty', test_only=True)
        checks.raises(lambda: empty.authorize(package, run_id, act, gs), IntegrityError,
                      'authority', 'no activation')
        checks.check(not empty.root.exists(), 'isolation', 'authority read does not create namespace')
        only = authority.Registry(root / 'candidate-only', test_only=True)
        only_cs = only.publish('candidates', only.candidate(timeout_seconds=30))
        checks.raises(lambda: only.authorize(package, run_id, only_cs, gs), IntegrityError,
                      'authority', 'published candidate is not active authority')
        checks.raises(lambda: authority.Registry(authority.NAMESPACE, test_only=True), IntegrityError,
                      'isolation', 'test fixture cannot live in production namespace')
        checks.raises(lambda: authority.Registry(root / 'arbitrary'), IntegrityError,
                      'isolation', 'alternate real namespace rejected')

        # Exact source validation, including transitive executable dependencies.
        for path in c['executable_sources']:
            wrong = dict(c['executable_sources'], **{path: '0' * 64})
            checks.raises(lambda wrong=wrong: authority.verify_sources(wrong), IntegrityError,
                          'sources', 'mismatched executable:' + path)
        for field, value in [('phase', 'A'), ('activation_sha256', authority.ANCHOR['activation_sha256']),
                             ('candidate_sha256', authority.ANCHOR['candidate_sha256']),
                             ('generation_head', '0' * 64), ('execution_sha256', '0' * 64),
                             ('synthetic_evidence_allowed', True), ('run_id', run_id + '-wrong')]:
            mutated = copy.deepcopy(reg.read('grants', gs))
            mutated[field] = value
            bad = reg.publish('grants', mutated)
            checks.raises(lambda bad=bad: reg.authorize(package, run_id, act, bad), IntegrityError,
                          'grants', 'stale/wrong grant:' + field)
        for value in (0, 1, 0.0, 1.0, 'false', 'False', 'true', None, [], {}):
            malformed = copy.deepcopy(reg.read('grants', gs))
            malformed['synthetic_evidence_allowed'] = value
            bad = reg.publish('grants', malformed)
            checks.raises(lambda bad=bad: reg.authorize(package, run_id, act, bad), IntegrityError,
                          'grant_schema', 'exact Boolean required:' + repr(value))
        for field in reg.read('grants', gs):
            if field == 'synthetic_evidence_allowed':
                continue
            malformed = copy.deepcopy(reg.read('grants', gs))
            malformed[field] = 0 if type(malformed[field]) is bool else []
            # Namespace/test flag has a separate exact publication check.
            checks.raises(lambda malformed=malformed: reg._grant(malformed, reg.history()[0], run_id), IntegrityError,
                          'grant_schema', 'typed grant field:' + field)
        checks.check(gate()['authorization_sha256'] == gs, 'grant_schema', 'literal Boolean false remains valid')

        # No operator action, unreviewed content or unsupported candidate can activate.
        prospective = reg.candidate(timeout_seconds=30)
        checks.check(prospective['launch_profile'] == BOOT['launch_profile'](authority.IMPORTED_SOURCES),
                     'bootstrap', 'candidate binds exact clean launch profile')
        checks.check(prospective['execution_sha256'] == digest(canonical(dict(
                     executable_sources=prospective['executable_sources'], launch_profile=prospective['launch_profile']))),
                     'bootstrap', 'review/activation/grant execution digest includes launch profile')
        for field, value in [('isolated_required', False), ('isolated_required', 1),
                             ('no_site_required', False), ('no_site_required', 1),
                             ('entrypoint', 'tools/g_cal1_live_v4.py'), ('entrypoint_sha256', '0' * 64),
                             ('authority_version', 'g-cal1.authority.v1'), ('bootstrap_version', 'wrong'),
                             ('schema_version', 'wrong'), ('interpreter', 'untrusted')]:
            bad = copy.deepcopy(prospective)
            bad['launch_profile'][field] = value
            bad['execution_sha256'] = digest(canonical(dict(executable_sources=bad['executable_sources'],
                                                           launch_profile=bad['launch_profile'])))
            checks.raises(lambda bad=bad: reg._candidate(bad, authority.historical(), prospective['predecessor']),
                          IntegrityError, 'bootstrap', 'wrong/malformed launch profile:' + field + ':' + repr(value))
        bad = copy.deepcopy(prospective)
        del bad['launch_profile']
        checks.raises(lambda: reg._candidate(bad, authority.historical(), prospective['predecessor']),
                      IntegrityError, 'bootstrap', 'missing launch profile never accepted')
        for field, value in [('predecessor', {}), ('science_binding', {}), ('provider_binding', {}),
                             ('reviewed_transport_commit', '0' * 40), ('activated', True)]:
            bad = copy.deepcopy(prospective)
            bad[field] = value
            bs = reg.publish('candidates', bad)
            checks.raises(lambda bad=bad: reg._candidate(bad, authority.historical(), prospective['predecessor']), IntegrityError,
                          'activation', 'candidate mutation:' + field)
        bad = copy.deepcopy(prospective)
        bad['executable_sources']['tools/g_cal1_live_v4.py'] = '0' * 64
        bad['execution_sha256'] = digest(canonical(dict(executable_sources=bad['executable_sources'],
                                                        launch_profile=bad['launch_profile'])))
        bs = reg.publish('candidates', bad)
        br = dict(reg.fields(), schema_version='g-cal1.freeze-review.v2', verdict='PASS', candidate_sha256=bs,
                  execution_sha256=bad['execution_sha256'], reviewer='Sol 6.1', scope='EXECUTION_FREEZE_REVIEW')
        brs = reg.publish('reviews', br)
        bop = dict(reg.fields(), status='EXPLICIT_OPERATOR_FREEZE_ACTIVATION', candidate_sha256=bs,
                   review_sha256=brs, predecessor=bad['predecessor'])
        checks.raises(lambda: reg.activate(bs, brs, operator=bop), IntegrityError, 'sources', 'actual activation source mismatch')
        checks.raises(lambda: reg.activate(cs, '0' * 64, operator=op), IntegrityError,
                      'activation', 'missing review')
        good_cs = reg.publish('candidates', prospective)
        good_review = dict(reg.fields(), schema_version='g-cal1.freeze-review.v2', verdict='PASS',
                           candidate_sha256=good_cs, execution_sha256=prospective['execution_sha256'],
                           reviewer='Sol 6.1', scope='EXECUTION_FREEZE_REVIEW')
        good_rs = reg.publish('reviews', good_review)
        checks.raises(lambda: reg.activate(good_cs, good_rs, operator={}), IntegrityError,
                      'activation', 'no operator authority')
        wrong_review = dict(good_review, verdict='REVISE')
        wrong_rs = reg.publish('reviews', wrong_review)
        checks.raises(lambda: reg.activate(good_cs, wrong_rs, operator=dict(reg.fields(),
                      status='EXPLICIT_OPERATOR_FREEZE_ACTIVATION', candidate_sha256=good_cs,
                      review_sha256=wrong_rs, predecessor=prospective['predecessor'])), IntegrityError,
                      'activation', 'non-PASS review rejected before activation')
        checks.raises(lambda: reg.publish('candidates', c), IntegrityError, 'immutability', 'write-once collision')

        # Exercise the actual frozen collection kernel through the new authority consumer.
        t, provider, metadata = verified(binding, package.schedule)
        row = package.schedule[0]
        provider.add(mocks.Script(mocks.envelope(row, synthetic_gold(package.members[row['fixture_id']]))))
        class UnboundEntrypoint(LiveRun):
            pass
        checks.raises(lambda: UnboundEntrypoint(package, reg, run_id, activation_sha256=act, grant_sha256=gs, transport=t),
                      IntegrityError, 'source_loading', 'unbound subclass cannot substitute the verified live entrypoint')
        checks.check(provider.posts() == [] and not (reg.root / 'runs' / run_id).exists(),
                     'source_loading', 'entrypoint identity refusal before contact/reservation')
        run = LiveRun(package, reg, run_id, activation_sha256=act, grant_sha256=gs, transport=t)
        checks.check(t.synthetic_only is False and metadata['internal_option_honoring'] == 'UNATTESTED',
                     'transport', 'live marker and honest sampling status')
        score = run.perform(row)
        checks.check(score['semantic_correct'] is True, 'integration', 'unchanged frozen scoring')
        checks.check(len(provider.posts()) == 1 and provider.posts()[0]['body'] == package.wire(row),
                     'integration', 'one exact request/seed; mocked HTTP only')
        cp = run.checkpoint()
        checks.raises(lambda: reg.authorize(package, run_id, act, gs), IntegrityError, 'run_id', 'no fresh reuse')
        same = authority.Registry(reg.root, test_only=True)
        checks.raises(lambda: same.authorize(package, run_id, act, gs), IntegrityError,
                      'run_id', 'reservation persists across registry reconstruction')
        resumed, provider2, _ = verified(binding, package.schedule, start_position=2)
        again = LiveRun(package, reg, run_id, activation_sha256=act, grant_sha256=gs, transport=resumed, resume=True)
        checks.raises(lambda: again.perform(package.schedule[1]), IntegrityError, 'checkpoint', 'unverified resume blocked')
        checks.check(provider2.posts() == [], 'checkpoint', 'zero transport after failed unverified resume')
        # The rejected attempt is deliberately terminal; clean verified resume is
        # tested in a separate namespace, never by clearing its integrity incident.
        checks.raises(lambda: LiveRun(package, reg, run_id, activation_sha256=act, grant_sha256=gs,
                                     transport=resumed, resume=True), IntegrityError, 'checkpoint', 'restart retains invalidity')

        # New generation supersedes old authority without touching historical artifacts.
        second = reg.candidate(timeout_seconds=31)
        scs = reg.publish('candidates', second)
        review = dict(reg.fields(), schema_version='g-cal1.freeze-review.v2', verdict='PASS', candidate_sha256=scs,
                      execution_sha256=second['execution_sha256'], reviewer='Sol 6.1', scope='EXECUTION_FREEZE_REVIEW')
        srs = reg.publish('reviews', review)
        sop = dict(reg.fields(), status='EXPLICIT_OPERATOR_FREEZE_ACTIVATION', candidate_sha256=scs,
                   review_sha256=srs, predecessor=second['predecessor'])
        new_act = reg.activate(scs, srs, operator=sop)
        checks.check(new_act != act and reg.read('activations', act)['candidate_sha256'] == cs,
                     'lineage', 'old immutable activation still readable')
        checks.raises(gate, IntegrityError, 'lineage', 'superseded activation rejected')
        checks.raises(lambda: reg.authorize(package, run_id, new_act, gs, resume=True), IntegrityError,
                      'lineage', 'stale authorization cannot follow rollover')
        checks.raises(lambda: reg.activate(cs, rs, operator=op), IntegrityError, 'lineage', 'old candidate cannot reactivate')

        # A live object created before rollover must not contact after rollover.
        r, cc, _, _, aa, _ = fixture(root / 'stale-object', package)
        rid = 'G-CAL1-CAL-offline-stale-0003'
        gg = grant(r, rid)
        tt, pp, _ = verified(binding, package.schedule)
        rr = LiveRun(package, r, rid, activation_sha256=aa, grant_sha256=gg, transport=tt)
        nc = r.candidate(timeout_seconds=31)
        ncs = r.publish('candidates', nc)
        nr = dict(r.fields(), schema_version='g-cal1.freeze-review.v2', verdict='PASS', candidate_sha256=ncs,
                  execution_sha256=nc['execution_sha256'], reviewer='Sol 6.1', scope='EXECUTION_FREEZE_REVIEW')
        nrs = r.publish('reviews', nr)
        r.activate(ncs, nrs, operator=dict(r.fields(), status='EXPLICIT_OPERATOR_FREEZE_ACTIVATION',
                                          candidate_sha256=ncs, review_sha256=nrs, predecessor=nc['predecessor']))
        checks.raises(lambda: rr.perform(package.schedule[0]), IntegrityError, 'lineage', 'stale live object rejected')
        checks.check(pp.posts() == [] and len(rr.journal.read()) == 1 and rr.incidents.read(),
                     'lineage', 'no START/contact; rejection retained')

        # Exact transport instance/type, injected IO marker and frozen configuration.
        for label in ('synthetic', 'timeout', 'model', 'seed', 'metadata'):
            r, _, _, _, aa, _ = fixture(root / ('transport-' + label), package)
            rid = 'G-CAL1-CAL-offline-transport-' + label
            gg = grant(r, rid)
            tt, pp, _ = verified(binding, package.schedule)
            if label == 'synthetic':
                tt.synthetic_only = True
            elif label == 'timeout':
                tt._timeout = 31
            elif label == 'model':
                tt._binding['models'][0]['model'] = 'wrong-model'
            elif label == 'seed':
                tt._schedule[0]['seed'] += 1
            else:
                tt._metadata['internal_option_honoring'] = 'ATTESTED'
            checks.raises(lambda: LiveRun(package, r, rid, activation_sha256=aa, grant_sha256=gg, transport=tt),
                          IntegrityError, 'transport', 'transport mutation:' + label)
            checks.check(not (r.root / 'runs' / rid).exists() and pp.posts() == [],
                         'transport', 'no run creation/POST:' + label)

        # Tamper only disposable fixtures, never the frozen package/source.
        for label in ('pointer', 'candidate', 'activation', 'lineage', 'extra_transition'):
            r, cc, ccsha, _, aa, _ = fixture(root / label, package)
            if label == 'pointer':
                write_once(r.root / 'ACTIVE_FREEZE.json', {})
            elif label in ('candidate', 'activation'):
                path = r.root / ('candidates' if label == 'candidate' else 'activations') / ((ccsha if label == 'candidate' else aa) + '.json')
                with path.open('ab') as stream:
                    stream.write(b' ')
            elif label == 'lineage':
                (r.root / 'transitions/000001.json').unlink()
            else:
                (r.root / 'transitions/hidden.txt').write_bytes(b'fixture corruption')
            checks.raises(r.history, IntegrityError, 'tamper', label + ' rejected')

        # Complete 80-call synthetic run, checkpoint, correct resume and report.
        r, cc, _, _, aa, _ = fixture(root / 'complete', package)
        rid = 'G-CAL1-CAL-offline-complete-0002'
        gg = grant(r, rid)
        t, p, _ = verified(binding, package.schedule)
        rr = LiveRun(package, r, rid, activation_sha256=aa, grant_sha256=gg, transport=t)
        for row in package.schedule[:40]:
            p.add(mocks.Script(mocks.envelope(row, synthetic_gold(package.members[row['fixture_id']]))))
            checks.check(rr.perform(row)['semantic_correct'], 'full_schedule', row['call_id'])
        cp = rr.checkpoint()
        t2, p2, _ = verified(binding, package.schedule, start_position=41)
        rr2 = LiveRun(package, r, rid, activation_sha256=aa, grant_sha256=gg, transport=t2, resume=True)
        rr2.verify_resume(cp)
        for row in package.schedule[40:]:
            p2.add(mocks.Script(mocks.envelope(row, synthetic_gold(package.members[row['fixture_id']]))))
            checks.check(rr2.perform(row)['semantic_correct'], 'full_schedule', row['call_id'])
        report = rr2.final_report()
        checks.check(report['state']['verdict'] == 'VALID_COMPLETE' and report['mocked_attempts'] == 80 and
                     report['provider_model_calls'] == 0 and report['scientific_observations'] == 0,
                     'full_schedule', 'complete synthetic report is not scientific evidence')
        checks.check(len(p.posts()) + len(p2.posts()) == 80, 'full_schedule', 'exact one mock POST per row')
        checks.check(len(list((rr2.directory / 'provider_metadata').glob('*.json'))) >= 1,
                     'integration', 'truthful provider metadata evidence retained separately')

        # Malformed sealed checkpoint attacks use the real inherited verifier.
        for payload in ([], None, 'wrong', {}):
            label = type(payload).__name__
            r, _, _, _, aa, _ = fixture(root / ('checkpoint-' + label), package)
            rid = 'G-CAL1-CAL-offline-checkpoint-' + label
            gg = grant(r, rid)
            tt, pp, _ = verified(binding, package.schedule)
            rr = LiveRun(package, r, rid, activation_sha256=aa, grant_sha256=gg, transport=tt)
            cp = rr.checkpoint()
            bad = rr.directory / 'malformed.json'
            write_once(bad, {'payload': payload, 'sha256': digest(canonical(payload))})
            checks.raises(lambda: rr.verify_resume(bad), IntegrityError, 'checkpoint', 'malformed payload:' + label,
                          predicate=lambda exc: exc.event == 'CORRUPTED_CHECKPOINT')
            checks.raises(lambda: rr.perform(package.schedule[0]), IntegrityError, 'checkpoint', 'caught corruption terminal')
            checks.check(pp.posts() == [] and 'CORRUPTED_CHECKPOINT' in rr.events,
                         'checkpoint', 'zero contact and corruption retained')

        for failure in (None, KeyboardInterrupt('fixture'), SystemExit('fixture'), GeneratorExit('fixture')):
            r, _, _, _, aa, _ = fixture(root / ('failure-' + type(failure).__name__), package)
            rid = 'G-CAL1-CAL-offline-failure-' + type(failure).__name__
            gg = grant(r, rid)
            tt, pp, _ = verified(binding, package.schedule)
            pp.add(mocks.Script(body=b'{}') if failure is None else mocks.Script(fail_at='read', error=failure))
            rr = LiveRun(package, r, rid, activation_sha256=aa, grant_sha256=gg, transport=tt)
            caught = checks.raises(lambda: rr.perform(package.schedule[0]), IntegrityError if failure is None else type(failure),
                                   'terminal', 'malformed/control-flow:' + type(failure).__name__)
            if failure is not None:
                checks.check(caught is failure and 'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT' in rr.events,
                             'terminal', 'original exception and retained omission')
            calls = len(pp.posts())
            checks.raises(lambda: rr.perform(package.schedule[1]), IntegrityError, 'terminal', 'external catch cannot continue')
            checks.check(len(pp.posts()) == calls, 'terminal', 'zero later HTTP')
            checks.raises(lambda: LiveRun(package, r, rid, activation_sha256=aa, grant_sha256=gg,
                                         transport=tt, resume=True), IntegrityError, 'terminal', 'restart rejects')

    checks.check(mocks.protected_snapshot() == protected, 'preservation', 'all existing protected/untracked bytes unchanged')
    checks.check({p.relative_to(authority.NAMESPACE).as_posix(): mocks.file_digest(p)
                  for p in authority.NAMESPACE.rglob('*') if p.is_file()} == production_before,
                 'isolation', 'no real authority artifacts created or changed')
    checks.check(len(mocks.AUDIT) == audit_before, 'no_contact', 'no socket/process/provider contact')
    result = dict(schema_version='g-cal1.authority-v2.offline-tests.v1', passed=checks.passed, failed=len(checks.failed),
                  categories=checks.categories, failures=checks.failed, provider_metadata_calls=0,
                  provider_generation_calls=0, actual_activation=False, scientific_observations=0,
                  protected_package_unchanged=True, executable_sources=authority.IMPORTED_SOURCES)
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(bool(checks.failed))


if __name__ == '__main__':
    raise SystemExit(main())
