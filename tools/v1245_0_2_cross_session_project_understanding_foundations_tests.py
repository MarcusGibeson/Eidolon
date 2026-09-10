from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from cross_session_project_understanding import *
from long_running_multi_day_session_continuity import record_session_progress_checkpoint,prepare_session_continuity_manifest,FRESHNESS_SCOPES
h=lambda s:hashlib.sha256(str(s).encode()).hexdigest(); c=[]; ck=lambda v:c.append(bool(v))

def item(code,kind,day=5,window=30,session='session-a'):
    return {'item_code':code,'item_type':kind,'statement_digest':h('statement-'+code),'evidence_digests':[h('evidence-'+code)],'confidence':'verified','last_verified_day':day,'freshness_window_days':window,'component_code':'component_core' if kind in {'architecture_component','important_boundary'} else '', 'related_codes':[], 'provenance_session_digest':h(session)}

reg=cross_session_project_understanding_registry(); contract=build_cross_session_project_understanding_contract()
for v in (reg['ok'],reg['inspection_only'],len(reg['item_types'])==11,len(reg['classifications'])==7,len(reg['review_dispositions'])==4,contract['ok'],contract['durable_project_summaries'],contract['architecture_components_and_relationships'],contract['decisions_risks_work_and_questions'],contract['confidence_provenance_and_freshness'],contract['immutable_revision_lineage'],contract['cross_session_reconciliation'],contract['remembered_state_never_current_without_revalidation'],bool(reg['registry_digest']),bool(contract['contract_digest'])):ck(v)
for k,e in AUTHORITY_FLAGS.items(): ck(reg.get(k) is e and contract.get(k) is e)
items=[item('purpose_core','project_purpose'),item('goal_operator','operator_goal'),item('component_engine','architecture_component'),item('relationship_flow','component_relationship'),item('framework_python','language_framework'),item('boundary_runtime','important_boundary'),item('decision_append_only','design_decision'),item('risk_stale_memory','limitation_risk'),item('work_completed','completed_work'),item('work_pending','pending_work'),item('question_adapter','open_question')]
relationships=[{'source_code':'component_engine','target_code':'boundary_runtime','relationship_code':'respects_boundary','evidence_digest':h('edge')},{'source_code':'purpose_core','target_code':'goal_operator','relationship_code':'supports_goal','evidence_digest':h('edge2')}]
with tempfile.TemporaryDirectory() as rt:
    progress=record_session_progress_checkpoint('project_alpha','session_alpha',session_digest=h('session'),checkpoint_index=1,logical_day=5,progress_state='paused',stage_code='safe_boundary',runtime_root=rt)
    evidence={scope:h(scope) for scope in FRESHNESS_SCOPES}
    manifest=prepare_session_continuity_manifest('project_alpha','session_alpha',session_digest=h('session'),session_state='paused',stop_reason='end_of_day',logical_day=5,continuity_generation=1,latest_progress_id=progress['progress_id'],expected_progress_digest=progress['progress_record_digest'],evidence_digests=evidence,runtime_root=rt)
    snap=prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),source_session_id='session_alpha',source_session_digest=h('session'),logical_day=5,generation=1,items=items,relationships=relationships,continuity_manifest_id=manifest['manifest_id'],continuity_manifest_digest=manifest['continuity_manifest_record_digest'],runtime_root=rt)
    for v in (snap['ok'],snap['status']=='project_understanding_snapshot_prepared',snap['generation']==1,snap['initial_snapshot'],snap['item_count']==11,snap['relationship_count']==2,snap['continuity_manifest_id']==manifest['manifest_id'],snap['current_truth_not_asserted'],bool(snap['project_understanding_snapshot_digest']),not snap['project_mutation_authorized'],not snap['cognition_write_authorized']):ck(v)
    for kind in ITEM_TYPES: ck(snap['item_type_counts'][kind]==1)
    same=prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),source_session_id='session_alpha',source_session_digest=h('session'),logical_day=5,generation=1,items=list(reversed(items)),relationships=list(reversed(relationships)),continuity_manifest_id=manifest['manifest_id'],continuity_manifest_digest=manifest['continuity_manifest_record_digest'],runtime_root=rt)
    ck(same['snapshot_id']==snap['snapshot_id']);ck(same['project_understanding_snapshot_digest']==snap['project_understanding_snapshot_digest'])
    loaded=load_project_understanding_snapshot(snap['snapshot_id'],runtime_root=rt);ck(loaded['ok']);ck(loaded['snapshot_id']==snap['snapshot_id'])
    public=public_project_understanding_snapshots(runtime_root=rt);dash=project_understanding_dashboard_record(runtime_root=rt);page=render_project_understanding_dashboard_html(runtime_root=rt)
    for v in (public['count']==1,dash['read_only'],dash['get_only'],dash['snapshot_count']==1,dash['reconciliation_count']==0,dash['review_count']==0,'Cross-Session Project Understanding' in page,'GET-only inspection' in page,'Remembered state is evidence' in page):ck(v)
    for k,e in AUTHORITY_FLAGS.items():ck(snap.get(k) is e and dash.get(k) is e)
    bad_manifest=prepare_project_understanding_snapshot('project_alpha',project_identity_digest=h('identity'),repository_fingerprint_digest=h('repo'),source_session_id='session_alpha',source_session_digest=h('session'),logical_day=5,generation=1,items=items,continuity_manifest_id=manifest['manifest_id'],continuity_manifest_digest=h('wrong'),runtime_root=rt);ck(not bad_manifest['ok']);ck('stale_or_mismatched_continuity_manifest' in bad_manifest['reason'])
invalid=[
 lambda rt:prepare_project_understanding_snapshot('project_secret_token',project_identity_digest=h('i'),repository_fingerprint_digest=h('r'),source_session_id='session_a',source_session_digest=h('s'),logical_day=1,generation=1,items=[item('purpose','project_purpose')],runtime_root=rt),
 lambda rt:prepare_project_understanding_snapshot('project_a',project_identity_digest='bad',repository_fingerprint_digest=h('r'),source_session_id='session_a',source_session_digest=h('s'),logical_day=1,generation=1,items=[item('purpose','project_purpose')],runtime_root=rt),
 lambda rt:prepare_project_understanding_snapshot('project_a',project_identity_digest=h('i'),repository_fingerprint_digest=h('r'),source_session_id='session_a',source_session_digest=h('s'),logical_day=-1,generation=1,items=[item('purpose','project_purpose')],runtime_root=rt),
 lambda rt:prepare_project_understanding_snapshot('project_a',project_identity_digest=h('i'),repository_fingerprint_digest=h('r'),source_session_id='session_a',source_session_digest=h('s'),logical_day=1,generation=1,items=[],runtime_root=rt),
 lambda rt:prepare_project_understanding_snapshot('project_a',project_identity_digest=h('i'),repository_fingerprint_digest=h('r'),source_session_id='session_a',source_session_digest=h('s'),logical_day=1,generation=1,items=[item('same','project_purpose'),item('same','operator_goal')],runtime_root=rt),
]
for fn in invalid:
    with tempfile.TemporaryDirectory() as rt:
        row=fn(rt);ck(not row['ok']);ck(row['status']=='project_understanding_snapshot_blocked')
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
