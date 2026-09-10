from __future__ import annotations
import os,sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from dependency_packaging_reliability import *
from dependency_packaging_foundations import inventory_dependency_intent, AUTHORITY_FLAGS
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
base=inventory_dependency_intent(ROOT);intent=inspect_lock_and_configuration_intent(ROOT,base);req(intent['ok'],'intent_preserved');req(intent['changed_dependency_intent_files']==[],'no_intent_changes');req(intent['lock_configuration_content_exposed'] is False,'lock_content_minimized')
privacy=validate_source_package_privacy(ROOT);req(privacy['ok'],'package_privacy');req(privacy['forbidden_runtime_entry_count']==0,'no_runtime_entries');req(privacy['private_content_finding_count']==0,'no_private_content')
health=inspect_dependency_packaging_health(source_root=ROOT);req(health['ok'],'health_ready');req(all(health['checks'].values()),'health_checks')
handoff=build_dependency_packaging_operator_handoff(source_root=ROOT);req(handoff['ok'],'handoff_ready');req(handoff['next_bounded_unit']=='v1276 Architecture Boundary Extraction','next_v1276');req(handoff['v1276_started'] is False,'v1276_not_started');req(len(handoff['native_windows_validation'])>=8,'windows_handoff_scope')
with tempfile.TemporaryDirectory() as td:
    t=Path(td)
    env=create_disposable_clean_environment(t/'envbase',with_pip=False);req(env['ok'],'clean_env_ready');req(env['python_present'] is True,'clean_env_python');req(env['raw_environment_path_persisted'] is False,'clean_env_path_minimized');req(env['active_source_modified'] is False,'clean_env_no_source_mutation')
    z1=write_reproducible_source_zip(ROOT,t/'a.zip');z2=write_reproducible_source_zip(ROOT,t/'b.zip')
    req(z1['ok'] and z2['ok'],'repro_zip_written');req(z1['archive_sha256']==z2['archive_sha256'],'repro_zip_byte_identical');req(z1['package_file_count']==z2['package_file_count'],'repro_zip_file_count');req(z1['fixed_archive_metadata'] is True,'fixed_zip_metadata');req(z1['release_authorized'] is False and z1['package_published'] is False,'zip_not_release')
for k,v in AUTHORITY_FLAGS.items(): req(v is False,'authority_'+k)
print(json.dumps({'ok':True,'suite':'v1275.6-8-dependency-packaging-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
