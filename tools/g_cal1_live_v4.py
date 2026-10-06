"""Versioned live entrypoint using frozen collection semantics and v2 authority.

No CLI and no automatic provider contact. The operator must separately activate,
grant, pass Registry.authorize(), and verify the adapter's provider metadata.
"""
from __future__ import annotations

import copy
import threading

import g_cal1_lab as frozen
from g_cal1_authority_v2 import Registry, check, verify_sources, IMPORTED_SOURCES
from g_cal1_source_loader_v1 import verified_context
from g_cal1_lock import run_lock
from g_cal1_ollama_transport import OllamaLiveTransport, IO_INJECTED, IO_STDLIB
from g_extract1_contract import canonical, digest, file_digest, require, IntegrityError
from g_extract1_journal import Journal, write_once
from g_extract1_runner import guarded

VERSION = 'g-cal1.live.v4'


class LiveRun(frozen.Run):
    @guarded
    def __init__(self, package, registry, run_id, *, activation_sha256, grant_sha256, transport, resume=False):
        check(type(self) is LiveRun, 'unbound live-entrypoint subclass forbidden')
        verify_sources(IMPORTED_SOURCES)
        verified_context(globals()).verify(IMPORTED_SOURCES, globals())
        check(type(registry) is Registry, 'registry type')
        self.registry, self.transport = registry, transport
        self.package, self.directory, self.run_id = package, registry.root / 'runs' / run_id, run_id
        self._lock_local = threading.local()
        self.mechanical, self._owned = False, False
        self.events, self.event_scopes, self._error_cell = [], [], None
        self._checkpoint_verified = not resume
        self.evidence, self.attempted, self.last_checkpoint = {}, set(), None
        self.activation_sha256, self.grant_sha256 = activation_sha256, grant_sha256
        # Reserve before creating a run. A crash consumes the ID rather than
        # permitting a second independent run at a different directory.
        authority = registry.authorize(package, run_id, activation_sha256, grant_sha256, resume=resume)
        self.binding = dict(package.binding, lab_version=VERSION, execution_sha256=authority['execution_sha256'],
                            authority_sha256=digest(canonical(authority)))
        self.authority_evidence = authority
        self._transport_ready(check_position=False)
        self.provider_receipts = copy.deepcopy(transport._metadata)
        self.provider_metadata_sha256 = digest(canonical(self.provider_receipts))
        if not resume:
            registry.authorize(package, run_id, activation_sha256, grant_sha256, reserve=True)
            self.directory.mkdir(parents=True, exist_ok=False)
        self._owned = True
        self.journal, self.incidents = Journal(self.directory / 'journal'), Journal(self.directory / 'integrity')
        acquired = False
        try:
            self._reject_boundary_incidents()
            with run_lock(self.directory):
                acquired = True
                self._lock_local.held = True
                try:
                    with registry.locked():
                        check(self._authority() == authority, 'authority changed during creation')
                        if resume:
                            self._synchronize()
                        else:
                            self.journal.append(dict(kind='RUN_CREATED', run_id=run_id, binding=self.binding,
                                                     mode='LIVE', authority=authority))
                        path = self.directory / 'provider_metadata' / (self.provider_metadata_sha256 + '.json')
                        if not path.exists():
                            write_once(path, self.provider_receipts)
                        check(not path.is_symlink() and path.read_bytes() == canonical(self.provider_receipts), 'metadata evidence')
                        self._transport_ready(check_position=True)
                finally:
                    self._lock_local.held = False
        except IntegrityError as exc:
            if not acquired:
                self._retain_boundary_incident(exc)
            raise

    def _authority(self):
        return self.registry.authorize(self.package, self.run_id, self.activation_sha256, self.grant_sha256, resume=True)

    def _transport_ready(self, *, check_position=True):
        t = self.transport
        check(type(t) is OllamaLiveTransport and t.synthetic_only is False, 'exact reviewed live transport required')
        a = self.registry.read('activations', self.activation_sha256)
        c = self.registry.read('candidates', a['candidate_sha256'])
        check(t._binding == c['provider_binding'] and canonical(t._binding) == t._binding_bytes and
              t._schedule == self.package.schedule and canonical(t._schedule) == t._schedule_bytes and
              t._timeout == c['transport_timeout_seconds'], 'transport binding/config/schedule')
        check(t.disabled is None, 'disabled transport')
        check((t._factory is not None and t._io == IO_INJECTED) if self.registry.test_only else
              (t._factory is None and t._io == IO_STDLIB), 'test-only injected IO forbidden in production')
        m = t._metadata
        check(type(m) is dict and digest(canonical(m)) == t._metadata_sha256 and
              m.get('provider') == c['provider_binding']['provider'] and
              m.get('provider_version') == c['provider_binding']['provider_version'] and
              m.get('models') == c['provider_binding']['models'] and
              m.get('generation_configuration') == c['provider_binding']['generation_configuration'] and
              m.get('internal_option_honoring_attested_by_provider') is False and
              m.get('internal_option_honoring') == 'UNATTESTED' and m.get('io') == t._io,
              'explicit verified metadata required; option honoring unattested')
        if hasattr(self, 'provider_receipts'):
            check(m == self.provider_receipts and digest(canonical(m)) == self.provider_metadata_sha256,
                  'metadata receipt mutation')
        if check_position:
            check(t._next == len(self.attempted), 'transport next-position mismatch')

    def _synchronize(self):
        check(self.binding == dict(self.package.binding, lab_version=VERSION,
                                   execution_sha256=self.authority_evidence['execution_sha256'],
                                   authority_sha256=digest(canonical(self.authority_evidence))), 'run binding drift')
        self.events, self.event_scopes = [], []
        for row in self.incidents.read():
            p = row['payload']
            check(type(p) is dict and set(p) == {'event', 'detail', 'phase', 'cell', 'run_id', 'binding'} and
                  p['binding'] == self.binding and p['run_id'] == self.run_id and p['phase'] == 'CAL' and
                  type(p['event']) is str and type(p['detail']) is str and
                  (p['cell'] is None or type(p['cell']) is str), 'incident shape/binding')
            self.events.append(p['event'])
            self.event_scopes.append(dict(event=p['event'], phase='CAL', cell=p['cell']))
        self._observe_boundary_incidents()
        require(not self.events, self.events[0] if self.events else 'PROVENANCE_MISMATCH', 'retained incident')
        records = self.journal.read()
        self.package.verify(contacted=any(r['payload'].get('kind') == 'START' for r in records if type(r['payload']) is dict))
        self.evidence, self.attempted, self.last_checkpoint = {}, set(), None
        self._replay()

    def _ready(self):
        verified_context(globals()).verify(IMPORTED_SOURCES, globals())
        self._reject_boundary_incidents()
        require(self._checkpoint_verified, 'UNVERIFIABLE_INTERRUPTION_CHECKPOINT', 'verify before collection')
        require(not self.events, self.events[0] if self.events else 'PROVENANCE_MISMATCH', 'terminal retained incident')
        check(self._authority() == self.authority_evidence, 'stale/replaced authority')
        self._transport_ready()
        path = self.directory / 'provider_metadata' / (self.provider_metadata_sha256 + '.json')
        check(path.is_file() and not path.is_symlink() and file_digest(path) == self.provider_metadata_sha256,
              'metadata evidence missing/drifted')

    @frozen.governed
    def perform(self, row, transport=None):
        with self.registry.locked():
            check(transport is None or transport is self.transport, 'transport substitution')
            # Call the unchanged kernel beneath its decorator while holding the
            # same run lock plus the registry lock across START and contact.
            return frozen.Run.perform.__wrapped__(self, row, self.transport)

    @frozen.governed
    def final_report(self):
        with self.registry.locked():
            report = frozen.Run.final_report.__wrapped__(self)
            report['provider_metadata_sha256'] = self.provider_metadata_sha256
            if self.registry.test_only:
                report.update(mode='MOCKED_LIVE_BOUNDARY_TEST', provider_model_calls=0,
                              mocked_attempts=len(self.attempted), scientific_observations=0)
            return copy.deepcopy(report)
