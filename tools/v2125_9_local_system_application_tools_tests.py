from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2125-data-')
from local_tool_interaction_v2100 import tool_contract_registry, build_tool_preview, prepare_existing_execution_handoff, reconcile_tool_result, process_era7_tool_control
checks=[]
def req(v,n): checks.append(n); assert v,n
reg=tool_contract_registry()
req(reg['ok'] and reg['tool_class_count']==7,'seven_typed_tool_classes')
req({x['tool_class'] for x in reg['tool_classes']}=={'read','write','process','application','file','clipboard','notification'},'roadmap_tool_classes_present')
req(reg['raw_shell_contract_present'] is False and reg['tool_executed'] is False,'no_arbitrary_shell_or_execution')
req(reg['new_executor_created'] is False and reg['retained_tool_registry_codes'],'tool_layer_reuses_retained_registry_boundary')
unknown=build_tool_preview(tool_class='shell',operation='rm',argument_metadata={},target_scope='workspace',request_id='x')
req(unknown['status']=='unknown_or_unregistered_tool_operation','unregistered_shell_rejected')
no_rb=build_tool_preview(tool_class='write',operation='file_replace',argument_metadata={'target':'workspace_file','content_digest':'a'*64},target_scope='candidate_workspace',allowlist=['candidate_workspace'],request_id='r')
not_allowed=build_tool_preview(tool_class='write',operation='file_replace',argument_metadata={'target':'workspace_file','content_digest':'a'*64},target_scope='candidate_workspace',allowlist=['other_scope'],rollback_code='restore_backup',request_id='na')
req(not_allowed['status']=='mutating_target_scope_not_allowlisted','mutating_target_must_be_allowlisted')
req(no_rb['status']=='rollback_contract_required','mutating_preview_requires_rollback')
preview=build_tool_preview(tool_class='write',operation='file_replace',argument_metadata={'target':'workspace_file','content_digest':'a'*64},target_scope='candidate_workspace',allowlist=['candidate_workspace'],rollback_code='restore_backup',timeout_seconds=999,request_id='r')
req(preview['ok'] and preview['preview']['state']=='preview_only','typed_preview_ready')
invalid_timeout=build_tool_preview(tool_class='read',operation='file_read',argument_metadata={'target':'workspace_file'},target_scope='candidate_workspace',timeout_seconds='not-a-number',request_id='bad-timeout')
req(not invalid_timeout['ok'] and invalid_timeout['status']=='invalid_tool_timeout','malformed_tool_timeout_fails_closed')
req(preview['preview']['timeout_seconds']==60 and preview['preview']['argument_values_included'] is False,'preview_bounded_and_content_minimized')
req(preview['preview']['conversation_can_authorize'] is False and preview['tool_executed'] is False,'preview_never_authorizes')
handoff=prepare_existing_execution_handoff(preview['preview'])
req(handoff['ok'] and handoff['handoff']['requires_existing_execution_admission'] is True,'existing_action_boundary_required')
tampered=dict(preview['preview']); tampered['target_scope']='other_scope'
req(not prepare_existing_execution_handoff(tampered)['ok'],'tampered_tool_preview_rejected')
req(handoff['handoff']['execution_admitted'] is False,'handoff_not_execution_admission')
bad=reconcile_tool_result(preview['preview'],{'contract_version':'v1178.8','terminal':True,'tool_preview_digest':'b'*64,'operation_digest':'c'*64,'terminal_result_digest':'9'*64,'state':'execution_succeeded'})
req(bad['truth_state']=='unknown' and bad['success_claim_allowed'] is False,'mismatched_result_cannot_claim_success')
forged=reconcile_tool_result(preview['preview'],{'authoritative':True,'terminal':True,'tool_preview_digest':preview['preview']['preview_digest'],'operation_digest':'c'*64,'terminal_result_digest':'9'*64,'state':'execution_succeeded'})
req(forged['status']=='matching_retained_terminal_result_required','arbitrary_authoritative_flag_not_enough')
good=reconcile_tool_result(preview['preview'],{'contract_version':'v1178.8','terminal':True,'tool_preview_digest':preview['preview']['preview_digest'],'operation_digest':'c'*64,'terminal_result_digest':'9'*64,'outcome_digest':'d'*64,'state':'execution_succeeded'})
req(good['ok'] and good['success_claim_allowed'] is True,'matching_authoritative_result_truthful')
unknown=reconcile_tool_result(preview['preview'],{'contract_version':'v1178.8','terminal':True,'tool_preview_digest':preview['preview']['preview_digest'],'operation_digest':'e'*64,'terminal_result_digest':'8'*64,'state':'mystery'})
req(unknown['truth_state']=='unknown' and unknown['success_claim_allowed'] is False,'unknown_result_not_upgraded')
ctrl=process_era7_tool_control('show local tool contracts')
req(ctrl['active'] and ctrl['ok'],'tool_contract_control')
blocked=process_era7_tool_control('show local tool contracts and execute one')
req(blocked['active'] and blocked['status']=='era7_tool_read_only_scope_expansion_rejected','compound_tool_scope_expansion_rejected')
print(json.dumps({'suite':'v2125.9-local-system-application-tools','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
