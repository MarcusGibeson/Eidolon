from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from portable_release_upgrade_engineering import *
import portable_release_upgrade_engineering as release_engineering
checks=[]
def req(v,n):checks.append(n);assert v,n

def tree(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def make(base,name,value):
 r=base/name;(r/'pkg').mkdir(parents=True);(r/'tests').mkdir();(r/'pkg/core.py').write_text(f'VALUE={value}\n');(r/'tests/test_core.py').write_text('from pkg.core import VALUE\n');(r/'README.md').write_text(f'# {name}\n');return r
with tempfile.TemporaryDirectory(prefix='eidolon-v1699-9-') as td:
 base=Path(td);old=make(base,'old',1);new=make(base,'new',2);(new/'CHANGELOG.md').write_text('changed\n');rt=base/'rt'
 (old/'data').mkdir();(old/'data/private-runtime.json').write_text('{"private":true}')
 old_before=tree(old);new_before=tree(new)
 candidate_result=build_candidate_coherence(new,candidate_version='v1699.9',changed_paths=['pkg/core.py','CHANGELOG.md'],migration_declarations=[{'migration_id':'none-required','kind':'runtime_schema','required':False,'backward_compatible':True,'rollback_supported':True}],known_limitations=['Native Windows upgrade still requires Desktop evidence.'],runtime_root=rt)
 c=candidate_result['candidate'];req(candidate_result['ok'],'candidate_ok');req(c['candidate_version']=='v1699.9','candidate_version');req(c['source_file_count']==4,'candidate_files');req(c['changed_path_count']==2 and c['unknown_changed_path_count']==0,'changed_paths');req(c['migration_count']==1 and c['required_migration_count']==0,'migration_decl');req(c['known_limitation_count']==1,'limitations');req(c['source_only'] and c['candidate_coherent'],'coherent');req(c['privacy_finding_count']==0,'privacy');req(not c['installation_performed'] and not c['promotion_performed'] and not c['certification_performed'],'candidate_authority');req(not c['source_paths_exposed'] and not c['raw_source_content_exposed'],'candidate_redacted');req(not c['action_executed'] and not c['standing_authority_granted'],'candidate_no_authority')
 loaded=load_candidate_coherence(c['candidate_id'],runtime_root=rt);req(loaded['candidate_id']==c['candidate_id'],'candidate_restart')
 unknown=build_candidate_coherence(new,candidate_version='v1699.9',changed_paths=['missing.py'],runtime_root=rt);req(not unknown['ok'] and unknown['candidate']['unknown_changed_path_count']==1,'unknown_changed_blocked')
 risky=base/'risky';risky.mkdir();(risky/'main.py').write_text('x=1\n');(risky/'runtime').mkdir();(risky/'runtime/state.json').write_text('{}')
 risk=build_candidate_coherence(risky,candidate_version='vX',runtime_root=rt);req(not risk['ok'] and not risk['candidate']['source_only'],'runtime_privacy_blocked')

 original_sha=release_engineering._sha
 hashed_private=[]
 def source_only_sha(path):
  if path.is_relative_to(old) and 'data' in path.relative_to(old).parts:hashed_private.append(path)
  return original_sha(path)
 release_engineering._sha=source_only_sha
 try:
  sim=simulate_upgrade_lifecycle(baseline_root=old,target_root=new,simulation_root=base/'sim1',runtime_root=rt)
 finally:
  release_engineering._sha=original_sha
 req(not hashed_private,'private_runtime_not_hashed')
 s=sim['simulation'];req(sim['ok'],'simulation_ok');req(s['upgraded_before_rollback'],'upgrade_happened_disposable');req(s['rollback_restored_baseline'],'rollback');req(s['baseline_source_unchanged'] and s['target_source_unchanged'],'sources_unchanged');req(not s['live_installation_touched'] and s['simulation_root_external'],'simulation_boundary');req(not s['migration_executed'] and not s['provider_contacted'],'no_native_sideeffects');req(not s['installation_authority_granted'] and not s['promotion_authority_granted'],'simulation_authority')
 interrupted=simulate_upgrade_lifecycle(baseline_root=old,target_root=new,simulation_root=base/'sim2',interrupt_after_files=1,runtime_root=rt);si=interrupted['simulation'];req(interrupted['ok'] and si['interrupted'],'interruption_recovered');req(not si['upgraded_before_rollback'],'interrupted_not_upgraded');req(si['rollback_restored_baseline'],'interrupted_rollback')
 nested=simulate_upgrade_lifecycle(baseline_root=old,target_root=new,simulation_root=old/'sim',runtime_root=rt);req(not nested['ok'] and nested['status']=='simulation_root_inside_source_rejected','nested_sim_rejected')
 gate=build_engineering_gate_preparation(candidate=c,simulations=[s,si],runtime_root=rt)['gate_preparation'];req(gate['ready_for_desktop_gate'],'gate_ready');req(gate['rollback_simulation_passed'] and gate['source_immutability_passed'],'gate_portable_evidence');req(not gate['native_windows_verified'] and not gate['native_providers_verified'],'gate_native_deferred');req(not gate['desktop_packaging_verified'] and not gate['live_upgrade_verified'],'gate_live_deferred');req(not gate['operator_trial_completed'],'gate_operator_deferred');req(not gate['promotion_performed'] and not gate['installation_performed'],'gate_no_release_action');req(not gate['action_executed'] and not gate['standing_authority_granted'],'gate_authority')
 req(tree(old)==old_before and tree(new)==new_before,'source_immutable')
print(json.dumps({'suite':'v1699.9-release-upgrade-engineering-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
