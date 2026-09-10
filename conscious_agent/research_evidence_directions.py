"""Bounded retrieval hints from observed text; never claim-support evidence."""
import hashlib
import re
from collections.abc import Mapping

from bounded_research_reasoning import _demand_discovery_subject, sanitize_public_query
from research_claim_assessment import passage_options

# Fixed phrases prevent page instructions from becoming executable search text.
_DIRECTIONS = (
    ('payment_delays', r'\b(?:late payments?|unpaid|payment delays?|chasing payments?)\b', 'late payments customer survey'),
    ('missed_deadlines', r'\b(?:missed deadlines?|miss deadlines?|overdue deliverables?)\b', 'missed deadlines customer survey'),
    ('manual_records', r'\b(?:spreadsheets?|manual data entry|duplicate data entry)\b', 'manual records customer workflow survey'),
    ('invoice_management', r'\b(?:invoices?|invoicing)\b', 'invoicing customer problems survey'),
    ('follow_up', r'\bfollow[- ]ups?\b', 'follow up customer workflow problems survey'),
)


def evidence_directed_queries(decomposition, documents, citations, fallback):
    result = {'status': 'evidence_directions_unavailable', 'queries': [],
              'directions': [], 'provider_contacted': False, 'provider_request_count': 0,
              'observed_text_is_claim_support': False}
    subs = decomposition.get('subquestions') or []
    if decomposition.get('objective_shape') != 'single_candidate_dimension' or len(subs) != 1:
        return result
    sub = subs[0]
    if sub.get('evidence_dimension') != 'demand' or not fallback:
        return result
    allowed = {row.get('citation_id') for row in citations if isinstance(row, Mapping)}
    subject = _demand_discovery_subject(sub)
    if not subject:
        return result
    label = re.sub(r'\s+demand\s*$', '', str(sub.get('report_label') or ''), flags=re.I)
    split = re.split(r'\s+for\s+', label, maxsplit=1, flags=re.I)
    audience = sanitize_public_query(split[1]) if len(split) == 2 else subject
    for code, pattern, phrase in _DIRECTIONS:
        basis = []
        for doc in list(documents)[:32]:
            cid = doc.get('citation_id')
            if cid not in allowed:
                continue
            for passage in passage_options(cid, str(doc.get('excerpt') or '')):
                if re.search(pattern, passage['text'], re.I):
                    basis.append({'citation_id': cid,
                                  'passage_digest': hashlib.sha256(passage['text'].encode()).hexdigest()})
                    break
        if not basis:
            continue
        # One audience-level route can find problem studies not named after a product.
        query = sanitize_public_query(f'{audience if not result["queries"] else subject} {phrase}')
        template = fallback[len(result['queries'])]
        result['queries'].append({**template, 'query': query,
                                  'query_digest': hashlib.sha256(query.encode()).hexdigest()})
        result['directions'].append({'direction': code, 'basis': basis[:8]})
        if len(result['queries']) >= min(2, len(fallback)):
            break
    if result['queries']:
        result['status'] = 'evidence_directions_ready'
        result['queries'].extend(fallback[len(result['queries']):min(2, len(fallback))])
    return result
