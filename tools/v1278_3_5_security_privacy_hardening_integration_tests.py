from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from security_privacy_hardening_foundations import AUTHORITY_FLAGS,inspect_archive_structure
from security_privacy_hardening import *
from package_integrity import source_package_bytes, package_privacy_summary_for_zip
from dependency_packaging_reliability import write_reproducible_source_zip
from dependency_packaging_foundations import inventory_requirement_files
from v1278_fixture import write_malicious_zip,try_symlink
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
def denied(row,prefix):
    for k,v in AUTHORITY_FLAGS.items():req(row.get(k) is v,f'{prefix}_{k}')

health=inspect_security_privacy_hardening(ROOT);req(health['ok'],'real_health');req(health['confirmed_or_likely_secret_count']==0,'real_no_secrets');req(health['package_private_content_finding_count']==0,'real_package_private_clear');req(health['source_file_count']>3000,'real_source_inventory');req(health['package_file_count']>3000,'real_package_inventory');req(not health['raw_paths_returned'] and not health['secret_values_returned'],'real_minimized');denied(health,'real_auth')
raw=source_package_bytes(ROOT,'README_NEXT_STEPS.md');req(raw.startswith(b'# Eidolon Next Steps'),'package_bytes_valid')
for bad in ['../README_NEXT_STEPS.md','C:/secret.txt','data/memories.json']:
    try:source_package_bytes(ROOT,bad)
    except (ValueError,FileNotFoundError):req(True,'package_read_block_'+bad)
    else:raise AssertionError('package read accepted '+bad)
with tempfile.TemporaryDirectory() as td:
    base=Path(td);out=base/'eidolon.zip';written=write_reproducible_source_zip(ROOT,out);req(written['ok'],'real_zip_written');arc=inspect_archive_structure(out);req(arc['ok'],'real_zip_structure');privacy=package_privacy_summary_for_zip(out);req(privacy['ok'],'real_zip_privacy');req(privacy['archive_structure_ok'],'real_zip_boundary')
    traversal=base/'traversal.zip';write_malicious_zip(traversal,'traversal');privacy=package_privacy_summary_for_zip(traversal);req(not privacy['ok'],'malicious_zip_privacy_block');req(not privacy['archive_structure_ok'],'malicious_zip_structure_block')
    src=base/'source';cand=base/'candidate';src.mkdir();cand.mkdir();(src/'pkg').mkdir();(cand/'pkg').mkdir();(src/'pkg'/'a.py').write_text('a=1\n');(cand/'pkg'/'a.py').write_text('a=2\n')
    changes=[{'relative_path':'pkg/a.py','action':'modify'}]
    guard=guard_governed_update_paths(src,cand,changes);req(guard['ok'] and guard['changed_file_count']==1,'update_guard');denied(guard,'update_guard_auth')
    app=guard_controlled_application_paths(src,cand,[{'relative_path':'pkg/a.py','operation':'modify'}]);req(app['ok'],'application_guard')
    outside=base/'outside';outside.mkdir();(outside/'a.py').write_text('bad')
    if try_symlink(outside,src/'linkpkg',directory=True):
        try:guard_governed_update_paths(src,cand,[{'relative_path':'linkpkg/a.py','action':'modify'}])
        except ValueError:req(True,'update_symlink_block')
        else:raise AssertionError('update symlink accepted')
    dep=base/'dep';dep.mkdir();(dep/'requirements.txt').write_text('-r nested.txt\n');(dep/'nested.txt').write_text('x==1\n');inv=inventory_requirement_files(dep);req(inv['file_count']==2,'dependency_normal_include')
    outside_req=base/'outside-req.txt';outside_req.write_text('evil==1\n')
    (dep/'requirements.txt').write_text('-r ../outside-req.txt\n')
    try:inventory_requirement_files(dep)
    except ValueError:req(True,'dependency_escape_block')
    else:raise AssertionError('dependency traversal accepted')
    if (dep/'requirements.txt').exists():(dep/'requirements.txt').unlink()
    if try_symlink(outside_req,dep/'requirements.txt'):
        try:inventory_requirement_files(dep)
        except ValueError:req(True,'dependency_link_block')
        else:raise AssertionError('dependency link accepted')
pre=prepare_security_hardened_package_preflight(ROOT,ROOT.parent/'candidate.zip');req(pre['ok'] and not pre['package_created'],'package_preflight');denied(pre,'pre_auth')
try:prepare_security_hardened_package_preflight(ROOT,ROOT/'inside.zip')
except ValueError:req(True,'package_output_inside_source_block')
else:raise AssertionError('inside package output accepted')
for generic in ['go ahead','proceed','do it']:
    r=validate_generic_approval_is_non_authorizing(generic,'AUTHORIZE EIDOLON SELF UPDATE selfupdate_123 0123456789abcdef');req(not r['ok'],'generic_non_authority_'+generic);denied(r,'generic_auth_'+generic)
pr=public_provider_security_receipt(provider_identifier='remote-x',provider_kind='remote',status='error',raw_payload='prompt=private\nresponse=private\napi_key=SECRET');req(pr['payload_present'] and not pr['payload_returned'],'provider_receipt');req('private' not in json.dumps(pr) and 'SECRET' not in json.dumps(pr),'provider_content_absent');denied(pr,'provider_auth')
print(json.dumps({'ok':True,'suite':'v1278.3-5-security-privacy-hardening-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
