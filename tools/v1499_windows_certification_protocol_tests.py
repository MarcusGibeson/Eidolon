from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=tempfile.mkdtemp(prefix='eidolon-v1499-');os.environ['EIDOLON_DATA_DIR']=R;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.windows_certification_protocol import REQUIRED_NATIVE_CHECKS,build_windows_certification_protocol,seal_windows_receipt,seal_soak_sample,evaluate_windows_receipts,soak_summary
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 proto=build_windows_certification_protocol(candidate_zip_sha256='a'*64,source_manifest_sha256='b'*64)
 ck('protocol binds exact candidate and source manifest',proto['candidate_zip_sha256']=='a'*64 and proto['source_manifest_sha256']=='b'*64,proto)
 ck('protocol forbids model management and requires external runtime',not proto['model_install_delete_switch_allowed'] and proto['private_runtime_must_be_external'],proto)
 partial=evaluate_windows_receipts(proto,[seal_windows_receipt(proto,check='compile',passed=True,platform='win32',execution_digest='1'*64)]);ck('partial Windows evidence cannot certify',not partial['evidence_complete'] and 'desktop_launch' in partial['missing_checks'],partial)
 linux=[seal_windows_receipt(proto,check=name,passed=True,platform='linux',execution_digest=f'{i:x}'*64 if i<10 else 'a'*64) for i,name in enumerate(REQUIRED_NATIVE_CHECKS,1)];wrong=evaluate_windows_receipts(proto,linux);ck('non-Windows receipts cannot satisfy native gate',not wrong['evidence_complete'] and not wrong['native_windows_receipts'],wrong)
 wins=[seal_windows_receipt(proto,check=name,passed=True,platform='win32',execution_digest=('abcdef0123456789'*4),first_visible_ms=500 if name=='ordinary_chat' else 0,total_ms=900 if name=='ordinary_chat' else 0,cold=False) for name in REQUIRED_NATIVE_CHECKS];complete=evaluate_windows_receipts(proto,wins)
 ck('complete native receipts can complete evidence set',complete['evidence_complete'] and complete['native_windows_receipts'],complete)
 ck('complete evidence still cannot self-certify install or promote',not complete['certification_granted'] and not complete['installation_authorized'] and not complete['promotion_authorized'],complete)
 forged=evaluate_windows_receipts(proto,[{'check':name,'passed':True,'platform':'win32'} for name in REQUIRED_NATIVE_CHECKS]);ck('unsealed self-asserted Windows rows are rejected',not forged['evidence_complete'] and forged['invalid_receipt_count']==len(REQUIRED_NATIVE_CHECKS),forged)
 soak=soak_summary([seal_soak_sample(iteration=i,passed=True,duplicate_operations=0,execution_digest=f'{i:064x}') for i in range(50)]);ck('content-free soak requires sealed zero-failure evidence',soak['soak_passed'] and soak['sample_count']==50,soak)
 bad=soak_summary([seal_soak_sample(iteration=1,passed=True,duplicate_operations=1,execution_digest='1'*64)]);ck('duplicate operation fails soak',not bad['soak_passed'],bad)
 forged_soak=soak_summary([{'iteration':1,'passed':True,'duplicate_operations':0}]);ck('unsealed soak assertion is rejected',not forged_soak['soak_passed'] and forged_soak['invalid_sample_count']==1,forged_soak)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1499-windows-certification-protocol','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
