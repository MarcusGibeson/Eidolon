"""Append-only replacement authority; never changes the historical v1 pointer.

Artifact publication alone is not activation. Only a verified transition chain
selects authority. All writer APIs require explicit operator records; this module
has no CLI, provider API, automatic activation, or automatic CAL grant.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import math
from pathlib import Path
import re
import threading

from g_cal1_contract import DATA, ROOT, Package
from g_cal1_lock import run_lock
from g_extract1_contract import canonical, digest, file_digest, load, require
from g_extract1_journal import Journal, write_once
from g_cal1_source_loader_v1 import inventory, verified_context

VERSION = 'g-cal1.authority.v2'
TRANSPORT_COMMIT = '9636b7e1fb1f5af05cb27ed29dfa6c9f5c63869c'
TRANSPORT_SHA256 = 'f7591ec18860cf65ca532bf3bd3956b86a7fd084a30e9dcc05538f3bd16b9e6c'
ANCHOR = {
    'pointer_sha256': '52869014eae6561b25ebefbbece43f5bdcab08876bbc9d6d29224560f317ae94',
    'activation_sha256': '60e2d5ed08661deb7647511dcc47ef45a637a1a37f2411167b987241aec0aae7',
    'candidate_sha256': 'fad0fddd74723a7019f30b8debe0a8f239ba8fbf31a3fcd49e593e0f795e9cd8',
}
ANCHOR_PATHS = ('execution/ACTIVE_FREEZE.json', 'execution/EXECUTION_FREEZE_ACTIVATION.json',
                'preexecution/lock_timeout_repair/EXECUTION_FREEZE_CANDIDATE.json')
NAMESPACE = DATA / 'execution/authority_v2'
BLOCKED_RUN = 'G-CAL1-CAL-20261005T162415Z-13ebb55187a8'
BLOCKED_FILES = {
    'CAL_AUTHORIZATION.json': 'ed51de839baf0e21c64e56eafa9790ff47e441a4a55b89650d26604d1653395b',
    'EVIDENCE_MANIFEST.json': '9e36bfe5775b20ad9453aec5b91030a4268c3e6bd8fd2f196083b2a52732e6d5',
    'PACKAGE_MANIFEST.json': 'a70365647e98d59cb547ebccd884a1b350d8da101d6a272a111b02d4104462e2',
    'POST_STOP_VERIFICATION.json': '227b74d446ca1e60eb7e8ada8b79a1af69b1232c72a3b86b297321f5e26205b3',
    'PRECONTACT_BLOCK_REPORT.json': 'd1dd3805d2d59405478916e9a44d405ae12cc7241593543027cd2023045ab7f7',
    'VERIFICATION_FIELD_CLARIFICATION.json': 'e8edc8be49fdd35a0fe76cfb11e385240aa5b66f72b1a013984898566e689668',
}
KINDS = ('candidates', 'reviews', 'activations', 'grants')


def check(condition, detail):
    require(condition, 'PROVENANCE_MISMATCH', 'authority-v2:' + detail)


def source_inventory():
    """Pin only repository Python modules in the entrypoint's import closure.

    Standard-library imports are excluded; tests/docs are evidence, not executable
    authority. Resolve repository imports from tools, never from arbitrary sys.path.
    """
    return inventory(ROOT)


# A source snapshot is not loaded-code authority without the source-only context.
IMPORTED_SOURCES = source_inventory()


def verify_sources(expected):
    check(type(expected) is dict and expected == IMPORTED_SOURCES == source_inventory(),
          'executable implementation hash mismatch')
    try:
        verified_context(globals()).verify(expected, globals())
    except Exception as exc:
        check(False, 'verified-source execution required:' + str(exc))


def exact_schema(value, template):
    """Field types precede binding comparisons; bool is never int/float."""
    if type(value) is not type(template):
        return False
    if type(template) is dict:
        return set(value) == set(template) and all(exact_schema(value[k], v) for k, v in template.items())
    if type(template) is list:
        return len(value) == len(template) and all(exact_schema(a, b) for a, b in zip(value, template))
    return True


def historical():
    for (key, sha), path in zip(ANCHOR.items(), ANCHOR_PATHS):
        check(file_digest(DATA / path) == sha, 'historical ' + key)
    pointer, activation, candidate = (load(DATA / p) for p in ANCHOR_PATHS)
    check(pointer == {'activation_path': ANCHOR_PATHS[1], 'activation_sha256': ANCHOR['activation_sha256']},
          'historical pointer')
    check(activation['candidate_sha256'] == ANCHOR['candidate_sha256'] and
          activation['status'] == 'EXECUTION_FREEZE_ACTIVE' and activation['phase_authorized'] is False and
          activation['binding'] == candidate['binding'], 'historical activation')
    check(file_digest(DATA / 'LAB_MANIFEST.json') == candidate['binding']['manifest_sha256'], 'science manifest')
    for path, sha in candidate['protected_artifacts'].items():
        check(file_digest(ROOT / path) == sha, 'historical protected package:' + path)
    for name, sha in BLOCKED_FILES.items():
        check(file_digest(DATA / 'execution' / BLOCKED_RUN / name) == sha, 'historical blocked run:' + name)
    return candidate


def protected_set(old):
    result = dict(old['protected_artifacts'])
    prefix = DATA.relative_to(ROOT).as_posix() + '/'
    result[prefix + ANCHOR_PATHS[0]] = ANCHOR['pointer_sha256']
    result[prefix + ANCHOR_PATHS[1]] = ANCHOR['activation_sha256']
    result.update({prefix + 'execution/' + BLOCKED_RUN + '/' + name: sha for name, sha in BLOCKED_FILES.items()})
    check(len(result) == 107, 'protected set cardinality')
    return result


class Registry:
    def __init__(self, root=None, *, test_only=False):
        check(type(test_only) is bool, 'test flag')
        self.root = Path(root) if root is not None else NAMESPACE
        self.test_only = test_only
        if test_only:
            check(root is not None and not self.root.resolve().is_relative_to(ROOT.resolve()),
                  'test namespace must be outside repository')
        else:
            check(self.root.absolute() == NAMESPACE.absolute(), 'fixed production namespace')
        self.namespace = ('TEST-' + digest(str(self.root.resolve()).encode())) if test_only else 'G-CAL1-AUTHORITY-V2'
        self._mutex, self._local = threading.RLock(), threading.local()

    @contextmanager
    def locked(self):
        with self._mutex:
            if getattr(self._local, 'held', False):
                yield
            else:
                with run_lock(self.root):
                    self._local.held = True
                    try:
                        yield
                    finally:
                        self._local.held = False

    def _layout(self):
        for parent in (self.root, *self.root.parents):
            check(not parent.is_symlink(), 'symlink namespace')
        if self.root.exists():
            check(self.root.is_dir(), 'namespace is not directory')
            for path in self.root.iterdir():
                check(path.name in (*KINDS, 'transitions', 'runs') and path.is_dir() and not path.is_symlink(),
                      'unauthorized pointer/namespace entry:' + path.name)

    def publish(self, kind, record):
        """Write-once immutable artifact. This does not select or grant authority."""
        with self.locked():
            self._layout()
            check(kind in KINDS and type(record) is dict, 'artifact kind/object')
            check(record.get('namespace') == self.namespace and record.get('test_only') is self.test_only,
                  'artifact namespace')
            sha = digest(canonical(record))
            write_once(self.root / kind / (sha + '.json'), record)
            return sha

    def read(self, kind, sha):
        self._layout()
        check(kind in KINDS and type(sha) is str and re.fullmatch('[0-9a-f]{64}', sha) is not None, 'artifact reference')
        path = self.root / kind / (sha + '.json')
        check(path.is_file() and not path.is_symlink(), 'missing artifact:' + kind)
        record = load(path)
        check(type(record) is dict and file_digest(path) == sha and path.read_bytes() == canonical(record),
              'artifact bytes/seal:' + kind)
        check(record.get('namespace') == self.namespace and record.get('test_only') is self.test_only,
              'artifact namespace')
        return record

    def fields(self):
        return {'namespace': self.namespace, 'test_only': self.test_only}

    def history(self):
        """Validate every transition and historical artifact, without granting CAL."""
        old = historical()
        self._layout()
        directory = self.root / 'transitions'
        rows = []
        if directory.exists():
            check(all(p.is_file() and not p.is_symlink() and re.fullmatch(r'[0-9]{6}\.json', p.name)
                      for p in directory.iterdir()), 'transition entries')
            rows = Journal(directory).read()
        current = dict(ANCHOR, generation_head=None)
        reserved = {}
        for i, row in enumerate(rows):
            p = row['payload']
            check(type(p) is dict and p.get('namespace') == self.namespace and p.get('test_only') is self.test_only,
                  'transition namespace/object')
            if i == 0:
                check(p == dict(self.fields(), kind='GENESIS', predecessor=ANCHOR), 'missing supersession genesis')
                continue
            if p.get('kind') == 'ACTIVATE_SUPERSEDING':
                check(set(p) == {'kind', 'namespace', 'test_only', 'predecessor', 'activation_sha256'}, 'transition shape')
                check(p['predecessor'] == current, 'supersession lineage')
                a = self.read('activations', p['activation_sha256'])
                c = self.read('candidates', a.get('candidate_sha256'))
                r = self.read('reviews', a.get('review_sha256'))
                self._candidate(c, old, current)
                self._review(r, c, a['candidate_sha256'])
                check(a == dict(self.fields(), schema_version='g-cal1.activation.v2', experiment='G-CAL1',
                    status='EXECUTION_FREEZE_ACTIVE', candidate_sha256=digest(canonical(c)), review_sha256=digest(canonical(r)),
                    predecessor=current, execution_sha256=c['execution_sha256'], science_binding=c['science_binding'],
                    authority_source='EXPLICIT_OPERATOR_FREEZE_ACTIVATION', phase_authorized=False), 'activation content')
                current = dict(activation_sha256=p['activation_sha256'], candidate_sha256=a['candidate_sha256'],
                               generation_head=row['sha256'])
            elif p.get('kind') == 'RUN_RESERVED':
                check(set(p) == {'kind', 'namespace', 'test_only', 'run_id', 'activation_sha256', 'grant_sha256',
                                 'generation_head'}, 'reservation shape')
                check(current['generation_head'] is not None and p['activation_sha256'] == current['activation_sha256'] and
                      p['generation_head'] == current['generation_head'], 'reservation activation')
                self.valid_id(p['run_id'])
                check(p['run_id'] not in reserved, 'run ID already reserved')
                self._grant(self.read('grants', p['grant_sha256']), current, p['run_id'])
                reserved[p['run_id']] = p
            else:
                check(False, 'unknown transition')
        return current, reserved

    def _candidate(self, c, old, predecessor):
        check(set(c) == {'schema_version', 'experiment', 'status', 'activated', 'namespace', 'test_only',
                        'predecessor', 'science_binding', 'provider_binding', 'reviewed_transport_commit',
                        'executable_sources', 'execution_sha256', 'transport_timeout_seconds', 'execution_authorized',
                        'protected_artifacts'},
              'candidate shape')
        check(c['schema_version'] == 'g-cal1.candidate.v2' and c['experiment'] == 'G-CAL1' and
              c['status'] == 'EXECUTION_FREEZE_CANDIDATE_ONLY' and c['activated'] is False and
              c['execution_authorized'] is False and c['predecessor'] == predecessor and
              c['science_binding'] == old['binding'] and c['provider_binding'] == old['provider_binding'] and
              c['protected_artifacts'] == protected_set(old) and
              c['reviewed_transport_commit'] == TRANSPORT_COMMIT, 'candidate lineage/science/authority')
        check(type(c['executable_sources']) is dict and c['execution_sha256'] == digest(canonical(c['executable_sources'])),
              'execution digest')
        check(c['executable_sources'].get('tools/g_cal1_ollama_transport.py') == TRANSPORT_SHA256,
              'reviewed transport identity, not just commit label')
        check(type(c['transport_timeout_seconds']) in (int, float) and math.isfinite(c['transport_timeout_seconds']) and
              c['transport_timeout_seconds'] > 0, 'explicit transport timeout')

    def _review(self, r, c, candidate_sha):
        check(r == dict(self.fields(), schema_version='g-cal1.freeze-review.v2', verdict='PASS',
              candidate_sha256=candidate_sha, execution_sha256=c['execution_sha256'],
              reviewer='Sol 6.1', scope='EXECUTION_FREEZE_REVIEW'), 'unreviewed candidate/review binding')

    def candidate(self, *, timeout_seconds):
        """Future preparation only: returns an unactivated object, does not publish."""
        with self.locked():
            predecessor, _ = self.history()
            old = historical()
            sources = source_inventory()
            verify_sources(sources)
            c = dict(self.fields(), schema_version='g-cal1.candidate.v2', experiment='G-CAL1',
                     status='EXECUTION_FREEZE_CANDIDATE_ONLY', activated=False, execution_authorized=False,
                     predecessor=predecessor, science_binding=old['binding'], provider_binding=old['provider_binding'],
                     protected_artifacts=protected_set(old),
                     reviewed_transport_commit=TRANSPORT_COMMIT, executable_sources=sources,
                     execution_sha256=digest(canonical(sources)), transport_timeout_seconds=timeout_seconds)
            self._candidate(c, old, predecessor)
            return c

    def activate(self, candidate_sha, review_sha, *, operator):
        """Future explicit rollover. No caller in this task uses a production registry."""
        with self.locked():
            current, _ = self.history()
            c, r = self.read('candidates', candidate_sha), self.read('reviews', review_sha)
            self._candidate(c, historical(), current)
            self._review(r, c, candidate_sha)
            verify_sources(c['executable_sources'])
            check(operator == dict(self.fields(), status='EXPLICIT_OPERATOR_FREEZE_ACTIVATION',
                  candidate_sha256=candidate_sha, review_sha256=review_sha, predecessor=current), 'explicit activation required')
            a = dict(self.fields(), schema_version='g-cal1.activation.v2', experiment='G-CAL1',
                     status='EXECUTION_FREEZE_ACTIVE', candidate_sha256=candidate_sha, review_sha256=review_sha,
                     predecessor=current, execution_sha256=c['execution_sha256'], science_binding=c['science_binding'],
                     authority_source='EXPLICIT_OPERATOR_FREEZE_ACTIVATION', phase_authorized=False)
            sha = self.publish('activations', a)
            journal = Journal(self.root / 'transitions')
            if not journal.read():
                journal.append(dict(self.fields(), kind='GENESIS', predecessor=ANCHOR))
            journal.append(dict(self.fields(), kind='ACTIVATE_SUPERSEDING', predecessor=current, activation_sha256=sha))
            return sha

    def valid_id(self, run_id):
        check(type(run_id) is str and re.fullmatch(r'G-CAL1-CAL-[A-Za-z0-9-]{8,100}', run_id) is not None,
              'run ID grammar')
        check(run_id != BLOCKED_RUN and not (DATA / 'execution' / run_id).exists(), 'historical run ID reuse')

    def _grant(self, g, current, run_id):
        a = self.read('activations', current['activation_sha256'])
        expected = dict(self.fields(), schema_version='g-cal1.cal-grant.v2', experiment='G-CAL1', phase='CAL',
              status='EXPLICIT_OPERATOR_PHASE_AUTHORIZATION', freeze_status='EXECUTION_FREEZE_ACTIVE',
              run_id=run_id, activation_sha256=current['activation_sha256'], candidate_sha256=current['candidate_sha256'],
              generation_head=current['generation_head'], execution_sha256=a['execution_sha256'],
              science_binding=a['science_binding'], synthetic_evidence_allowed=False,
              authority_source='EXPLICIT_OPERATOR_CAL_AUTHORIZATION')
        check(exact_schema(g, expected), 'CAL grant exact schema/types')
        check(g['synthetic_evidence_allowed'] is False and g == expected, 'fresh activation-bound CAL grant')

    def authorize(self, package, run_id, activation_sha, grant_sha, *, resume=False, reserve=False):
        """Offline gate to run BEFORE any future metadata contact; no writes unless reserve=True."""
        with self.locked():
            current, reservations = self.history()
            check(current['generation_head'] is not None and activation_sha == current['activation_sha256'],
                  'stale activation/old freeze/candidate-only authority')
            c = self.read('candidates', current['candidate_sha256'])
            verify_sources(c['executable_sources'])
            if not self.test_only:
                check(type(package) is Package, 'production requires frozen Package')
            package.verify()
            check(package.binding == c['science_binding'], 'science binding unchanged')
            self.valid_id(run_id)
            self._grant(self.read('grants', grant_sha), current, run_id)
            expected = dict(self.fields(), kind='RUN_RESERVED', run_id=run_id, activation_sha256=activation_sha,
                            grant_sha256=grant_sha, generation_head=current['generation_head'])
            path = self.root / 'runs' / run_id
            if resume:
                check(reservations.get(run_id) == expected and path.is_dir() and not path.is_symlink(),
                      'resume reservation/lineage')
            else:
                check(run_id not in reservations and not path.exists(), 'run ID already used')
                if reserve:
                    Journal(self.root / 'transitions').append(expected)
            return dict(activation_sha256=activation_sha, candidate_sha256=current['candidate_sha256'],
                        authorization_sha256=grant_sha, generation_head=current['generation_head'],
                        execution_sha256=c['execution_sha256'], namespace=self.namespace, test_only=self.test_only)
