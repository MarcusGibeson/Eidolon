"""URL layout alone neither disqualifies surveys nor verifies their claims."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'conscious_agent'))
from research_source_independence import source_evidence_role

for path in ('/blog/survey-results', '/articles/survey-results', '/survey-results'):
    role = source_evidence_role({'public_url': 'https://example.com' + path})
    assert role['evidence_role'] == 'unclassified_public_source'
    assert role['supportable_dimensions'] == []
    assert role['quality_cap'] == 0.3
for path in ('/blog/how-to-track-brand-deals-creator-2026', '/how-to-manage-invoices',
             '/blog/best-tools', '/blog/customer-guide', '/blog/profitable-ideas'):
    role = source_evidence_role({'public_url': 'https://example.com' + path})
    assert role['evidence_role'] == 'promotional_summary'
    assert role['supportable_dimensions'] == []
assert source_evidence_role({'public_url':'https://example.com/blog/survey-results',
    'source_kind':'primary_official'})['evidence_role'] == 'first_party_product_claim'
assert source_evidence_role({'public_url':'https://example.com/blog/pricing'})['evidence_role'] == 'pricing_or_free_tier'
print(json.dumps({'ok':True,'cases':10}))
