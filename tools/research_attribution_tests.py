"""Offline original-source traversal and conservative independence regression."""
import copy
import hashlib
import runpy
import tempfile
from pathlib import Path

f = runpy.run_path(str(Path(__file__).with_name('research_batch_selection_tests.py')))
from governed_public_web_research_adapter import _VisibleTextParser, _public_url
from research_claim_assessment import assess_source_claims, model_assessed_conclusion

p = _VisibleTextParser()
p.feed('<nav><a href="/bad">survey</a></nav><p>Published in <a href="https://study.example/report">Journal</a>.</p><a href="/original">Original study</a><a href="#x">source</a>')
assert p.attribution_links == ['https://study.example/report', '/original']
for url in ('http://127.0.0.1/x', 'http://169.254.169.254/x', 'http://localhost/x', 'file:///tmp/x'):
    assert not _public_url(url)

class Linked(f['Adapter']):
    def _fetch(self, url, **kwargs):
        result = super()._fetch(url, **kwargs)
        body = result['body'] + b'<p>According to <a href="https://study.example/original">a survey</a>.</p>'
        result.update(body=body, observed_bytes=len(body), content_digest=hashlib.sha256(body).hexdigest())
        return result

with tempfile.TemporaryDirectory() as td:
    store = f['BoundedResearchSessionStore'](td)
    s = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')['result']
    auth = store.authorize_session('authorize', session_id=s['session_id'], session_digest=s['session_digest'], public_query_confirmed=True)
    adapter = Linked()
    r = store.execute_session('execute', session_id=s['session_id'], authorization_digest=auth['result']['authorization_digest'], adapter=adapter)
    assert r['ok'], r
    observed = [e[1] for e in adapter.events if e[0] == 'observe']
    assert observed.count('https://study.example/original') == 1, observed
    assert len(observed) <= 12
    assert len([e for e in adapter.events if e[0] == 'search']) == 4
    assert r['result']['report']['provider_request_count'] == 1
    assert r['result']['report']['source_assessment_summary']['observed_attribution_relationships']
    assert not adapter._transient_documents

class LateLinked(f['Adapter']):
    def _fetch(self, url, **kwargs):
        result = super()._fetch(url, **kwargs)
        suffix = b''
        if 'source3.' in url or 'source4.' in url:
            suffix = b'<a href="https://journal.example/study">Original study</a>'
        elif url == 'https://journal.example/study':
            suffix = b'<a href="https://origin.example/report">Survey</a>'
        body = result['body'] + suffix
        result.update(body=body, observed_bytes=len(body), content_digest=hashlib.sha256(body).hexdigest())
        return result

with tempfile.TemporaryDirectory() as td:
    store = f['BoundedResearchSessionStore'](td)
    s = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')['result']
    auth = store.authorize_session('authorize', session_id=s['session_id'], session_digest=s['session_digest'], public_query_confirmed=True)
    adapter = LateLinked()
    r = store.execute_session('execute', session_id=s['session_id'], authorization_digest=auth['result']['authorization_digest'], adapter=adapter)
    assert r['ok'], r
    observed = [e[1] for e in adapter.events if e[0] == 'observe']
    assert observed.count('https://journal.example/study') == 1, observed
    assert observed.count('https://origin.example/report') == 1, observed
    assert len(observed) <= 12
    assert r['result']['session']['candidate_count'] <= 12
    assert len([e for e in adapter.events if e[0] == 'search']) == 4

a = runpy.run_path(str(Path(__file__).with_name('research_automatic_assessment_tests.py')))
assessment = assess_source_claims(a['payload'], documents=a['docs'], citations=a['sources'])
assert model_assessed_conclusion(a['payload'], assessment_summary=assessment, citations=a['sources'], dimension='demand')['ok']
assessment['observed_attribution_relationships'] = [['a', 'b']]
assert not model_assessed_conclusion(a['payload'], assessment_summary=assessment, citations=a['sources'], dimension='demand')['ok']
print('attribution traversal, budget, privacy, and independence checks passed')
