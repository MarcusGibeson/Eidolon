"""Offline bounded batch execution and exact passage-selector acceptance tests."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'conscious_agent'), str(ROOT)]
sys.dont_write_bytecode = True
from research_claim_assessment import assess_source_claims, passage_options
from governed_public_web_research_adapter import GovernedPublicWebResearchAdapter
from bounded_autonomous_web_research import BoundedResearchSessionStore

checks = []
def check(value, name):
    assert value, name
    checks.append(name)

doc = {'citation_id': 'a', 'excerpt': 'Creators reported difficulty tracking invoices. However, they did not express willingness to pay.'}
source = {'citation_id': 'a', 'public_url': 'https://example.com/survey'}
row = {'citation_id': 'a', 'passage_index': 2, 'claim': 'Willingness to pay is not established.', 'assessment': 'unclear'}
def assess(r):
    return assess_source_claims({'source_assessments': [r]}, documents=[doc], citations=[source])

result = assess(row)
check(result['grounded_assessment_count'] == 1, 'numeric_selector_exactly_bound')
check(not result['assessments'][0]['semantic_support_verified'], 'selector_does_not_verify_claim')
for invalid in (0, -1, 3, True, '2', 1.5, None):
    check(assess({**row, 'passage_index': invalid})['grounded_assessment_count'] == 0, 'invalid_index_' + str(invalid))
for value, reason in ((0, 'below_one'), (4, 'above_source_range'), ('2', 'wrong_type')):
    check(assess({**row, 'passage_index': value})['selector_diagnostics'] == {reason: 1}, 'selector_diagnostic_' + reason)
empty = assess_source_claims({'source_assessments': [row]}, documents=[{**doc, 'excerpt': 'Too short.'}], citations=[source])
check(empty['selector_diagnostics'] == {'no_offered_passages': 1}, 'empty_source_diagnostic')
check(assess({**row, 'passage_id': 'invented'})['grounded_assessment_count'] == 0, 'conflicting_selectors_rejected')
check(assess({**row, 'evidence_quote': doc['excerpt']})['grounded_assessment_count'] == 0, 'mismatching_quote_rejected')
legacy = {**row, 'passage_id': passage_options('a', doc['excerpt'])[1]['passage_id']}
del legacy['passage_index']
check(assess(legacy)['grounded_assessment_count'] == 1, 'legacy_hash_preserved')

class Adapter(GovernedPublicWebResearchAdapter):
    def __init__(self):
        super().__init__(synthesizer=self.synthesize_fixture)
        self.events = []
        self.searches = 0

    def synthesize_fixture(self, prompt):
        documents = json.loads(prompt.split('UNTRUSTED PUBLIC DOCUMENTS:\n', 1)[1])
        document = next(d for d in documents if d.get('passages'))
        check(document['passages'][0]['passage_index'] == 1, 'normal_prompt_offers_local_indices')
        cid = document['citation_id']
        claim = 'Product availability does not establish customer demand.'
        return {'findings': [{'title': 'Demand unknown', 'summary': claim, 'citation_ids': [cid]}],
                'source_assessments': [{'citation_id': cid, 'passage_index': 1, 'claim': claim,
                                        'assessment': 'unclear', 'dimension': 'demand', 'evidence_kind': 'vendor_offering'}]}

    def search(self, query, *, limit, timeout_seconds):
        self.searches += 1
        self.events.append(('search', limit, query))
        return [{'url': 'https://source%d.example.com/page%d' % (self.searches, i)} for i in range(limit)]

    def observe(self, candidate, **kwargs):
        self.events.append(('observe', candidate['public_url']))
        return super().observe(candidate, **kwargs)

    def _fetch(self, url, **kwargs):
        body = b'<html><body>Brand deal tracking for content creators software offers invoice management. Product availability does not establish customer demand.</body></html>'
        return {'body': body, 'final_url': url, 'public_url': url, 'observed_bytes': len(body), 'redirect_count': 0,
                'content_digest': hashlib.sha256(body).hexdigest()}

with tempfile.TemporaryDirectory() as td:
    store = BoundedResearchSessionStore(td)
    created = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.',
                                   budget={'max_queries': 20, 'max_candidates': 32, 'max_observed_pages': 28})
    session = created['result']
    authorized = store.authorize_session('authorize', session_id=session['session_id'], session_digest=session['session_digest'], public_query_confirmed=True)
    adapter = Adapter()
    result = store.execute_session('execute', session_id=session['session_id'], authorization_digest=authorized['result']['authorization_digest'], adapter=adapter)
    assert result['ok'], result
    check(result['ok'], 'normal_authorized_cycle_completes')
    searches = [e for e in adapter.events if e[0] == 'search']
    check(len(searches) == 4, 'two_initial_and_two_gap_followups')
    check(all(e[1] <= 3 for e in searches), 'all_search_batches_bounded')
    third = [i for i,e in enumerate(adapter.events) if e[0] == 'search'][2]
    check(sum(e[0] == 'observe' for e in adapter.events[:third]) == 6, 'gap_review_after_six_not_full_budget')
    check(result['result']['session']['observed_page_count'] <= 12, 'weak_results_do_not_exhaust_page_budget')
    check(searches[2][2] != searches[3][2], 'distinct_followup_routes')
    check(not result['result']['report']['verified_findings'], 'vendor_pages_do_not_become_demand')
    check(result['result']['report']['source_assessment_summary']['grounded_assessment_count'] == 1,
          'numeric_choice_grounded_through_normal_session')

prompts = []
def prompt_fixture(prompt):
    prompts.append(prompt)
    docs = json.loads(prompt.split('UNTRUSTED PUBLIC DOCUMENTS:\n', 1)[1])
    check([d['citation_id'] for d in docs] == ['visible'], 'empty_source_not_offered_to_model')
    check(all(d['passages'] for d in docs), 'every_offered_source_selectable')
    return {'findings': [], 'source_assessments': []}

adapter = GovernedPublicWebResearchAdapter(synthesizer=prompt_fixture)
for cid, text in [('visible', 'Creators reported tracking problems, but not willingness to pay.'), ('empty', 'Too short.')]:
    adapter._transient_documents[cid] = {'citation_id': cid, 'title': cid, 'excerpt': text,
                                        'source_kind': 'unknown', 'public_url': 'https://example.com/' + cid}
decomposition = {'objective_shape': 'single_candidate_dimension', 'subquestions': [{'evidence_dimension': 'demand'}]}
result = adapter.synthesize(decomposition=decomposition, citations=[{'citation_id': c} for c in ('visible', 'empty')])
check(result['ok'] and result['source_assessment_summary']['omitted_passage_source_count'] == 1, 'omission_count_explicit')
check('but not willingness to pay.' in prompts[0], 'complete_qualification_in_prompt')
prompts.clear()
result = adapter.synthesize(decomposition=decomposition, citations=[{'citation_id': 'empty'}])
check(not result['ok'] and not result['provider_contacted'] and not prompts, 'all_empty_abstains_without_model')
print(json.dumps({'ok': True, 'passed': len(checks), 'checks': checks}))
