from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from broad_software_engineering import *
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v1699-integration-') as td:
 b=Path(td);r=b/'repo';(r/'pkg').mkdir(parents=True);(r/'tests').mkdir();(r/'pkg/core.py').write_text('def work(): return 1\n');(r/'pkg/service.py').write_text('from pkg.core import work\n');(r/'tests/test_core.py').write_text('from pkg.core import work\n');(r/'pyproject.toml').write_text('[project]\nname="x"\n')
 before={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file()}
 out=build_broad_software_engineering_assessment(r,changed_paths=['pkg/core.py'],candidate_version='v1699.9',runtime_root=b/'rt');a=out['assessment']
 req(out['ok'],'ok');req(a['manifest_consistent'],'manifest');req(a['language_count']>=1,'language');req('focused' in a['selected_test_kinds'],'tests');req(a['candidate_coherent'],'candidate');req(not a['tests_executed'] and not a['dependencies_installed'],'no_exec');req(not a['network_contacted'] and not a['provider_contacted'],'no_network');req(not a['source_modified'] and not a['installation_performed'],'no_mutation');req(not a['promotion_performed'] and not a['certification_performed'],'no_release');req(not a['native_windows_verified'],'native_deferred');req(not a['action_executed'] and not a['standing_authority_granted'],'authority')
 ctl=process_broad_software_engineering_control('inspect broad software engineering',project_root=r,changed_paths=['pkg/core.py'],runtime_root=b/'rt2');req(ctl['active'] and ctl['ok'],'control')
 missing=process_broad_software_engineering_control('inspect broad software engineering');req(missing['active'] and not missing['ok'],'root_required')
 reject=process_broad_software_engineering_control('inspect software engineering and install',project_root=r);req(reject['active'] and not reject['ok'],'scope_reject')
 ordinary=process_broad_software_engineering_control('how are you?');req(not ordinary['active'],'ordinary')
 after={p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file()};req(before==after,'source_immutable')
print(json.dumps({'suite':'v1699.9-broad-software-engineering-integration','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
