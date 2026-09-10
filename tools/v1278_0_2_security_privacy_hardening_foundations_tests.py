from __future__ import annotations
import json, os, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from security_privacy_hardening_foundations import *
from v1278_fixture import write_safe_zip,write_malicious_zip,try_symlink
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)

def denied(row,prefix):
    for k,v in AUTHORITY_FLAGS.items():req(row.get(k) is v,f'{prefix}_{k}')

contract=build_security_privacy_hardening_contract();req(contract['ok'],'contract');req(contract['contract_version']=='v1278.2','contract_version');req(all(contract['checks'].values()),'contract_checks');denied(contract,'contract_auth')
for good in ['README.md','conscious_agent/module.py','docs/release/V1278.md','a-b_c/123.txt']:
    req(validate_untrusted_relative_path(good)==good,f'valid_{good}')
for bad in ['', '../x','a/../x','/abs','C:/x','a:b','a\\b','NUL.txt','com1','a.','a ','./x']:
    try:validate_untrusted_relative_path(bad)
    except ValueError:req(True,'reject_'+repr(bad))
    else:raise AssertionError('accepted_'+bad)
with tempfile.TemporaryDirectory() as td:
    base=Path(td);src=base/'src';runtime=base/'runtime';src.mkdir();runtime.mkdir();(src/'a').mkdir();(src/'a'/'b.txt').write_text('x')
    row=inspect_contained_path(src,'a/b.txt',require_exists=True,require_file=True);req(row['ok'] and row['exists'],'contained');req(not row['raw_path_returned'],'contained_minimized');denied(row,'path_auth')
    sep=inspect_runtime_source_separation(src,runtime);req(sep['ok'] and not sep['overlap'],'separate');denied(sep,'sep_auth')
    overlap=inspect_runtime_source_separation(src,src/'runtime');req(not overlap['ok'] and overlap['overlap'],'overlap_blocked')
    outside=base/'outside';outside.mkdir();(outside/'secret.txt').write_text('secret')
    if try_symlink(outside,src/'linked',directory=True):
        try:inspect_contained_path(src,'linked/secret.txt',require_exists=True)
        except ValueError:req(True,'symlink_ancestor_rejected')
        else:raise AssertionError('symlink ancestor accepted')
        surface=inspect_untrusted_project_surface(src);req(not surface['ok'] and surface['link_or_reparse_finding_count']>=1,'surface_link_blocked');req(not surface['file_contents_read'],'surface_content_free')
    (src/'.env').write_text('DO_NOT_READ=abc')
    surface=inspect_untrusted_project_surface(src);req(surface['sensitive_name_finding_count']>=1,'sensitive_name_detected');req(surface['raw_paths_returned'] is False,'surface_paths_minimized')
    safe=base/'safe.zip';write_safe_zip(safe);arc=inspect_archive_structure(safe);req(arc['ok'],'safe_archive');req(not arc['archive_contents_extracted'],'archive_no_extract');denied(arc,'archive_auth')
    for kind in ['traversal','absolute','drive','backslash','casefold','symlink']:
        z=base/f'{kind}.zip';write_malicious_zip(z,kind);r=inspect_archive_structure(z);req(not r['ok'],f'archive_{kind}_blocked');req(r['error_count']>=1,f'archive_{kind}_error')
exact='AUTHORIZE EIDOLON TEST abc 0123456789abcdef'
for generic in ['go ahead','proceed','do it','yes','continue','keep going']:
    r=validate_exact_authorization_boundary(generic,exact);req(not r['ok'] and r['generic_approval_rejected'],f'generic_{generic}')
r=validate_exact_authorization_boundary(exact,exact);req(r['ok'] and not r['authorization_phrase_returned'],'exact_auth');denied(r,'exact_auth_flags')
provider=build_provider_material_receipt(provider_identifier='ollama-local',provider_kind='local',status='available',raw_payload='Bearer SUPERSECRET payload text');req(provider['payload_present'],'payload_present');req(provider['payload_digest'],'payload_digest');req(provider['payload_returned'] is False and provider['payload_persisted'] is False,'payload_hidden');req('SUPERSECRET' not in json.dumps(provider),'payload_not_leaked');denied(provider,'provider_auth')
mini=validate_content_minimized_evidence({'phase':'verify','count':2});req(mini['ok'],'minimized_ok')
blocked=validate_content_minimized_evidence({'phase':'verify','provider_payload':'secret'});req(not blocked['ok'] and blocked['private_field_count']==1,'private_field_rejected');req(blocked['private_field_names_returned'] is False,'private_names_hidden')
print(json.dumps({'ok':True,'suite':'v1278.0-2-security-privacy-hardening-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
