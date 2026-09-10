"""Failed native observations stay attributable across report persistence."""
import hashlib
import json
import runpy
import tempfile
from pathlib import Path
f = runpy.run_path(str(Path(__file__).with_name('research_batch_selection_tests.py')))
from research_failure_receipts import sanitize_failures
from bounded_research_history import sanitize_report
from conversational_research_actions import _research_report_message
from governed_public_web_research_adapter import PublicWebResearchError

class Failed(f['Adapter']):
    def observe(self, candidate, **kwargs):
        if not self._transient_documents:
            return super().observe(candidate, **kwargs)
        raise PublicWebResearchError('public_web_connected_peer_unavailable')

with tempfile.TemporaryDirectory() as td:
    store = f['BoundedResearchSessionStore'](td)
    s = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')['result']
    a = store.authorize_session('authorize', session_id=s['session_id'], session_digest=s['session_digest'], public_query_confirmed=True)
    r = store.execute_session('execute', session_id=s['session_id'], authorization_digest=a['result']['authorization_digest'], adapter=Failed())
    report = r['result']['report']
    receipts = report['source_failure_receipts']
    assert len(receipts) == report['source_failure_count'] == 4
    assert report['collection_stop_reason'] == 'source_failure_budget_reached'
    saved = sanitize_report(report)
    assert saved['source_failure_receipts'] == receipts
    assert saved['collection_stop_reason'] == report['collection_stop_reason']
    message = _research_report_message({}, saved)
    assert 'source-failure limit reached' in message
    assert 'connection identity unavailable' in message
    assert receipts[0]['public_url'] in message

row = {'source_candidate_digest': 'a'*64, 'failure_code_digest': hashlib.sha256(b'SECRET exception').hexdigest(), 'public_url': 'https://example.com/page?token=SECRET#private'}
safe = sanitize_failures([row])[0]
assert safe['public_url'] == 'https://example.com/page' and safe['reason'] == 'source_fetch_failed'
assert 'SECRET' not in json.dumps(safe)
assert sanitize_failures([{**row, 'public_url':'http://127.0.0.1/private'}])[0]['public_url'] == ''
assert not sanitize_failures([{'public_url':'https://example.com'}])
print('failure receipt persistence, rendering and privacy checks passed')

class AllFailed(f['Adapter']):
    def observe(self, candidate, **kwargs):
        raise PublicWebResearchError('public_web_connected_peer_unavailable')

with tempfile.TemporaryDirectory() as td:
    store = f['BoundedResearchSessionStore'](td)
    s = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')['result']
    a = store.authorize_session('authorize', session_id=s['session_id'], session_digest=s['session_digest'], public_query_confirmed=True)
    r = store.execute_session('execute', session_id=s['session_id'], authorization_digest=a['result']['authorization_digest'], adapter=AllFailed())
    report = r['result']['report']
    assert r['result']['failure_code']
    assert report['verified_findings'] == []
    assert len(report['source_failure_receipts']) == 4
    saved = store._load()['reports'][s['session_id']]
    assert store._validate_report_storage(saved)[0]
    assert 'connection_identity_unavailable' in json.dumps(saved), saved
    assert 'source-failure limit reached' in _research_report_message({}, report)
print('all-sources-failed persisted diagnostics passed')
