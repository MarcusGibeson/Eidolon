from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2299-int-data-')
from era8_trustworthy_operation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2299-int-runtime-'))
snap=build_era8_trust_snapshot(runtime_root=runtime)
req(snap['ok'] and snap['status']=='era8_trustworthy_operation_snapshot','era8_snapshot_available')
req(snap['authority_is_capability_specific'] and snap['revocation_is_first_class'],'fine_grained_authority_visible')
req(snap['untrusted_content_cannot_redefine_authority'],'trust_zone_boundary_visible')
req(snap['recovery_requires_exact_lineage'] and snap['audit_receipts_are_content_free'],'recovery_and_audit_contract_visible')
req(snap['trust_zones']['web_content']['treated_as_data'],'web_content_is_data')
req(not snap['trust_zones']['operator_instruction']['may_define_authority'],'operator_text_still_uses_authority_path')
ctrl=process_era8_trust_control('show era8 trust status',runtime_root=runtime)
req(ctrl['active'] and ctrl['ok'],'direct_integrated_control')
blocked=process_era8_trust_control('show era8 trust status and install it',runtime_root=runtime)
req(blocked['active'] and blocked['status']=='era8_read_only_scope_expansion_rejected','compound_authority_rejected')
turn=process_ordinary_chat_development_turn('show era8 trust status',runtime_root=runtime)
req(turn.get('active') is True and turn.get('status')=='era8_trustworthy_operation_snapshot','ordinary_chat_routes_era8')
compound=process_ordinary_chat_development_turn('show era8 trust status and install it',runtime_root=runtime)
req(compound.get('status')=='era8_read_only_scope_expansion_rejected','ordinary_chat_rejects_compound')
ordinary=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
req('process_era8_trust_control' in ordinary,'era8_uses_existing_ordinary_chat_boundary')
req(all(not bool(snap[k]) for k in ('tool_executed','network_contacted','provider_contacted','source_modified','installation_authorized','promotion_authorized','authority_expanded')),'integrated_snapshot_no_external_effects')
print(json.dumps({'suite':'v2299.9-era8-integrated-trustworthy-operation','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
