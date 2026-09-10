from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2399-int-data-')
from era9_learning_collaboration_self_model import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from release_authority import WORKING_SOURCE_VERSION
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2399-int-runtime-'))
snap=build_era9_snapshot(runtime_root=runtime)
req(snap['ok'] and snap['status']=='era9_integrated_mind_snapshot','era9_snapshot_available')
req(snap['verified_outcomes_not_raw_logs'],'learning_evidence_boundary_visible')
req(snap['preferences_do_not_define_identity'],'preference_identity_boundary_visible')
req(snap['collaboration_does_not_replace_execution_ownership'],'collaboration_owner_boundary_visible')
req(snap['self_claims_require_evidence'],'self_model_evidence_boundary_visible')
req(snap['self_model']['working_source_version']==WORKING_SOURCE_VERSION,'snapshot_uses_current_release_authority')
ctrl=process_era9_control('show era9 integrated mind status',runtime_root=runtime)
req(ctrl['active'] and ctrl['ok'],'direct_era9_control')
blocked=process_era9_control('show era9 integrated mind status and install it',runtime_root=runtime)
req(blocked['active'] and blocked['status']=='era9_read_only_scope_expansion_rejected','compound_authority_rejected')
turn=process_ordinary_chat_development_turn('show era9 integrated mind status',runtime_root=runtime)
req(turn.get('active') is True and turn.get('status')=='era9_integrated_mind_snapshot','ordinary_chat_routes_era9')
compound=process_ordinary_chat_development_turn('show era9 integrated mind status and install it',runtime_root=runtime)
req(compound.get('status')=='era9_read_only_scope_expansion_rejected','ordinary_chat_rejects_compound')
ordinary=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
req('process_era9_control' in ordinary,'era9_uses_existing_ordinary_chat_boundary')
runtime_text=(ROOT/'conscious_agent/conversation_runtime.py').read_text(encoding='utf-8')
req(runtime_text.count('build_private_adaptation_prompt(')>=2,'preferences_integrated_in_both_provider_paths')
req(runtime_text.count('era9_preference_adaptation["prompt_section"]')>=2,'private_preferences_reach_provider_prompt')
req(all(not snap[k] for k in ('model_training_performed','memory_mutated','source_modified','candidate_merged','tool_executed','installation_authorized','promotion_authorized','authority_expanded')),'integrated_era9_no_side_effects')
print(json.dumps({'suite':'v2399.9-era9-integrated-mind','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
