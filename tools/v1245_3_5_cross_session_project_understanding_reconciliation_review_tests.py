from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from cross_session_project_understanding import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
def item(code,day=10,window=20):return {'item_code':code,'item_type':'architecture_component','statement_digest':h('statement-'+code),'evidence_digests':[h('evidence-'+code)],'confidence':'high','last_verified_day':day,'freshness_window_days':window,'provenance_session_digest':h('source-session')}
items=[item('valid_item'),item('changed_item'),item('contradicted_item'),item('missing_item'),item('stale_item',day=1,window=2),item('unverified_item'),item('superseded_item')]
with tempfile.TemporaryDirectory() as rt:
    snap=prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),source_session_id='session_source',source_session_digest=h('source-session'),logical_day=10,generation=1,items=items,runtime_root=rt)
    observations=[
      {'item_code':'valid_item','observation_state':'present','statement_digest':h('statement-valid_item'),'evidence_digest':h('evidence-valid_item'),'confidence':'verified'},
      {'item_code':'changed_item','observation_state':'changed','statement_digest':h('new-statement'),'evidence_digest':h('new-evidence'),'confidence':'high'},
      {'item_code':'contradicted_item','observation_state':'contradictory','statement_digest':h('opposite'),'evidence_digest':h('contradiction'),'confidence':'high'},
      {'item_code':'missing_item','observation_state':'missing'},
      {'item_code':'stale_item','observation_state':'present','statement_digest':h('statement-stale_item'),'evidence_digest':h('evidence-stale_item')},
      {'item_code':'unverified_item','observation_state':'unverified'},
      {'item_code':'superseded_item','observation_state':'superseded','evidence_digest':h('replacement')},
    ]
    rec=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later-session'),current_logical_day=10,scan_evidence_digest=h('scan'),observations=observations,runtime_root=rt)
    for v in (rec['ok'],rec['cross_session'],rec['still_valid_count']==1,rec['changed_count']==1,rec['contradicted_count']==1,rec['missing_count']==1,rec['stale_count']==1,rec['unverified_count']==1,rec['superseded_count']==1,rec['operator_review_required'],rec['prior_snapshot_unchanged'],rec['current_truth_not_asserted'],sorted(rec['proposed_update_codes'])==['changed_item','missing_item','stale_item','superseded_item'],sorted(rec['unresolved_codes'])==['contradicted_item','unverified_item'],bool(rec['project_understanding_reconciliation_digest'])):ck(v)
    same=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later-session'),current_logical_day=10,scan_evidence_digest=h('scan'),observations=list(reversed(observations)),runtime_root=rt)
    ck(same['reconciliation_id']==rec['reconciliation_id']);ck(same['project_understanding_reconciliation_digest']==rec['project_understanding_reconciliation_digest'])
    for decision in sorted(REVIEW_DISPOSITIONS):
        phrase=f"review project understanding {decision} for reconciliation {rec['reconciliation_id']} digest {rec['project_understanding_reconciliation_digest']}"
        review=review_project_understanding_reconciliation(rec['reconciliation_id'],expected_reconciliation_digest=rec['project_understanding_reconciliation_digest'],disposition=decision,exact_phrase=phrase,runtime_root=rt)
        ck(review['ok']);ck(review['disposition']==decision);ck(review['update_interpretation_accepted'] is (decision=='accept_update'));ck(review['new_snapshot_not_created']);ck(not review['project_mutation_authorized']);ck(not review['cognition_write_authorized'])
        chat=process_project_understanding_control(phrase,runtime_root=rt);ck(chat['active']);ck(not chat['action_taken']);ck(not chat['execution_started']);ck('No snapshot' in chat['response'])
        if decision=='accept_update': accepted=review
    revised_items=[dict(row,statement_digest=h('revised-'+row['item_code']),evidence_digests=[h('revised-evidence-'+row['item_code'])],last_verified_day=11,provenance_session_digest=h('later-session')) for row in items]
    revised=prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),source_session_id='session_later',source_session_digest=h('later-session'),logical_day=11,generation=2,items=revised_items,previous_snapshot_id=snap['snapshot_id'],previous_snapshot_digest=snap['project_understanding_snapshot_digest'],accepted_review_id=accepted['review_id'],accepted_review_digest=accepted['project_understanding_review_digest'],runtime_root=rt)
    for v in (revised['ok'],revised['generation']==2,revised['previous_snapshot_id']==snap['snapshot_id'],revised['accepted_review_id']==accepted['review_id'],revised['operator_review_bound_revision'],not revised['current_truth_not_asserted'] is False):ck(v)
    original=load_project_understanding_snapshot(snap['snapshot_id'],runtime_root=rt);ck(original['project_understanding_snapshot_digest']==snap['project_understanding_snapshot_digest']);ck(original['generation']==1)
    bad=prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),source_session_id='session_later',source_session_digest=h('later-session'),logical_day=11,generation=2,items=revised_items,previous_snapshot_id=snap['snapshot_id'],previous_snapshot_digest=snap['project_understanding_snapshot_digest'],accepted_review_id='',accepted_review_digest='',runtime_root=rt);ck(not bad['ok']);ck('requires_exact_review_lineage' in bad['reason'])
    pubs=public_project_understanding_snapshots(runtime_root=rt);pubr=public_project_understanding_reconciliations(runtime_root=rt);pubv=public_project_understanding_reviews(runtime_root=rt);dash=project_understanding_dashboard_record(runtime_root=rt)
    for v in (pubs['count']==2,pubr['count']==1,pubv['count']==4,dash['snapshot_count']==2,dash['reconciliation_count']==1,dash['review_count']==4):ck(v)
    for text in ('show cross session project understanding registry','show project understanding snapshots','show project understanding reconciliations','show project understanding reviews'):
        row=process_project_understanding_control(text,runtime_root=rt);ck(row['active']);ck(not row['action_taken']);ck(not row['execution_started'])
for token in ('cross-session-project-understanding-registry','project-understanding-snapshots','project-understanding-reconciliations','project-understanding-reviews','cross-session-project-understanding-checkpoint'):
    ck(token in (R/'eidolon.py').read_text());ck(token in (R/'conscious_agent/api_server.py').read_text())
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
