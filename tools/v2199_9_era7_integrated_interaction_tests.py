from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2199-int-data-')
from local_tool_interaction_v2100 import build_tool_preview
from research_web_intelligence_v2100 import plan_research,assess_source_candidate,prepare_browser_research_request
from voice_audio_interaction_v2100 import begin_voice_turn
from multimodal_context_v2100 import register_visual_evidence,prepare_multimodal_workflow
from era7_interaction_intelligence import build_era7_interaction_snapshot,prepare_era7_interaction_packet,process_era7_interaction_control
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2199-int-runtime-'))
snap=build_era7_interaction_snapshot(runtime_root=runtime)
req(snap['ok'] and snap['status']=='era7_interaction_snapshot','integrated_era7_snapshot')
req(snap['tools']['tool_class_count']==7 and snap['research']['governed_browser_required'],'tools_and_research_visible')
req(snap['authority_boundary']['planning_or_inspection_can_grant_execution'] is False,'integrated_authority_boundary')
preview=build_tool_preview(tool_class='read',operation='file_read',argument_metadata={'target':'workspace_file'},target_scope='candidate_workspace',request_id='t1')['preview']
plan=plan_research('What is current?',freshness='current')
source=assess_source_candidate(url='https://example.com/reference',source_kind='reputable_secondary',freshness_policy='stable',plan_digest=plan['plan_digest'])
research=prepare_browser_research_request(plan=plan,source_candidates=[source],operation_id='r1')['request']
voice=begin_voice_turn(turn_id='v1',input_audio_digest='a'*64,event_id='v1',runtime_root=runtime)['turn']
register_visual_evidence(item_id='img',source_type='operator_image',content_digest='b'*64,captured_at='2026-08-23T12:00:00+00:00',event_id='m1',runtime_root=runtime)
visual=prepare_multimodal_workflow(workflow='screenshot_explanation',item_ids=['img'],operation_id='m2',runtime_root=runtime)['workflow']
packet=prepare_era7_interaction_packet(operation_id='all1',tool_preview=preview,research_request=research,voice_turn=voice,multimodal_workflow=visual,runtime_root=runtime)
req(packet['ok'] and packet['packet']['component_count']==4,'integrated_packet_binds_four_modalities')
invalid=prepare_era7_interaction_packet(operation_id='bad',tool_preview={'state':'preview_only','preview_digest':'a'*64},runtime_root=runtime)
req(not invalid['ok'] and invalid['status']=='invalid_era7_tool_component','integrated_packet_rejects_unbound_component')
empty=prepare_era7_interaction_packet(operation_id='empty',runtime_root=runtime)
req(not empty['ok'] and empty['status']=='era7_interaction_component_required','integrated_packet_requires_component')
req(packet['packet']['prepared_not_executed'] is True and packet['tool_executed'] is False,'integrated_packet_nonexecuting')
req(packet['browser_contacted'] is False and packet['microphone_accessed'] is False and packet['screen_captured'] is False,'integrated_packet_no_external_effects')
ctrl=process_era7_interaction_control('show era7 interaction status',runtime_root=runtime)
req(ctrl['active'] and ctrl['ok'],'ordinary_chat_integrated_status')
tool=process_era7_interaction_control('show local tool contracts',runtime_root=runtime)
req(tool['active'] and tool['tool_class_count']==7,'integrated_router_delegates_tool_contract')
research_ctrl=process_era7_interaction_control('show research and web intelligence contract',runtime_root=runtime)
req(research_ctrl['active'] and research_ctrl['network_contacted'] is False,'integrated_router_delegates_research')
voice_ctrl=process_era7_interaction_control('show voice and audio status',runtime_root=runtime)
req(voice_ctrl['active'] and voice_ctrl['microphone_accessed'] is False,'integrated_router_delegates_voice')
visual_ctrl=process_era7_interaction_control('show multimodal context status',runtime_root=runtime)
req(visual_ctrl['active'] and visual_ctrl['screen_captured'] is False,'integrated_router_delegates_multimodal')
blocked=process_era7_interaction_control('show era7 interaction status and install it',runtime_root=runtime)
req(blocked['status']=='era7_integrated_read_only_scope_expansion_rejected','integrated_compound_authority_rejected')
ordinary=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
req('process_era7_interaction_control' in ordinary,'era7_uses_existing_ordinary_chat_boundary')
turn=process_ordinary_chat_development_turn('show era7 interaction status',runtime_root=runtime)
req(turn.get('active') is True and turn.get('status')=='era7_interaction_snapshot','ordinary_chat_routes_era7_status')
compound_turn=process_ordinary_chat_development_turn('show era7 interaction status and install it',runtime_root=runtime)
req(compound_turn.get('status')=='era7_integrated_read_only_scope_expansion_rejected','ordinary_chat_rejects_era7_compound_authority')
req(packet['installation_authorized'] is False and packet['authority_expanded'] is False,'era7_preserves_install_authority')
print(json.dumps({'suite':'v2199.9-era7-integrated-interaction','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
