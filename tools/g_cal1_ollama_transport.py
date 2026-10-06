"""Injectable live Ollama transport for the frozen G-CAL1 laboratory.

Plumbing only. Importing or constructing this module contacts nothing and grants
no collection authority: a caller still needs a separately reviewed active freeze
and an explicit phase authorization accepted by g_cal1_lab.authority().

Interface: transport(request_bytes, schedule_row), passed as the transport
argument of g_cal1_lab.Run.perform(row, transport). Results follow the existing
g_extract1_runner.transport_outcome / failure_event contract.
"""
from __future__ import annotations

import base64
import copy
import http.client
import json
import math
from pathlib import Path
import re
import threading

from g_extract1_contract import canonical, digest

VERSION = 'g-cal1.ollama-live-transport.v2'
RECEIPT_SCHEMA = 'g-cal1.ollama-live-transport.receipt.v1'
METADATA_SCHEMA = 'g-cal1.ollama-live-transport.metadata.v2'
COMPONENT_SCHEMA = 'g-cal1.ollama-model-components.v1'
COMPONENT_ROLES = ('model', 'projector')
METADATA_LAYER_TYPES = ('license', 'params', 'template', 'system', 'messages')
HOST, PORT = '127.0.0.1', 11434
ENDPOINT = 'http://127.0.0.1:11434'
GENERATE_PATH = '/api/generate'
# Frozen non-sampling controls; every other generation key is a provider option.
REQUIRED_CONTROLS = {'stream': False, 'think': False, 'fallback': False, 'retry_limit': 0,
                     'repair_calls': 0, 'fresh_session_per_call': True}
# Exact request keys: no context/messages/images/raw/template/format/keep_alive.
REQUEST_KEYS = {'model', 'system', 'prompt', 'stream', 'think', 'options'}
# Only these provider done_reason values carry a usable truncation signal.
DONE_REASONS = {'stop': False, 'length': True}
HEX64 = re.compile('[0-9a-f]{64}')
BLOB_REFERENCE = re.compile('sha256-([0-9a-f]{64})')
IO_STDLIB = 'STDLIB_HTTP_CLIENT_LOOPBACK'
IO_INJECTED = 'INJECTED_CONNECTION_FACTORY_OFFLINE_TEST_ONLY'
TRANSPORT_ERRORS = (OSError, http.client.HTTPException)
READ_CHUNK = 65536


class TransportContractError(RuntimeError):
    """Caller or binding violation; never a provider receipt. Disables the adapter."""


class MetadataVerificationError(RuntimeError):
    """Provider metadata did not match the frozen binding. Disables the adapter."""


def _check(condition, detail, error=TransportContractError):
    if not condition:
        raise error(detail)


def _strict_json(raw):
    """UTF-8 JSON without duplicate keys or non-finite numbers."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result

    def finite(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('non-finite number')
        return value

    def constant(name):
        raise ValueError('non-finite constant:' + name)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_float=finite, parse_constant=constant)


def _b64(raw):
    return base64.b64encode(raw).decode('ascii')


def _plain(value):
    """Deep plain-JSON copy; rejects objects that cannot be canonically serialized."""
    return json.loads(canonical(value).decode('utf-8'))


def _integer(value):
    return type(value) is int


def _components(values, primary):
    _check(type(values) is list and 1 <= len(values) <= 2, 'explicit component list')
    for item in values:
        _check(type(item) is dict and set(item) == {'role', 'sha256'} and
               type(item['role']) is str and item['role'] in COMPONENT_ROLES and
               type(item['sha256']) is str and HEX64.fullmatch(item['sha256']), 'component schema')
    roles = [item['role'] for item in values]
    _check(roles in (['model'], ['model', 'projector']) and
           len({item['sha256'] for item in values}) == len(values), 'component order/duplicates')
    _check(values[0]['sha256'] == primary, 'primary component contradicts blob_sha256')
    return values


def manifest_components(raw, model):
    """Read-only role proof from exact digest-bound manifest bytes, not FROM position."""
    _check(type(raw) is bytes and digest(raw) == model['manifest_digest'], 'local manifest digest mismatch')
    try:
        manifest = _strict_json(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise TransportContractError('malformed local manifest') from exc
    _check(type(manifest) is dict and type(manifest.get('schemaVersion')) is int and
           manifest['schemaVersion'] == 2 and
           manifest.get('mediaType') == 'application/vnd.docker.distribution.manifest.v2+json', 'manifest schema')
    config = manifest.get('config')
    _check(type(config) is dict and config.get('mediaType') == 'application/vnd.docker.container.image.v1+json' and
           type(config.get('digest')) is str and re.fullmatch('sha256:[0-9a-f]{64}', config['digest']) and
           _integer(config.get('size')) and config['size'] >= 0, 'manifest config')
    layers = manifest.get('layers')
    _check(type(layers) is list and layers, 'manifest layers')
    found = {}
    for layer in layers:
        _check(type(layer) is dict and type(layer.get('mediaType')) is str and
               type(layer.get('digest')) is str and re.fullmatch('sha256:[0-9a-f]{64}', layer['digest']) and
               _integer(layer.get('size')) and layer['size'] >= 0, 'manifest layer schema')
        kind = layer['mediaType'].removeprefix('application/vnd.ollama.image.')
        _check(layer['mediaType'] == 'application/vnd.ollama.image.' + kind and
               kind in (*COMPONENT_ROLES, *METADATA_LAYER_TYPES), 'unsupported manifest layer role')
        if kind in COMPONENT_ROLES:
            _check(kind not in found, 'duplicate manifest component role')
            found[kind] = layer['digest'][7:]
    result = [dict(role=role, sha256=found[role]) for role in COMPONENT_ROLES if role in found]
    return _components(result, model['blob_sha256'])


def component_provider_binding(binding, manifest_bytes):
    """Prospective binding only; never publishes a freeze or grants authority."""
    result = _frozen_binding(binding)
    _check(type(manifest_bytes) is dict and set(manifest_bytes) == {m['model'] for m in result['models']},
           'manifest evidence coverage')
    for model in result['models']:
        model['components'] = manifest_components(manifest_bytes[model['model']], model)
    return _frozen_binding(result)


def _manifest_path(name):
    # This version supports the fixed default local Ollama registry, not ambient
    # OLLAMA_MODELS overrides or arbitrary caller-selected component evidence.
    _check(type(name) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*', name),
           'unsupported local manifest model name')
    library, tag = name.split(':')
    return Path.home() / '.ollama/models/manifests/registry.ollama.ai/library' / library / tag


def _from_references(modelfile):
    _check(type(modelfile) is str, 'show modelfile')
    references = []
    for line in modelfile.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if re.match(r'(?i)^FROM(?:\s|$)', stripped):
            # One complete blob path per directive; comments/extra tokens,
            # generic model names and malformed/truncated hashes are not proof.
            match = re.fullmatch(r'FROM\s+(?:[^\s"\x00]+[/\\])?sha256-([0-9a-f]{64})', stripped)
            _check(match is not None, 'malformed FROM blob reference')
            references.append(match.group(1))
    _check(references and len(references) == len(set(references)), 'missing/duplicate FROM component')
    return references


def _frozen_binding(binding):
    binding = _plain(binding)
    _check(type(binding) is dict and binding.get('provider') == 'ollama', 'provider binding must be Ollama')
    _check(type(binding.get('provider_version')) is str and binding['provider_version'], 'provider_version')
    _check(binding.get('internal_option_honoring_attested_by_provider') is not True,
           'internal option honoring cannot be attested by this adapter')
    models = binding.get('models')
    _check(type(models) is list and models, 'models')
    names = []
    for model in models:
        _check(type(model) is dict and type(model.get('model')) is str and model['model'] and
               type(model.get('manifest_digest')) is str and HEX64.fullmatch(model['manifest_digest']) and
               type(model.get('blob_sha256')) is str and HEX64.fullmatch(model['blob_sha256']), 'model identity')
        names.append(model['model'])
        if 'components' in model:
            _components(model['components'], model['blob_sha256'])
    _check(len(set(names)) == len(names), 'duplicate model identity')
    config = binding.get('generation_configuration')
    _check(type(config) is dict, 'generation_configuration')
    for key, value in REQUIRED_CONTROLS.items():
        _check(key in config and canonical(config[key]) == canonical(value), 'frozen control ' + key)
    _check('seed' not in config, 'seed is per scheduled call')
    for key, value in config.items():
        if key not in REQUIRED_CONTROLS:
            _check(type(value) in (int, float), 'sampling option type ' + key)
    return binding


def _frozen_schedule(schedule, binding):
    rows = _plain(schedule)
    _check(type(rows) is list and rows, 'schedule')
    models = {m['model'] for m in binding['models']}
    config = canonical(binding['generation_configuration'])
    seen = set()
    for index, row in enumerate(rows, 1):
        _check(type(row) is dict and row.get('schedule_position') == index and _integer(row['schedule_position']),
               'schedule position')
        _check(type(row.get('call_id')) is str and row['call_id'] not in seen, 'call_id')
        seen.add(row['call_id'])
        _check(_integer(row.get('seed')), 'seed')
        _check(row.get('model') in models and row.get('provider_version') == binding['provider_version'],
               'row model/provider identity')
        _check(canonical(row.get('generation_configuration')) == config, 'row generation configuration')
        _check(type(row.get('request_sha256')) is str and HEX64.fullmatch(row['request_sha256']), 'request_sha256')
    return rows


class OllamaLiveTransport:
    """One-shot, schedule-ordered live transport. Never retries or repairs."""

    synthetic_only = False

    def __init__(self, provider_binding, schedule, *, timeout_seconds, start_position=1, connection_factory=None):
        # No provider contact here: only frozen inputs are validated and copied.
        _check(type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds) and timeout_seconds > 0,
               'explicit positive timeout_seconds required')
        _check(connection_factory is None or callable(connection_factory), 'connection factory')
        self._binding = _frozen_binding(provider_binding)
        self._binding_bytes = canonical(self._binding)
        self._schedule = _frozen_schedule(schedule, self._binding)
        self._schedule_bytes = canonical(self._schedule)
        # A resumed run supplies its verified next position; the adapter cannot
        # itself prove that earlier positions were attempted, and never revisits them.
        _check(_integer(start_position) and 1 <= start_position <= len(self._schedule), 'start_position')
        self._start = start_position
        self._models = {m['model']: m for m in self._binding['models']}
        self._options = {k: v for k, v in self._binding['generation_configuration'].items()
                         if k not in REQUIRED_CONTROLS}
        self._timeout = timeout_seconds
        self._factory = connection_factory
        self._io = IO_STDLIB if connection_factory is None else IO_INJECTED
        self._gate = threading.Lock()
        self._metadata = None
        self._metadata_sha256 = None
        self._next = start_position - 1
        self._consumed = set()
        self._connections = 0
        self._disabled = None

    # -- state -----------------------------------------------------------
    @property
    def disabled(self):
        return self._disabled

    @property
    def consumed_calls(self):
        return len(self._consumed)

    def _disable(self, reason):
        if self._disabled is None:
            self._disabled = reason

    def _enter(self):
        # Parallel use is a contract violation, never a queue.
        if not self._gate.acquire(blocking=False):
            self._disable('parallel use')
            raise TransportContractError('parallel use forbidden')

    def _frozen_inputs_unchanged(self):
        _check(canonical(self._binding) == self._binding_bytes and canonical(self._schedule) == self._schedule_bytes,
               'frozen binding/schedule drift')

    # -- HTTP --------------------------------------------------------------
    def _connect(self):
        """A fresh connection per exchange; stdlib http.client uses no proxy and follows no redirect."""
        self._connections += 1
        if self._factory is None:
            connection = http.client.HTTPConnection(HOST, PORT, timeout=self._timeout)
        else:
            connection = self._factory(HOST, PORT, self._timeout)
        return connection, self._connections

    def _connection_evidence(self, ordinal):
        return {'fresh_connection': True, 'connection_ordinal': ordinal, 'io': self._io,
                'host': HOST, 'port': PORT, 'timeout_seconds': self._timeout,
                'timeout_scope': 'per blocking socket operation', 'proxy': 'none',
                'redirects': 'not_followed', 'retries': 0}

    @staticmethod
    def _http_evidence(status, reason, headers, body):
        return {'http_status': status, 'http_reason': reason,
                'response_headers': [[str(k), str(v)] for k, v in headers],
                'response_body_b64': _b64(body), 'response_body_sha256': digest(body),
                'response_body_length': len(body),
                'response_body_scope': 'entity body after HTTP/1.1 transfer framing; no content decoding'}

    def _metadata_exchange(self, method, path, body=None):
        connection, ordinal = self._connect()
        try:
            headers = {'Connection': 'close'}
            if body is not None:
                headers['Content-Type'] = 'application/json'
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            status, reason, headers = response.status, response.reason, response.getheaders()
            raw = response.read()
        finally:
            try:
                connection.close()
            except Exception:
                pass
        observation = {'method': method, 'path': path, 'connection': self._connection_evidence(ordinal),
                       'request_body_b64': None if body is None else _b64(body),
                       **self._http_evidence(status, reason, headers, raw)}
        _check(type(status) is int and status == 200, method + ' ' + path + ' HTTP status', MetadataVerificationError)
        return _strict_json(raw), observation

    # -- metadata ------------------------------------------------------------
    def verify_metadata(self):
        """Explicit pre-generation provider/model verification. Exactly once.

        Checks: GET /api/version equals the frozen provider_version; GET /api/tags
        lists each frozen model exactly once with the frozen manifest digest; and
        POST /api/show reports a modelfile whose FROM blob reference is exactly the
        frozen blob sha256. The blob content itself is NOT rehashed.
        """
        self._enter()
        try:
            _check(self._disabled is None, 'transport disabled:' + str(self._disabled))
            _check(self._metadata is None, 'metadata already verified')
            self._frozen_inputs_unchanged()
            try:
                receipts = self._verify_metadata()
            except BaseException as exc:
                self._disable('metadata verification failed')
                if isinstance(exc, Exception) and not isinstance(exc, MetadataVerificationError):
                    raise MetadataVerificationError(type(exc).__name__) from exc
                raise
            self._metadata = receipts
            self._metadata_sha256 = digest(canonical(receipts))
            return copy.deepcopy(receipts)
        finally:
            self._gate.release()

    def _verify_metadata(self):
        fail = MetadataVerificationError
        observations = []
        version, observation = self._metadata_exchange('GET', '/api/version')
        observations.append(observation)
        _check(type(version) is dict and type(version.get('version')) is str, 'version envelope', fail)
        _check(version['version'] == self._binding['provider_version'], 'provider version mismatch', fail)
        tags, observation = self._metadata_exchange('GET', '/api/tags')
        observations.append(observation)
        _check(type(tags) is dict and type(tags.get('models')) is list and
               all(type(x) is dict for x in tags['models']), 'tags envelope', fail)
        verified = []
        for name, model in self._models.items():
            entries = [x for x in tags['models'] if x.get('name') == name or x.get('model') == name]
            _check(len(entries) == 1, 'model not installed exactly once:' + name, fail)
            entry = entries[0]
            _check(entry.get('name') == name and entry.get('model', name) == name, 'model name:' + name, fail)
            _check(entry.get('digest') == model['manifest_digest'], 'manifest digest mismatch:' + name, fail)
            show, observation = self._metadata_exchange('POST', '/api/show', canonical({'model': name}))
            observations.append(observation)
            _check(type(show) is dict and type(show.get('modelfile')) is str, 'show envelope:' + name, fail)
            try:
                references = _from_references(show['modelfile'])
                component_evidence = None
                if 'components' in model:
                    path = _manifest_path(name)
                    raw_manifest = path.read_bytes()
                    components = manifest_components(raw_manifest, model)
                    _check(components == model['components'], 'manifest component roles/identities mismatch')
                    expected = {item['sha256'] for item in components}
                    _check(set(references) == expected and len(references) == len(components),
                           'show component set mismatch')
                    component_evidence = dict(schema_version=COMPONENT_SCHEMA, components=components,
                        role_source='digest-bound local manifest layer mediaType, never FROM order',
                        manifest_path=str(path), manifest_sha256=digest(raw_manifest),
                        manifest_body_b64=_b64(raw_manifest), FROM_blob_references=references,
                        FROM_order_semantics='unordered exact set; binding order model then projector',
                        blob_content_rehashed=False)
                else:
                    # Historical single-component inputs retain their narrower
                    # meaning; they never gain implied projector authority.
                    _check(references == [model['blob_sha256']], 'legacy single-component blob mismatch')
            except (TransportContractError, OSError) as exc:
                raise MetadataVerificationError('model components:' + name + ':' + str(exc)) from exc
            identity = {'model': name, 'manifest_digest': entry['digest'], 'blob_sha256': model['blob_sha256']}
            if component_evidence is not None:
                identity['component_evidence'] = component_evidence
            verified.append(identity)
        return {'schema_version': METADATA_SCHEMA, 'transport_version': VERSION, 'endpoint': ENDPOINT,
                'provider': 'ollama', 'provider_version': version['version'],
                # Frozen entries echoed after their provider-observable fields matched;
                # non-observable fields such as tier are not provider-attested.
                'models': copy.deepcopy(self._binding['models']),
                'generation_configuration': copy.deepcopy(self._binding['generation_configuration']),
                'verified_observable_identity': verified,
                'verification_sources': {
                    'provider_version': 'GET /api/version version field',
                    'manifest_digest': 'GET /api/tags digest field for the exact model name',
                    'blob_sha256': 'POST /api/show exact FROM blob set; legacy input requires single FROM',
                    'component_roles': 'explicit components require exact digest-bound local manifest layers',
                    'blob_content_rehashed': False,
                    'generation_configuration': 'frozen binding only; not provider-reported'},
                'internal_option_honoring_attested_by_provider': False,
                'internal_option_honoring': 'UNATTESTED',
                'io': self._io, 'observations': observations}

    # -- generation ----------------------------------------------------------
    def __call__(self, request_bytes, schedule_row):
        self._enter()
        try:
            try:
                _check(self._disabled is None, 'transport disabled:' + str(self._disabled))
                _check(self._metadata is not None, 'explicit metadata verification must precede generation')
                self._frozen_inputs_unchanged()
                row = self._bind(request_bytes, schedule_row)
            except BaseException:
                self._disable('call contract violation')
                raise
            # The attempt is consumed before the first POST byte; nothing re-enables it.
            self._next += 1
            self._consumed.add(row['call_id'])
            return self._generate(request_bytes, row)
        finally:
            self._gate.release()

    def _bind(self, request_bytes, schedule_row):
        _check(self._next < len(self._schedule), 'schedule exhausted')
        row = self._schedule[self._next]
        _check(type(schedule_row) is dict and canonical(schedule_row) == canonical(row),
               'schedule row does not equal the next frozen position')
        _check(row['call_id'] not in self._consumed, 'repeated call')
        _check(type(request_bytes) is bytes, 'request must be original wire bytes')
        _check(digest(request_bytes) == row['request_sha256'], 'request hash mismatch')
        try:
            request = _strict_json(request_bytes)
        except (ValueError, UnicodeDecodeError, RecursionError) as exc:
            raise TransportContractError('request bytes are not strict JSON') from exc
        _check(type(request) is dict and set(request) == REQUEST_KEYS, 'request keys/history')
        _check(request['model'] == row['model'] and row['model'] in self._models, 'request model')
        _check(type(request['system']) is str and type(request['prompt']) is str, 'request text fields')
        _check(request['stream'] is False and request['think'] is False, 'stream/think')
        expected = dict(self._options, seed=row['seed'])
        _check(type(request['options']) is dict and canonical(request['options']) == canonical(expected),
               'request options/seed differ from frozen configuration')
        return copy.deepcopy(row)

    def _base_receipt(self, request_bytes, row, ordinal, transmission):
        return {'schema_version': RECEIPT_SCHEMA, 'transport_version': VERSION, 'synthetic_only': False,
                'call_id': row['call_id'], 'request_sha256': row['request_sha256'],
                'schedule_position': row['schedule_position'], 'adapter_start_position': self._start,
                'seed': row['seed'], 'model': row['model'],
                'provider': 'ollama', 'provider_version_verified': self._metadata['provider_version'],
                'metadata_receipts_sha256': self._metadata_sha256,
                'endpoint': ENDPOINT + GENERATE_PATH, 'method': 'POST',
                'request_body_b64': _b64(request_bytes), 'request_body_length': len(request_bytes),
                'post_transmission': transmission,
                'connection': None if ordinal is None else self._connection_evidence(ordinal),
                'internal_option_honoring': 'UNATTESTED'}

    @staticmethod
    def _failure(receipt, kind, reason, **evidence):
        return {'failure': kind, 'receipt': dict(receipt, failure_kind=kind, failure_reason=reason, **evidence)}

    def _generate(self, request_bytes, row):
        ordinal, transmission, stage = None, 'NOT_STARTED', 'connect'
        connection, observed, chunks = None, {}, []
        try:
            connection, ordinal = self._connect()
            connection.connect()
            stage, transmission = 'send', 'STARTED'
            connection.request('POST', GENERATE_PATH, body=request_bytes,
                               headers={'Content-Type': 'application/json', 'Connection': 'close'})
            stage, transmission = 'response', 'COMPLETED'
            response = connection.getresponse()
            # Only values http.client actually returned are recorded; nothing is filled in later.
            observed['status'], observed['reason'] = response.status, response.reason
            stage = 'response_headers'
            observed['headers'] = response.getheaders()
            stage = 'response_body_read'
            while True:
                # read1 performs at most one underlying socket read, so every chunk
                # already returned survives a later timeout/reset in `chunks`.
                chunk = response.read1(READ_CHUNK)
                if not chunk:
                    break
                chunks.append(chunk)
            remaining = getattr(response, 'length', None)
            if _integer(remaining) and remaining > 0:
                # http.client reports EOF before the declared Content-Length as b'', not an exception.
                receipt = self._base_receipt(request_bytes, row, ordinal, transmission)
                return self._interrupted(receipt, 'error', 'eof_before_declared_content_length', stage,
                                         observed, chunks, None, content_length_remaining=remaining)
        except TimeoutError as exc:
            receipt = self._base_receipt(request_bytes, row, ordinal, transmission)
            if observed:
                return self._interrupted(receipt, 'timeout', 'socket_timeout', stage, observed, chunks, exc)
            return self._failure(receipt, 'timeout', 'socket_timeout', failure_stage=stage,
                                 exception_type=type(exc).__name__)
        except TRANSPORT_ERRORS as exc:
            receipt = self._base_receipt(request_bytes, row, ordinal, transmission)
            if observed:
                return self._interrupted(receipt, 'error', 'transport_exception', stage, observed, chunks, exc)
            return self._failure(receipt, 'error', 'transport_exception', failure_stage=stage,
                                 exception_type=type(exc).__name__,
                                 errno=exc.errno if isinstance(exc, OSError) and _integer(exc.errno) else None)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
        receipt = self._base_receipt(request_bytes, row, ordinal, transmission)
        return self._classify(receipt, row, observed['status'], observed['reason'], observed['headers'],
                              b''.join(chunks))

    def _interrupted(self, receipt, kind, reason, stage, observed, chunks, exc, **detail):
        """Failure after getresponse() returned: exactly the HTTP evidence observed, flagged incomplete.

        The entity body is the concatenation of bytes returned by completed read1
        calls. An IncompleteRead.partial is preserved separately and losslessly:
        under read1 http.client may place chunk-framing bytes there, so it is not
        spliced into the entity body.
        """
        headers_observed = 'headers' in observed
        body_read_started = stage == 'response_body_read'
        evidence = {'http_status': observed['status'], 'http_reason': observed['reason']}
        if headers_observed:
            evidence['response_headers'] = [[str(k), str(v)] for k, v in observed['headers']]
        if body_read_started:
            evidence.update(self._http_evidence(observed['status'], observed['reason'], observed['headers'],
                                                b''.join(chunks)))
        evidence['response_capture'] = {
            'state': 'INTERRUPTED_INCOMPLETE', 'interrupted_stage': stage, 'status_observed': True,
            'headers_observed': headers_observed, 'body_read_started': body_read_started, 'body_complete': False,
            'body_read_calls_returning_bytes': len(chunks),
            'read_method': 'http.client HTTPResponse.read1 incremental; at most one socket read per call'}
        partial = getattr(exc, 'partial', None) if isinstance(exc, http.client.IncompleteRead) else None
        if type(partial) is bytes:
            expected = getattr(exc, 'expected', None)
            evidence.update(exception_partial_b64=_b64(partial), exception_partial_sha256=digest(partial),
                            exception_partial_length=len(partial),
                            exception_expected_more=expected if _integer(expected) else None)
        return self._failure(receipt, kind, reason, failure_stage=stage,
                             exception_type=None if exc is None else type(exc).__name__,
                             exception_message=None if exc is None else str(exc),
                             errno=exc.errno if isinstance(exc, OSError) and _integer(exc.errno) else None,
                             **detail, **evidence)

    def _classify(self, receipt, row, status, reason, headers, body):
        """Envelope classification. Never cleans, repairs or substitutes the response."""
        receipt = dict(receipt, **self._http_evidence(status, reason, headers, body))
        error = lambda why: self._failure(receipt, 'error', why)
        if type(status) is not int or status != 200:
            return error('http_status_not_200')
        encodings = [v.strip().lower() for k, v in headers if str(k).lower() == 'content-encoding']
        if any(x not in ('', 'identity') for x in encodings):
            return error('unsupported_content_encoding')
        try:
            envelope = _strict_json(body)
        except (ValueError, UnicodeDecodeError, RecursionError):
            return error('malformed_json')
        if type(envelope) is not dict:
            return error('non_object_root')
        if 'error' in envelope:
            return error('provider_error_envelope')
        if type(envelope.get('model')) is not str or envelope['model'] != row['model']:
            return error('model_identity_mismatch')
        if envelope.get('done') is not True:
            return error('envelope_not_done')
        provider_fields = {k: envelope[k] for k in ('model', 'created_at', 'done', 'done_reason', 'total_duration',
                                                    'load_duration', 'prompt_eval_count', 'prompt_eval_duration',
                                                    'eval_count', 'eval_duration')
                           if k in envelope and type(envelope[k]) in (str, int, bool)}
        receipt['provider_fields'] = provider_fields
        if envelope.get('response') is None:
            return self._failure(receipt, 'missing', 'response_field_absent_or_null')
        response = envelope['response']
        if type(response) is not str:
            return error('response_not_string')
        try:
            response.encode('utf-8')
        except UnicodeEncodeError:
            return error('response_not_utf8_encodable')
        thinking = envelope.get('thinking')
        if thinking is not None and (type(thinking) is not str or thinking != ''):
            # think=false was frozen; returned reasoning is never used as the answer.
            return error('thinking_returned_despite_think_false')
        done_reason = envelope.get('done_reason')
        if type(done_reason) is not str or done_reason not in DONE_REASONS:
            return error('truncation_signal_unusable')
        truncated = DONE_REASONS[done_reason]
        receipt['truncation'] = {'basis': 'provider done_reason', 'done_reason': done_reason,
                                 'provider_truncated': truncated}
        return {'raw_output': response, 'provider_truncated': truncated, 'receipt': receipt}
