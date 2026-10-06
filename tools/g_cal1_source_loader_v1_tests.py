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
import types
from unittest.mock import patch

ROOT = Path(__file__).absolute().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))  # Test fixtures only, after isolated startup.
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


def stdlib_worker(kind, expected_path, directory):
    expected = json.loads(Path(expected_path).read_bytes())
    directory = Path(directory)
    sentinel = 'UNBOUND_STANDARD_LIBRARY_PROBE'
    shadow = directory / ('site-packages' if kind == 'site_packages' else 'shadow')
    shadow.mkdir()
    fixture = shadow / 'copy.py'
    fixture.write_bytes(('PROBE_ORIGIN_SENTINEL = ' + repr(sentinel) + '\n').encode())
    (shadow / 'gcal_third_party_package.py').write_bytes(('PROBE_ORIGIN_SENTINEL = ' + repr(sentinel) + '\n').encode())
    sys.modules.pop('copy', None)
    if kind in ('preloaded_external', 'preloaded_repository', 'forged_origin'):
        stale = types.ModuleType('copy')
        stale.__file__ = str(fixture if kind == 'preloaded_external' else ROOT / 'tools/g_cal1_authority_v2.py')
        stale.__spec__ = importlib.util.spec_from_file_location('copy', stale.__file__)
        stale.PROBE_ORIGIN_SENTINEL = sentinel
        if kind == 'forged_origin':
            legitimate = Path(sys._stdlib_dir) / 'copy.py'
            stale.__file__ = str(legitimate)
            stale.__spec__ = importlib.util.spec_from_file_location('copy', legitimate)
            exec(compile('def deepcopy(value): return value\n', str(fixture), 'exec'), stale.__dict__)
        sys.modules['copy'] = stale
    if kind == 'cwd':
        os.chdir(shadow)
        sys.path.insert(0, '')
    else:
        sys.path.insert(0, str(shadow))
    try:
        trusted = boot()
        runtime = trusted['VerifiedRuntime'](expected)
    except Exception as exc:
        assert kind in ('preloaded_external', 'preloaded_repository', 'forged_origin')
        assert type(exc).__name__ == 'SourceVerificationError'
        assert sys.modules['copy'] is stale
        result = dict(foreign_preloaded_module_rejected=True, reason=str(exc), global_foreign_module_unchanged=True)
    else:
        assert kind in ('path', 'cwd', 'site_packages')
        copy_module = runtime.module('g_cal1_authority_v2').copy
        assert not hasattr(copy_module, 'PROBE_ORIGIN_SENTINEL')
        assert Path(copy_module.__file__).resolve() == (Path(sys._stdlib_dir) / 'copy.py').resolve()
        data = {'nested': [1,2]}
        copied = copy_module.deepcopy(data)
        assert copied == data and copied is not data and copied['nested'] is not data['nested']
        runtime.module('g_cal1_authority_v2').verify_sources(expected)
        try:
            trusted['_STDLIB']('gcal_third_party_package')
        except trusted['SourceVerificationError']:
            third_party_rejected = True
        else:
            third_party_rejected = False
        assert third_party_rejected and 'gcal_third_party_package' not in sys.modules
        result = dict(external_fixture_not_executed=True, legitimate_copy_origin=copy_module.__file__,
                      legitimate_behavior_unchanged=True, authority_source_verification=True,
                      existing_third_party_source_rejected=True)
    assert AUDIT == []
    print(json.dumps(dict(probe=kind, provider_calls=0, **result), sort_keys=True))


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
        for kind in ('path','cwd','site_packages','preloaded_external','preloaded_repository','forged_origin'):
            target = directory / kind
            target.mkdir()
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(Path(__file__).absolute()), '--stdlib-worker',
                                     kind, str(expected_file), str(target)], capture_output=True, timeout=60)
            check(result.returncode == 0, kind + ' standard-library boundary:' + result.stderr.decode(errors='replace'))
            row = json.loads(result.stdout)
            check(row['provider_calls'] == 0, kind + ' standard-library zero provider calls')
            print(json.dumps({'probe':'stdlib_' + kind,'result':row},sort_keys=True))
        for name, origin in [('copy', 'source'), ('textwrap', 'source'), ('sys', 'built-in'), ('os', 'frozen')]:
            module = BOOT['_STDLIB'](name)
            check(module.__spec__.origin == origin if origin != 'source' else
                  BOOT['_STDLIB'].origin(module.__spec__.origin) == BOOT['_STDLIB'].origin(module.__file__),
                  'legitimate interpreter import:' + name)
        for name in ('gcal_third_party_package', 'gcal_missing_external_dependency'):
            reject(lambda name=name: BOOT['_STDLIB'](name), 'unproven external dependency fails closed:' + name)
        reject(lambda: runtime._import('g_cal1_authority_v2', level=1), 'relative repository import cannot escape graph')
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
            result = subprocess.run([sys.executable, '-I', '-S', '-B', '-X', 'pycache_prefix=' + str(prefix),
                                     str(Path(__file__).absolute()), '--worker', kind, str(expected_file), str(directory / kind)],
                                    capture_output=True, timeout=120)
            check(result.returncode == 0, kind + ' fresh-process cached/preloaded attack closed:' + result.stderr.decode(errors='replace'))
            row = json.loads(result.stdout)
            check(row['provider_calls'] == 0, kind + ' zero provider calls')
            print(json.dumps({'probe': kind, 'result': row}, sort_keys=True))
        direct = subprocess.run([sys.executable, '-I', '-S', '-B', str(SOURCE), '--inventory-file', str(expected_file),
                                 '--inventory-sha256', hashlib.sha256(expected_file.read_bytes()).hexdigest()],
                                capture_output=True, timeout=60)
        check(direct.returncode == 0 and json.loads(direct.stdout) == dict(verified_source_count=18, provider_calls=0,
              execution_authorized=False, authority_created=False), 'direct-source CLI loads code only, no authority')
        bad_cli = subprocess.run([sys.executable, '-I', '-S', '-B', str(SOURCE), '--inventory-file', str(expected_file),
                                  '--inventory-sha256', '0' * 64], capture_output=True, timeout=60)
        check(bad_cli.returncode != 0, 'direct-source CLI rejects wrong reviewed inventory identity')
        # Exact startup attack: hooks write only harmless external markers.
        # The positive guarantee is the initial -I -S process, not an in-file guard.
        startup = directory / 'STARTUP_ATTACK'
        startup.mkdir()
        marker = startup / 'UNBOUND_STARTUP_EXECUTED.txt'
        hook = ('from pathlib import Path\nPath(' + repr(str(marker)) + ').write_bytes(b"startup executed")\n').encode()
        for name in ('sitecustomize.py', 'usercustomize.py', 'copy.py', 'g_cal1_authority_v2.py'):
            (startup / name).write_bytes(hook)
        user_site = startup / 'USERBASE' / ('Python' + str(sys.version_info.major) + str(sys.version_info.minor)) / 'site-packages'
        user_site.mkdir(parents=True)
        for name in ('sitecustomize.py', 'usercustomize.py'):
            (user_site / name).write_bytes(hook)
        argv = [str(SOURCE), '--inventory-file', str(expected_file), '--inventory-sha256',
                hashlib.sha256(expected_file.read_bytes()).hexdigest()]
        for label, extras in (
                ('PYTHONPATH/sitecustomize exact attack', {'PYTHONPATH': str(startup)}),
                ('PYTHONHOME ignored', {'PYTHONHOME': str(startup / 'INVALID_HOME')}),
                ('user site and usercustomize suppressed', {'PYTHONUSERBASE': str(startup / 'USERBASE')}),
                ('combined ambient startup configuration', {'PYTHONPATH': str(startup),
                 'PYTHONHOME': str(startup / 'INVALID_HOME'), 'PYTHONUSERBASE': str(startup / 'USERBASE')})):
            result = subprocess.run([sys.executable, '-I', '-S', '-B', *argv], cwd=startup,
                                    env=dict(os.environ, **extras), capture_output=True, timeout=60)
            check(result.returncode == 0, label + ' verified graph operates:' + result.stderr.decode(errors='replace'))
            check(not marker.exists(), label + ' no startup/ambient module executed')
            check(json.loads(result.stdout)['verified_source_count'] == 18, label + ' exact source graph')
        for flags in ([], ['-I'], ['-S']):
            result = subprocess.run([sys.executable, *flags, '-B', *argv], cwd=startup,
                                    env=dict(os.environ, PYTHONPATH=str(startup)), capture_output=True, timeout=60)
            check(result.returncode != 0 and b'requires direct trusted CPython -I -S' in result.stderr,
                  'unsafe/missing startup isolation rejected:' + repr(flags))
            check(not result.stdout, 'unsafe invocation never attests graph:' + repr(flags))
            if not flags:
                check(marker.read_bytes() == b'startup executed',
                      'unsafe guard cannot undo already-executed startup hook')
                marker.unlink()
        check(BOOT['launch_profile'](expected)['entrypoint_sha256'] == expected['tools/g_cal1_source_loader_v1.py'],
              'launch profile binds exact explicit loader source')
        print(json.dumps(dict(probe='clean_bootstrap', bootstrap='PASS', protected_startup_hooks_not_executed=True,
                              unsafe_launch_rejected=True, unsafe_guard_not_startup_prevention=True,
                              launch_profile=BOOT['launch_profile'](expected), provider_calls=0), sort_keys=True))
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
    if sys.argv[1:2] == ['--stdlib-worker']:
        stdlib_worker(*sys.argv[2:])
    elif sys.argv[1:2] == ['--worker']:
        worker(*sys.argv[2:])
    else:
        raise SystemExit(main())
