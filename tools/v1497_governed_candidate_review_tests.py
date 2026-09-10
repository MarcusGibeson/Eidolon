from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=tempfile.mkdtemp(prefix='eidolon-v1497-');os.environ['EIDOLON_DATA_DIR']=R;os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.governed_candidate_review import build_review_packet,installation_preview,admit_operator_installation
from conscious_agent.development_authority import issue_operator_authorization
p=f=0
def ck(n,c,d=''):
 global p,f
 if c:p+=1;print('PASS',n)
 else:f+=1;print('FAIL',n,d)
try:
 plan={'status':'plan_ready_for_operator_review','candidate_id':'c','plan_digest':'a'*64}
 change={'status':'workspace_changed','workspace_only':True,'active_source_modified':False,'plan_digest':'a'*64,'change_digest':'c'*64}
 verify={'verification_passed':True,'verification_digest':'d'*64}
 review=build_review_packet(plan=plan,change_receipt=change,verification=verify,source_manifest_digest='e'*64,rollback_digest='f'*64)
 ck('complete evidence produces review-ready packet',review['review_ready'],review)
 ck('review packet itself installs nothing',not review['installation_executed'] and review['operator_review_required'],review)
 preview=installation_preview(review,authoritative_source_digest='a'*64,candidate_source_digest='b'*64)
 ck('installation preview is non-mutating and rollback aware',preview['preview_ready'] and preview['would_replace_source'] and preview['preserve_private_runtime'] and not preview['installation_executed'],preview)
 blocked=admit_operator_installation(preview,operator_authorization_receipt=None,expected_preview_digest=preview['preview_digest']);ck('no operator approval means no admission',not blocked['admitted_for_external_installer'],blocked)
 phrase='Install reviewed candidate c.';receipt=issue_operator_authorization(stage='installation',subject_id='c',subject_digest=preview['preview_digest'],explicit_operator_text=phrase,expected_operator_text=phrase)
 tampered=admit_operator_installation(preview,operator_authorization_receipt=receipt,expected_preview_digest='wrong');ck('preview digest mismatch blocks installation admission',not tampered['admitted_for_external_installer'],tampered)
 admitted=admit_operator_installation(preview,operator_authorization_receipt=receipt,expected_preview_digest=preview['preview_digest']);ck('exact operator approval admits external installer only',admitted['admitted_for_external_installer'] and not admitted['installation_executed'] and not admitted['promotion_executed'],admitted)
 bad=build_review_packet(plan=plan,change_receipt=change,verification={'verification_passed':False,'verification_digest':'b'*64},source_manifest_digest='e'*64,rollback_digest='f'*64);ck('failed verification blocks review readiness',not bad['review_ready'],bad)
 print({'ok':f==0,'passed':p,'failed':f,'suite':'v1497-governed-candidate-review','content_free':True})
finally:shutil.rmtree(R,ignore_errors=True)
if f:raise SystemExit(1)
