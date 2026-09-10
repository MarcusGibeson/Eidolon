from __future__ import annotations

import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1274_fixture import prepared_environment_chain
from environment_awareness_foundations import *

C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

with tempfile.TemporaryDirectory(prefix='eidolon-v1274-found-') as td:
    c=prepared_environment_chain(Path(td),now=1000.0);env=c['environment'];eid=env['environment_id']
    req(env['operation_status']=='created','environment_created')
    req(env['ownership_id']==c['ownership']['ownership_id'],'v1273_lineage_bound')
    req(env['recovery_id']==c['recovery']['recovery_id'],'v1272_lineage_bound')
    req(env['session_id']==c['session']['session_id'],'v1271_lineage_bound')
    req(env['campaign_id']==c['campaign']['campaign_id'],'v1270_lineage_bound')
    req(validate_environment_awareness(env)['ok'],'prepared_record_valid')
    req(env['raw_paths_persisted'] is False and env['configuration_values_persisted'] is False and env['provider_payloads_persisted'] is False,'privacy_minimized_record')

    observed=build_environment_fact(domain='platform',key='operating_system',evidence_class='observed',value_kind='code',value='windows',source_code='fixture_probe',observed_at=1001.0)
    inferred=build_environment_fact(domain='path',key='windows_path_semantics',evidence_class='inferred',value_kind='boolean',value=True,source_code='fixture_inference',basis_fact_digests=[observed['fact_digest']],observed_at=1001.0)
    assumed=build_environment_fact(domain='provider',key='provider_local_expected',evidence_class='assumed',value_kind='boolean',value=True,source_code='operator_assumption',observed_at=1001.0)
    unknown=build_environment_fact(domain='resource',key='memory_total_state',evidence_class='unknown',value_kind='state',value='unknown',source_code='probe_unavailable',observed_at=1001.0)
    for fact,label in ((observed,'observed_fact_valid'),(inferred,'inferred_fact_valid'),(assumed,'assumed_fact_valid'),(unknown,'unknown_fact_valid')):
        req(validate_environment_fact(fact),label)
    try:
        build_environment_fact(domain='path',key='bad_inference',evidence_class='inferred',value_kind='boolean',value=True,source_code='fixture',observed_at=1001.0)
        raise AssertionError('inference_without_basis_accepted')
    except ValueError: C.append('inference_requires_basis')
    try:
        build_environment_fact(domain='resource',key='bad_unknown',evidence_class='unknown',value_kind='boolean',value=False,source_code='fixture',observed_at=1001.0)
        raise AssertionError('unknown_as_false_accepted')
    except ValueError: C.append('unknown_not_treated_as_false')

    updated=record_environment_facts(eid,[observed,inferred,assumed,unknown],runtime_root=c['runtime'],now=1002.0)
    req(updated['operation_status']=='facts_recorded','facts_recorded')
    req(len(updated['facts'])==4,'four_fact_classes_retained')
    public=public_environment_awareness(updated,now=1002.0)
    req(public['observed_count']==1 and public['inferred_count']==1 and public['assumed_count']==1 and public['unknown_count']==1,'evidence_counts_exact')
    req(public['stale_fact_count']==0,'fresh_facts_not_stale')
    later=public_environment_awareness(updated,now=2000.0);req(later['stale_fact_count']==4,'staleness_detected')

    replacement=build_environment_fact(domain='platform',key='operating_system',evidence_class='observed',value_kind='code',value='linux',source_code='fixture_probe',observed_at=1003.0)
    updated2=record_environment_facts(eid,[replacement],runtime_root=c['runtime'],now=1003.0)
    req(len(updated2['facts'])==4,'same_key_replaces_without_growth')
    req(next(x for x in updated2['facts'] if x['domain']=='platform' and x['key']=='operating_system')['value']=='linux','latest_fact_replaces_projection')
    req(len(updated2['bounded_summaries'])<=8,'summary_bounded')

    persisted=json.dumps(load_environment_awareness(eid,runtime_root=c['runtime']),sort_keys=True)
    req(str(c['source']) not in persisted,'raw_source_path_not_persisted')
    req(str(c['runtime']) not in persisted,'raw_runtime_path_not_persisted')
    req('super-secret-value' not in persisted,'secret_value_absent')
    req(all(env.get(k) is v for k,v in AUTHORITY_FLAGS.items()),'authority_flags_contained')
    req(AUTHORITY_FLAGS['environment_fact_is_authorization'] is False,'fact_not_authorization')
    req(AUTHORITY_FLAGS['assumption_may_be_promoted_without_observation'] is False,'assumption_not_promoted')

    restored=prepare_environment_awareness(c['ownership']['ownership_id'],runtime_root=c['runtime'],now=1004.0)
    req(restored['operation_status']=='restored','prepare_idempotent')
    req(restored['record_digest']==updated2['record_digest'],'restored_same_record')

print(json.dumps({'ok':True,'suite':'v1274.0-v1274.2-environment-awareness-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
