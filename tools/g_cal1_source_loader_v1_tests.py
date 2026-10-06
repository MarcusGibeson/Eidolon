"""NO-PROVIDER P1 probes, including Sol's exact external timestamp-pyc attack."""
from __future__ import annotations

import sys
import json
import hashlib
import importlib.util
import importlib._bootstrap_external
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).absolute().parent.parent
SOURCE = ROOT / 'tools/g_cal1_source_loader_v1.py'
AUDIT = []


def no_socket(event, args):
    if event.startswith('socket.'):
        AUDIT.append(event)
        raise RuntimeError('NO_PROVIDER_SOCKET_DENIED:' + event)


sys.addaudithook(no_socket)


def boot():
    namespace = {'__name__': 'gcal_source_only_test_bootstrap', '__file__': str(SOURCE)}
    raw = SOURCE.read_bytes()
    exec(compile(raw, str(SOURCE), 'exec', dont_inherit=True), namespace)
    return namespace


BOOT = boot()


def worker(kind, expected_path, directory):
    expected = json.loads(Path(expected_path).read_bytes())
    if kind == 'cached_loader':
        import g_cal1_source_loader_v1 as cached
        assert cached.P1_UNREVIEWED_CACHE_MARKER is True
        try:
            cached.VerifiedRuntime(expected)
        except cached.SourceVerificationError:
            rejected = True
        else:
            rejected = False
        assert rejected
        runtime = BOOT['VerifiedRuntime'](expected)
        assert not hasattr(runtime.module('g_cal1_source_loader_v1'), 'P1_UNREVIEWED_CACHE_MARKER')
        result = dict(cached_bootstrap_rejected=True, source_bootstrap_verified=True)
    else:
        import g_cal1_ollama_transport as cached
        assert cached.REVIEW_UNREVIEWED_BYTECODE_MARKER == 'not in frozen source'
        assert Path(cached.__file__).resolve() == (ROOT / 'tools/g_cal1_ollama_transport.py').resolve()
        import g_cal1_authority_v2 as ordinary
        try:
            ordinary.verify_sources(expected)
        except Exception as exc:
            assert getattr(exc, 'event', None) == 'PROVENANCE_MISMATCH'
            rejected = True
        else:
            rejected = False
        assert rejected
        # Existing stale sys.modules entries remain present; the verified graph
        # must ignore them rather than delete caches or replace global modules.
        import g_cal1_authority_v2_tests as migration
        private = migration.RUNTIME.module('g_cal1_ollama_transport')
        assert private is not cached and not hasattr(private, 'REVIEW_UNREVIEWED_BYTECODE_MARKER')
        package = migration.mocks.TestPackage()
        package.binding.pop('test_only')
        package._derived = migration.canonical(package._state())
        registry, _, _, _, activation, _ = migration.fixture(Path(directory) / 'TEST_ONLY_AUTHORITY', package)
        run_id = 'G-CAL1-CAL-offline-cache-repair-0001'
        grant = migration.grant(registry, run_id)
        registry.authorize(package, run_id, activation, grant)
        migration.authority.verify_sources(expected)
        result = dict(unreviewed_cached_code_observed=True, cached_path=cached.__cached__,
                      correct_source_hash=hashlib.sha256((ROOT / 'tools/g_cal1_ollama_transport.py').read_bytes()).hexdigest(),
                      ordinary_consumer_rejected=True, verified_private_transport_is_separate=True,
                      cached_marker_absent_from_executed_graph=True, source_only_authorization_valid=True)
    assert not AUDIT
    print(json.dumps(dict(result, provider_calls=0), sort_keys=True))


def main():
    checks = []

    def check(ok, label):
        checks.append(dict(case=label, passed=bool(ok)))
        if not ok:
            raise AssertionError(label)

    def reject(action, label):
        try:
            action()
        except BOOT['SourceVerificationError']:
            check(True, label)
        else:
            check(False, label)

    expected = BOOT['inventory']()
    runtime = BOOT['VerifiedRuntime'](expected)
    check(len(expected) == 18 and len(runtime._executed) == 18, 'complete verified-source graph loads')
    runtime.module('g_cal1_authority_v2').verify_sources(expected)
    check(True, 'authority requires and accepts source-only ownership')
    check(all(runtime._codes[Path(p).stem].co_filename == str(ROOT / p) for p in expected), 'exact compiled logical paths')
    for path in expected:
        wrong = dict(expected, **{path: '0' * 64})
        reject(lambda wrong=wrong: BOOT['VerifiedRuntime'](wrong), 'dependency hash mismatch:' + path)
    wrong = dict(expected)
    wrong['tools/other_entry.py'] = wrong.pop('tools/g_cal1_live_v4.py')
    reject(lambda: BOOT['VerifiedRuntime'](wrong), 'logical path substitution')
    reject(lambda: BOOT['VerifiedRuntime']({}), 'missing inventory is never authority')
    with tempfile.TemporaryDirectory(prefix='gcal-source-loader-tests-') as temp:
        directory = Path(temp)
        copied = directory / 'EXECUTABLE_COPY'
        for p in expected:
            target = copied / p
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / p, target)
        reject(lambda: BOOT['VerifiedRuntime'](expected, root=copied / '..' / copied.name), 'root path-alias substitution')
        changed = copied / 'tools/g_cal1_ollama_transport.py'
        with changed.open('ab') as stream:
            stream.write(b'\nP1_VERIFIED_SOURCE_MARKER = "compiled from verified bytes"\n')
        reject(lambda: BOOT['VerifiedRuntime'](expected, root=copied), 'modified source rejected before execution')
        new_expected = BOOT['inventory'](copied)
        observed = []
        original = BOOT['_COMPILE']

        def observe(raw, filename, *args, **kwargs):
            observed.append((raw, filename))
            return original(raw, filename, *args, **kwargs)

        BOOT['_COMPILE'] = observe
        try:
            marked = BOOT['VerifiedRuntime'](new_expected, root=copied)
        finally:
            BOOT['_COMPILE'] = original
        check(marked.module('g_cal1_ollama_transport').P1_VERIFIED_SOURCE_MARKER == 'compiled from verified bytes',
              'executed code derives from the accepted source buffer')
        for p, sha in new_expected.items():
            matches = [raw for raw, filename in observed if filename == str(copied / p)]
            check(len(matches) == 1 and type(matches[0]) is bytes and hashlib.sha256(matches[0]).hexdigest() == sha,
                  'exact hashed buffer compiled once:' + p)
        with changed.open('ab') as stream:
            stream.write(b'\n# external post-verification mutation\n')
        reject(lambda: marked.verify(new_expected), 'source drift after verified loading rejected')
        # Deterministic Windows reparse/symlink refusal without requiring admin.
        native_stat = Path.lstat

        def reparse_stat(path, *args, **kwargs):
            value = native_stat(path, *args, **kwargs)
            if path == copied / 'tools/g_cal1_live_v4.py':
                from types import SimpleNamespace
                return SimpleNamespace(st_mode=value.st_mode, st_file_attributes=0x400)
            return value

        with patch.object(Path, 'lstat', reparse_stat):
            reject(lambda: BOOT['VerifiedRuntime'](new_expected, root=copied), 'reparse/symlink source aliases reject')

        expected_file = directory / 'EXPECTED_INVENTORY_TEST_ONLY.json'
        expected_file.write_bytes(json.dumps(expected, sort_keys=True).encode())
        for kind, module, marker in (
                ('cached_transport', 'g_cal1_ollama_transport', b'\nREVIEW_UNREVIEWED_BYTECODE_MARKER = "not in frozen source"\n'),
                ('unchecked_hash_transport', 'g_cal1_ollama_transport', b'\nREVIEW_UNREVIEWED_BYTECODE_MARKER = "not in frozen source"\n'),
                ('checked_hash_transport', 'g_cal1_ollama_transport', b'\nREVIEW_UNREVIEWED_BYTECODE_MARKER = "not in frozen source"\n'),
                ('cached_loader', 'g_cal1_source_loader_v1', b'\nP1_UNREVIEWED_CACHE_MARKER = True\n')):
            prefix = directory / kind / 'EXTERNAL_CACHE'
            source = ROOT / 'tools' / (module + '.py')
            previous = sys.pycache_prefix
            sys.pycache_prefix = str(prefix)
            try:
                cache = Path(importlib.util.cache_from_source(str(source)))
            finally:
                sys.pycache_prefix = previous
            cache.parent.mkdir(parents=True, exist_ok=True)
            stat = source.stat()
            # Exact Sol attack: valid source timestamp and size, altered code;
            # Python -B still reads this external cache in a clean process.
            payload = compile(source.read_bytes() + marker, str(source), 'exec', dont_inherit=True)
            if 'hash_transport' in kind:
                cache.write_bytes(importlib._bootstrap_external._code_to_hash_pyc(
                    payload, importlib.util.source_hash(source.read_bytes()), checked=kind.startswith('checked')))
            else:
                cache.write_bytes(importlib._bootstrap_external._code_to_timestamp_pyc(payload, int(stat.st_mtime), stat.st_size))
            result = subprocess.run([sys.executable, '-B', '-X', 'pycache_prefix=' + str(prefix),
                                     str(Path(__file__).absolute()), '--worker', kind, str(expected_file), str(directory / kind)],
                                    capture_output=True, timeout=120)
            check(result.returncode == 0, kind + ' fresh-process cached/preloaded attack closed:' + result.stderr.decode(errors='replace'))
            row = json.loads(result.stdout)
            check(row['provider_calls'] == 0, kind + ' zero provider calls')
            print(json.dumps({'probe': kind, 'result': row}, sort_keys=True))
        direct = subprocess.run([sys.executable, '-B', str(SOURCE), '--inventory-file', str(expected_file),
                                 '--inventory-sha256', hashlib.sha256(expected_file.read_bytes()).hexdigest()],
                                capture_output=True, timeout=60)
        check(direct.returncode == 0 and json.loads(direct.stdout) == dict(verified_source_count=18, provider_calls=0,
              execution_authorized=False, authority_created=False), 'direct-source CLI loads code only, no authority')
        bad_cli = subprocess.run([sys.executable, '-B', str(SOURCE), '--inventory-file', str(expected_file),
                                  '--inventory-sha256', '0' * 64], capture_output=True, timeout=60)
        check(bad_cli.returncode != 0, 'direct-source CLI rejects wrong reviewed inventory identity')
        # A preloaded object bearing the expected name/path cannot affect a graph.
        import types
        stale = types.ModuleType('g_cal1_ollama_transport')
        stale.__file__ = str(ROOT / 'tools/g_cal1_ollama_transport.py')
        stale.P1_STALE_PRELOADED = True
        with patch.dict(sys.modules, g_cal1_ollama_transport=stale):
            clean = BOOT['VerifiedRuntime'](expected)
            check(clean.module('g_cal1_ollama_transport') is not stale and
                  not hasattr(clean.module('g_cal1_ollama_transport'), 'P1_STALE_PRELOADED'), 'preloaded module substitution bypassed safely')
            check(sys.modules['g_cal1_ollama_transport'] is stale, 'loader does not rewrite historical/global modules')
    check(AUDIT == [], 'no socket/provider contact')
    print(json.dumps(dict(schema_version='g-cal1.source-loader.offline-tests.v1', passed=len(checks), failed=0,
                          assertions=checks, executable_source_count=len(expected), provider_metadata_calls=0,
                          provider_generation_calls=0, actual_authority_created=False), sort_keys=True))
    return 0


if __name__ == '__main__':
    if sys.argv[1:2] == ['--worker']:
        worker(*sys.argv[2:])
    else:
        raise SystemExit(main())
