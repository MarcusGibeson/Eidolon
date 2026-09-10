from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2225-data-')
from fine_grained_authority_v2200 import *
from local_tool_interaction_v2100 import build_tool_preview,prepare_existing_execution_handoff
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2225-runtime-'))
policy=build_permission_policy(policy_id='p1',capability='file_write',target_digest='a'*64,scope=['candidate/a.py'],mode='reversible_workspace',duration_seconds=600,command_budget=4,file_budget=2,network_budget=0,disk_mb_budget=32,environment='isolated_workspace',issued_epoch=1000.0)
req(validate_permission_policy(policy)['ok'],'policy_validates')
req(policy['policy_is_authority_grant'] is False and policy['execution_authorized'] is False,'policy_is_ceiling_not_grant')
allowed=evaluate_policy_ceiling(policy,{'capability':'file_write','target_digest':'a'*64,'scope':['candidate/a.py'],'commands':1,'files':1,'network_requests':0,'disk_mb':1,'environment':'isolated_workspace','effect':'write'},runtime_root=runtime,now_epoch=1200.0)
req(allowed['allowed_by_policy_ceiling'] is True,'bounded_request_within_ceiling')
req(allowed['external_authority_receipt_still_required'] is True and allowed['execution_authorized'] is False,'ceiling_does_not_authorize')
expanded=evaluate_policy_ceiling(policy,{'capability':'file_write','target_digest':'a'*64,'scope':['candidate/a.py','outside.py'],'commands':1,'files':1,'environment':'isolated_workspace','effect':'write'},runtime_root=runtime,now_epoch=1200.0)
req(not expanded['allowed_by_policy_ceiling'] and 'scope_expansion' in expanded['reason_codes'],'scope_expansion_denied')
over=evaluate_policy_ceiling(policy,{'capability':'file_write','target_digest':'a'*64,'scope':['candidate/a.py'],'commands':9,'files':1,'environment':'isolated_workspace','effect':'write'},runtime_root=runtime,now_epoch=1200.0)
req('commands_budget_exceeded' in over['reason_codes'],'budget_exceeded_denied')
expired=evaluate_policy_ceiling(policy,{'capability':'file_write','target_digest':'a'*64,'scope':['candidate/a.py'],'commands':0,'files':0,'environment':'isolated_workspace','effect':'write'},runtime_root=runtime,now_epoch=1700.0)
req('policy_expired' in expired['reason_codes'] and not expired['allowed_by_policy_ceiling'],'time_bound_policy_expires')
read_only=build_permission_policy(policy_id='p-read',capability='file_read',target_digest='c'*64,scope=['candidate/a.py'],mode='read_only',file_budget=1,environment='source_read',issued_epoch=1000.0)
read_write=evaluate_policy_ceiling(read_only,{'capability':'file_read','target_digest':'c'*64,'scope':['candidate/a.py'],'files':1,'environment':'source_read','effect':'write'},runtime_root=runtime,now_epoch=1100.0)
req('read_only_policy' in read_write['reason_codes'],'read_only_tier_denies_write')
protected=build_permission_policy(policy_id='p2',capability='secret_access',target_digest='b'*64,scope=['x'],mode='reviewed_installation')
req(protected['mode']=='deny' and protected['protected_capability'],'protected_capability_forced_deny')
rev=revoke_policy(policy_digest=policy['policy_digest'],reason_code='operator_revoked',event_id='ev1',runtime_root=runtime)
req(rev['ok'] and rev['status']=='authority_policy_revoked','revocation_persisted')
replay=revoke_policy(policy_digest=policy['policy_digest'],reason_code='operator_revoked',event_id='ev1',runtime_root=runtime)
req(replay['idempotent'] and replay['status']=='authority_policy_revocation_replayed','revocation_exactly_once')
after=evaluate_policy_ceiling(policy,{'capability':'file_write','target_digest':'a'*64,'scope':['candidate/a.py'],'commands':0,'files':0,'environment':'isolated_workspace','effect':'write'},runtime_root=runtime,now_epoch=1200.0)
req(after['status']=='authority_policy_revoked' and not after['allowed_by_policy_ceiling'],'revoked_policy_cannot_be_reused')
state=public_policy_state(runtime_root=runtime)
req(state['revoked_policy_count']==1 and state['raw_content_exposed'] is False,'public_state_content_free')
preview=build_tool_preview(tool_class='read',operation='file_read',argument_metadata={'target':'workspace_file'},target_scope='candidate_workspace',request_id='era8-policy')['preview']
deny_tool=build_permission_policy(policy_id='tool-deny',capability='tool:read:file_read',target_digest='d'*64,scope=['candidate_workspace'],mode='deny',environment='isolated_workspace',issued_epoch=1000.0)
blocked_handoff=prepare_existing_execution_handoff(preview,authority_policy=deny_tool,authority_request={'capability':'tool:read:file_read','target_digest':'d'*64,'scope':['candidate_workspace'],'environment':'isolated_workspace','effect':'read'},runtime_root=runtime)
req(not blocked_handoff['ok'] and blocked_handoff['status']=='authority_policy_ceiling_denied_tool_handoff','fine_grained_policy_can_restrict_existing_tool_handoff')
tampered=dict(policy); tampered['scope']=['candidate/a.py','evil.py']
req(not validate_permission_policy(tampered)['ok'],'tampered_policy_rejected')
req(all(not bool(allowed[k]) for k in ('execution_authorized','installation_authorized','promotion_authorized','authority_expanded')),'authority_invariants_hold')
print(json.dumps({'suite':'v2225.9-fine-grained-authority','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
