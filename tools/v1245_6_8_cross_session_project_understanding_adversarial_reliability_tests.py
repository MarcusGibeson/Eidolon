from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from cross_session_project_understanding import *
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest();c=[];ck=lambda v:c.append(bool(v))
def item(code='component_core',day=5,window=2):return {'item_code':code,'item_type':'architecture_component','statement_digest':h('statement-'+code),'evidence_digests':[h('evidence-'+code)],'confidence':'high','last_verified_day':day,'freshness_window_days':window,'provenance_session_digest':h('session-source')}
def base(rt):return prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),source_session_id='session_source',source_session_digest=h('session-source'),logical_day=5,generation=1,items=[item()],runtime_root=rt)
with tempfile.TemporaryDirectory() as rt:
    snap=base(rt)
    partial=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later'),current_logical_day=6,scan_evidence_digest=h('partial'),observations=[],partial_scan=True,runtime_root=rt)
    ck(partial['ok']);ck(partial['unverified_count']==1);ck(partial['missing_count']==0);ck(partial['operator_review_required']);ck(partial['unresolved_codes']==['component_core'])
    full=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later'),current_logical_day=6,scan_evidence_digest=h('full'),observations=[],partial_scan=False,runtime_root=rt)
    ck(full['ok']);ck(full['missing_count']==1);ck(full['unverified_count']==0)
    stale=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later'),current_logical_day=9,scan_evidence_digest=h('stale'),observations=[{'item_code':'component_core','observation_state':'present','statement_digest':h('statement-component_core'),'evidence_digest':h('evidence-component_core')}],runtime_root=rt)
    ck(stale['ok']);ck(stale['stale_count']==1);ck(stale['still_valid_count']==0)
    attacks=[
      dict(project_id='project_beta',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_logical_day=6,reason='cross_project_snapshot'),
      dict(project_id='project_alpha',project_identity_digest=h('other'),repository_fingerprint_digest=h('repo'),current_logical_day=6,reason='project_identity_mismatch'),
      dict(project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('copy'),current_logical_day=6,reason='repository_fingerprint_mismatch'),
      dict(project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_logical_day=4,reason='logical_clock_reversal'),
    ]
    for attack in attacks:
        row=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id=attack['project_id'],project_identity_digest=attack['project_identity_digest'],repository_fingerprint_digest=attack['repository_fingerprint_digest'],current_session_id='session_later',current_session_digest=h('later'),current_logical_day=attack['current_logical_day'],scan_evidence_digest=h('scan'),observations=[],runtime_root=rt)
        ck(not row['ok']);ck(attack['reason'] in row['reason']);ck(not row['project_mutation_authorized']);ck(not row['cognition_write_authorized'])
    unknown=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later'),current_logical_day=6,scan_evidence_digest=h('scan'),observations=[{'item_code':'unknown_item','observation_state':'present'}],runtime_root=rt);ck(not unknown['ok']);ck('observation_not_in_snapshot' in unknown['reason'])
    duplicate=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later'),current_logical_day=6,scan_evidence_digest=h('scan2'),observations=[{'item_code':'component_core','observation_state':'present'},{'item_code':'component_core','observation_state':'missing'}],runtime_root=rt);ck(not duplicate['ok']);ck('duplicate_observation_item_code' in duplicate['reason'])
    wrong=review_project_understanding_reconciliation(partial['reconciliation_id'],expected_reconciliation_digest=h('wrong'),disposition='hold',exact_phrase='x',runtime_root=rt);ck(not wrong['ok']);ck('stale_or_mismatched_reconciliation' in wrong['reason'])
    phrase=f"review project understanding hold for reconciliation {partial['reconciliation_id']} digest {partial['project_understanding_reconciliation_digest']}"
    review=review_project_understanding_reconciliation(partial['reconciliation_id'],expected_reconciliation_digest=partial['project_understanding_reconciliation_digest'],disposition='hold',exact_phrase=phrase,runtime_root=rt);ck(review['ok'])
    replay=review_project_understanding_reconciliation(partial['reconciliation_id'],expected_reconciliation_digest=partial['project_understanding_reconciliation_digest'],disposition='hold',exact_phrase=phrase,runtime_root=rt);ck(replay['review_id']==review['review_id']);ck(replay['project_understanding_review_digest']==review['project_understanding_review_digest'])
    snap_path=Path(rt)/'development_campaigns'/'project_understanding_snapshots'/f"{snap['snapshot_id']}.json";data=json.loads(snap_path.read_text());data['logical_day']=999;snap_path.write_text(json.dumps(data))
    tampered=load_project_understanding_snapshot(snap['snapshot_id'],runtime_root=rt);ck(not tampered['ok']);ck(tampered['status']=='project_understanding_snapshot_tampered')
with tempfile.TemporaryDirectory() as rt:
    snap=base(rt)
    rec=prepare_project_understanding_reconciliation(snap['snapshot_id'],expected_snapshot_digest=snap['project_understanding_snapshot_digest'],project_id='project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),current_session_id='session_later',current_session_digest=h('later'),current_logical_day=6,scan_evidence_digest=h('scan'),observations=[],partial_scan=True,runtime_root=rt)
    rec_path=Path(rt)/'development_campaigns'/'project_understanding_reconciliations'/f"{rec['reconciliation_id']}.json";data=json.loads(rec_path.read_text());data['unverified_count']=0;rec_path.write_text(json.dumps(data))
    tampered=load_project_understanding_reconciliation(rec['reconciliation_id'],runtime_root=rt);ck(not tampered['ok']);ck(tampered['status']=='project_understanding_reconciliation_tampered')
for bad_code in ('secret_component','private_architecture','prompt_history'):
    with tempfile.TemporaryDirectory() as rt:
        row=prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('i'),repository_fingerprint_digest=h('r'),source_session_id='session_aa',source_session_digest=h('s'),logical_day=1,generation=1,items=[item(bad_code)],runtime_root=rt);ck(not row['ok']);ck('invalid_item_code' in row['reason'])
for record in (cross_session_project_understanding_registry(),build_cross_session_project_understanding_contract(),project_understanding_dashboard_record()):
    for k,e in AUTHORITY_FLAGS.items():ck(record.get(k) is e)
    for key in ('raw_project_content_read','raw_project_content_exposed','private_path_exposed','private_content_exposed','project_modified','cognition_written','commands_executed','tests_executed','session_resumed','session_launched'):ck(record.get(key) is False)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
