from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2499-data-')
from era10_product_autonomy import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from release_authority import WORKING_SOURCE_VERSION
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2499-runtime-'))
snap=build_era10_snapshot(runtime_root=runtime)
req(snap['ok'] and snap['status']=='era10_product_autonomy_snapshot','era10_snapshot_ready')
req(snap['release']['working_source_version']==WORKING_SOURCE_VERSION,'snapshot_uses_current_release_truth')
req(snap['product']['chat_first'],'product_maturity_integrated')
req(snap['unattended']['preparation_not_execution'],'unattended_boundary_integrated')
req(snap['developer_beta']['final_state']=='review_ready' and snap['developer_beta']['installation_out_of_scope'],'developer_beta_boundary_integrated')
req(snap['benchmark']['native_certification_required'],'benchmark_native_gate_visible')
ctrl=process_era10_control('show era10 product autonomy status',runtime_root=runtime)
req(ctrl['active'] and ctrl['ok'],'direct_era10_control')
ctrl2=process_era10_control('show v2500 benchmark preparation status',runtime_root=runtime)
req(ctrl2['active'] and ctrl2['ok'],'benchmark_control_alias')
blocked=process_era10_control('show era10 product autonomy status and install it',runtime_root=runtime)
req(blocked['active'] and blocked['status']=='era10_read_only_scope_expansion_rejected','compound_install_rejected')
turn=process_ordinary_chat_development_turn('show bounded autonomy status',runtime_root=runtime)
req(turn.get('active') is True and turn.get('status')=='era10_product_autonomy_snapshot','ordinary_chat_routes_era10')
compound=process_ordinary_chat_development_turn('show bounded autonomy status and promote it',runtime_root=runtime)
req(compound.get('status')=='era10_read_only_scope_expansion_rejected','ordinary_chat_compound_scope_rejected')
ordinary=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
req('process_era10_control' in ordinary,'era10_reuses_ordinary_chat_boundary')
verify=(ROOT/'tools/release_verify.py').read_text(encoding='utf-8')
req('V2401_BROWSER_FOCUSED_SUITES' in verify,'era10_registered_with_full_verifier')
registry=(ROOT/'conscious_agent/checkpoint_registry.py').read_text(encoding='utf-8')
req('v2499_9_era10_integrated_product_autonomy_tests.py' in registry,'era10_checkpoint_registered')
req(all(not snap[k] for k in ('background_work_executed','tool_executed','provider_contacted','source_modified','candidate_installed','candidate_promoted','benchmark_certified','authority_expanded')),'integrated_era10_no_side_effect_authority')
print(json.dumps({'suite':'v2499.9-era10-integrated-product-autonomy','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
