"""Offline title-only page regression through normal research execution."""
import hashlib
import json
from pathlib import Path
import runpy
import tempfile

fixtures = runpy.run_path(str(Path(__file__).with_name('research_batch_selection_tests.py')))
from conversational_research_actions import _research_report_message

class ShellAdapter(fixtures['Adapter']):
    def _fetch(self, url, **kwargs):
        body = b'<html><title>Reddit</title><script>private application state</script></html>'
        return {'body': body, 'final_url': url, 'public_url': url, 'observed_bytes': len(body),
                'redirect_count': 0, 'content_digest': hashlib.sha256(body).hexdigest()}

class MixedAdapter(ShellAdapter):
    def _fetch(self, url, **kwargs):
        if 'source1.example.com' in url:
            return super()._fetch(url, **kwargs)
        return fixtures['Adapter']._fetch(self, url, **kwargs)

class PlanBoundAdapter(MixedAdapter):
    def observe(self, candidate, **kwargs):
        assert candidate.get('evidence_dimension') == 'demand'
        candidate = dict(candidate, _evidence_terms=['content', 'creators', 'survey'])
        return super().observe(candidate, **kwargs)

with tempfile.TemporaryDirectory() as td:
    store = fixtures['BoundedResearchSessionStore'](td)
    result = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')
    session = result['result']
    auth = store.authorize_session('authorize', session_id=session['session_id'], session_digest=session['session_digest'], public_query_confirmed=True)
    adapter = ShellAdapter()
    result = store.execute_session('execute', session_id=session['session_id'], authorization_digest=auth['result']['authorization_digest'], adapter=adapter)
    assert not result['ok']
    assert result['result']['session']['observed_page_count'] == 0
    assert result['result']['session']['evidence_count'] == 0
    assert result['result']['session']['source_failure_count'] > 0
    assert not adapter._transient_documents

with tempfile.TemporaryDirectory() as td:
    store = fixtures['BoundedResearchSessionStore'](td)
    session = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')['result']
    auth = store.authorize_session('authorize', session_id=session['session_id'], session_digest=session['session_digest'], public_query_confirmed=True)
    result = store.execute_session('execute', session_id=session['session_id'], authorization_digest=auth['result']['authorization_digest'], adapter=PlanBoundAdapter())
    assert result['ok']
    assert result['result']['report']['readable_content_failure_count'] == 3
    assert result['result']['session']['observed_page_count'] > 0

message = _research_report_message({'session_id': 'test'}, {'readable_content_failure_count': 2})
assert 'Readable-content gaps: 2' in message and 'not counted as evidence' in message
assert 'absent demand' in message
print(json.dumps({'ok': True, 'passed': 10, 'checks': ['shell_fails_safely','no_observed_pages','no_evidence_items',
    'failure_accounted','no_transient_evidence','mixed_session_continues','gap_count_in_real_report','readable_pages_retained',
    'readable_gap_rendered','no_absence_inference']}))
