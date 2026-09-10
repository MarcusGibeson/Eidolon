"""Inconclusive reports explain receipts without admitting unsupported findings."""
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'conscious_agent'))
from conversational_research_actions import _research_report_message

report = {'status': 'research_evidence_incomplete', 'citations': [
    {'citation_id': 'web-a', 'public_url': 'https://example.com/survey', 'freshness': 'unknown'},
    {'citation_id': 'web-b', 'public_url': 'https://example.org/product', 'freshness': 'stale'}],
    'source_assessment_summary': {'assessments': [
        {'citation_id': 'web-a', 'textual_provenance_verified': True,
         'model_evidence_kind': 'survey_result', 'model_assessment': 'supports'},
        {'citation_id': 'web-b', 'textual_provenance_verified': True,
         'model_evidence_kind': 'vendor_offering', 'model_assessment': 'unclear'}]},
    'verified_findings': [], 'missing_evidence': [{'finding': 'Demand unverified'}]}
before = copy.deepcopy(report)
text = _research_report_message({'session_id': 'test'}, report)
assert 'survey material' in text and 'vendor offering' in text
assert 'currentness unverified' in text and 'recorded as stale' in text
assert 'not independently verified' in text and 'did not establish the proposed claim' in text
assert 'did not produce a trustworthy answer' in text
assert report == before
bad = copy.deepcopy(report)
bad['source_assessment_summary']['assessments'].extend([
    {'citation_id': 'absent', 'textual_provenance_verified': True, 'model_assessment': 'supports'},
    {'citation_id': 'web-a', 'textual_provenance_verified': True, 'model_assessment': 'supports'}])
assert _research_report_message({'session_id': 'test'}, bad) == text
bad['citations'][0]['public_url'] = 'http://127.0.0.1/private'
assert 'Model classification: survey material' not in _research_report_message({}, bad)
bad = copy.deepcopy(report)
bad['source_assessment_summary']['assessments'][0]['model_evidence_kind'] = 'SECRET'
assert 'SECRET' not in _research_report_message({}, bad)
bad['status'] = 'research_report_ready'
assert 'Source assessment review' not in _research_report_message({}, bad)
print(json.dumps({'ok': True, 'checks': 9}))
