from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from initiative_proposal_pacing import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
def make(rt,project='project_alpha',code='candidate',**extra):
    args=dict(proposal_code=code,proposal_kind='development',subject_digest=h(code),evidence_digests=[h('e-'+code)],origin_system_code='project_understanding',origin_record_id='origin_'+code,origin_record_digest=h('origin-'+code),goal_alignment=.8,urgency=.8,confidence=.8,novelty=.7,operator_attention_cost=.3,future_condition_code='new_evidence')
    args.update(extra);return prepare_initiative_proposal_candidate(project,runtime_root=rt,**args)
with tempfile.TemporaryDirectory() as rt:
    a=make(rt,code='alpha');b=make(rt,code='beta')
    good=prepare_initiative_pacing_decision(a['candidate_id'],expected_candidate_digest=a['initiative_proposal_candidate_digest'],context_digest=h('ctx'),logical_day=5,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True,runtime_root=rt)
    same=prepare_initiative_pacing_decision(a['candidate_id'],expected_candidate_digest=a['initiative_proposal_candidate_digest'],context_digest=h('ctx'),logical_day=5,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True,runtime_root=rt)
    ck(good['decision_id']==same['decision_id']);ck(good['initiative_pacing_decision_digest']==same['initiative_pacing_decision_digest'])
    cases=[
      dict(expected_candidate_digest=h('stale'),context_digest=h('ctx'),logical_day=5,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True),
      dict(expected_candidate_digest=a['initiative_proposal_candidate_digest'],context_digest='bad',logical_day=5,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True),
      dict(expected_candidate_digest=a['initiative_proposal_candidate_digest'],context_digest=h('ctx'),logical_day=-1,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True),
      dict(expected_candidate_digest=a['initiative_proposal_candidate_digest'],context_digest=h('ctx'),logical_day=5,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=2,evidence_complete=True,condition_satisfied=True),
      dict(expected_candidate_digest=a['initiative_proposal_candidate_digest'],context_digest=h('ctx'),logical_day=5,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True,duplicate_candidate_id=b['candidate_id']),
    ]
    for args in cases:
        row=prepare_initiative_pacing_decision(a['candidate_id'],runtime_root=rt,**args);ck(not row['ok']);ck(row['status']=='initiative_pacing_decision_blocked')
    other=make(rt,project='project_beta',code='other')
    cross=prepare_initiative_pacing_decision(a['candidate_id'],expected_candidate_digest=a['initiative_proposal_candidate_digest'],context_digest=h('ctx'),logical_day=5,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.2,evidence_complete=True,condition_satisfied=True,duplicate_candidate_id=other['candidate_id'],duplicate_candidate_digest=other['initiative_proposal_candidate_digest'],runtime_root=rt)
    ck(not cross['ok']);ck('cross_project_duplicate_candidate' in cross['reason'])
    phrase=f"review initiative pacing dismiss for decision {good['decision_id']} digest {good['initiative_pacing_decision_digest']}"
    review=review_initiative_pacing_decision(good['decision_id'],expected_decision_digest=good['initiative_pacing_decision_digest'],disposition='dismiss',exact_phrase=phrase,runtime_root=rt);ck(review['ok'])
    stale=review_initiative_pacing_decision(good['decision_id'],expected_decision_digest=h('stale'),disposition='dismiss',exact_phrase=phrase,runtime_root=rt);ck(not stale['ok'])
    wrong_phrase=review_initiative_pacing_decision(good['decision_id'],expected_decision_digest=good['initiative_pacing_decision_digest'],disposition='dismiss',exact_phrase='dismiss it',runtime_root=rt);ck(not wrong_phrase['ok']);ck('exact_review_phrase_required' in wrong_phrase['reason'])
    # Tamper each stored record and require fail-closed loading.
    targets=[('initiative_proposal_candidates',a['candidate_id'],'initiative_proposal_candidate_tampered',load_initiative_proposal_candidate),('initiative_pacing_decisions',good['decision_id'],'initiative_pacing_decision_tampered',load_initiative_pacing_decision),('initiative_pacing_reviews',review['review_id'],'initiative_pacing_review_tampered',load_initiative_pacing_review)]
    for directory,rid,status,loader in targets:
        path=Path(rt)/'development_campaigns'/directory/f'{rid}.json';data=json.loads(path.read_text());data['project_id']='project_tampered';path.write_text(json.dumps(data))
        loaded=loader(rid,runtime_root=rt);ck(not loaded['ok']);ck(loaded['status']==status)
    for row in (good,review):
        for k,e in AUTHORITY_FLAGS.items():ck(row.get(k) is e)
    # Pacing restraint precedence and no storm behavior.
    load_case=make(rt,code='loadcase')
    high_load=prepare_initiative_pacing_decision(load_case['candidate_id'],expected_candidate_digest=load_case['initiative_proposal_candidate_digest'],context_digest=h('hl'),logical_day=6,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.99,evidence_complete=True,condition_satisfied=True,recent_surface_count=99,runtime_root=rt)
    ck(high_load['classification']=='suppress_operator_load');ck(not high_load['operator_review_required']);ck(not high_load['message_send_authorized'])
    cooldown=prepare_initiative_pacing_decision(load_case['candidate_id'],expected_candidate_digest=load_case['initiative_proposal_candidate_digest'],context_digest=h('cd'),logical_day=6,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.1,evidence_complete=True,condition_satisfied=True,cooldown_until_day=9,runtime_root=rt)
    ck(cooldown['classification']=='wait_for_condition')
    dismissed=prepare_initiative_pacing_decision(load_case['candidate_id'],expected_candidate_digest=load_case['initiative_proposal_candidate_digest'],context_digest=h('dm'),logical_day=6,operator_present=True,operator_receptive=True,conversation_active=True,operator_load=.1,evidence_complete=True,condition_satisfied=False,topic_dismissed=True,meaningful_change_since_review=False,runtime_root=rt)
    ck(dismissed['classification']=='wait_for_condition');ck(dismissed['reason_code']=='dismissed_topic_requires_change_or_condition')
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
