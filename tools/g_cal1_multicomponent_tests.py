"""Offline component identity tests; preserved HTTP evidence, no provider contact."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).absolute().parent))
import g_cal1_ollama_transport_tests as mocks
import base64
import copy
import json
import tempfile
from unittest.mock import patch

import g_cal1_ollama_transport as live
from g_extract1_contract import canonical, digest, load

EVIDENCE = mocks.DATA / 'preexecution/multicomponent_metadata_repair/provider_evidence'


def main():
    checks = mocks.Checks()
    snapshot = mocks.protected_snapshot()
    audit_before = len(mocks.AUDIT)
    raw_manifest = (EVIDENCE / 'LOCAL_OLLAMA_MANIFEST.json').read_bytes()
    raw_show = (EVIDENCE / 'PRESERVED_SHOW_RESPONSE.json').read_bytes()
    base = load(mocks.CANDIDATE)['provider_binding']
    binding = live.component_provider_binding(base, {base['models'][0]['model']: raw_manifest})
    model = binding['models'][0]
    expected = model['components']
    checks.check([x['role'] for x in expected] == ['model', 'projector'], 'composition', 'role order deterministic')
    checks.check(digest(raw_manifest) == model['manifest_digest'] and expected[0]['sha256'] == model['blob_sha256'],
                 'composition', 'exact existing manifest and primary preserved')
    checks.check(len(json.loads(raw_manifest)['layers']) == 4, 'composition', 'other layers are license and params, not model components')
    package = mocks.TestPackage()

    with tempfile.TemporaryDirectory(prefix='g-cal1-components-') as tmp:
        root = Path(tmp)
        manifest_path = root / 'manifest'
        manifest_path.write_bytes(raw_manifest)
        with patch.object(live, '_manifest_path', return_value=manifest_path):
            def probe(label, scripts=None, candidate=binding, passed=False):
                provider = mocks.Provider(scripts or mocks.metadata_scripts(candidate))
                transport = live.OllamaLiveTransport(candidate, package.schedule, timeout_seconds=120,
                                                     connection_factory=provider)
                if passed:
                    receipts = transport.verify_metadata()
                    proof = receipts['verified_observable_identity'][0]['component_evidence']
                    checks.check(proof['components'] == candidate['models'][0]['components'], label, 'exact component identities and roles')
                    checks.check(proof['manifest_sha256'] == candidate['models'][0]['manifest_digest'] and
                                 base64.b64decode(proof['manifest_body_b64']) == manifest_path.read_bytes(),
                                 label, 'exact manifest bytes retained')
                    checks.check(receipts['internal_option_honoring'] == 'UNATTESTED' and
                                 receipts['internal_option_honoring_attested_by_provider'] is False,
                                 label, 'no internal option attestation')
                else:
                    checks.raises(transport.verify_metadata, live.MetadataVerificationError, label, 'fail closed')
                    checks.check(transport.disabled is not None, label, 'failed verification disables transport')
                checks.check(provider.posts() == [], label, 'zero generation attempts')
                return transport

            scripts = mocks.metadata_scripts(binding)
            scripts[-1] = mocks.Script(raw_show)
            probe('preserved_response', scripts, passed=True)
            primary, projector = (x['sha256'] for x in expected)
            from_text = lambda values: '\n'.join('FROM C:\\models\\blobs\\sha256-' + value for value in values)
            probe('order_forward', mocks.metadata_scripts(binding, modelfile=from_text([primary, projector])), passed=True)
            probe('order_reversed', mocks.metadata_scripts(binding, modelfile=from_text([projector, primary])), passed=True)
            for label, values in (
                ('wrong_projector', [primary, 'a' * 64]), ('wrong_primary', ['b' * 64, projector]),
                ('missing_projector', [primary]), ('missing_primary', [projector]),
                ('unexpected_third', [primary, projector, 'c' * 64]),
                ('duplicate_component', [primary, projector, projector]), ('empty_components', [])):
                probe(label, mocks.metadata_scripts(binding, modelfile=from_text(values)))
            for value in ('FROM bad/sha256-' + primary + 'x', 'FROM bad/sha256-' + primary[:-1],
                          'FROM bad/sha256-' + primary + ' trailing', 'FROM qwen3.8:27b',
                          'from bad/sha256-' + primary, 'FROM bad/sha256-' + primary + '\x00'):
                probe('malformed_FROM', mocks.metadata_scripts(binding, modelfile=value))
            probe('wrong_manifest', mocks.metadata_scripts(binding, digest_value='d' * 64))
            probe('wrong_version', mocks.metadata_scripts(binding, version='0.0.0'))
            scripts = mocks.metadata_scripts(binding)
            scripts[1] = mocks.Script(mocks.body({'models': [dict(name='wrong', digest=model['manifest_digest'])]}))
            probe('wrong_model', scripts)
            manifest_path.write_bytes(raw_manifest + b' ')
            probe('local_manifest_digest_mismatch')
            manifest_path.write_bytes(raw_manifest)
            for label, change in (
                ('role_swap', lambda m: [x.update(mediaType='application/vnd.ollama.image.' +
                    ('model' if x['mediaType'].endswith('.projector') else 'projector'))
                    for x in m['layers'] if x['mediaType'].endswith(('.model', '.projector'))]),
                ('extra_adapter', lambda m: m['layers'].append(dict(mediaType='application/vnd.ollama.image.adapter',
                    digest='sha256:' + 'e' * 64, size=1))),
                ('duplicate_role', lambda m: m['layers'].append(copy.deepcopy(m['layers'][0]))),
                ('wrong_size_type', lambda m: m['layers'][0].update(size=True))):
                manifest = json.loads(raw_manifest)
                change(manifest)
                altered = canonical(manifest)
                bad = copy.deepcopy(binding)
                bad['models'][0]['manifest_digest'] = digest(altered)
                manifest_path.write_bytes(altered)
                probe(label, candidate=bad)
            manifest_path.write_bytes(raw_manifest)
            for bad_components in (list(reversed(expected)), expected + [expected[0]],
                [dict(role='model', sha256='a' * 64)], [dict(role='projector', sha256=projector)],
                [dict(role='model', sha256=primary, extra='unknown')]):
                bad = copy.deepcopy(binding)
                bad['models'][0]['components'] = bad_components
                checks.raises(lambda bad=bad: live.OllamaLiveTransport(bad, package.schedule, timeout_seconds=120),
                              live.TransportContractError, 'binding_schema', 'malformed component binding rejected')
            # The original contract is not silently upgraded to cover a projector.
            legacy, provider, _ = mocks.verified(base, package.schedule)
            checks.check(legacy._metadata['verified_observable_identity'][0]['blob_sha256'] == base['models'][0]['blob_sha256'],
                         'legacy_single', 'valid old single-component fixture still passes')
            probe('legacy_two_not_reinterpreted', mocks.metadata_scripts(base, modelfile=from_text([primary, projector])), candidate=base)
            mocks.integration_tests(package, binding, checks, root / 'frozen_Run')

    # Authority checks use the source-only graph, never ordinary-import authority.
    source = mocks.ROOT / 'tools/g_cal1_source_loader_v1.py'
    boot = {'__file__': str(source), '__name__': 'gcal_component_test_bootstrap'}
    exec(compile(source.read_bytes(), str(source), 'exec', dont_inherit=True), boot)
    runtime = boot['VerifiedRuntime'](boot['inventory']())
    authority = runtime.module('g_cal1_authority_v2')
    registry = authority.Registry()
    current, reservations = registry.history()
    checks.check(current['activation_sha256'] == 'f6c2a0abe5c5539dc3ef2bf248c6dbcb56a9e6def1ae57f6c33bd1ae1b2e0207' and
                 reservations == {}, 'old_authority', 'historical active selection remains readable, no reservation')
    old = registry.read('candidates', current['candidate_sha256'])
    checks.raises(lambda: authority.verify_sources(old['executable_sources']), runtime.module('g_extract1_contract').IntegrityError,
                  'old_authority', 'old active freeze cannot authorize repaired executable')
    checks.check(authority.provider_extension(binding, base), 'prospective_binding', 'explicit component-only extension allowed')
    for field, value in [('provider_version', '0.0.0'), ('generation_configuration', {})]:
        bad = copy.deepcopy(binding)
        bad[field] = value
        checks.raises(lambda bad=bad: authority.provider_extension(bad, base), runtime.module('g_extract1_contract').IntegrityError,
                      'prospective_binding', 'no scientific/configuration change:' + field)
    checks.raises(lambda: registry.candidate(timeout_seconds=120), runtime.module('g_extract1_contract').IntegrityError,
                  'prospective_binding', 'production preparation cannot silently omit explicit components')
    checks.check(mocks.protected_snapshot() == snapshot, 'preservation', 'all existing evidence and protected bytes unchanged')
    checks.check(len(mocks.AUDIT) == audit_before, 'no_contact', 'zero provider/socket/process contact')
    print(json.dumps(dict(passed=checks.passed, failed=len(checks.failed), failures=checks.failed,
        categories=checks.categories, preserved_metadata_response='PASS', provider_metadata_calls=0,
        provider_generation_calls=0, scientific_observations=0), indent=2, sort_keys=True))
    return int(bool(checks.failed))


if __name__ == '__main__':
    raise SystemExit(main())
