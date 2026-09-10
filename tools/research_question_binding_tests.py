"""The normal synthesis handoff preserves the public question, not query drift."""
import copy
import json
from pathlib import Path
import runpy
import tempfile

f = runpy.run_path(str(Path(__file__).with_name('research_batch_selection_tests.py')))
from bounded_research_reasoning import decompose_research_objective
from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter

seen = []
def synth(prompt):
    seen.append(prompt)
    return {'findings': [], 'source_assessments': []}

adapter = GovernedPublicWebResearchAdapter(synthesizer=synth)
adapter._transient_documents['source'] = {
    'citation_id': 'source', 'title': 'Survey', 'source_kind': 'unknown',
    'excerpt': 'Creators earn money from sponsorships, which does not establish tracking software demand.',
    'query_terms': ['sponsorship', 'income', 'survey'], 'public_url': 'https://example.com/survey'}
plan = decompose_research_objective('Research Brand Deal Tracking for Content Creators demand.')
before = copy.deepcopy(plan)
result = adapter.synthesize(decomposition=plan, citations=[{'citation_id': 'source'}], retain_documents=True)
assert result['ok'] and len(seen) == 1
assert 'brand deal tracking content creators demand' in seen[0]
assert 'retrieval hints only' in seen[0]
assert 'not a broader market question' in seen[0]
assert plan == before

retry_prompts = []
def repair(prompt):
    retry_prompts.append(prompt)
    return 'invalid' if len(retry_prompts) == 1 else {'findings': [], 'source_assessments': []}
adapter.synthesizer = repair
result = adapter.synthesize(decomposition=plan, citations=[{'citation_id': 'source'}], retain_documents=True)
assert len(retry_prompts) == 2
assert all('brand deal tracking content creators demand' in p for p in retry_prompts)
adapter.synthesizer = synth

plan = decompose_research_objective('Research my wife Sarah Jenkins brand deal tracking demand.')
adapter.synthesize(decomposition=plan, citations=[{'citation_id': 'source'}], retain_documents=True)
assert 'sarah' not in seen[-1].lower() and 'jenkins' not in seen[-1].lower()

class Native(f['Adapter']):
    def __init__(self):
        super().__init__()
        self.synthesizer = synth

with tempfile.TemporaryDirectory() as td:
    store = f['BoundedResearchSessionStore'](td)
    session = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')['result']
    auth = store.authorize_session('authorize', session_id=session['session_id'], session_digest=session['session_digest'], public_query_confirmed=True)
    result = store.execute_session('execute', session_id=session['session_id'], authorization_digest=auth['result']['authorization_digest'], adapter=Native())
    assert result['ok']
    assert 'brand deal tracking content creators demand' in seen[-1]
    assert not result['result']['report']['verified_findings']
print(json.dumps({'ok': True, 'checks': 11}))
