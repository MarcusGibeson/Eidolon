from __future__ import annotations
import hashlib, json, os, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timezone, timedelta
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2199-mm-data-')
from multimodal_context_v2100 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
def observation_receipt(item_id,content_digest,region_id,kind,observation_digest):
    row={'contract_version':NATIVE_OBSERVATION_RECEIPT_VERSION,'receipt_kind':'visual_observation','authoritative':True,'terminal':True,'operation_digest':'8'*64,'terminal_result_digest':'9'*64,'item_id':item_id,'content_digest':content_digest,'region_id':region_id,'observation_kind':kind,'observation_digest':observation_digest}
    row['receipt_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    return row
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2199-mm-runtime-'))
now=datetime.now(timezone.utc)
reg=register_visual_evidence(item_id='img1',source_type='operator_image',content_digest='a'*64,captured_at=now.isoformat(),width=1000,height=800,retention_policy='turn_only',event_id='reg1',runtime_root=runtime)
req(reg['ok'] and reg['state']['item_count']==1,'operator_visual_evidence_registered')
req(reg['image_bytes_read'] is False and reg['screen_captured'] is False,'registration_does_not_read_media_or_capture_screen')
replay=register_visual_evidence(item_id='img1',source_type='operator_image',content_digest='a'*64,captured_at=now.isoformat(),event_id='reg1',runtime_root=runtime)
req(replay['idempotent'] is True,'visual_registration_exactly_once')
bad=register_region_observation(item_id='img1',expected_content_digest='b'*64,region_id='r1',observation_kind='visual',observation_digest='c'*64,confidence=.9,bounds={'x':0,'y':0,'w':.5,'h':.5},event_id='obsbad',observation_receipt=observation_receipt('img1','b'*64,'r1','visual','c'*64),runtime_root=runtime)
req(bad['status']=='stale_visual_content_digest','stale_visual_digest_rejected')
unreceipted=register_region_observation(item_id='img1',expected_content_digest='a'*64,region_id='fake',observation_kind='visual',observation_digest='c'*64,confidence=.9,bounds={'x':0,'y':0,'w':.5,'h':.5},event_id='fake',runtime_root=runtime)
req(unreceipted['status']=='authoritative_visual_observation_receipt_required','unreceipted_visual_observation_rejected')
obs=register_region_observation(item_id='img1',expected_content_digest='a'*64,region_id='r1',observation_kind='visual',observation_digest='c'*64,confidence=.9,bounds={'x':0,'y':0,'w':.5,'h':.5},event_id='obs1',observation_receipt=observation_receipt('img1','a'*64,'r1','visual','c'*64),runtime_root=runtime)
req(obs['ok'] and obs['observation']['raw_text_stored'] is False,'region_observation_content_minimized')
claim=build_visual_claim(item_id='img1',region_ids=['r1'],claim_code='button_visible',runtime_root=runtime)
req(claim['ok'] and claim['claim']['claim_supported'],'visual_claim_requires_observation')
def add_region(i):
    od=(format(i+2,'x')*64)[:64]; rid=f'cr{i}'
    return register_region_observation(item_id='img1',expected_content_digest='a'*64,region_id=rid,observation_kind='layout',observation_digest=od,confidence=.75,bounds={'x':i*.05,'y':.6,'w':.04,'h':.1},event_id=f'concurrent-region-{i}',observation_receipt=observation_receipt('img1','a'*64,rid,'layout',od),runtime_root=runtime)
with ThreadPoolExecutor(max_workers=6) as pool:
    concurrent=list(pool.map(add_region,range(6)))
req(all(r['ok'] for r in concurrent),'concurrent_visual_observation_writes_succeed')
mm_state=public_multimodal_state(read_multimodal_state(runtime_root=runtime),now=now)
img_public=next(x for x in mm_state['items'] if x['item_id']=='img1')
req(img_public['region_count']==7,'concurrent_visual_observations_no_lost_writes')
missing=build_visual_claim(item_id='img1',region_ids=['missing'],claim_code='imagined',runtime_root=runtime)
req(not missing['ok'] and missing['claim_supported'] is False,'unobserved_region_cannot_support_claim')
transient=register_visual_evidence(item_id='transient',source_type='document_page',content_digest='9'*64,captured_at=now.isoformat(),page_number=1,accessible=True,sensitive=True,retention_policy='do_not_retain',event_id='transient1',runtime_root=runtime)
req(transient['status']=='visual_evidence_transient_not_persisted' and transient['persisted'] is False,'do_not_retain_policy_honored')
inacc=register_visual_evidence(item_id='secret',source_type='document_page',content_digest='d'*64,captured_at=now.isoformat(),page_number=2,accessible=False,sensitive=True,retention_policy='turn_only',event_id='reg2',runtime_root=runtime)
blocked=register_region_observation(item_id='secret',expected_content_digest='d'*64,region_id='r2',observation_kind='ocr',observation_digest='e'*64,confidence=.8,bounds={'x':0,'y':0,'w':1,'h':1},event_id='obs2',observation_receipt=observation_receipt('secret','d'*64,'r2','ocr','e'*64),runtime_root=runtime)
req(blocked['status']=='inaccessible_visual_item_cannot_be_observed','inaccessible_content_fail_closed')
old=(now-timedelta(seconds=90)).isoformat()
register_visual_evidence(item_id='screen1',source_type='selected_screen_frame',content_digest='f'*64,captured_at=old,width=1920,height=1080,event_id='reg3',runtime_root=runtime)
register_region_observation(item_id='screen1',expected_content_digest='f'*64,region_id='r3',observation_kind='ui_state',observation_digest='1'*64,confidence=.95,bounds={'x':0,'y':0,'w':.2,'h':.2},event_id='obs3',observation_receipt=observation_receipt('screen1','f'*64,'r3','ui_state','1'*64),runtime_root=runtime)
stale=build_visual_claim(item_id='screen1',region_ids=['r3'],claim_code='window_open',runtime_root=runtime,now=now,stale_after_seconds=30)
req(stale['status']=='stale_screen_frame_requires_reobservation','stale_screen_frame_not_presented_as_current')
workflow=prepare_multimodal_workflow(workflow='ui_troubleshooting',item_ids=['img1','secret'],operation_id='wf1',runtime_root=runtime)
req(workflow['ok'] and workflow['workflow']['evidence_item_count']==2,'multimodal_workflow_prepared')
req(workflow['screen_captured'] is False and workflow['ocr_executed'] is False,'workflow_does_not_capture_or_ocr')
state=public_multimodal_state(read_multimodal_state(runtime_root=runtime),now=now)
req(any(x['item_id']=='screen1' and x['stale'] for x in state['items']),'public_state_exposes_staleness')
ctrl=process_era7_multimodal_control('inspect multimodal context status',runtime_root=runtime)
req(ctrl['active'] and ctrl['native_capture_deferred'],'multimodal_status_control')
compound=process_era7_multimodal_control('inspect multimodal context status and capture my screen',runtime_root=runtime)
req(compound['status']=='era7_multimodal_read_only_scope_expansion_rejected','compound_capture_scope_rejected')
req(ctrl['memory_modified'] is False and ctrl['authority_expanded'] is False,'multimodal_never_expands_authority')
pruned=prune_multimodal_evidence(scope='turn_end',event_id='prune1',runtime_root=runtime)
req(pruned['ok'] and pruned['removed_count']>=2,'turn_only_visual_evidence_pruned')
req(pruned['memory_candidates_created'] is False and pruned['memory_modified'] is False,'retention_prune_does_not_promote_to_memory')
prune_replay=prune_multimodal_evidence(scope='turn_end',event_id='prune1',runtime_root=runtime)
req(prune_replay['idempotent'] is True,'multimodal_prune_exactly_once')
print(json.dumps({'suite':'v2199.9-multimodal-context','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
