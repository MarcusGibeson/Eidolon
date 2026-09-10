from __future__ import annotations

import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1274_fixture import prepared_environment_chain
from environment_awareness_foundations import *
from environment_awareness_reliability import *

C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

with tempfile.TemporaryDirectory(prefix='eidolon-v1274-rel-') as td:
    base=Path(td);c=prepared_environment_chain(base/'main',now=3000.0);eid=c['environment']['environment_id']
    drive=classify_windows_path_shape(r'C:\\Users\\operator\\Eidolon')
    req(drive['windows_drive_shape'] is True,'drive_shape_detected')
    req(drive['host_windows_inferred'] is False and drive['host_windows_observed'] is False,'drive_shape_not_host_evidence')
    unc=classify_windows_path_shape(r'\\\\server\\share\\Eidolon')
    req(unc['unc_shape'] is True,'unc_shape_detected')
    extended=classify_windows_path_shape(r'\\?\C:\very\long\path')
    req(extended['extended_length_shape'] is True,'extended_length_shape_detected')
    long_shape=classify_windows_path_shape('C:\\'+('nested\\'*60)+'file.py')
    req(long_shape['path_length']>260,'long_path_length_visible')
    req(long_shape['raw_path_persisted'] is False,'path_classifier_no_persistence')

    observed=build_environment_fact(domain='permission',key='runtime_writable',evidence_class='observed',value_kind='boolean',value=True,source_code='fixture_probe',observed_at=3001.0,stale_after_seconds=30)
    assumption=build_environment_fact(domain='provider',key='provider_ollama_available',evidence_class='assumed',value_kind='boolean',value=True,source_code='operator_assumption',observed_at=3001.0,stale_after_seconds=30)
    basis=build_environment_fact(domain='platform',key='operating_system',evidence_class='observed',value_kind='code',value='windows',source_code='fixture_probe',observed_at=3001.0,stale_after_seconds=30)
    inference=build_environment_fact(domain='path',key='windows_path_semantics',evidence_class='inferred',value_kind='boolean',value=True,source_code='fixture_inference',basis_fact_digests=[basis['fact_digest']],observed_at=3001.0,stale_after_seconds=30)
    unknown=build_environment_fact(domain='resource',key='memory_total_state',evidence_class='unknown',value_kind='state',value='unknown',source_code='probe_missing',observed_at=3001.0,stale_after_seconds=30)
    record_environment_facts(eid,[observed,assumption,basis,inference,unknown],runtime_root=c['runtime'],now=3002.0)

    ok=evaluate_environment_preflight(eid,runtime_root=c['runtime'],requirements={'permission:runtime_writable':True},now=3003.0)
    req(ok['preflight_passed'] is True,'current_observed_fact_can_satisfy_preflight')
    assumed=evaluate_environment_preflight(eid,runtime_root=c['runtime'],requirements={'provider:provider_ollama_available':True},now=3003.0)
    req(assumed['preflight_passed'] is False,'assumption_cannot_satisfy_preflight')
    req(assumed['assumptions_used_as_authority'] is False,'assumption_not_authority')
    inferred=evaluate_environment_preflight(eid,runtime_root=c['runtime'],requirements={'path:windows_path_semantics':True},now=3003.0)
    req(inferred['preflight_passed'] is False,'inference_cannot_satisfy_sensitive_preflight')
    req(inferred['inferences_used_as_authority'] is False,'inference_not_authority')
    unknown_req=evaluate_environment_preflight(eid,runtime_root=c['runtime'],requirements={'resource:memory_total_state':'unknown'},now=3003.0)
    req(unknown_req['preflight_passed'] is False,'unknown_cannot_satisfy_preflight')
    req(unknown_req['unknowns_treated_as_success'] is False,'unknown_not_success')
    stale=evaluate_environment_preflight(eid,runtime_root=c['runtime'],requirements={'permission:runtime_writable':True},now=3040.0)
    req(stale['preflight_passed'] is False,'stale_observation_cannot_satisfy_preflight')
    stale_status=reconcile_stale_environment_facts(eid,runtime_root=c['runtime'],now=3040.0)
    req(stale_status['refresh_required'] is True and stale_status['stale_fact_count']==5,'stale_facts_require_refresh')
    req(stale_status['stale_observation_reused_as_current'] is False,'stale_not_reused')
    req(stale_status['automatic_external_action_performed'] is False,'stale_reconciliation_read_only')

    c2=prepared_environment_chain(base/'corrupt',now=4000.0);eid2=c2['environment']['environment_id']
    # Locate the runtime record using the same internal path contract and corrupt it.
    from environment_awareness_foundations import _path
    p=_path(eid2,c2['runtime']);p.write_text('{broken',encoding='utf-8')
    q=quarantine_invalid_environment_projection(eid2,runtime_root=c2['runtime'],now=4010.0)
    req(q['quarantined'] is True,'invalid_projection_quarantined')
    req(q['facts_reconstructed_from_assumptions'] is False,'corrupt_facts_not_invented')
    req(q['fresh_observation_required'] is True,'corrupt_projection_requires_fresh_observation')

    health=inspect_environment_awareness_health(source_root=ROOT);req(health['ok'],'health_ready')
    handoff=build_environment_awareness_operator_handoff(source_root=ROOT);req(handoff['ok'],'handoff_ready')
    req('observed_inferred_assumed_unknown_fact_classes' in handoff['capabilities'],'evidence_classes_capability')
    req('windows_path_shape_is_not_host_os_evidence' in handoff['known_limitations'],'windows_shape_limitation')
    req('extended_length_long_paths' in handoff['native_windows_review'],'windows_long_path_handoff')
    req('occupied_and_available_loopback_ports' in handoff['native_windows_review'],'windows_port_handoff')
    req(handoff['next_bounded_unit']=='v1275 Dependency and Packaging Management','next_v1275')
    req(AUTHORITY_FLAGS['environment_observation_is_execution_authority'] is False,'environment_observation_not_execution_authority')
    req(AUTHORITY_FLAGS['environment_preflight_is_execution_authority'] is False if 'environment_preflight_is_execution_authority' in AUTHORITY_FLAGS else True,'preflight_authority_boundary')

print(json.dumps({'ok':True,'suite':'v1274.6-v1274.8-environment-awareness-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
