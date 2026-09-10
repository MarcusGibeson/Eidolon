"""Offline demand-discovery targeting and complete-passage regressions."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'conscious_agent'), str(root)]
from bounded_research_reasoning import (
    decompose_research_objective, build_source_strategy, plan_public_search_queries,
    MAX_QUERY_CHARS, MAX_QUERY_TERMS, _demand_discovery_subject,
)
from governed_public_web_research_adapter import _focused_excerpt, _VisibleTextParser
from research_claim_assessment import passage_options

checks = []
def check(value, name):
    assert value, name
    checks.append(name)

check(_demand_discovery_subject({'report_label': 'Brand Deal Tracking for Content Creators demand'}) == 'content creators brand deal', 'audience_survey_subject')
check(_demand_discovery_subject({'report_label': 'Appointment Scheduling for Independent Clinics demand'}) == 'independent clinics appointment scheduling', 'other_domain_preserved')
check('tracking' in _demand_discovery_subject({'report_label': 'Tracking for Couriers demand'}), 'single_product_not_erased')
check('sarah' not in _demand_discovery_subject({'report_label': 'Brand Deal Tracking for my wife Sarah Jenkins demand'}), 'audience_privacy_preserved')

objective = 'Research Brand Deal Tracking for Content Creators demand.'
decomposition = decompose_research_objective(objective)
strategy = build_source_strategy(decomposition)
for budget in (1, 2, 3):
    plan = plan_public_search_queries(objective, decomposition, strategy, max_queries=budget)
    rows = plan['queries']
    check(len(rows) <= budget, 'query_budget_' + str(budget))
    check(all(len(r['query']) <= MAX_QUERY_CHARS and len(r['query'].split()) <= MAX_QUERY_TERMS for r in rows), 'query_bounds_' + str(budget))
    check(all(hashlib.sha256(r['query'].encode()).hexdigest() == r['query_digest'] for r in rows), 'query_digest_' + str(budget))
    check(all(all(t in r['query'].split() for t in ('brand','deal','tracking','content','creators','demand')) for r in rows), 'subject_preserved_' + str(budget))
check('survey' in rows[0]['query'] and 'respondents' in rows[0]['query'], 'measurement_route')
check('saas software tool product' not in rows[0]['query'], 'generic_vendor_terms_removed')
check(len(rows) == 2 and rows[1]['query'].endswith('site:reddit.com'), 'separate_public_discussion_route')
check(not plan['network_contacted'] and not plan['authority_expanded'], 'planning_only')
check('site:reddit.com' not in json.dumps(plan['public_summary']), 'public_summary_has_no_raw_queries')
private = decompose_research_objective('Research my wife Sarah Jenkins brand deal tracking demand.')
private_plan = plan_public_search_queries('', private, build_source_strategy(private), max_queries=3)
check(all('sarah' not in r['query'] and 'jenkins' not in r['query'] for r in private_plan['queries']), 'discussion_route_retains_privacy_filter')
long = decompose_research_objective('Research ' + ' '.join('topic' + str(i) for i in range(40)) + ' demand.')
long_plan = plan_public_search_queries('', long, build_source_strategy(long), max_queries=3)
check(all(len(r['query']) <= MAX_QUERY_CHARS and len(r['query'].split()) <= MAX_QUERY_TERMS for r in long_plan['queries']), 'long_subject_bounded')

intro = 'Brand deal tracking software offers many convenient features for content creators. '
evidence = 'Survey respondents reported brand deal tracking problems, but did not express willingness to pay for new software.'
text = intro * 20 + evidence
excerpt = _focused_excerpt(text, ['survey','respondents','brand','deal','tracking','problems'], limit=300, max_sentences=3)
check(evidence in excerpt, 'late_high_ranked_passage_retained')
check(len(excerpt) <= 300, 'excerpt_budget')
check(all(p['text'] in text for p in passage_options('a', excerpt)), 'offered_passages_are_exact')
check('but did not express willingness to pay' in excerpt, 'negative_qualification_preserved')
check(not _focused_excerpt('x' * 700, ['x'], max_sentences=3), 'oversized_sentence_not_truncated_into_evidence')
check(_focused_excerpt(evidence, ['survey'], limit=20, max_sentences=3) == '', 'too_small_budget_abstains')
parser = _VisibleTextParser()
parser.feed('<title>Survey</title><nav>tracking survey menus<aside>nested menu</aside></nav>'
            '<article><p>Respondents reported delays but did not request new tools.</p></article>'
            '<footer>newsletter tracking survey</footer><p>Follow-up disagreed with the result.</p>')
visible = ' '.join(parser.parts)
check('menus' not in visible and 'newsletter' not in visible, 'semantic_navigation_excluded')
check('did not request new tools' in visible and 'disagreed' in visible, 'article_qualifications_and_adverse_text_retained')
check(parser.title_parts == ['Survey'], 'title_metadata_retained')
print(json.dumps({'ok': True, 'passed': len(checks), 'checks': checks}))
