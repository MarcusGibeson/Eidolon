from __future__ import annotations
"""v1183.6-v1183.8 governed sandbox retesting and bounded repair results."""
import hashlib,json,subprocess,sys,time
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
SCHEMA_VERSION='1'; CONTRACT_VERSION='v1183.8'; MAX_TESTS=8; MAX_TIMEOUT_SECONDS=30
_ALLOWED={'python_compile','content_digest_match'}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def _bytes(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def _text(v:Any,n=260)->str:return ' '.join(str(v or '').split())[:n]
def _hex(v:Any)->str:
 t=_text(v,64).lower(); return t if len(t)==64 and all(c in '0123456789abcdef' for c in t) else ''
def _safe(v:Any)->str:
 r=_text(v).replace('\\','/'); p=PurePosixPath(r)
 if not r or r.startswith(('/','//')) or (len(r)>1 and r[1]==':') or any(x in {'','.','..','data','runtime','private','secrets','.git','sandbox'} for x in p.parts): return ''
 return p.as_posix()
def _base(): return {'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'sandbox_only':True,'production_source_modified':False,'source_modified':False,'provider_contacted':False,'model_contacted':False,'promotion_authorized':False,'installation_performed':False,'certification_performed':False,'release_authorized':False,'source_application_authorized':False,'content_free':True}
def review_sandbox_retest(draft:Mapping[str,Any],materialization:Mapping[str,Any],*,decision:str,operator_actor:str,requested_tests:Sequence[str])->dict[str,Any]:
 tests=list(dict.fromkeys(_text(x,40) for x in requested_tests if _text(x,40)))[:MAX_TESTS]; target=_safe(materialization.get('target_path')); dec=_text(decision,20).lower(); actor=_text(operator_actor,100)
 valid=(draft.get('contract_version')=='v1183.2' and materialization.get('contract_version')=='v1183.5' and materialization.get('materialization_status') in {'materialized','already_materialized'} and materialization.get('sandbox_repair_materialized') is True and _hex(draft.get('draft_digest'))==_hex(materialization.get('draft_digest')) and _hex(draft.get('replacement_digest'))==_hex(materialization.get('sandbox_target_digest')) and target==_safe(draft.get('target_path')))
 if not valid: result={**_base(),'review_status':'blocked','block_reason':'invalid_repair_materialization_lineage'}
 elif dec not in {'approve','reject','defer'}: result={**_base(),'review_status':'blocked','block_reason':'invalid_review_decision'}
 elif not actor: result={**_base(),'review_status':'blocked','block_reason':'missing_operator_actor'}
 elif not tests or any(x not in _ALLOWED for x in tests) or ('python_compile' in tests and not target.endswith('.py')): result={**_base(),'review_status':'blocked','block_reason':'unsupported_retest_request'}
 else:
  structural={'draft_digest':_hex(draft.get('draft_digest')),'materialization_receipt_digest':_hex(materialization.get('materialization_receipt_digest')),'target_path':target,'before_evidence_digest':_hex(draft.get('evidence_digest')),'baseline_target_digest':_hex(draft.get('baseline_target_digest')),'repaired_target_digest':_hex(materialization.get('sandbox_target_digest')),'requested_tests':tests,'decision':dec,'operator_actor_digest':_digest(actor),'retest_authorized':dec=='approve','single_use':True}
  result={**_base(),**structural,'review_status':{'approve':'approved_for_sandbox_retest','reject':'rejected','defer':'deferred'}[dec],'review_digest':_digest(structural)}
 result['review_receipt_digest']=_digest(result); return result
def execute_reviewed_sandbox_retest(draft:Mapping[str,Any],materialization:Mapping[str,Any],review:Mapping[str,Any],*,sandbox_root:str|Path,source_root:str|Path,timeout_seconds:int=10)->dict[str,Any]:
 target=_safe(materialization.get('target_path')); sandbox=Path(sandbox_root).resolve(); source=Path(source_root).resolve(); tests=list(review.get('requested_tests') or [])[:MAX_TESTS]
 valid=(review.get('contract_version')==CONTRACT_VERSION and review.get('review_status')=='approved_for_sandbox_retest' and review.get('retest_authorized') is True and review.get('single_use') is True and _hex(review.get('draft_digest'))==_hex(draft.get('draft_digest')) and _hex(review.get('materialization_receipt_digest'))==_hex(materialization.get('materialization_receipt_digest')) and _safe(review.get('target_path'))==target)
 if not valid:return _blocked('invalid_retest_review_binding')
 if sandbox==source or sandbox in source.parents or source in sandbox.parents:return _blocked('sandbox_not_isolated')
 path=sandbox.joinpath(*PurePosixPath(target).parts)
 if not path.is_file() or path.is_symlink():return _blocked('sandbox_target_missing_or_unsafe')
 observed=_bytes(path.read_bytes()); expected=_hex(materialization.get('sandbox_target_digest'))
 if observed!=expected:return _blocked('sandbox_target_drift',expected_target_digest=expected,observed_target_digest=observed)
 rows=[]; started=time.monotonic(); timeout=max(1,min(int(timeout_seconds),MAX_TIMEOUT_SECONDS))
 for test in tests:
  if test=='content_digest_match': rows.append({'test':test,'status':'passed','result_digest':observed}); continue
  try:
   cp=subprocess.run([sys.executable,'-I','-m','py_compile',str(path)],cwd=sandbox,env={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':str(sandbox/'.eidolon_pycache')},capture_output=True,timeout=timeout,check=False)
   rows.append({'test':test,'status':'passed' if cp.returncode==0 else 'failed','error_class':'' if cp.returncode==0 else 'python_compile_failed'})
  except subprocess.TimeoutExpired: rows.append({'test':test,'status':'timed_out','error_class':'test_timeout'})
 status='passed' if all(r['status']=='passed' for r in rows) else ('timed_out' if any(r['status']=='timed_out' for r in rows) else 'failed')
 result={**_base(),'retest_status':status,'tests_rerun':True,'retest_authorized':True,'single_use_consumed':True,'target_path':target,'draft_digest':_hex(draft.get('draft_digest')),'materialization_receipt_digest':_hex(materialization.get('materialization_receipt_digest')),'review_digest':_hex(review.get('review_digest')),'before_evidence_digest':_hex(draft.get('evidence_digest')),'repaired_target_digest':observed,'test_count':len(rows),'test_results':rows,'elapsed_ms':int((time.monotonic()-started)*1000)}
 result['retest_receipt_digest']=_digest(result); return result
def _blocked(reason:str,**kw:Any)->dict[str,Any]:
 r={**_base(),'retest_status':'blocked','tests_rerun':False,'retest_authorized':False,'block_reason':reason,**kw};r['retest_receipt_digest']=_digest(r);return r
def build_bounded_repair_result(draft:Mapping[str,Any],materialization:Mapping[str,Any],retest:Mapping[str,Any])->dict[str,Any]:
 valid=(retest.get('contract_version')==CONTRACT_VERSION and _hex(retest.get('draft_digest'))==_hex(draft.get('draft_digest')) and _hex(retest.get('materialization_receipt_digest'))==_hex(materialization.get('materialization_receipt_digest')))
 if not valid:r={**_base(),'result_status':'blocked','block_reason':'invalid_retest_lineage'}
 else:
  rs=retest.get('retest_status'); original=_text(draft.get('failure_code'),80)
  classification='repair_succeeded' if rs=='passed' else ('original_failure_persists' if (rs=='failed' and original=='python_compile_failure_observed') or (rs=='timed_out' and original=='sandbox_test_timeout_observed') or (rs=='blocked' and original=='sandbox_test_execution_blocked') else 'regression_or_different_failure')
  r={**_base(),'result_status':'complete','repair_classification':classification,'target_path':_safe(draft.get('target_path')),'draft_digest':_hex(draft.get('draft_digest')),'before_evidence_digest':_hex(draft.get('evidence_digest')),'after_retest_receipt_digest':_hex(retest.get('retest_receipt_digest')),'before_target_digest':_hex(draft.get('baseline_target_digest')),'after_target_digest':_hex(materialization.get('sandbox_target_digest')),'original_failure_code':original,'after_status':rs,'regression_detected':classification=='regression_or_different_failure','repair_accepted':classification=='repair_succeeded','operator_review_required':True,'rollback_available':materialization.get('rollback_artifact_digest_verified') is True,'rollback_executed':False}
 r['repair_result_digest']=_digest(r);return r
def sandbox_repair_result_public_summary(result:Mapping[str,Any])->dict[str,Any]:
 allowed={'schema_version','contract_version','result_status','block_reason','repair_classification','target_path','draft_digest','before_evidence_digest','after_retest_receipt_digest','before_target_digest','after_target_digest','original_failure_code','after_status','regression_detected','repair_accepted','operator_review_required','rollback_available','rollback_executed','repair_result_digest'}
 s={k:result[k] for k in allowed if k in result};s.update({'content_free':True,'raw_source_included':False,'stdout_included':False,'stderr_included':False,'production_source_modified':False,'authority_granted':False});s['summary_digest']=_digest(s);return s
