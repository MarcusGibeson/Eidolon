from __future__ import annotations
import os, sys, tempfile, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from dependency_packaging_foundations import *
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)

r=parse_requirement_line('Requests>=2.31,<3 ; python_version >= "3.11"',source_file='requirements-core.txt',line_number=3)
req(r['kind']=='requirement','parse_requirement');req(r['name']=='requests','normalize_name');req(len(r['specifiers'])==2,'parse_specifiers');req(r['has_marker'] is True and bool(r['marker_digest']),'marker_minimized');req('python_version' not in json.dumps(r),'marker_content_not_persisted')
i=parse_requirement_line('-r requirements-core.txt');req(i['kind']=='include' and i['relative_path']=='requirements-core.txt','parse_include')
try: parse_requirement_line('-r ../escape.txt'); raise AssertionError('escape_not_rejected')
except ValueError: C.append('include_escape_rejected')

good=[parse_requirement_line('demo>=1,<2'),parse_requirement_line('demo!=1.5')]
c=detect_dependency_conflicts(good);req(c['conflict_count']==0,'coherent_constraints')
bad=[parse_requirement_line('demo==1.0'),parse_requirement_line('demo==2.0')]
c=detect_dependency_conflicts(bad);req(c['conflict_count']==1 and c['conflicts'][0]['reason']=='incompatible_exact_pins','exact_pin_conflict')
bad2=[parse_requirement_line('demo>=3'),parse_requirement_line('demo<2')]
req(detect_dependency_conflicts(bad2)['conflict_count']==1,'bound_conflict')
bad3=[parse_requirement_line('demo @ https://example.invalid/demo.whl'),parse_requirement_line('demo>=1')]
req(detect_dependency_conflicts(bad3)['conflict_count']==1,'direct_reference_conflict')

with tempfile.TemporaryDirectory() as td:
    p=Path(td);(p/'requirements.txt').write_text('-r requirements-core.txt\n',encoding='utf-8');(p/'requirements-core.txt').write_text('requests>=2.31,<3\n',encoding='utf-8');(p/'requirements-test.txt').write_text('pytest>=8,<9\n',encoding='utf-8');(p/'pyproject.toml').write_text('[project]\nname="x"\n',encoding='utf-8');(p/'uv.lock').write_text('version=1\n',encoding='utf-8')
    inv=inventory_dependency_intent(p);req(inv['dependency_file_count']==5,'inventory_files');req(inv['declaration_count']==3,'inventory_declarations');req(inv['lock_file_count']==1,'lock_inventory');req(inv['configuration_file_count']==1,'config_inventory');req(inv['raw_dependency_file_contents_persisted'] is False,'contents_minimized')
    d1=inv['dependency_intent_digest'];d2=inventory_dependency_intent(p)['dependency_intent_digest'];req(d1==d2,'intent_deterministic')
    plan=build_dependency_change_plan(p,additions=['idna>=3'],target_file='requirements-core.txt');req(plan['ok'],'change_plan_ready');req(plan['addition_count']==1,'addition_count');req(plan['active_source_modified'] is False,'plan_no_source_mutation');req(plan['requires_separate_install_authorization'] is True,'install_authority_separate')
    blocked=build_dependency_change_plan(p,additions=['requests==1'],target_file='requirements-core.txt');req(blocked['ok'] is False and blocked['conflict_count']>=1,'conflicting_plan_blocked')

manifest=build_reproducible_source_package_manifest(ROOT);req(manifest['source_only'] is True,'source_only_manifest');req(manifest['runtime_data_included'] is False,'runtime_excluded');req(manifest['private_state_included'] is False,'private_excluded');req(manifest['package_file_count']>3000,'real_package_inventory');req(manifest['package_root']=='Eidolon','single_package_root_contract');req(manifest['package_manifest_digest']==build_reproducible_source_package_manifest(ROOT)['package_manifest_digest'],'package_manifest_deterministic')
for k,v in AUTHORITY_FLAGS.items(): req(v is False,'authority_'+k)
print(json.dumps({'ok':True,'suite':'v1275.0-2-dependency-packaging-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
