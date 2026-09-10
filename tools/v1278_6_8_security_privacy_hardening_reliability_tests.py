from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from security_privacy_hardening_foundations import *
from security_privacy_hardening import guard_governed_update_paths
from security_privacy_hardening_reliability import *
from package_integrity import source_package_bytes,package_privacy_summary_for_root,package_privacy_summary_for_zip
from isolated_self_modification_foundations import source_only_manifest
from privacy_security_secret_management_audit import scan_source_tree_for_secret_findings
from development_observability_reliability import inspect_development_observability_health
from v1278_fixture import write_malicious_zip,try_symlink
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
def denied(row,prefix):
    for k,v in AUTHORITY_FLAGS.items():req(row.get(k) is v,f'{prefix}_{k}')

def tree_digest(root):
    h=hashlib.sha256()
    for p in sorted(x for x in Path(root).rglob('*') if x.is_file() and '__pycache__' not in x.parts):
        h.update(p.relative_to(root).as_posix().encode());h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

before=tree_digest(ROOT);health=inspect_security_privacy_hardening_health(source_root=ROOT);after=tree_digest(ROOT);req(health['ok'],'health');req(before==after,'health_read_only');req(health['checks']['confirmed_or_likely_secrets_absent'],'health_secrets');req(health['checks']['package_private_content_absent'],'health_privacy');denied(health,'health_auth')
handoff=build_security_privacy_hardening_operator_handoff(source_root=ROOT);req(handoff['ok'],'handoff');req(handoff['next_bounded_unit']=='v1279 Operator Experience','next');req(handoff['v1279_started'] is False,'not_started');req(len(handoff['native_windows_validation'])>=10,'windows_scope');req(handoff['security_evidence_is_not_authorization'],'handoff_no_authority');denied(handoff,'handoff_auth')
obs=inspect_development_observability_health(source_root=ROOT);req(obs['ok'],'observability_retained')
with tempfile.TemporaryDirectory() as td:
    base=Path(td);src=base/'src';src.mkdir();(src/'safe.py').write_text('x=1\n');outside=base/'outside.txt';outside.write_text('api_key="REALISHSECRET1234567890"\n')
    if try_symlink(outside,src/'leak.py'):
        summary=package_privacy_summary_for_root(src);req(not summary['ok'] and summary['boundary_finding_count']>=1,'root_link_privacy_block')
        scan=scan_source_tree_for_secret_findings(src);req(scan['confirmed_or_likely_count']==0,'secret_scanner_does_not_follow_link');req(scan['classification_counts']['sensitive_metadata']>=1,'secret_scanner_link_metadata')
        try:source_package_bytes(src,'leak.py')
        except ValueError:req(True,'direct_package_symlink_read_block')
        else:raise AssertionError('package symlink read allowed')
        try:source_only_manifest(src)
        except ValueError:req(True,'source_manifest_link_block')
        else:raise AssertionError('source manifest link allowed')
    deep=src
    relparts=[]
    for i in range(12):
        name='segment_'+str(i)+'_'+'x'*15;relparts.append(name);deep=deep/name;deep.mkdir()
    leaf=deep/'file.py';leaf.write_text('x=1\n');rel='/'.join(relparts+['file.py']);r=inspect_contained_path(src,rel,require_exists=True,require_file=True);req(r['ok'],'long_path_contained')
    req(len(str(leaf))>200,'long_path_fixture')
    for kind in ['traversal','absolute','drive','backslash','casefold','symlink','runtime']:
        z=base/f'{kind}.zip';write_malicious_zip(z,kind);a=inspect_archive_structure(z);p=package_privacy_summary_for_zip(z);req(not a['ok'] if kind!='runtime' else True,f'archive_structure_{kind}');req(not p['ok'],f'archive_privacy_{kind}')
    project=base/'project';candidate=base/'candidate';project.mkdir();candidate.mkdir();(project/'pkg').mkdir();(candidate/'pkg').mkdir();(project/'pkg'/'a.py').write_text('a=1');(candidate/'pkg'/'a.py').write_text('a=2')
    req(guard_governed_update_paths(project,candidate,[{'relative_path':'pkg/a.py','action':'modify'}])['ok'],'guard_before_swap')
    old=project/'pkg';old.rename(project/'pkg_real')
    if try_symlink(base/'outside_dir',project/'pkg',directory=True):
        pass
    else:
        # target must exist on some platforms for a directory symlink fixture
        (base/'outside_dir').mkdir(exist_ok=True)
        try_symlink(base/'outside_dir',project/'pkg',directory=True)
    if (project/'pkg').is_symlink():
        try:guard_governed_update_paths(project,candidate,[{'relative_path':'pkg/a.py','action':'modify'}])
        except ValueError:req(True,'ancestor_swap_blocked')
        else:raise AssertionError('ancestor swap accepted')
    sep=inspect_runtime_source_separation(project,project/'runtime');req(not sep['ok'],'runtime_inside_source_block')
    sep2=inspect_runtime_source_separation(project,base/'runtime');req(sep2['ok'],'external_runtime_allowed')
for p in ['foo:bar','aux.txt','folder/lpt1.log','folder/name.','folder/name ']:
    try:validate_untrusted_relative_path(p)
    except ValueError:req(True,'windows_ambiguous_'+repr(p))
    else:raise AssertionError('windows ambiguous accepted '+p)
print(json.dumps({'ok':True,'suite':'v1278.6-8-security-privacy-hardening-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
