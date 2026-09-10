from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from initiative_proposal_pacing import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
reg=initiative_proposal_pacing_registry();contract=build_initiative_proposal_pacing_contract()
for v in (reg['ok'],reg['inspection_only'],len(reg['proposal_kinds'])==8,len(reg['pacing_classifications'])==8,len(reg['review_dispositions'])==4,contract['ok'],contract['proposal_eligibility_and_novelty'],contract['urgency_confidence_and_attention_cost'],contract['cooldowns_and_duplicate_suppression'],contract['unresolved_dependency_awareness'],contract['one_bounded_question_maximum'],contract['deliberate_silence_is_valid'],contract['no_automatic_notification_or_surface'],bool(reg['registry_digest']),bool(contract['contract_digest'])):ck(v)
for k,e in AUTHORITY_FLAGS.items():ck(reg.get(k) is e and contract.get(k) is e)
base=dict(project_id='project_alpha',proposal_code='repair_quality_gap',proposal_kind='development',subject_digest=h('subject'),evidence_digests=[h('e1'),h('e2')],origin_system_code='quality_assessment',origin_record_id='quality_assessment_alpha',origin_record_digest=h('origin'),goal_alignment=.9,urgency=.8,confidence=.85,novelty=.7,operator_attention_cost=.4,unresolved_dependency_count=0,awaiting_authority=False,future_condition_code='operator_available')
with tempfile.TemporaryDirectory() as rt:
    row=prepare_initiative_proposal_candidate(runtime_root=rt,**base)
    for v in (row['ok'],row['status']=='initiative_proposal_candidate_prepared',row['generation']==1,not row['resurfaced'],row['evidence_count']==2,row['operator_specific_review_only'],bool(row['initiative_proposal_candidate_digest'])):ck(v)
    same=prepare_initiative_proposal_candidate(runtime_root=rt,**dict(base,evidence_digests=list(reversed(base['evidence_digests']))))
    ck(same['candidate_id']==row['candidate_id']);ck(same['initiative_proposal_candidate_digest']==row['initiative_proposal_candidate_digest'])
    loaded=load_initiative_proposal_candidate(row['candidate_id'],runtime_root=rt);ck(loaded['ok']);ck(loaded['candidate_id']==row['candidate_id'])
    public=public_initiative_proposal_candidates(runtime_root=rt);dash=initiative_pacing_dashboard_record(runtime_root=rt);page=render_initiative_pacing_dashboard_html(runtime_root=rt)
    for v in (public['count']==1,dash['read_only'],dash['get_only'],dash['candidate_count']==1,dash['decision_count']==0,dash['review_count']==0,'Initiative and Proposal Pacing' in page,'GET-only inspection' in page,'never sends' in page):ck(v)
    for k,e in AUTHORITY_FLAGS.items():ck(row.get(k) is e and dash.get(k) is e)
invalid=[
 dict(base,project_id='project_secret_token'),dict(base,proposal_kind='unsupported'),dict(base,evidence_digests=[]),dict(base,confidence=1.2),dict(base,operator_attention_cost=-.1),dict(base,unresolved_dependency_count=-1),dict(base,generation=2),dict(base,origin_record_digest='bad'),dict(base,proposal_code='private_content'),
]
for args in invalid:
    with tempfile.TemporaryDirectory() as rt:
        row=prepare_initiative_proposal_candidate(runtime_root=rt,**args);ck(not row['ok']);ck(row['status']=='initiative_proposal_candidate_blocked')
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
