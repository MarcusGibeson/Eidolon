from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True

_RUNTIME=tempfile.mkdtemp(prefix='eidolon-v2502-6-runtime-')
os.environ['EIDOLON_DATA_DIR']=_RUNTIME

from bounded_research_reasoning import decompose_research_objective
from bounded_autonomous_web_research import BoundedResearchSessionStore

CHECKS=[]
def require(cond,name):
    if not cond: raise AssertionError(name)
    CHECKS.append(name)

budget={'max_queries':4,'max_candidates':12,'max_observed_pages':8,'max_total_bytes':1048576,'max_elapsed_seconds':120}
objective='What is the current official support policy?; Compare option A versus option B for reliability; What historical changes explain the difference?; Explore remaining evidence gaps?'
plan=decompose_research_objective(objective,freshness='current',budget=budget)
require(plan['ok'] and plan['objective_assessment']=='bounded_answerable','broad_bounded_objective_is_accepted')
require(plan['subquestion_count']==4,'objective_decomposes_into_bounded_answerable_questions')
kinds=[r['question_kind'] for r in plan['subquestions']]
require(kinds==['current','comparative','historical','exploratory'],'question_kinds_distinguish_current_comparative_historical_exploratory')
roles=[r['planning_role'] for r in plan['subquestions']]
require(roles==['required_fact','comparative_criterion','required_fact','exploratory_unknown'],'planning_roles_distinguish_facts_criteria_and_unknowns')
require(len(plan['required_facts'])==2 and len(plan['comparative_criteria'])==1,'required_facts_and_comparative_criteria_are_explicit')
require(len(plan['unknowns'])==4 and all(not r['resolved'] for r in plan['unknowns']),'unknowns_are_explicit_and_unresolved')
require({a['assumption_code'] for a in plan['assumptions']}=={'public_evidence_only','literal_objective_interpretation'},'planning_assumptions_are_explicit')
conditions={r['condition'] for r in plan['stopping_conditions']}
require({'query_budget_reached','page_budget_reached','time_budget_reached','evidence_sufficient_or_material_gap_preserved'} <= conditions,'stopping_conditions_are_explicit')
require(plan['uncertainty_preserved'] and plan['non_repetitive'],'uncertainty_and_nonrepetition_are_preserved')
require(plan['provider_neutral'] and not plan['provider_contacted'] and not plan['network_contacted'],'decomposition_is_provider_neutral_and_offline')
require(all('question' not in r or 'question_digest' in r for r in plan['public_subquestions']),'public_planning_rows_are_digest_minimized')
require(all('question' not in r for r in plan['public_subquestions']),'public_planning_projection_excludes_private_question_text')
require(len(plan['decomposition_digest'])==64,'decomposition_is_digest_bound')

repeated=decompose_research_objective('Current policy?; Current policy?; Current policy?',budget={'max_queries':4})
require(repeated['ok'] and repeated['subquestion_count']==1,'repeated_questions_are_deduplicated')
ambiguous=decompose_research_objective('this',budget=budget)
require(not ambiguous['ok'] and ambiguous['status']=='research_objective_ambiguous','ambiguous_objective_is_detected')
too_broad=decompose_research_objective('Find everything about public software systems',budget=budget)
require(not too_broad['ok'] and too_broad['status']=='research_objective_too_broad','unbounded_objective_is_detected')
unsafe=decompose_research_objective('Research how to bypass a paywall access control',budget=budget)
require(not unsafe['ok'] and unsafe['status']=='research_objective_unsafe_access_expansion','unsafe_access_expansion_is_detected')
side_effect=decompose_research_objective('Research the announcement and then post it',budget=budget)
require(not side_effect['ok'] and side_effect['status']=='research_objective_requests_external_side_effect','side_effecting_objective_is_detected')
shopping_research=decompose_research_objective('Compare which public laptop specifications I should buy based on reliability',budget=budget)
require(shopping_research['ok'],'research_about_a_purchase_is_not_confused_with_purchase_authority')
impossible=decompose_research_objective('Fact one?; Fact two?; Fact three?; Fact four?',budget={'max_queries':1})
require(not impossible['ok'] and impossible['status']=='research_objective_impossible_within_query_budget','budget_impossible_objective_is_detected')
require(impossible['required_subquestion_count']==4 and impossible['available_query_budget']==1,'budget_failure_explains_required_and_available_capacity')

store=BoundedResearchSessionStore()
created=store.create_session('v2502.6:create',objective='Current official policy?; Compare current implementation versus documented behavior?',budget=budget)
require(created['ok'],'coordinator_reuses_improved_decomposition')
session=created['result']
require(session['subquestion_count']==2 and session['state']=='awaiting_session_authorization','coordinator_preserves_bounded_session_authorization_boundary')
require(session['budget']['max_queries']==4 and session['budget']['max_observed_pages']==8,'coordinator_binds_decomposition_to_exact_bounded_budget')
rejected=store.create_session('v2502.6:reject',objective='Research this and then upload it',budget=budget)
require(not rejected['ok'] and rejected['status']=='research_objective_requests_external_side_effect','coordinator_rejects_side_effecting_research_before_session_persistence')
summary=store.inspection_summary()
require(summary['session_count']==1,'rejected_objective_creates_no_runtime_session')
require(not (Path(__file__).resolve().parents[1]/'data'/'projects.json').exists(),'decomposition_fixture_keeps_runtime_data_outside_source')
print(json.dumps({'suite':'v2502.6-research-question-decomposition','ok':True,'passed':len(CHECKS),'failed':0,'checks':CHECKS,'network_request_count':0,'provider_request_count':0,'authority_expanded':False},sort_keys=True))
