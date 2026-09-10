from __future__ import annotations
"""v1331 content-minimized registry of tool contracts, schemas, and side effects."""
from pathlib import Path
from typing import Any, Mapping

from cognitive_coding_foundations import digest
from candidate_approaches import PLANNING_DENIED_AUTHORITY
from project_evidence_store import atomic_json, evidence_root, read_json, seal, valid

CONTRACT_VERSION="v1331.8"
TOOL_CLASSES=("file_read","file_patch","search","git","shell","browser","build","test","service")

_CAPABILITIES={
 "file_read":{"schema":{"path":"workspace_relative_path","encoding":"optional_encoding"},"side_effects":[],"authority_class":"read_only"},
 "file_patch":{"schema":{"path":"workspace_relative_path","patch":"structured_patch","precondition_digest":"optional_digest"},"side_effects":["workspace_file_mutation"],"authority_class":"workspace_mutation"},
 "search":{"schema":{"query":"text_query","root":"workspace_scope","filters":"optional_filters"},"side_effects":[],"authority_class":"read_only"},
 "git":{"schema":{"operation":"typed_git_operation","workspace":"repository_root","args":"validated_arguments"},"side_effects":["repository_metadata_read_or_mutation"],"authority_class":"typed_operation_dependent"},
 "shell":{"schema":{"operation":"typed_process_operation","cwd":"workspace_scope","args":"argument_vector","environment":"filtered_environment"},"side_effects":["process_spawn","possible_workspace_mutation"],"authority_class":"typed_operation_dependent"},
 "browser":{"schema":{"operation":"inspect_or_interact","target":"local_or_allowed_url","input":"optional_interaction"},"side_effects":["browser_process","possible_local_app_interaction","possible_network_contact"],"authority_class":"typed_operation_dependent"},
 "build":{"schema":{"adapter":"declared_build_adapter","workspace":"candidate_workspace","target":"optional_target"},"side_effects":["process_spawn","generated_workspace_files"],"authority_class":"workspace_process"},
 "test":{"schema":{"adapter":"declared_test_adapter","workspace":"candidate_workspace","selection":"test_selection"},"side_effects":["process_spawn","temporary_runtime_files"],"authority_class":"workspace_process"},
 "service":{"schema":{"operation":"start_stop_status","service_code":"declared_service","workspace":"candidate_workspace"},"side_effects":["process_tree","local_port_binding","temporary_runtime_files"],"authority_class":"service_process"},
}


def _path(registry_id:str,runtime_root=None)->Path:
    return evidence_root("tool_capability_registry",runtime_root)/"records"/f"{registry_id}.json"


def build_tool_capability_registry(*,availability_evidence:Mapping[str,Mapping[str,Any]]|None=None,runtime_root=None)->dict[str,Any]:
    evidence=availability_evidence or {};rows=[]
    for code in TOOL_CLASSES:
        spec=_CAPABILITIES[code];ev=dict(evidence.get(code) or {})
        evidence_digests=sorted({str(x) for x in ev.get('evidence_digests') or [] if str(x)})[:16]
        availability='evidence_available' if ev.get('available') is True and evidence_digests else ('evidence_unavailable' if ev.get('available') is False and evidence_digests else 'declared_not_probed')
        row={"tool_code":code,"schema":dict(spec['schema']),"schema_digest":digest(spec['schema']),"side_effect_codes":list(spec['side_effects']),"side_effect_count":len(spec['side_effects']),"authority_class":spec['authority_class'],
             "availability_state":availability,"availability_evidence_digests":evidence_digests,"availability_probe_executed":False,"tool_invoked":False,"content_free":True}
        row['capability_digest']=digest(row);rows.append(row)
    registry_id='tools_'+digest({"contract":CONTRACT_VERSION,"rows":[x['capability_digest'] for x in rows]})[:24]
    record=seal({"contract_version":CONTRACT_VERSION,"registry_id":registry_id,"tool_classes":list(TOOL_CLASSES),"capabilities":rows,"capability_count":len(rows),"schemas_declared":True,"side_effects_declared":True,
                 "availability_probes_executed":False,"tools_invoked":False,"registry_is_authority":False,"action_executed":False,**PLANNING_DENIED_AUTHORITY})
    atomic_json(_path(registry_id,runtime_root),record)
    return {"ok":True,"status":"tool_capability_registry_ready","tool_capability_registry":public_tool_capability_registry(record),"action_executed":False,**PLANNING_DENIED_AUTHORITY}


def public_tool_capability_registry(row:Mapping[str,Any])->dict[str,Any]:
    return {"contract_version":CONTRACT_VERSION,"registry_id":row.get('registry_id'),"tool_classes":list(row.get('tool_classes') or []),"capability_count":int(row.get('capability_count') or 0),
            "capabilities":[{"tool_code":x.get('tool_code'),"schema":dict(x.get('schema') or {}),"schema_digest":x.get('schema_digest'),"side_effect_codes":list(x.get('side_effect_codes') or []),"authority_class":x.get('authority_class'),"availability_state":x.get('availability_state'),"availability_evidence_count":len(x.get('availability_evidence_digests') or []),"tool_invoked":False} for x in row.get('capabilities') or []],
            "schemas_declared":True,"side_effects_declared":True,"availability_probes_executed":False,"tools_invoked":False,"registry_is_authority":False,"read_only":True,"action_executed":False,**PLANNING_DENIED_AUTHORITY}


def load_tool_capability_registry(registry_id:str,*,runtime_root=None,include_private:bool=False)->dict[str,Any]:
    row=read_json(_path(str(registry_id),runtime_root));
    if not row or not valid(row):return {}
    return row if include_private else public_tool_capability_registry(row)


def inspect_tool_capability(registry:Mapping[str,Any],tool_code:str)->dict[str,Any]:
    row=next((dict(x) for x in registry.get('capabilities') or [] if x.get('tool_code')==str(tool_code)),None)
    return {"ok":bool(row),"status":"tool_capability_found" if row else "tool_capability_unknown","tool_capability":row or {},"tool_invoked":False,"action_executed":False,**PLANNING_DENIED_AUTHORITY}


def process_tool_capability_registry_control(text:str,*,availability_evidence=None,runtime_root=None,**_)->dict[str,Any]:
    if str(text or '').strip().lower() not in {'show tool capability registry','inspect tool capability registry','show available tool contracts'}:return {'active':False}
    return {'active':True,**build_tool_capability_registry(availability_evidence=availability_evidence,runtime_root=runtime_root)}


__all__=['CONTRACT_VERSION','TOOL_CLASSES','build_tool_capability_registry','public_tool_capability_registry','load_tool_capability_registry','inspect_tool_capability','process_tool_capability_registry_control']
