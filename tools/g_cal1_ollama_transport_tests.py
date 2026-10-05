"""NO-PROVIDER tests for the G-CAL1 live Ollama transport.

Every socket/subprocess audit event is denied before any test runs; all HTTP is
scripted. The integration path drives the actual frozen g_cal1_lab.Run in live
(mechanical=False) mode through a temporary, test-only authority namespace and a
test-only package built read-only from committed data. The real freeze,
activation, candidate and blocked-run grant are never used as authority.
"""
from __future__ import annotations

import sys

AUDIT = []


def deny_contact(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system', 'os.startfile'):
        AUDIT.append(event)
        raise RuntimeError('NO_PROVIDER_NETWORK_BOUNDARY:' + event)


sys.addaudithook(deny_contact)

import base64
import copy
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

import g_cal1_contract as contract
import g_cal1_lab as lab
import g_cal1_ollama_transport as live
from g_cal1_contract import DATA, ROOT, build_schedule, make_member, wire_bytes
from g_cal1_lab import Run
from g_cal1_ollama_transport import (MetadataVerificationError, OllamaLiveTransport, TransportContractError)
from g_extract1_contract import IntegrityError, canonical, digest, file_digest, load, require
from g_extract1_journal import write_once
from g_extract1_runner import failure_event, transport_outcome
from g_extract1_scoring import synthetic_gold

TEST_MARK = 'TASK-GCAL1-LIVE-TRANSPORT offline adapter integration; never experiment authority'
CANDIDATE = DATA / 'preexecution/lock_timeout_repair/EXECUTION_FREEZE_CANDIDATE.json'
UNTRACKED = ['AUTHORING_ATTEMPTS', 'AUTHORING_CANDIDATES', 'AUTHORING_FEASIBILITY_REPORT',
             'FINALIZATION_CONTAMINATION_DISAGREEMENT_REPORT', 'FINALIZATION_FAILURE_REPORT',
             'FINALIZATION_HISTORICAL_REUSE_CONTRACT_STOP_REPORT', 'FRESHNESS_CANONICALIZATION_DIAGNOSIS_REPORT']
REMOVE = object()


class Checks:
    def __init__(self):
        self.passed, self.failed, self.categories = 0, [], {}

    def check(self, condition, category, detail):
        self.categories[category] = self.categories.get(category, 0) + 1
        if condition:
            self.passed += 1
        else:
            self.failed.append(category + ':' + detail)
            print('FAIL', category, detail)

    def raises(self, action, kind, category, detail, predicate=None):
        try:
            action()
        except kind as exc:
            self.check(predicate is None or predicate(exc), category, detail + ':' + repr(exc))
            return exc
        except BaseException as exc:
            self.check(False, category, detail + ': wrong exception ' + repr(exc))
            if not isinstance(exc, Exception):
                raise
            return exc
        self.check(False, category, detail + ': accepted')
        return None


# -- test-only package ----------------------------------------------------------
class TestPackage:
    """Frozen G-CAL1 structure and G-EXTRACT1 event catalog read from committed files.

    The primary Package is never instantiated (it pins untracked corpus files),
    and the binding carries a test-only marker that no real activation matches.
    """
    PINNED = ('experiments/G-CAL1-candidate/DESIGN.json', 'experiments/G-CAL1-candidate/corpus/CORPUS.json',
              'experiments/G-CAL1-candidate/schedule/SCHEDULE.json',
              'experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json')

    def __init__(self):
        self.manifest_sha = file_digest(DATA / 'LAB_MANIFEST.json')
        manifest = load(DATA / 'LAB_MANIFEST.json')
        self.pins = {path: manifest['protected_artifacts'][path] for path in self.PINNED}
        self.verify()
        self.design = load(DATA / 'DESIGN.json')
        self.historical = SimpleNamespace(design=load(ROOT / 'experiments/G-EXTRACT1-candidate/DESIGN_CANDIDATE.json'))
        self.baseline = self.historical.design['baseline_binding']
        self.members = {m['fixture_id']: m for m in load(DATA / 'corpus/CORPUS.json')['members']}
        self.schedule = load(DATA / 'schedule/SCHEDULE.json')['rows']
        require(self.schedule == build_schedule(list(self.members.values()), self.design, self.wire),
                'PRE_SCHEDULE_DIGEST_MISMATCH')
        for m in self.members.values():
            require(m == make_member(self.design, self.baseline, m['stratum'], m['slot'], m['source_date']),
                    'PRE_GOLD_DIGEST_MISMATCH')
        self.binding = {'experiment': 'G-CAL1', 'contract_version': contract.VERSION,
                        'manifest_sha256': self.manifest_sha, 'schedule_sha256': digest(canonical(self.schedule)),
                        'journal_schema': 'g-extract1.call-journal.v2', 'test_only': TEST_MARK}
        self._derived = canonical(self._state())

    def _state(self):
        return [self.pins, self.design, self.historical.design, self.members, self.schedule, self.binding]

    def wire(self, row):
        return wire_bytes(self.members[row['fixture_id']], row, self.design, self.baseline)

    def verify(self, contacted=False):
        event = 'PROTECTED_ARTIFACT_DIGEST_MISMATCH' if contacted else 'PRE_ARTIFACT_DIGEST_MISMATCH'
        if hasattr(self, '_derived'):
            require(canonical(self._state()) == self._derived, event, 'test package drift')
        require(file_digest(DATA / 'LAB_MANIFEST.json') == self.manifest_sha, event, 'manifest')
        for path, expected in self.pins.items():
            require(file_digest(ROOT / path) == expected, event, path)


# -- scripted HTTP ----------------------------------------------------------------
class Script:
    def __init__(self, body=b'', status=200, reason='OK', headers=None, fail_at=None, error=None, hook=None,
                 chunks=None, length=None):
        self.body, self.status, self.reason, self.fail_at, self.error, self.hook = body, status, reason, fail_at, error, hook
        self.headers = [('Content-Type', 'application/json; charset=utf-8')] if headers is None else headers
        # read1 returns these chunks in order; a fail_at='read' error is raised once they are exhausted.
        self.chunks = ([body] if body else []) if chunks is None else list(chunks)
        self.length = length


class FakeResponse:
    def __init__(self, connection):
        self.connection, script = connection, connection.script
        self.status, self.reason, self.length = script.status, script.reason, script.length
        self.pending, self.ended = list(script.chunks), False

    def getheaders(self):
        self.connection.step('getheaders')
        return list(self.connection.script.headers)

    def read(self):
        self.connection.step('read')
        return self.connection.script.body

    def read1(self, n=-1):
        if self.pending:
            chunk = self.pending.pop(0)
            if 0 <= n < len(chunk):
                self.pending.insert(0, chunk[n:])
                chunk = chunk[:n]
            return chunk
        if not self.ended:
            self.ended = True
            self.connection.step('read')
        return b''


class FakeConnection:
    def __init__(self, provider, host, port, timeout, script):
        self.provider, self.host, self.port, self.timeout, self.script = provider, host, port, timeout, script
        self.requests, self.closed, self.connected = [], False, False

    def step(self, stage):
        if self.script.hook is not None and self.script.hook[0] == stage:
            self.script.hook[1]()
        if self.script.fail_at == stage:
            raise self.script.error

    def connect(self):
        self.step('connect')
        self.connected = True

    def request(self, method, path, body=None, headers=None):
        self.requests.append({'method': method, 'path': path, 'body': body, 'headers': dict(headers or {})})
        self.step('request')

    def getresponse(self):
        self.step('getresponse')
        return FakeResponse(self)

    def close(self):
        self.closed = True


class ScriptedRaw(io.RawIOBase):
    """Raw stream yielding one scripted segment per readinto, then the scripted error (or EOF). No socket."""

    def __init__(self, segments, error=None):
        self.segments, self.error = list(segments), error

    def readable(self):
        return True

    def readinto(self, buffer):
        if not self.segments:
            if self.error is not None:
                raise self.error
            return 0
        segment = self.segments.pop(0)
        size = min(len(buffer), len(segment))
        buffer[:size] = segment[:size]
        if size < len(segment):
            self.segments.insert(0, segment[size:])
        return size


class ScriptedSocket:
    def __init__(self, raw):
        self.raw = raw

    def makefile(self, mode, *args, **kwargs):
        return io.BufferedReader(self.raw)


class StdlibConnection:
    """Generation connection whose response is parsed by the real http.client.HTTPResponse from scripted bytes."""

    def __init__(self, segments, error=None):
        self.segments, self.error, self.requests, self.closed = segments, error, [], False

    def connect(self):
        pass

    def request(self, method, path, body=None, headers=None):
        self.requests.append({'method': method, 'path': path, 'body': body, 'headers': dict(headers or {})})

    def getresponse(self):
        response = http.client.HTTPResponse(ScriptedSocket(ScriptedRaw(self.segments, self.error)), method='POST')
        response.begin()
        return response

    def close(self):
        self.closed = True


class Provider:
    """Connection factory; each scripted exchange gets a brand-new connection object."""

    def __init__(self, scripts=()):
        self.scripts, self.connections = list(scripts), []

    def add(self, *scripts):
        self.scripts.extend(scripts)

    def __call__(self, host, port, timeout):
        if not self.scripts:
            raise AssertionError('unscripted connection')
        script = self.scripts.pop(0)
        connection = script if isinstance(script, StdlibConnection) else FakeConnection(self, host, port, timeout, script)
        self.connections.append(connection)
        return connection

    def posts(self, path='/api/generate'):
        return [r for c in self.connections for r in c.requests if r['method'] == 'POST' and r['path'] == path]


def body(value):
    return json.dumps(value, ensure_ascii=False).encode('utf-8')


def metadata_scripts(binding, *, version=None, digest_value=None, blob=None, extra_tags=(), modelfile=None):
    model = binding['models'][0]
    tags = {'models': [{'name': model['model'], 'model': model['model'], 'size': 1,
                        'digest': digest_value or model['manifest_digest'], 'details': {'format': 'gguf'}}, *extra_tags]}
    show = {'modelfile': modelfile if modelfile is not None else
            '# Modelfile generated by "ollama show"\n# FROM ' + model['model'] + '\n\nFROM C:\\models\\blobs\\sha256-' +
            (blob or model['blob_sha256']) + '\nTEMPLATE "{{ .Prompt }}"\n',
            'parameters': 'stop "<|im_end|>"', 'details': {'format': 'gguf'}}
    return [Script(body({'version': version or binding['provider_version']})), Script(body(tags)), Script(body(show))]


def envelope(row, response, **changes):
    value = {'model': row['model'], 'created_at': '2026-10-05T00:00:00.000Z', 'response': response, 'done': True,
             'done_reason': 'stop', 'context': [1, 2, 3], 'total_duration': 10, 'load_duration': 1,
             'prompt_eval_count': 100, 'prompt_eval_duration': 2, 'eval_count': 20, 'eval_duration': 3}
    if response is REMOVE:
        del value['response']
    for key, item in changes.items():
        if item is REMOVE:
            value.pop(key, None)
        else:
            value[key] = item
    return body(value)


# -- adapter-level tests --------------------------------------------------------------
def verified(binding, schedule, provider=None, **kwargs):
    provider = provider or Provider()
    provider.add(*metadata_scripts(binding))
    transport = OllamaLiveTransport(binding, schedule, timeout_seconds=30, connection_factory=provider, **kwargs)
    receipts = transport.verify_metadata()
    return transport, provider, receipts


def adapter_tests(package, binding, checks):
    schedule, row, request = package.schedule, package.schedule[0], package.wire(package.schedule[0])
    member = package.members[row['fixture_id']]

    # Constructor and import make no provider contact; generation requires metadata first.
    provider = Provider()
    transport = OllamaLiveTransport(binding, schedule, timeout_seconds=30, connection_factory=provider)
    checks.check(transport.synthetic_only is False and OllamaLiveTransport.synthetic_only is False,
                 'boundary', 'synthetic_only is False')
    checks.check(provider.connections == [], 'no_contact', 'constructor made zero connections')
    checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'metadata_first',
                  'generation before metadata verification')
    checks.check(provider.connections == [] and transport.disabled, 'metadata_first', 'zero POST and disabled')

    # Default stdlib connection: fixed loopback endpoint, no injected factory.
    made = []
    class Recorder(Provider):
        def __call__(self, host, port, timeout=None):
            made.append((host, port, timeout))
            return Provider.__call__(self, host, port, timeout)
    recorder = Recorder(metadata_scripts(binding))
    with patch.object(live.http.client, 'HTTPConnection', recorder):
        default = OllamaLiveTransport(binding, schedule, timeout_seconds=12.5)
        receipts = default.verify_metadata()
    checks.check(made == [('127.0.0.1', 11434, 12.5)] * 3 and receipts['io'] == live.IO_STDLIB,
                 'endpoint', 'stdlib loopback 127.0.0.1:11434 with explicit timeout')
    checks.check(http.client.HTTPConnection is not recorder, 'endpoint', 'stdlib restored')

    # Metadata receipts: frozen identity verified; nothing claims blob rehashing.
    transport, provider, receipts = verified(binding, schedule)
    checks.check(receipts['provider'] == 'ollama' and receipts['provider_version'] == binding['provider_version'] and
                 receipts['models'] == binding['models'] and
                 receipts['generation_configuration'] == package.design['generation_configuration'],
                 'metadata', 'receipts satisfy the lab authority comparison fields')
    checks.check(receipts['verification_sources']['blob_content_rehashed'] is False and
                 receipts['internal_option_honoring'] == 'UNATTESTED', 'metadata', 'no false rehash/honoring claim')
    paths = [(r['method'], r['path']) for c in provider.connections for r in c.requests]
    checks.check(paths == [('GET', '/api/version'), ('GET', '/api/tags'), ('POST', '/api/show')] and
                 len({id(c) for c in provider.connections}) == 3 and all(c.closed for c in provider.connections),
                 'metadata', 'three fresh closed metadata connections; no pull/create/generate')
    checks.check(base64.b64decode(receipts['observations'][2]['request_body_b64']) == canonical({'model': row['model']}),
                 'metadata', 'show request body preserved')
    checks.raises(transport.verify_metadata, TransportContractError, 'metadata', 'metadata verification is once only')

    for name, kwargs in [('version', {'version': '0.34.2'}), ('manifest', {'digest_value': '0' * 64}),
                         ('blob', {'blob': 'f' * 64}),
                         ('duplicate_model', {'extra_tags': [{'name': binding['models'][0]['model'], 'digest': '1' * 64}]}),
                         ('two_from', {'modelfile': 'FROM x/sha256-' + binding['models'][0]['blob_sha256'] +
                                       '\nFROM y/sha256-' + 'a' * 64 + '\n'}),
                         ('no_from', {'modelfile': 'TEMPLATE x\n'})]:
        provider = Provider(metadata_scripts(binding, **kwargs))
        transport = OllamaLiveTransport(binding, schedule, timeout_seconds=30, connection_factory=provider)
        checks.raises(transport.verify_metadata, MetadataVerificationError, 'metadata_mismatch', name)
        checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'metadata_mismatch',
                      name + ' disables generation')
        checks.check(provider.posts() == [], 'metadata_mismatch', name + ' zero generation POST')
    scripts = metadata_scripts(binding)
    for name, replacement in [('missing_model', Script(body({'models': []}))), ('tags_malformed', Script(b'{"models":')),
                              ('tags_http_500', Script(b'{}', status=500)),
                              ('tags_redirect', Script(b'', status=301, headers=[('Location', 'http://example.invalid/')]))]:
        provider = Provider([scripts[0], replacement, scripts[2]])
        transport = OllamaLiveTransport(binding, schedule, timeout_seconds=30, connection_factory=provider)
        checks.raises(transport.verify_metadata, MetadataVerificationError, 'metadata_mismatch', name)
        checks.check(len(provider.connections) == 2, 'metadata_mismatch', name + ' no redirect follow/retry')
    interrupt = KeyboardInterrupt('metadata interrupt')
    provider = Provider([Script(fail_at='request', error=interrupt)])
    transport = OllamaLiveTransport(binding, schedule, timeout_seconds=30, connection_factory=provider)
    checks.raises(transport.verify_metadata, KeyboardInterrupt, 'process_control', 'metadata KeyboardInterrupt',
                  lambda exc: exc is interrupt)
    checks.check(transport.disabled is not None, 'process_control', 'metadata interrupt disables adapter')

    # Success: exact bytes, raw output, receipt identity, one fresh POST.
    raw = '  ```json\n{"d001_01": "2026-01-02"}\n```\n\u00e9 '
    transport, provider, receipts = verified(binding, schedule)
    response_body = envelope(row, raw)
    provider.add(Script(response_body))
    sent_row = copy.deepcopy(row)
    result = transport(request, sent_row)
    post = provider.posts()
    checks.check(len(post) == 1 and post[0]['body'] is request, 'exact_bytes', 'original request object POSTed once')
    checks.check(post[0]['headers'] == {'Content-Type': 'application/json', 'Connection': 'close'},
                 'exact_bytes', 'no request header mutation')
    checks.check(result['raw_output'] == raw and result['provider_truncated'] is False, 'raw_output', 'no cleanup')
    receipt = result['receipt']
    checks.check(receipt['call_id'] == row['call_id'] and receipt['request_sha256'] == row['request_sha256'] and
                 receipt['seed'] == row['seed'] and receipt['schedule_position'] == 1 and
                 receipt['model'] == row['model'] and receipt['synthetic_only'] is False,
                 'receipt_identity', 'call/request/seed/position bound')
    checks.check(base64.b64decode(receipt['request_body_b64']) == request and
                 base64.b64decode(receipt['response_body_b64']) == response_body and
                 receipt['response_body_sha256'] == digest(response_body), 'exact_bytes', 'lossless request/response bytes')
    checks.check(receipt['metadata_receipts_sha256'] == digest(canonical(receipts)) and
                 receipt['truncation'] == {'basis': 'provider done_reason', 'done_reason': 'stop',
                                           'provider_truncated': False}, 'receipt_identity', 'metadata and truncation basis')
    checks.check(transport_outcome(row, result) == result, 'runner_contract', 'success passes transport_outcome')
    checks.check(sent_row == row, 'exact_bytes', 'caller row not mutated')
    checks.check(len(provider.connections) == 4 and provider.connections[-1].closed and
                 len({id(c) for c in provider.connections}) == 4, 'fresh_connection', 'new closed connection per call')

    # Second call uses yet another connection and the next seed; repeated calls are rejected.
    row2 = schedule[1]
    provider.add(Script(envelope(row2, '{}')))
    second = transport(package.wire(row2), copy.deepcopy(row2))
    checks.check(second['receipt']['seed'] == row2['seed'] and len(provider.connections) == 5 and
                 provider.connections[3] is not provider.connections[4], 'fresh_connection', 'second call fresh connection')
    checks.raises(lambda: transport(package.wire(row2), copy.deepcopy(row2)), TransportContractError, 'retry',
                  'repeated call rejected')
    checks.check(len(provider.posts()) == 2, 'retry', 'one POST maximum per call')
    checks.raises(lambda: transport(package.wire(schedule[2]), copy.deepcopy(schedule[2])), TransportContractError,
                  'retry', 'disabled after repeated-call attempt')

    # Truncation is derived only from done_reason.
    for name, changes, outcome in [('length', {'done_reason': 'length'}, True), ('stop', {}, False)]:
        transport, provider, _ = verified(binding, schedule)
        provider.add(Script(envelope(row, '{"d', **changes)))
        result = transport(request, copy.deepcopy(row))
        checks.check(result.get('provider_truncated') is outcome and result['raw_output'] == '{"d',
                     'truncation', name)

    # Empty string response with a complete envelope is preserved, not repaired or reclassified.
    transport, provider, _ = verified(binding, schedule)
    provider.add(Script(envelope(row, '')))
    result = transport(request, copy.deepcopy(row))
    checks.check(result.get('raw_output') == '' and result['provider_truncated'] is False,
                 'empty_response', 'empty provider response preserved as empty raw output')

    # Adversarial envelopes and transport failures: none can become a success.
    timeout = TimeoutError('timed out')
    vectors = [
        ('malformed_json', Script(b'{"model":'), 'error', 'malformed_json'),
        ('invalid_utf8', Script(b'{"response":"\xff"}'), 'error', 'malformed_json'),
        ('bom', Script(b'\xef\xbb\xbf' + envelope(row, 'x')), 'error', 'malformed_json'),
        ('duplicate_key', Script(b'{"response":"a","response":"b"}'), 'error', 'malformed_json'),
        ('nan', Script(b'{"response":"a","total_duration":NaN}'), 'error', 'malformed_json'),
        ('infinite', Script(b'{"response":"a","total_duration":1e999}'), 'error', 'malformed_json'),
        ('root_list', Script(b'[]'), 'error', 'non_object_root'),
        ('root_string', Script(b'"x"'), 'error', 'non_object_root'),
        ('error_envelope', Script(body({'error': 'model runner crashed'})), 'error', 'provider_error_envelope'),
        ('error_with_response', Script(envelope(row, 'x', error='oops')), 'error', 'provider_error_envelope'),
        ('http_500', Script(body({'error': 'boom'}), status=500, reason='Internal Server Error'), 'error',
         'http_status_not_200'),
        ('http_redirect', Script(b'', status=307, headers=[('Location', 'http://127.0.0.1:9/api/generate')]), 'error',
         'http_status_not_200'),
        ('gzip', Script(envelope(row, 'x'), headers=[('Content-Encoding', 'gzip')]), 'error',
         'unsupported_content_encoding'),
        ('wrong_model', Script(envelope(row, 'x', model='qwen3.8:8b')), 'error', 'model_identity_mismatch'),
        ('model_missing', Script(envelope(row, 'x', model=REMOVE)), 'error', 'model_identity_mismatch'),
        ('done_false', Script(envelope(row, 'x', done=False)), 'error', 'envelope_not_done'),
        ('done_missing', Script(envelope(row, 'x', done=REMOVE)), 'error', 'envelope_not_done'),
        ('done_string', Script(envelope(row, 'x', done='true')), 'error', 'envelope_not_done'),
        ('response_missing', Script(envelope(row, REMOVE)), 'missing', 'response_field_absent_or_null'),
        ('response_null', Script(envelope(row, None)), 'missing', 'response_field_absent_or_null'),
        ('response_missing_thinking', Script(envelope(row, REMOVE, thinking='2026-01-02')), 'missing',
         'response_field_absent_or_null'),
        ('response_int', Script(envelope(row, 7)), 'error', 'response_not_string'),
        ('response_list', Script(envelope(row, ['x'])), 'error', 'response_not_string'),
        ('response_surrogate', Script(b'{"model":' + json.dumps(row['model']).encode() +
                                      b',"response":"\\ud800","done":true,"done_reason":"stop"}'), 'error',
         'response_not_utf8_encodable'),
        ('thinking_present', Script(envelope(row, '', thinking='reasoning')), 'error',
         'thinking_returned_despite_think_false'),
        ('thinking_type', Script(envelope(row, 'x', thinking=1)), 'error', 'thinking_returned_despite_think_false'),
        ('done_reason_missing', Script(envelope(row, 'x', done_reason=REMOVE)), 'error', 'truncation_signal_unusable'),
        ('done_reason_unknown', Script(envelope(row, 'x', done_reason='unload')), 'error', 'truncation_signal_unusable'),
        ('done_reason_load', Script(envelope(row, 'x', done_reason='load')), 'error', 'truncation_signal_unusable'),
        ('done_reason_type', Script(envelope(row, 'x', done_reason=True)), 'error', 'truncation_signal_unusable'),
        ('timeout_connect', Script(fail_at='connect', error=TimeoutError('connect')), 'timeout', 'socket_timeout'),
        ('timeout_response', Script(fail_at='getresponse', error=timeout), 'timeout', 'socket_timeout'),
        ('timeout_read', Script(fail_at='read', error=TimeoutError('read')), 'timeout', 'socket_timeout'),
        ('refused', Script(fail_at='connect', error=ConnectionRefusedError(10061, 'refused')), 'error',
         'transport_exception'),
        ('reset_send', Script(fail_at='request', error=ConnectionResetError(10054, 'reset')), 'error',
         'transport_exception'),
        ('remote_disconnected', Script(fail_at='getresponse', error=http.client.RemoteDisconnected('closed')), 'error',
         'transport_exception'),
        ('incomplete_read', Script(fail_at='read', error=http.client.IncompleteRead(b'{"resp')), 'error',
         'transport_exception'),
    ]
    events = {'timeout': 'PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', 'error': 'PROVIDER_ERROR_WITH_FAILURE_RECEIPT',
              'missing': 'MISSING_RESPONSE_WITH_FAILURE_RECEIPT'}
    for name, script, kind, reason in vectors:
        transport, provider, _ = verified(binding, schedule)
        provider.add(script)
        result = transport(request, copy.deepcopy(row))
        receipt = result.get('receipt') or {}
        checks.check(set(result) == {'failure', 'receipt'} and result['failure'] == kind and
                     receipt.get('failure_reason') == reason, 'adversarial', name + ':' + repr(result.get('failure')) +
                     ':' + repr(receipt.get('failure_reason')))
        checks.check(receipt.get('call_id') == row['call_id'] and receipt.get('request_sha256') == row['request_sha256'] and
                     receipt.get('failure_kind') == kind, 'adversarial', name + ' receipt binding')
        checks.check(transport_outcome(row, result) == result and failure_event(row, kind, receipt) == events[kind],
                     'adversarial', name + ' frozen failure event')
        checks.check(len(provider.posts()) <= 1 and len(provider.connections) == 4 and provider.connections[-1].closed,
                     'adversarial', name + ' at most one POST, one closed connection')
        if 'response_body_b64' in receipt:
            checks.check(base64.b64decode(receipt['response_body_b64']) == script.body, 'adversarial',
                         name + ' raw response bytes preserved')
        checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'retry',
                      name + ' no retry after failure')
        checks.check(len(provider.posts()) <= 1, 'retry', name + ' still at most one POST')
    transmission = {}
    for stage, error in [('connect', ConnectionRefusedError()), ('request', ConnectionResetError()),
                         ('getresponse', TimeoutError())]:
        transport, provider, _ = verified(binding, schedule)
        provider.add(Script(fail_at=stage, error=error))
        transmission[stage] = transport(request, copy.deepcopy(row))['receipt']['post_transmission']
    checks.check(transmission == {'connect': 'NOT_STARTED', 'request': 'STARTED', 'getresponse': 'COMPLETED'},
                 'adversarial', 'truthful POST transmission stage')

    # Unexpected non-transport exceptions propagate; the runner records them as unreceipted.
    transport, provider, _ = verified(binding, schedule)
    provider.add(Script(fail_at='getresponse', error=ValueError('bug')))
    checks.raises(lambda: transport(request, copy.deepcopy(row)), ValueError, 'unreceipted', 'no fabricated receipt')
    checks.check(provider.connections[-1].closed, 'unreceipted', 'connection closed')

    # Process-control exceptions propagate unchanged and consume the attempt.
    for stage, make in [('request', KeyboardInterrupt), ('getresponse', SystemExit), ('read', GeneratorExit)]:
        transport, provider, _ = verified(binding, schedule)
        error = make('control')
        provider.add(Script(fail_at=stage, error=error))
        checks.raises(lambda: transport(request, copy.deepcopy(row)), make, 'process_control',
                      make.__name__ + ' propagates unchanged', lambda exc: exc is error)
        checks.check(provider.connections[-1].closed and transport.consumed_calls == 1, 'process_control',
                     make.__name__ + ' attempt consumed, connection closed')
        checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'process_control',
                      make.__name__ + ' no retry')

    # Call binding violations: rejected before any POST and permanently disabling.
    def bad_call(name, make_request, make_row, transport_schedule=schedule):
        transport, provider, _ = verified(binding, transport_schedule)
        checks.raises(lambda: transport(make_request(), make_row()), TransportContractError, 'call_binding', name)
        checks.check(provider.posts() == [] and transport.disabled is not None, 'call_binding', name + ' zero POST')
        provider.add(Script(envelope(row, 'x')))
        checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'call_binding',
                      name + ' stays disabled')
        checks.check(provider.posts() == [], 'call_binding', name + ' no later POST')
    mutated = request.replace(b'"seed":', b'"seed": ', 1)
    reserialized = json.dumps(json.loads(request), indent=1).encode('utf-8')
    bad_seed = canonical(dict(json.loads(request), options=dict(json.loads(request)['options'], seed=row['seed'] + 1)))
    bad_seed_row = dict(row, seed=row['seed'] + 1, request_sha256=digest(bad_seed))
    bad_model = canonical(dict(json.loads(request), model='qwen3.8:8b'))
    bad_model_row = dict(row, model='qwen3.8:8b', request_sha256=digest(bad_model))
    bad_hash_row = dict(row, request_sha256='0' * 64)
    bad_call_id_row = dict(row, call_id=row['call_id'] + 'X')
    bad_call('wrong_position', lambda: package.wire(schedule[1]), lambda: copy.deepcopy(schedule[1]))
    bad_call('request_byte_mutation', lambda: mutated, lambda: copy.deepcopy(row))
    bad_call('reserialized_json', lambda: reserialized, lambda: copy.deepcopy(row))
    bad_call('request_str', lambda: request.decode('utf-8'), lambda: copy.deepcopy(row))
    bad_call('request_bytearray', lambda: bytearray(request), lambda: copy.deepcopy(row))
    bad_call('seed_mutation', lambda: bad_seed, lambda: bad_seed_row)
    bad_call('model_fallback', lambda: bad_model, lambda: bad_model_row)
    bad_call('request_hash_mismatch', lambda: request, lambda: bad_hash_row)
    bad_call('call_id_mismatch', lambda: request, lambda: bad_call_id_row)
    bad_call('row_not_dict', lambda: request, lambda: list(row.items()))

    # Hash-consistent but non-frozen request content (custom one-row schedules).
    original = json.loads(request)
    options = original['options']
    for name, change in [('stream_true', {'stream': True}), ('think_true', {'think': True}),
                         ('history_context', {'context': [1, 2]}), ('history_messages', {'messages': []}),
                         ('keep_alive', {'keep_alive': 0}), ('raw_mode', {'raw': True}),
                         ('temperature', {'options': dict(options, temperature=0.0)}),
                         ('num_predict_int_vs_float', {'options': dict(options, num_predict=350.0)}),
                         ('missing_option', {'options': {k: v for k, v in options.items() if k != 'top_k'}}),
                         ('extra_option', {'options': dict(options, min_p=0.1)}),
                         ('options_seed_only_changed', {'options': dict(options, seed=options['seed'] + 10)}),
                         ('system_missing', {'system': REMOVE})]:
        value = dict(original, **{k: v for k, v in change.items() if v is not REMOVE})
        value = {k: v for k, v in value.items() if change.get(k, None) is not REMOVE}
        wire = canonical(value)
        custom = [dict(row, request_sha256=digest(wire))]
        bad_call('config_' + name, lambda: wire, lambda: copy.deepcopy(custom[0]), custom)
    duplicate = request[:-1] + b',"stream":false}'
    custom = [dict(row, request_sha256=digest(duplicate))]
    bad_call('config_duplicate_key', lambda: duplicate, lambda: copy.deepcopy(custom[0]), custom)

    # Frozen binding/schedule: fallback, retry, repair, session, config and model substitutions.
    config = binding['generation_configuration']
    for name, change in [('fallback', {'fallback': True}), ('retry_limit', {'retry_limit': 1}),
                         ('repair_calls', {'repair_calls': 1}), ('fresh_session', {'fresh_session_per_call': False}),
                         ('think', {'think': True}), ('stream', {'stream': True}), ('retry_bool', {'retry_limit': False}),
                         ('seed_in_config', {'seed': 1})]:
        changed = dict(binding, generation_configuration=dict(config, **change))
        checks.raises(lambda: OllamaLiveTransport(changed, schedule, timeout_seconds=30, connection_factory=Provider()),
                      TransportContractError, 'frozen_binding', name)
    for name, changed, rows in [
            ('honoring_claimed', dict(binding, internal_option_honoring_attested_by_provider=True), schedule),
            ('not_ollama', dict(binding, provider='openai'), schedule),
            ('bad_manifest', dict(binding, models=[dict(binding['models'][0], manifest_digest='x')]), schedule),
            ('row_fallback_model', binding, [dict(schedule[0], model='qwen3.8:8b')] + schedule[1:]),
            ('row_version', binding, [dict(schedule[0], provider_version='0.0.1')] + schedule[1:]),
            ('row_config', binding, [dict(schedule[0], generation_configuration=dict(config, temperature=1.0))]),
            ('row_position', binding, schedule[1:]),
            ('row_duplicate', binding, [schedule[0], dict(schedule[0], schedule_position=2)]),
            ('row_seed_bool', binding, [dict(schedule[0], seed=True)])]:
        checks.raises(lambda: OllamaLiveTransport(changed, rows, timeout_seconds=30, connection_factory=Provider()),
                      TransportContractError, 'frozen_binding', name)
    for timeout_value in (None, 0, -1, float('inf'), float('nan'), True):
        checks.raises(lambda: OllamaLiveTransport(binding, schedule, timeout_seconds=timeout_value),
                      TransportContractError, 'frozen_binding', 'timeout ' + repr(timeout_value))
    checks.raises(lambda: OllamaLiveTransport(binding, schedule, connection_factory=Provider()), TypeError,
                  'frozen_binding', 'timeout is required')

    # Caller mutation after construction cannot alter the frozen copies.
    mutable_binding, mutable_schedule = copy.deepcopy(binding), copy.deepcopy(schedule)
    transport, provider, _ = verified(mutable_binding, mutable_schedule)
    mutable_binding['generation_configuration']['temperature'] = 2.0
    mutable_schedule[0]['seed'] = 1
    provider.add(Script(envelope(row, 'x')))
    checks.check('raw_output' in transport(request, copy.deepcopy(row)), 'immutability', 'frozen copies used')

    # Explicit start position for verified resume; earlier positions are never revisited.
    transport, provider, _ = verified(binding, schedule, start_position=3)
    checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'start_position',
                  'position before start rejected')
    transport, provider, _ = verified(binding, schedule, start_position=3)
    provider.add(Script(envelope(schedule[2], 'x')))
    result = transport(package.wire(schedule[2]), copy.deepcopy(schedule[2]))
    checks.check(result['receipt']['schedule_position'] == 3 and result['receipt']['adapter_start_position'] == 3,
                 'start_position', 'start position bound in receipt')
    for value in (0, 81, '1', True):
        checks.raises(lambda: OllamaLiveTransport(binding, schedule, timeout_seconds=30, start_position=value),
                      TransportContractError, 'start_position', repr(value))
    one = [schedule[0]]
    transport, provider, _ = verified(binding, one)
    provider.add(Script(envelope(row, 'x')))
    transport(request, copy.deepcopy(row))
    checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'retry', 'schedule exhausted')

    # Parallel generation is rejected, not queued.
    transport, provider, _ = verified(binding, schedule)
    nested = []
    def concurrent():
        def other():
            try:
                transport(package.wire(schedule[1]), copy.deepcopy(schedule[1]))
            except BaseException as exc:
                nested.append(exc)
        thread = threading.Thread(target=other)
        thread.start()
        thread.join(10)
    provider.add(Script(envelope(row, 'x'), hook=('getresponse', concurrent)))
    first = transport(request, copy.deepcopy(row))
    checks.check(len(nested) == 1 and isinstance(nested[0], TransportContractError) and 'raw_output' in first and
                 len(provider.posts()) == 1, 'parallel', 'concurrent call rejected; one POST')

    # Runner contract vectors: receipts with the wrong identity cannot become evidence.
    transport, provider, _ = verified(binding, schedule)
    provider.add(Script(envelope(row, synthetic_gold(member))))
    good = transport(request, copy.deepcopy(row))
    unusable = {'failure': 'unreceipted', 'receipt': None, 'unusable_reason': 'malformed_transport_outcome'}
    for name, value in [('call_id', dict(good, receipt=dict(good['receipt'], call_id='X'))),
                        ('request_hash', dict(good, receipt=dict(good['receipt'], request_sha256='0' * 64))),
                        ('truncated_type', dict(good, provider_truncated=None)),
                        ('receipt_missing', {k: v for k, v in good.items() if k != 'receipt'})]:
        checks.check(transport_outcome(row, value) == unusable, 'runner_contract', 'unusable success ' + name)
    for name, value in [('kind_mismatch', {'failure': 'timeout', 'receipt': {'call_id': row['call_id'],
                         'request_sha256': row['request_sha256'], 'failure_kind': 'error'}}),
                        ('call_mismatch', {'failure': 'error', 'receipt': {'call_id': 'X',
                         'request_sha256': row['request_sha256'], 'failure_kind': 'error'}})]:
        checks.check(transport_outcome(row, value) == unusable and
                     failure_event(row, 'unreceipted', None) == 'PROVIDER_FAILURE_WITHOUT_RECEIPT',
                     'runner_contract', 'failure without usable receipt ' + name)


# -- interrupted response reads ----------------------------------------------------------
BASE_RECEIPT_KEYS = {'schema_version', 'transport_version', 'synthetic_only', 'call_id', 'request_sha256',
                     'schedule_position', 'adapter_start_position', 'seed', 'model', 'provider',
                     'provider_version_verified', 'metadata_receipts_sha256', 'endpoint', 'method',
                     'request_body_b64', 'request_body_length', 'post_transmission', 'connection',
                     'internal_option_honoring'}
EVENTS = {'timeout': 'PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', 'error': 'PROVIDER_ERROR_WITH_FAILURE_RECEIPT'}


class CustomControl(BaseException):
    pass


def interrupted_read_tests(package, binding, checks):
    schedule, row, request = package.schedule, package.schedule[0], package.wire(package.schedule[0])
    headers = [('Content-Type', 'application/json; charset=utf-8'), ('Date', 'Mon, 05 Oct 2026 00:00:00 GMT'),
               ('X-Dup', 'a'), ('X-Dup', 'b')]

    def exchange(connection_script):
        transport, provider, _ = verified(binding, schedule)
        provider.add(connection_script)
        return transport, provider, transport(request, copy.deepcopy(row))

    def interrupted(name, transport, provider, result, kind, reason, stage, status, phrase, observed_headers, body_bytes,
                    error, partial=None, **detail):
        """Every expected field is asserted unconditionally; absent evidence fails."""
        receipt = result.get('receipt') or {}
        capture = receipt.get('response_capture') or {}
        read_started = stage == 'response_body_read'
        checks.check(set(result) == {'failure', 'receipt'} and result['failure'] == kind and
                     receipt.get('failure_kind') == kind and receipt.get('failure_reason') == reason,
                     'interrupted_read', name + ' failure kind/reason ' + repr((result.get('failure'),
                                                                                receipt.get('failure_reason'))))
        checks.check(receipt.get('failure_stage') == stage, 'interrupted_read',
                     name + ' accurate stage ' + repr(receipt.get('failure_stage')))
        checks.check(receipt.get('http_status') == status and receipt.get('http_reason') == phrase,
                     'interrupted_read', name + ' exact observed status/reason')
        if observed_headers is None:
            checks.check('response_headers' not in receipt, 'interrupted_read', name + ' unobserved headers absent')
        else:
            checks.check(receipt.get('response_headers') == [[k, v] for k, v in observed_headers], 'interrupted_read',
                         name + ' exact observed headers ' + repr(receipt.get('response_headers')))
        if read_started:
            checks.check(receipt.get('response_body_b64') == base64.b64encode(body_bytes).decode('ascii') and
                         receipt.get('response_body_sha256') == digest(body_bytes) and
                         receipt.get('response_body_length') == len(body_bytes), 'interrupted_read',
                         name + ' exact available body bytes ' + repr(receipt.get('response_body_b64')))
        else:
            checks.check(not {'response_body_b64', 'response_body_sha256', 'response_body_length'} & set(receipt),
                         'interrupted_read', name + ' unread body not fabricated')
        checks.check(capture.get('state') == 'INTERRUPTED_INCOMPLETE' and capture.get('body_complete') is False and
                     capture.get('interrupted_stage') == stage and capture.get('status_observed') is True and
                     capture.get('headers_observed') is (observed_headers is not None) and
                     capture.get('body_read_started') is read_started, 'interrupted_read',
                     name + ' truthful incomplete capture state ' + repr(capture))
        checks.check(receipt.get('exception_type') == (None if error is None else type(error).__name__) and
                     receipt.get('exception_message') == (None if error is None else str(error)) and
                     receipt.get('errno') == (error.errno if isinstance(error, OSError) else None),
                     'interrupted_read', name + ' original error evidence')
        if partial is None:
            checks.check(not any(k.startswith('exception_partial') for k in receipt), 'interrupted_read',
                         name + ' no fabricated exception partial')
        else:
            checks.check(receipt.get('exception_partial_b64') == base64.b64encode(partial).decode('ascii') and
                         receipt.get('exception_partial_sha256') == digest(partial) and
                         receipt.get('exception_partial_length') == len(partial), 'interrupted_read',
                         name + ' IncompleteRead.partial preserved')
        for key, value in detail.items():
            checks.check(receipt.get(key) == value, 'interrupted_read', name + ' ' + key)
        checks.check('raw_output' not in result and 'truncation' not in receipt and 'provider_fields' not in receipt,
                     'interrupted_read', name + ' never classified as a response')
        checks.check(receipt.get('call_id') == row['call_id'] and receipt.get('request_sha256') == row['request_sha256'] and
                     receipt.get('post_transmission') == 'COMPLETED' and
                     transport_outcome(row, result) == result and failure_event(row, kind, receipt) == EVENTS[kind],
                     'interrupted_read', name + ' receipt binding and frozen failure event')
        checks.check(len(provider.posts()) == 1 and provider.connections[-1].closed, 'interrupted_read',
                     name + ' exactly one POST, connection closed')
        checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'interrupted_read',
                      name + ' no retry')
        checks.check(len(provider.posts()) == 1, 'interrupted_read', name + ' still one POST')

    # Scripted responses: interruption after status, after headers (zero bytes) and after partial bytes.
    first, second = b'{"model":"q', b'wen3.8:27b","resp'
    for label, make, kind, reason in [
            ('timeout', lambda: TimeoutError('read timed out'), 'timeout', 'socket_timeout'),
            ('reset', lambda: ConnectionResetError(10054, 'reset by peer'), 'error', 'transport_exception'),
            ('incomplete', lambda: http.client.IncompleteRead(b'ing"', 9), 'error', 'transport_exception')]:
        partial = b'ing"' if label == 'incomplete' else None
        detail = {'exception_expected_more': 9} if label == 'incomplete' else {}
        error = make()
        transport, provider, result = exchange(Script(status=200, reason='OK', headers=headers,
                                                      fail_at='getheaders', error=error))
        interrupted(label + '_after_status', transport, provider, result, kind, reason, 'response_headers', 200, 'OK',
                    None, b'', error, partial, **detail)
        error = make()
        transport, provider, result = exchange(Script(headers=headers, chunks=[], fail_at='read', error=error))
        interrupted(label + '_after_headers_zero_bytes', transport, provider, result, kind, reason,
                    'response_body_read', 200, 'OK', headers, b'', error, partial, **detail)
        error = make()
        transport, provider, result = exchange(Script(headers=headers, chunks=[first], fail_at='read', error=error))
        interrupted(label + '_after_one_chunk', transport, provider, result, kind, reason, 'response_body_read', 200,
                    'OK', headers, first, error, partial, **detail)
        error = make()
        transport, provider, result = exchange(Script(status=503, reason='Service Unavailable', headers=headers,
                                                      chunks=[first, second], fail_at='read', error=error))
        interrupted(label + '_after_two_chunks_non_200', transport, provider, result, kind, reason,
                    'response_body_read', 503, 'Service Unavailable', headers, first + second, error, partial,
                    **detail)

    # Premature EOF before the declared Content-Length is incomplete, not a parseable response.
    transport, provider, result = exchange(Script(headers=headers, chunks=[first], length=7))
    interrupted('eof_before_content_length', transport, provider, result, 'error',
                'eof_before_declared_content_length', 'response_body_read', 200, 'OK', headers, first, None,
                content_length_remaining=7)

    # The real http.client parser over scripted bytes (no socket): bytes returned before the interruption survive.
    complete = envelope(row, 'kept')
    head = (b'HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: ' +
            str(len(complete)).encode() + b'\r\nX-Dup: a\r\nX-Dup: b\r\nConnection: close\r\n\r\n')
    wire_headers = [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(complete))),
                    ('X-Dup', 'a'), ('X-Dup', 'b'), ('Connection', 'close')]
    chunked_head = b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n'
    chunked_headers = [('Content-Type', 'application/json'), ('Transfer-Encoding', 'chunked')]
    for name, segments, error, kind, reason, observed_headers, body_bytes, extra in [
            ('stdlib_timeout_after_partial', [head, complete[:9], complete[9:20]], TimeoutError('timed out'),
             'timeout', 'socket_timeout', wire_headers, complete[:20], {}),
            ('stdlib_reset_after_partial', [head, complete[:13]], ConnectionResetError(10054, 'reset'), 'error',
             'transport_exception', wire_headers, complete[:13], {}),
            ('stdlib_timeout_zero_bytes', [head], TimeoutError('timed out'), 'timeout', 'socket_timeout',
             wire_headers, b'', {}),
            ('stdlib_eof_short_content_length', [head, complete[:11]], None, 'error',
             'eof_before_declared_content_length', wire_headers, complete[:11],
             {'content_length_remaining': len(complete) - 11}),
            ('stdlib_chunked_reset_after_chunk', [chunked_head, b'5\r\nhello\r\n'],
             ConnectionResetError(10054, 'reset'), 'error', 'transport_exception', chunked_headers, b'hello', {}),
            ('stdlib_chunked_timeout_after_chunks', [chunked_head, b'5\r\nhello\r\n', b'3\r\nabc\r\n'],
             TimeoutError('timed out'), 'timeout', 'socket_timeout', chunked_headers, b'helloabc', {})]:
        transport, provider, result = exchange(StdlibConnection(segments, error))
        interrupted(name, transport, provider, result, kind, reason, 'response_body_read', 200, 'OK', observed_headers,
                    body_bytes, error, **extra)
    # A malformed chunk size makes http.client raise IncompleteRead(b'') itself; earlier chunks survive.
    transport, provider, result = exchange(StdlibConnection([chunked_head, b'5\r\nhello\r\nZZ\r\n']))
    raised = result.get('receipt', {}).get('exception_message')
    interrupted('stdlib_chunked_incomplete_read', transport, provider, result, 'error', 'transport_exception',
                'response_body_read', 200, 'OK', chunked_headers, b'hello',
                http.client.IncompleteRead(b''), b'', exception_expected_more=None)
    checks.check(raised == str(http.client.IncompleteRead(b'')), 'interrupted_read', 'stdlib IncompleteRead message')

    # Complete responses are unchanged: Content-Length and chunked framing, split across reads.
    chunked_body = (format(len(complete[:10]), 'x').encode() + b'\r\n' + complete[:10] + b'\r\n' +
                    format(len(complete[10:]), 'x').encode() + b'\r\n' + complete[10:] + b'\r\n0\r\n\r\n')
    for name, segments, observed_headers in [
            ('stdlib_complete_content_length', [head, complete[:5], complete[5:]], wire_headers),
            ('stdlib_complete_chunked', [chunked_head, chunked_body[:7], chunked_body[7:]], chunked_headers),
            ('stdlib_complete_single_segment', [head + complete], wire_headers)]:
        transport, provider, result = exchange(StdlibConnection(segments))
        receipt = result.get('receipt') or {}
        checks.check(result.get('raw_output') == 'kept' and result.get('provider_truncated') is False and
                     base64.b64decode(receipt.get('response_body_b64', '')) == complete and
                     receipt.get('response_body_length') == len(complete) and
                     receipt.get('response_headers') == [[k, v] for k, v in observed_headers] and
                     receipt.get('http_status') == 200 and set(receipt) == BASE_RECEIPT_KEYS | {
                         'http_status', 'http_reason', 'response_headers', 'response_body_b64',
                         'response_body_sha256', 'response_body_length', 'response_body_scope', 'provider_fields',
                         'truncation'}, 'complete_response', name + ' unchanged complete receipt')
    transport, provider, result = exchange(Script(envelope(row, 'kept'), headers=headers))
    checks.check(result.get('raw_output') == 'kept' and 'response_capture' not in result['receipt'] and
                 base64.b64decode(result['receipt']['response_body_b64']) == envelope(row, 'kept'),
                 'complete_response', 'scripted complete response unchanged')
    transport, provider, result = exchange(Script(headers=headers, chunks=[b'{"model":', b'"x"}']))
    checks.check(result.get('failure') == 'error' and result['receipt']['failure_reason'] == 'model_identity_mismatch' and
                 base64.b64decode(result['receipt']['response_body_b64']) == b'{"model":"x"}',
                 'complete_response', 'multi-chunk complete body joined exactly')

    # Pre-response failures keep their original receipt shape and stages.
    for name, stage, error, kind, expected_stage, transmission in [
            ('connect_refused', 'connect', ConnectionRefusedError(10061, 'refused'), 'error', 'connect', 'NOT_STARTED'),
            ('connect_timeout', 'connect', TimeoutError('t'), 'timeout', 'connect', 'NOT_STARTED'),
            ('send_reset', 'request', ConnectionResetError(10054, 'reset'), 'error', 'send', 'STARTED'),
            ('send_timeout', 'request', TimeoutError('t'), 'timeout', 'send', 'STARTED'),
            ('getresponse_disconnect', 'getresponse', http.client.RemoteDisconnected('closed'), 'error', 'response',
             'COMPLETED'),
            ('getresponse_timeout', 'getresponse', TimeoutError('t'), 'timeout', 'response', 'COMPLETED')]:
        transport, provider, result = exchange(Script(fail_at=stage, error=error))
        receipt = result['receipt']
        extra = {'failure_kind', 'failure_reason', 'failure_stage', 'exception_type'} | (
            {'errno'} if kind == 'error' else set())
        checks.check(result['failure'] == kind and receipt['failure_stage'] == expected_stage and
                     receipt['post_transmission'] == transmission and set(receipt) == BASE_RECEIPT_KEYS | extra,
                     'pre_response_unchanged', name + ' receipt shape/stage unchanged ' + repr(sorted(set(receipt))))

    # Process control during an interrupted read still propagates unchanged; no receipt is fabricated.
    for make in (KeyboardInterrupt, SystemExit, GeneratorExit, CustomControl):
        transport, provider, _ = verified(binding, schedule)
        error = make('control')
        provider.add(Script(headers=headers, chunks=[first], fail_at='read', error=error))
        checks.raises(lambda: transport(request, copy.deepcopy(row)), make, 'process_control',
                      make.__name__ + ' after partial bytes propagates unchanged', lambda exc: exc is error)
        checks.check(provider.connections[-1].closed and transport.consumed_calls == 1 and len(provider.posts()) == 1,
                     'process_control', make.__name__ + ' after partial bytes: consumed, closed, one POST')
        checks.raises(lambda: transport(request, copy.deepcopy(row)), TransportContractError, 'process_control',
                      make.__name__ + ' after partial bytes: no retry')


# -- live Run integration ----------------------------------------------------------------
def namespace(root, package, provider_binding):
    """Temporary test-only authority/candidate namespace; never copied from real authority."""
    data = root / 'authority-namespace'
    candidate_path = data / 'preexecution/lock_timeout_repair/EXECUTION_FREEZE_CANDIDATE.json'
    write_once(candidate_path, {'experiment': 'G-CAL1', 'status': 'EXECUTION_FREEZE_CANDIDATE_ONLY', 'activated': False,
                                'binding': package.binding, 'provider_binding': provider_binding, 'test_only': TEST_MARK})
    activation = {'experiment': 'G-CAL1', 'status': 'EXECUTION_FREEZE_ACTIVE', 'binding': package.binding,
                  'phase_authorized': False, 'candidate_sha256': file_digest(candidate_path), 'test_only': TEST_MARK}
    write_once(data / 'execution/EXECUTION_FREEZE_ACTIVATION.json', activation)
    write_once(data / 'execution/ACTIVE_FREEZE.json', {
        'activation_path': 'execution/EXECUTION_FREEZE_ACTIVATION.json',
        'activation_sha256': file_digest(data / 'execution/EXECUTION_FREEZE_ACTIVATION.json')})
    return data, activation


def grant(package, run_id):
    return {'status': 'EXPLICIT_OPERATOR_PHASE_AUTHORIZATION', 'experiment': 'G-CAL1', 'phase': 'CAL', 'run_id': run_id,
            'freeze_status': 'EXECUTION_FREEZE_ACTIVE', 'binding': package.binding,
            'synthetic_evidence_allowed': False, 'test_only': TEST_MARK}


def integration_tests(package, binding, checks, root):
    schedule = package.schedule
    checks.check(package.binding.get('test_only') == TEST_MARK, 'authority_isolation', 'test-only binding marker')
    data, activation = namespace(root, package, binding)
    counter = [0]

    def fresh_transport(start=1):
        provider = Provider(metadata_scripts(binding))
        transport = OllamaLiveTransport(binding, schedule, timeout_seconds=30, start_position=start,
                                        connection_factory=provider)
        return transport, provider

    def directory(name):
        counter[0] += 1
        return root / 'runs' / f'{counter[0]:03d}-{name}'

    def kinds(run):
        return [r['payload']['kind'] for r in run.journal.read()]

    # Missing authority rejects before any directory, journal or transport contact.
    empty = root / 'empty-namespace'
    empty.mkdir()
    transport, provider = fresh_transport()
    with patch.object(lab, 'DATA', empty):
        target = directory('missing-authority')
        checks.raises(lambda: Run(package, target, 'G-CAL1-TEST-MISSING', mechanical=False), IntegrityError,
                      'authority', 'missing active freeze', lambda exc: exc.event == 'PROVENANCE_MISMATCH')
        checks.check(not target.exists() and provider.connections == [], 'authority', 'nothing created or contacted')

    with patch.object(lab, 'DATA', data):
        receipts = transport.verify_metadata()
        metadata_connections = len(provider.connections)
        for name, kwargs, event in [
                ('no_grant', {'authorization': None}, 'PROVENANCE_MISMATCH'),
                ('wrong_run_grant', {'authorization': grant(package, 'OTHER')}, 'PROVENANCE_MISMATCH'),
                ('synthetic_grant', {'authorization': dict(grant(package, 'G-CAL1-TEST-AUTH'),
                                                           synthetic_evidence_allowed=True)}, 'PROVENANCE_MISMATCH'),
                ('wrong_activation', {'activation': dict(activation, phase_authorized=True)}, 'PROVENANCE_MISMATCH'),
                ('no_receipts', {'provider_receipts': None}, 'PRE_PROVIDER_VERSION_MISMATCH'),
                ('wrong_version', {'provider_receipts': dict(receipts, provider_version='0.34.2')},
                 'PRE_PROVIDER_VERSION_MISMATCH'),
                ('wrong_model', {'provider_receipts': dict(receipts, models=[dict(binding['models'][0],
                                                                                  blob_sha256='0' * 64)])},
                 'PRE_MODEL_IDENTITY_MISMATCH'),
                ('wrong_config', {'provider_receipts': dict(receipts, generation_configuration=dict(
                    receipts['generation_configuration'], temperature=0.0))}, 'PRE_GENERATION_CONFIG_MISMATCH')]:
            arguments = dict(activation=activation, authorization=grant(package, 'G-CAL1-TEST-AUTH'),
                             provider_receipts=receipts)
            arguments.update(kwargs)
            target = directory(name)
            checks.raises(lambda: Run(package, target, 'G-CAL1-TEST-AUTH', mechanical=False, **arguments),
                          IntegrityError, 'authority', name, lambda exc: exc.event == event)
            checks.check(not target.exists() and len(provider.connections) == metadata_connections,
                         'authority', name + ' rejected before run creation and transport')
        # A real-binding package can never be authorized by this temporary namespace either.
        impostor = copy.copy(package)
        impostor.binding = {k: v for k, v in package.binding.items() if k != 'test_only'}
        target = directory('real-binding')
        checks.raises(lambda: Run(impostor, target, 'G-CAL1-TEST-REAL', mechanical=False, activation=activation,
                                  authorization=grant(impostor, 'G-CAL1-TEST-REAL'), provider_receipts=receipts),
                      IntegrityError, 'authority', 'real binding rejected by test namespace')

        def live_run(name, transport_receipts):
            run_id = 'G-CAL1-TEST-LIVE-' + name
            return Run(package, directory(name), run_id, mechanical=False, activation=activation,
                       authorization=grant(package, run_id), provider_receipts=transport_receipts)

        # Accidental synthetic or unmarked transports cannot cross the live boundary.
        calls = []
        def synthetic_stub(request, row):
            calls.append(row)
        synthetic_stub.synthetic_only = True
        def unmarked_stub(request, row):
            calls.append(row)
        for name, stub in [('synthetic', synthetic_stub), ('unmarked', unmarked_stub)]:
            run = live_run(name, receipts)
            checks.raises(lambda: run.perform(copy.deepcopy(schedule[0]), stub), IntegrityError, 'boundary',
                          name + ' transport rejected in live mode', lambda exc: exc.event == 'PROVENANCE_MISMATCH')
            checks.check(kinds(run) == ['RUN_CREATED'] and not calls, 'boundary', name + ' zero START/calls')
        mechanical_transport, mechanical_provider = fresh_transport()
        run = Run(package, directory('mechanical'), 'G-CAL1-TEST-MECHANICAL')
        checks.raises(lambda: run.perform(copy.deepcopy(schedule[0]), mechanical_transport), IntegrityError, 'boundary',
                      'live adapter rejected in mechanical mode')
        checks.check(kinds(run) == ['RUN_CREATED'] and mechanical_provider.connections == [], 'boundary',
                     'mechanical rejection precedes contact')

        # Live success through the actual Run, checkpoint, restart and resume.
        run = live_run('success', receipts)
        checks.check(run.journal.read()[0]['payload']['mode'] == 'LIVE', 'integration', 'LIVE run created')
        bodies, outputs = [], []
        for index in range(3):
            row = schedule[index]
            member = package.members[row['fixture_id']]
            gold = synthetic_gold(member)
            output = [gold, gold.replace(next(iter(member['gold'].values())), '1999-01-01'),
                      '\n' + gold + '\n'][index]
            changes = {'done_reason': 'length'} if index == 1 else {}
            bodies.append(envelope(row, output, **changes))
            outputs.append(output)
            provider.add(Script(bodies[-1]))
            score = run.perform(copy.deepcopy(row), transport)
            expected = [(True, False), (False, True), (None, False)][index]
            checks.check((expected[0] is None or score['semantic_correct'] is expected[0]) and
                         score['provider_truncated'] is expected[1], 'integration', 'scored call ' + str(index + 1))
        records = [r['payload'] for r in run.journal.read()]
        completes = [r for r in records if r['kind'] == 'COMPLETE']
        checks.check([r['kind'] for r in records] == ['RUN_CREATED'] + ['START', 'COMPLETE'] * 3,
                     'integration', 'journal START/COMPLETE lineage')
        for index, record in enumerate(completes):
            row, receipt = schedule[index], record['result']['receipt']
            checks.check(record['call_id'] == row['call_id'] and record['result']['raw_output'] == outputs[index] and
                         base64.b64decode(receipt['request_body_b64']) == package.wire(row) and
                         base64.b64decode(receipt['response_body_b64']) == bodies[index] and
                         receipt['request_sha256'] == row['request_sha256'] and receipt['synthetic_only'] is False,
                         'integration', 'journaled exact bytes/receipt ' + str(index + 1))
        posts = provider.posts()
        checks.check(len(posts) == 3 and [p['body'] for p in posts] == [package.wire(r) for r in schedule[:3]] and
                     len({id(c) for c in provider.connections}) == len(provider.connections) == 6 and
                     all(c.closed for c in provider.connections), 'integration', 'one POST per call, fresh connections')
        checkpoint = run.checkpoint()
        success_directory = run.directory
        del run
        resumed_transport, resumed_provider = fresh_transport(start=4)
        resumed_receipts = resumed_transport.verify_metadata()
        checks.check(resumed_receipts['models'] == receipts['models'] and
                     resumed_receipts['provider_version'] == receipts['provider_version'],
                     'integration', 'restart re-verifies metadata')
        resumed = Run(package, success_directory, 'G-CAL1-TEST-LIVE-success',
                      mechanical=False, resume=True, activation=activation,
                      authorization=grant(package, 'G-CAL1-TEST-LIVE-success'), provider_receipts=receipts)
        resumed.verify_resume(checkpoint)
        resumed_provider.add(Script(envelope(schedule[3], synthetic_gold(package.members[schedule[3]['fixture_id']]))))
        resumed.perform(copy.deepcopy(schedule[3]), resumed_transport)
        report = resumed.final_report()
        checks.check(report['mode'] == 'LIVE' and report['provider_model_calls'] == 4 and
                     report['state']['verdict'] == 'RUNNING' and report['state']['completed_observations'] == 4,
                     'integration', 'resume/replay/final report through live boundary')
        replay = Run(package, resumed.directory, resumed.run_id, mechanical=False, resume=True, activation=activation,
                     authorization=grant(package, resumed.run_id), provider_receipts=receipts)
        checks.check(len(replay.evidence) == 4, 'integration', 'independent journal/scorer replay of live receipts')

        # Failures through the actual Run: frozen events, terminality, no retries.
        for name, script, event, verdict in [
                ('timeout', Script(fail_at='getresponse', error=TimeoutError('t')),
                 'PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', 'INCOMPLETE'),
                ('error', Script(body({'error': 'x'}), status=500), 'PROVIDER_ERROR_WITH_FAILURE_RECEIPT', 'INCOMPLETE'),
                ('missing', Script(envelope(schedule[0], REMOVE)), 'MISSING_RESPONSE_WITH_FAILURE_RECEIPT', 'INCOMPLETE'),
                ('wrong_model', Script(envelope(schedule[0], 'x', model='other:1b')),
                 'PROVIDER_ERROR_WITH_FAILURE_RECEIPT', 'INCOMPLETE'),
                ('read_reset_partial', Script(chunks=[b'{"model":"qw'], fail_at='read',
                                              error=ConnectionResetError(10054, 'reset')),
                 'PROVIDER_ERROR_WITH_FAILURE_RECEIPT', 'INCOMPLETE'),
                ('read_timeout_partial', Script(chunks=[b'{"mo', b'del"'], fail_at='read', error=TimeoutError('t')),
                 'PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', 'INCOMPLETE'),
                ('read_timeout_zero_bytes', Script(chunks=[], fail_at='read', error=TimeoutError('t')),
                 'PROVIDER_TIMEOUT_WITH_FAILURE_RECEIPT', 'INCOMPLETE'),
                ('unreceipted', Script(fail_at='connect', error=ValueError('bug')),
                 'PROVIDER_FAILURE_WITHOUT_RECEIPT', 'INVALID')]:
            failing, failing_provider = fresh_transport()
            failing_receipts = failing.verify_metadata()
            run = live_run('failure-' + name, failing_receipts)
            failing_provider.add(script)
            checks.raises(lambda: run.perform(copy.deepcopy(schedule[0]), failing), IntegrityError, 'integration_failure',
                          name, lambda exc: exc.event == event)
            records = [r['payload'] for r in run.journal.read()]
            checks.check([r['kind'] for r in records] == ['RUN_CREATED', 'START', 'FAILURE'] and
                         records[-1]['event'] == event and run.state()['verdict'] == verdict,
                         'integration_failure', name + ' journaled terminal failure')
            if event != 'PROVIDER_FAILURE_WITHOUT_RECEIPT':
                checks.check(records[-1]['receipt']['call_id'] == schedule[0]['call_id'] and
                             records[-1]['receipt']['request_sha256'] == schedule[0]['request_sha256'],
                             'integration_failure', name + ' receipt bound')
                if name.startswith('read_'):
                    journaled = records[-1]['receipt']
                    checks.check(journaled.get('failure_stage') == 'response_body_read' and
                                 journaled.get('response_body_b64') ==
                                 base64.b64encode(b''.join(script.chunks)).decode('ascii') and
                                 journaled.get('response_body_length') == len(b''.join(script.chunks)) and
                                 journaled.get('http_status') == script.status and
                                 journaled.get('response_headers') == [[k, v] for k, v in script.headers] and
                                 (journaled.get('response_capture') or {}).get('state') == 'INTERRUPTED_INCOMPLETE',
                                 'integration_failure', name + ' journaled partial bytes/status/headers preserved')
            else:
                checks.check(records[-1]['receipt'] is None, 'integration_failure', name + ' no fabricated receipt')
            before = len(failing_provider.connections)
            checks.raises(lambda: run.perform(copy.deepcopy(schedule[1]), failing), IntegrityError,
                          'integration_failure', name + ' later collection rejected')
            checks.check(len(failing_provider.connections) == before and len(failing_provider.posts()) <= 1,
                         'integration_failure', name + ' zero later contact')

        # Unverified adapter inside a live Run: no POST, unreceipted terminal failure.
        unverified, unverified_provider = fresh_transport()
        run = live_run('unverified', receipts)
        checks.raises(lambda: run.perform(copy.deepcopy(schedule[0]), unverified), IntegrityError, 'metadata_first',
                      'unverified adapter in Run', lambda exc: exc.event == 'PROVIDER_FAILURE_WITHOUT_RECEIPT')
        checks.check(unverified_provider.connections == [], 'metadata_first', 'zero contact')

        # Process control through the actual Run propagates unchanged; no receipt is fabricated.
        control, control_provider = fresh_transport()
        control_receipts = control.verify_metadata()
        run = live_run('interrupt', control_receipts)
        interrupt = KeyboardInterrupt('operator')
        control_provider.add(Script(fail_at='getresponse', error=interrupt))
        checks.raises(lambda: run.perform(copy.deepcopy(schedule[0]), control), KeyboardInterrupt, 'process_control',
                      'Run propagates original KeyboardInterrupt', lambda exc: exc is interrupt)
        records = [r['payload'] for r in run.journal.read()]
        checks.check([r['kind'] for r in records] == ['RUN_CREATED', 'START'] and
                     'SCHEDULED_CALL_OMITTED_WITHOUT_FAILURE_RECEIPT' in run.events, 'process_control',
                     'open START retained as omitted-call incident without receipt')
        checks.raises(lambda: run.perform(copy.deepcopy(schedule[1]), control), IntegrityError, 'process_control',
                      'no continuation after interrupt')
        checks.check(len(control_provider.posts()) == 1, 'process_control', 'single POST')
    checks.check(lab.DATA == DATA, 'authority_isolation', 'lab namespace restored')


# -- protection ------------------------------------------------------------------------
def protected_snapshot():
    tree = {p.relative_to(ROOT).as_posix(): file_digest(p) for p in sorted(DATA.rglob('*')) if p.is_file()}
    for name in UNTRACKED:
        path = ROOT / 'experiments/G-EXTRACT1-candidate/corpus' / (name + '.json')
        tree[path.relative_to(ROOT).as_posix()] = file_digest(path) if path.is_file() else None
    for path in sorted((ROOT / 'tools').glob('g_*.py')):
        tree[path.relative_to(ROOT).as_posix()] = file_digest(path)
    return tree


def main():
    checks = Checks()
    try:
        __import__('socket').socket()
        AUDIT.append('SELF_TEST_NOT_DENIED')
    except RuntimeError:
        pass
    checks.check(AUDIT == ['socket.__new__'], 'no_contact', 'socket audit denial active before tests')
    self_test = len(AUDIT)
    before = protected_snapshot()
    package = TestPackage()
    binding = load(CANDIDATE)['provider_binding']
    checks.check(binding['generation_configuration'] == package.design['generation_configuration'] and
                 all(r['request_sha256'] == digest(package.wire(r)) for r in package.schedule),
                 'test_package', 'committed provider binding/config/wire bytes agree')
    with tempfile.TemporaryDirectory(prefix='g-cal1-transport-tests-', ignore_cleanup_errors=True) as tmp:
        adapter_tests(package, binding, checks)
        interrupted_read_tests(package, binding, checks)
        integration_tests(package, binding, checks, Path(tmp))
    checks.check(protected_snapshot() == before, 'protection', 'G-CAL1 tree, tools and untracked artifacts unchanged')
    checks.check(len(AUDIT) == self_test, 'no_contact', 'zero socket/subprocess audit events during tests')
    summary = {'passed': checks.passed, 'failed': len(checks.failed), 'categories': checks.categories,
               'socket_or_subprocess_audit_events_after_self_test': len(AUDIT) - self_test,
               'provider_contact': 'NONE (all HTTP scripted; sockets denied by audit hook)'}
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 1 if checks.failed else 0


if __name__ == '__main__':
    sys.exit(main())
