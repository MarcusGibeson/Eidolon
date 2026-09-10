"""Offline admission and native-session tests for model-assessed inferences."""
import copy
import hashlib
import json
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'conscious_agent'), str(root)]
from research_claim_assessment import assess_source_claims, model_assessed_conclusion, passage_options

checks = []
def check(value, name):
    assert value, name
    checks.append(name)

claim = 'Some creators report difficulty tracking sponsorship payments.'
docs = [{'citation_id': 'a', 'excerpt': 'Creators surveyed reported difficulty tracking sponsorship payments and invoice deadlines.'},
        {'citation_id': 'b', 'excerpt': 'As content creators, we lose track of brand deal invoices and need help tracking outstanding sponsorship payments.'}]
sources = [{'citation_id': cid, 'public_url': 'https://' + host + '/study', 'source_kind': 'unknown', 'stance': 'unknown', 'relevance_score': 0.9}
           for cid, host in [('a', 'one.example'), ('b', 'two.example')]]
payload = {'findings': [{'title': 'Payment tracking', 'summary': claim, 'citation_ids': ['a', 'b']}],
           'source_assessments': [{'citation_id': d['citation_id'], 'claim': claim, 'dimension': 'demand',
                                   'evidence_kind': 'customer_experience', 'assessment': 'supports',
                                   'passage_id': passage_options(d['citation_id'], d['excerpt'])[0]['passage_id']} for d in docs]}
def run(p=None, s=None, d=None):
    p, s, d = p or payload, s or sources, d or docs
    assessment = assess_source_claims(p, documents=d, citations=s)
    return model_assessed_conclusion(p, assessment_summary=assessment, citations=s, dimension='demand')

result = run()
p = copy.deepcopy(payload)
for row in p['source_assessments']:
    del row['dimension']
bound = assess_source_claims(p, documents=docs, citations=sources, required_dimension='demand')
check(model_assessed_conclusion(p, assessment_summary=bound, citations=sources, dimension='demand')['ok'], 'plan_supplies_omitted_dimension')
p['source_assessments'][0]['evidence_kind'] = 'vendor_offering'
bound = assess_source_claims(p, documents=docs, citations=sources, required_dimension='demand')
check(not model_assessed_conclusion(p, assessment_summary=bound, citations=sources, dimension='demand')['ok'], 'plan_scope_does_not_promote_vendor_evidence')
check(result['ok'], 'two_grounded_lineages_admit_tentative_inference')
check(not result['verified_findings'] and not result['strongest_opportunity_admitted'], 'no_verified_fact_or_winner')
check('not verified fact' in result['rendered_answer'] and 'Freshness is not established' in result['rendered_answer'], 'visible_model_and_currency_limits')
check(all(s['stance'] == 'unknown' for s in sources), 'native_metadata_unchanged')
for name, change in [
    ('mismatched_claim', {'claim': 'Everyone will pay for this product'}),
    ('wrong_dimension', {'dimension': 'competition'}),
    ('vendor_offering', {'evidence_kind': 'vendor_offering'}),
    ('invented_passage', {'passage_id': 'fake'}),
    ('contradiction', {'assessment': 'refutes'}),
    ('unclear', {'assessment': 'unclear'}),
]:
    p = copy.deepcopy(payload)
    p['source_assessments'][1].update(change)
    check(not run(p)['ok'], name)
same_host = copy.deepcopy(sources)
same_host[1]['public_url'] = 'https://one.example/other'
check(not run(s=same_host)['ok'], 'same_publisher_rejected')
stale = copy.deepcopy(sources)
stale[1]['freshness'] = 'stale'
check(not run(s=stale)['ok'], 'known_stale_rejected')
irrelevant = copy.deepcopy(sources)
irrelevant[1]['relevance_score'] = 0.1
check(not run(s=irrelevant)['ok'], 'low_relevance_rejected')
copied = copy.deepcopy(docs)
copied[1]['excerpt'] = copied[0]['excerpt']
p = copy.deepcopy(payload)
p['source_assessments'][1]['passage_id'] = passage_options('b', copied[1]['excerpt'])[0]['passage_id']
check(not run(p, d=copied)['ok'], 'copied_passage_across_hosts_rejected')
derivative = copy.deepcopy(sources)
for s in derivative:
    s['lineage_origin_digest'] = 'a' * 64
check(not run(s=derivative)['ok'], 'existing_derivative_lineage_preserved')
p = copy.deepcopy(payload)
p['source_assessments'].append({**p['source_assessments'][0], 'assessment': 'refutes'})
check(not run(p)['ok'], 'adverse_assessment_not_outvoted')

extra_docs = copy.deepcopy(docs)
extra_sources = copy.deepcopy(sources)
extra_docs.append({**docs[0], 'citation_id': 'c'})
extra_sources.append({**sources[0], 'citation_id': 'c'})
p = copy.deepcopy(payload)
p['source_assessments'].append({**p['source_assessments'][0], 'citation_id': 'c',
                              'passage_id': passage_options('c', extra_docs[-1]['excerpt'])[0]['passage_id'],
                              'assessment': 'unclear'})
outcome = run(p, d=extra_docs, s=extra_sources)
check(outcome['ok'] and any('not counted as support' in x for x in outcome['limitations']),
      'uncited_inconclusive_source_is_not_a_contradiction')
p['source_assessments'][-1]['assessment'] = 'refutes'
check(not run(p, d=extra_docs, s=extra_sources)['ok'], 'uncited_refutation_still_blocks')

fixture = runpy.run_path(str(root / 'tools/v2730_9_4_research_trial_repair_tests.py'))
class Native(fixture['NativeAdapterProbe']):
    def __init__(self):
        super().__init__()
        self.receipts = []
        self.synthesizer = self.assess
    def search(self, query, *, limit, timeout_seconds):
        return [{'url': s['public_url'], 'source_kind': 'unknown'} for s in sources][:limit]
    def _fetch(self, url, *, max_bytes, timeout_seconds):
        text = docs[0 if 'one.example' in url else 1]['excerpt']
        body = text.encode()
        return {'body': body, 'content_type': 'text/html', 'final_url': url, 'public_url': url,
                'redirect_count': 0, 'observed_bytes': len(body), 'content_digest': hashlib.sha256(body).hexdigest()}
    def observe(self, *args, **kwargs):
        row = super().observe(*args, **kwargs)
        self.receipts.append(dict(row))
        return row
    def assess(self, prompt):
        documents = json.loads(prompt.split('UNTRUSTED PUBLIC DOCUMENTS:\n')[1])
        return {'findings': [{'title': 'Payment tracking', 'summary': claim,
                              'citation_ids': [d['citation_id'] for d in documents]}],
                'source_assessments': [{'citation_id': d['citation_id'], 'claim': claim, 'dimension': 'demand',
                                        'evidence_kind': 'customer_experience', 'assessment': 'supports',
                                        'passage_id': d['passages'][0]['passage_id']} for d in documents]}

store = fixture['store']
created = store.create_session('automatic-create', objective=fixture['objective'], budget=fixture['budget'])['result']
auth = store.authorize_session('automatic-authorize', session_id=created['session_id'], session_digest=created['session_digest'], public_query_confirmed=True)['result']
adapter = Native()
with patch('model_training.training_capture_adapters.capture_research_synthesis', return_value={'status': 'fixture_capture'}) as capture:
    executed = store.execute_session('automatic-execute', session_id=created['session_id'], authorization_digest=auth['authorization_digest'], adapter=adapter, capture_training_evidence=True)
    check(capture.call_count == 1 and capture.call_args.kwargs['validation']['passed'] is False,
          'model_assessment_not_a_verified_training_success')
report = executed['result']['report']
check(report['synthesis_status'] == 'research_model_assessed_inference', 'native_session_admits_assessed_inference')
check(report['status'] == 'research_report_ready' and not report['verified_findings'], 'ready_is_labeled_inference_not_verification')
check(all(r['stance'] == 'unknown' for r in adapter.receipts), 'native_signed_receipts_unchanged')
check(report['provider_request_count'] == 1, 'one_counted_synthesis_no_extra_provider')
check(not adapter._transient_documents, 'transient_excerpts_cleared')
check(all(d['excerpt'] not in json.dumps(report) for d in docs), 'raw_passages_not_persisted')
from conversational_research_actions import _research_report_message
check('Model-assessed inference' in _research_report_message(created, report), 'operator_sees_assessment_label')
print(json.dumps({'ok': True, 'passed': len(checks), 'checks': checks}))
