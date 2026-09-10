from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT)]
from product_quality_judgment_checkpoint import product_quality_judgment_checkpoint
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
r=product_quality_judgment_checkpoint(ROOT)
req(r['ok'],'checkpoint')
req(r['contract_version']=='v1289.9','version')
req(r['status']=='product_quality_judgment_checkpoint_ready','status')
req(all(r['checks'].values()),'all_checks')
req(r['checks']['six_dimensions'],'six_dimensions')
req(r['checks']['narrow_tests_not_product_readiness'],'tests_not_readiness')
req(r['checks']['quality_not_release_authority'],'not_release_authority')
req(r['checks']['review_packet_bridge'],'review_bridge')
req(r['checks']['native_operator_quality_review_pending'],'native_pending')
req(r['next']=='v1290 Cognitive Coding Checkpoint','next')
req(r['v1290_started'] is True and r['checks']['v1290_transition_coherent'],'v1290_transition_coherent')
req(r['read_only'] and not r['project_mutation_authorized'] and not r['release_authorized'],'readonly_no_authority')
print(json.dumps({'ok':True,'suite':'v1289.9-product-quality-judgment-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
