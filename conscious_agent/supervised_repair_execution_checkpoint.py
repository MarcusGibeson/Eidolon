from __future__ import annotations
"""v1141.5 supervised isolated repair execution checkpoint."""
from pathlib import Path
from sandbox_repair_materialization import build_sandbox_repair_materialization_inspection
from sandbox_repair_execution import build_sandbox_repair_execution_inspection
CONTRACT_VERSION='v1141.5'
def build_supervised_repair_execution_checkpoint(runtime_root=None,source_root=None):
 m=build_sandbox_repair_materialization_inspection(runtime_root); e=build_sandbox_repair_execution_inspection(runtime_root)
 checks=[('materialization_contract',m.get('contract_version')=='v1141.3'),('execution_contract',e.get('contract_version')=='v1141.4'),('approval_separate',not m.get('approval_created') and not e.get('approval_created')),('authorization_separate',not m.get('authorization_created') and not e.get('authorization_created')),('source_protected',not m.get('source_modified') and not e.get('source_modified')),('installation_protected',not m.get('installation_modified') and not e.get('installation_modified')),('promotion_protected',not m.get('promotion_created') and not e.get('promotion_created')),('certification_protected',not m.get('certification_created') and not e.get('certification_created')),('privacy_patch',not m.get('patch_text_exposed') and not e.get('patch_text_exposed')),('privacy_commands',not m.get('commands_exposed') and not e.get('commands_exposed')),('privacy_logs',not m.get('logs_exposed') and not e.get('logs_exposed')),('desktop_pending',True)]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'passed':sum(v for _,v in checks),'total':len(checks),'checks':[{'name':n,'passed':v} for n,v in checks],'materialization':m,'execution':e,'runtime_mutated':False,'source_modified':False,'installation_modified':False,'raw_source_exposed':False,'patch_text_exposed':False,'commands_exposed':False,'logs_exposed':False,'hidden_reasoning_exposed':False,'desktop_verification':'pending'}
