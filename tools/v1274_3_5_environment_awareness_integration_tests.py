from __future__ import annotations

import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1274_fixture import prepared_environment_chain, deterministic_windows_probes
from environment_awareness import *
from environment_awareness_foundations import load_environment_awareness

C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

with tempfile.TemporaryDirectory(prefix='eidolon-v1274-int-') as td:
    c=prepared_environment_chain(Path(td),now=2000.0);eid=c['environment']['environment_id']
    provider_calls=[];port_calls=[]
    def provider_probe(code):
        provider_calls.append(code);return {'ollama':True,'fallback':False}.get(code)
    def port_probe(port):
        port_calls.append(port);return 'in_use' if port==11434 else 'available'
    probes=deterministic_windows_probes()
    result=refresh_development_environment(
        eid,c['source'],runtime_root=c['runtime'],requested_ports=[11434,8765],configuration_names=['EIDOLON_PROVIDER_TOKEN','EIDOLON_MODE'],
        provider_codes=['ollama','fallback','unknown-local'],provider_availability_probe=provider_probe,port_probe=port_probe,
        process_probe=lambda:{'current_process_alive':True,'worker_count':3},resource_probe=lambda:{'cpu_count':8,'memory_total_bytes':16_000_000_000,'disk_free_bytes':50_000_000_000},
        probes=probes,environ={'EIDOLON_MODE':'development','EIDOLON_PROVIDER_TOKEN':'do-not-persist-this-secret'},now=2001.0,
    )
    req(result['ok'],'refresh_ok')
    req(result['operation_status']=='development_environment_refreshed','refresh_status')
    facts={(x['domain'],x['key']):x for x in result['facts']}
    req(facts[('platform','operating_system')]['value']=='windows' and facts[('platform','operating_system')]['evidence_class']=='observed','windows_host_observed')
    req(facts[('platform','os_api_family')]['value']=='nt','nt_api_observed')
    req(facts[('platform','machine_architecture')]['value']=='x86_64','architecture_observed')
    req(facts[('python','version')]['value']=='3.11.9','python_version_observed')
    req(facts[('python','implementation')]['value']=='cpython','python_implementation_observed')
    req(facts[('python','virtual_environment_active')]['value'] is True,'venv_observed')
    req(facts[('python','executable_digest')]['value_kind']=='digest','python_executable_hashed')
    req(facts[('permission','source_readable')]['value'] is True and facts[('permission','runtime_writable')]['value'] is True,'permissions_observed')
    req(facts[('configuration','config-eidolon-provider-token')]['value'] is True,'config_presence_observed')
    req(facts[('configuration','config-eidolon-mode')]['value'] is True,'second_config_presence_observed')
    req(facts[('provider','provider_ollama_available')]['value'] is True,'provider_available_observed')
    req(facts[('provider','provider_fallback_available')]['value'] is False,'provider_unavailable_observed')
    req(facts[('provider','provider_unknown-local_available')]['evidence_class']=='unknown','provider_unknown_preserved')
    req(facts[('port','tcp_port_11434_state')]['value']=='in_use','occupied_port_observed')
    req(facts[('port','tcp_port_8765_state')]['value']=='available','available_port_observed')
    req(facts[('process','worker_count')]['value']==3,'process_state_observed')
    req(facts[('resource','logical_cpu_count')]['value']==8,'cpu_observed')
    req(facts[('resource','memory_total_bytes')]['value']==16_000_000_000,'memory_observed')
    req(facts[('resource','source_volume_free_bytes')]['value']==50_000_000_000,'disk_observed')
    req(provider_calls==['ollama','fallback','unknown-local'],'providers_only_explicitly_probed')
    req(port_calls==[11434,8765],'ports_only_explicitly_probed')

    raw=json.dumps(load_environment_awareness(eid,runtime_root=c['runtime']),sort_keys=True)
    req('do-not-persist-this-secret' not in raw,'configuration_value_not_persisted')
    req(r'C:\\Python311\\python.exe' not in raw,'python_executable_path_not_persisted')
    req(str(c['source']) not in raw and str(c['runtime']) not in raw,'raw_project_paths_not_persisted')
    req('\"provider_payload_present\": true' not in raw.lower(),'provider_payload_absent')

    status=environment_aware_operator_status(eid,runtime_root=c['runtime'],now=2002.0)
    req(status['ownership_status']=='ownership_concurrency_operator_status','v1273_operator_status_integrated')
    req(status['environment_observation_grants_authority'] is False,'status_no_authority')
    req(status['fact_count']==len(result['facts']),'operator_fact_count')
    req(status['domains']==['configuration','path','permission','platform','port','process','provider','python','resource'],'all_environment_domains_visible')

    # Provider observation defaults to unknown rather than silently contacting it.
    no_probe=observe_provider_facts(['ollama'],availability_probe=None,now=2003.0)
    req(no_probe[0]['evidence_class']=='unknown','provider_no_probe_unknown')
    req(no_probe[0]['value']=='unknown','provider_no_probe_not_false')
    ports_no_probe=observe_port_facts([9999],port_probe=None,now=2003.0)
    req(ports_no_probe[0]['evidence_class']=='unknown','port_no_probe_unknown')

print(json.dumps({'ok':True,'suite':'v1274.3-v1274.5-environment-awareness-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
