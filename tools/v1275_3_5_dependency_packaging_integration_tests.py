from __future__ import annotations
import os,sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1275_fixture import prepared_dependency_environment_chain
from dependency_packaging import *
from dependency_packaging_foundations import build_reproducible_source_package_manifest
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory() as td:
    chain=prepared_dependency_environment_chain(Path(td))
    source=chain['source'];runtime=chain['runtime'];eid=chain['environment']['environment_id']
    a=inspect_dependency_packaging(source,environment_id=eid,runtime_root=runtime,now=1000.0)
    req(a['ok'],'assessment_ready');req(a['environment_record_valid'] is True,'environment_valid');req(a['environment_source_lineage_match'] is True,'environment_lineage');req(a['conflict_count']==0,'no_conflicts');req(a['package_file_count']>=8,'package_inventory_bound')
    request=prepare_clean_install_request(source,environment_id=eid,runtime_root=runtime,requirement_files=['requirements.txt'],now=1000.0)
    req(request['ok'],'clean_install_request_ready');req(request['status']=='clean_install_authorization_required','exact_authorization_required');req(request['environment_preflight_passed'] is True,'observed_environment_preflight');req(request['network_default_allowed'] is False,'network_default_denied');req(request['install_executed'] is False,'prepare_does_not_install')
    wrong=execute_clean_install_request(request,exact_authorization='go ahead',source_root=source,runner=lambda c,w,e:{'returncode':0})
    req(wrong['status']=='clean_install_exact_authorization_required','generic_approval_rejected');req(wrong['install_executed'] is False,'wrong_auth_no_install')
    calls=[]
    def runner(cmd,cwd,env):
        calls.append((cmd,cwd,dict(env)));return {'returncode':0,'stdout':'installed secret-ish output','stderr':''}
    done=execute_clean_install_request(request,exact_authorization=request['authorization_phrase'],source_root=source,runner=runner)
    req(done['ok'] and done['status']=='clean_install_verified','authorized_clean_install');req(done['authorization_consumed'] is True,'authorization_consumed');req(done['network_used'] is False,'offline_install');req(done['raw_installer_output_persisted'] is False,'installer_output_minimized');req(len(calls)==1,'runner_once');req('--no-index' in calls[0][0],'no_index_enforced');req(calls[0][2]['PIP_NO_INDEX']=='1','no_index_env')
    real_request=prepare_clean_install_request(source,environment_id=eid,runtime_root=runtime,requirement_files=['requirements-empty.txt'],now=1000.0)
    real_done=execute_clean_install_request(real_request,exact_authorization=real_request['authorization_phrase'],source_root=source)
    req(real_done['ok'] and real_done['status']=='clean_install_verified','real_disposable_offline_clean_install');req(real_done['install_executed'] is True,'real_install_executed');req(real_done['network_used'] is False,'real_install_offline')
    stale=prepare_clean_install_request(source,environment_id=eid,runtime_root=runtime,requirement_files=['requirements.txt'],now=1000.0)
    (source/'requirements-core.txt').write_text('requests>=2.31,<3\nidna>=3\n',encoding='utf-8')
    res=execute_clean_install_request(stale,exact_authorization=stale['authorization_phrase'],source_root=source,runner=runner)
    req(res['status']=='clean_install_stale_dependency_intent','stale_intent_blocked');req(len(calls)==1,'stale_no_runner')

m=build_reproducible_source_package_manifest(ROOT);r=verify_reproducible_package_manifest(ROOT,m);req(r['ok'],'real_manifest_reproducible');req(r['package_published'] is False,'verification_not_publish')
print(json.dumps({'ok':True,'suite':'v1275.3-5-dependency-packaging-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
