from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from initiative_proposal_pacing import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
def candidate(rt,code='candidate',kind='development',confidence=.8,urgency=.8,novelty=.7,cost=.3,deps=0,awaiting=False,generation=1,**extra):
    return prepare_initiative_proposal_candidate('project_alpha',proposal_code=code,proposal_kind=kind,subject_digest=h(code),evidence_digests=[h('e-'+code)],origin_system_code='operator_queue',origin_record_id='queue_'+code,origin_record_digest=h('o-'+code),goal_alignment=.9,urgency=urgency,confidence=confidence,novelty=novelty,operator_attention_cost=cost,unresolved_dependency_count=deps,awaiting_authority=awaiting,future_condition_code='operator_available',generation=generation,runtime_root=rt,**extra)
def decide(rt,row,**over):
    args=dict(expected_candidate_digest=row['initiative_proposal_candidate_digest'],context_digest=h('context-'+row['proposal_code']),logical_day=10,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True,cooldown_until_day=0,recent_surface_count=0)
    args.update(over);return prepare_initiative_pacing_decision(row['candidate_id'],runtime_root=rt,**args)
with tempfile.TemporaryDirectory() as rt:
    surface=candidate(rt,'surface');d_surface=decide(rt,surface);ck(d_surface['classification']=='surface_now');ck(d_surface['operator_review_required'])
    question=candidate(rt,'question',kind='clarification');d_question=decide(rt,question);ck(d_question['classification']=='ask_one_bounded_question');ck(d_question['bounded_question_count']==1)
    evidence=candidate(rt,'evidence',deps=2);d_evidence=decide(rt,evidence,evidence_complete=False);ck(d_evidence['classification']=='defer_for_evidence');ck(d_evidence['missing_evidence_count']==3)
    wait=candidate(rt,'wait');d_wait=decide(rt,wait,condition_satisfied=False);ck(d_wait['classification']=='wait_for_condition')
    low=candidate(rt,'low',confidence=.2);d_low=decide(rt,low);ck(d_low['classification']=='suppress_low_confidence')
    load=candidate(rt,'load');d_load=decide(rt,load,operator_load=.9);ck(d_load['classification']=='suppress_operator_load')
    silent=candidate(rt,'silent',awaiting=True);d_silent=decide(rt,silent);ck(d_silent['classification']=='deliberate_silence')
    duplicate=candidate(rt,'duplicate');d_dup=decide(rt,duplicate,duplicate_candidate_id=surface['candidate_id'],duplicate_candidate_digest=surface['initiative_proposal_candidate_digest']);ck(d_dup['classification']=='suppress_duplicate')
    for decision in (d_surface,d_question,d_evidence,d_wait,d_low,d_load,d_silent,d_dup):
        ck(decision['ok']);ck(not decision['message_send_authorized']);ck(not decision['notification_send_authorized']);ck(not decision['session_resume_authorized']);ck(not decision['priority_mutation_authorized'])
    for disposition in sorted(REVIEW_DISPOSITIONS):
        phrase=f"review initiative pacing {disposition} for decision {d_surface['decision_id']} digest {d_surface['initiative_pacing_decision_digest']}"
        review=review_initiative_pacing_decision(d_surface['decision_id'],expected_decision_digest=d_surface['initiative_pacing_decision_digest'],disposition=disposition,exact_phrase=phrase,runtime_root=rt)
        ck(review['ok']);ck(review['disposition']==disposition);ck(review['proposal_specific_only']);ck(review['global_preference_unchanged']);ck(review['message_not_sent']);ck(review['surface_interpretation_accepted'] is (disposition=='accept_surface'))
        chat=process_initiative_pacing_control(phrase,runtime_root=rt);ck(chat['active']);ck(not chat['action_taken']);ck(not chat['execution_started']);ck(not chat['message_sent']);ck('No message was sent' in chat['response'])
        if disposition=='dismiss':dismissed=review
    resurfaced=candidate(rt,'surface',generation=2,previous_candidate_id=surface['candidate_id'],previous_candidate_digest=surface['initiative_proposal_candidate_digest'],prior_review_id=dismissed['review_id'],prior_review_digest=dismissed['initiative_pacing_review_digest'],meaningful_change_digest=h('meaningful-change'))
    for v in (resurfaced['ok'],resurfaced['generation']==2,resurfaced['resurfaced'],resurfaced['previous_candidate_id']==surface['candidate_id'],resurfaced['prior_review_id']==dismissed['review_id']):ck(v)
    blocked=candidate(rt,'surface',generation=2,previous_candidate_id=surface['candidate_id'],previous_candidate_digest=surface['initiative_proposal_candidate_digest'],prior_review_id=dismissed['review_id'],prior_review_digest=dismissed['initiative_pacing_review_digest'])
    ck(not blocked['ok']);ck('requires_exact_review_and_change' in blocked['reason'])
    for text in ('show initiative proposal pacing registry','show initiative proposal candidates','show initiative pacing decisions','show initiative pacing reviews'):
        chat=process_initiative_pacing_control(text,runtime_root=rt);ck(chat['active']);ck(not chat['action_taken']);ck(not chat['execution_started'])
    dash=initiative_pacing_dashboard_record(runtime_root=rt);ck(dash['candidate_count']==9);ck(dash['decision_count']==8);ck(dash['review_count']==4)
for token in ('initiative-proposal-pacing-registry','initiative-proposal-candidates','initiative-pacing-decisions','initiative-pacing-reviews','initiative-proposal-pacing-checkpoint'):
    ck(token in (R/'eidolon.py').read_text());ck(token in (R/'conscious_agent/api_server.py').read_text())
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
