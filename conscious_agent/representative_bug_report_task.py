from __future__ import annotations
"""v1393 representative bug-report reproduction and repair task."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
from typing import Any
CONTRACT_VERSION='v1393.8';DIGEST=re.compile(r'^[a-f0-9]{64}$')
DENIED={'eidolon_source_mutation_authorized':False,'release_authorized':False,'promotion_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _tests(root:Path,timeout:int):
 st=time.monotonic()
 try:cp=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=root,capture_output=True,timeout=timeout,env={'PYTHONDONTWRITEBYTECODE':'1'})
 except Exception as e:return {'passed':False,'exit_code':None,'error_digest':_d(type(e).__name__),'duration_ms':int((time.monotonic()-st)*1000)}
 blob=(cp.stdout or b'')+(cp.stderr or b'');return {'passed':cp.returncode==0,'exit_code':cp.returncode,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)}
def _repro(root:Path,timeout:int):
 code='from money import format_currency; print(format_currency(-12.5), end="")'
 cp=subprocess.run([sys.executable,'-c',code],cwd=root,capture_output=True,timeout=timeout,env={'PYTHONDONTWRITEBYTECODE':'1'});out=(cp.stdout or b'').decode('utf-8','replace');return {'exit_code':cp.returncode,'observed_output_digest':hashlib.sha256((cp.stdout or b'')+(cp.stderr or b'')).hexdigest(),'defect_reproduced':out=='$12.50','expected_output_digest':hashlib.sha256(b'-$12.50').hexdigest()}
def run_bug_report_task(*,project_root:str|Path,bug_report:str,visual_evidence_digest:str,operator_authorized:bool,timeout_seconds:int=30)->dict[str,Any]:
 root=Path(project_root).expanduser().resolve();active=Path(__file__).resolve().parents[1];text=' '.join(str(bug_report or '').split())
 if not operator_authorized or not DIGEST.fullmatch(str(visual_evidence_digest or '')) or not re.search(r'negative|minus|refund',text,re.I) or not re.search(r'currency|dollar|\$',text,re.I):return {'ok':False,'status':'bug_report_context_invalid','action_executed':False,**DENIED}
 try:root.relative_to(active);return {'ok':False,'status':'bug_report_eidolon_source_blocked','action_executed':False,**DENIED}
 except ValueError:pass
 target=root/'money.py';reg=root/'tests'/'test_negative_currency.py'
 if not target.is_file() or reg.exists():return {'ok':False,'status':'bug_report_project_state_invalid','action_executed':False,**DENIED}
 baseline=_tests(root,timeout_seconds)
 if not baseline['passed']:return {'ok':False,'status':'bug_report_baseline_tests_failed','baseline_tests':baseline,'action_executed':False,**DENIED}
 try:repro=_repro(root,timeout_seconds)
 except Exception as e:return {'ok':False,'status':'bug_report_reproduction_failed','reason_digest':_d(type(e).__name__),'action_executed':False,**DENIED}
 if not repro['defect_reproduced']:return {'ok':False,'status':'bug_report_not_reproduced','reproduction':repro,'action_executed':False,**DENIED}
 original=target.read_text(encoding='utf-8');before=hashlib.sha256(original.encode()).hexdigest();needle='return f"${abs(amount):.2f}"'
 if needle not in original:return {'ok':False,'status':'bug_report_repair_pattern_not_grounded','reproduction':repro,'action_executed':False,**DENIED}
 fixed=original.replace(needle,'return f"-${abs(amount):.2f}" if amount < 0 else f"${amount:.2f}"',1)
 regression='''import unittest\nfrom money import format_currency\nclass NegativeCurrencyRegression(unittest.TestCase):\n    def test_negative_value_keeps_minus_sign(self): self.assertEqual(format_currency(-12.5), "-$12.50")\n    def test_positive_value_unchanged(self): self.assertEqual(format_currency(12.5), "$12.50")\n'''
 try:
  target.write_text(fixed,encoding='utf-8');reg.parent.mkdir(parents=True,exist_ok=True);reg.write_text(regression,encoding='utf-8');after_repro=_repro(root,timeout_seconds);final=_tests(root,timeout_seconds)
  repaired=after_repro['exit_code']==0 and after_repro['observed_output_digest']==after_repro['expected_output_digest'] and final['passed']
  if not repaired:raise RuntimeError('repair verification failed')
 except Exception as e:
  target.write_text(original,encoding='utf-8');reg.unlink(missing_ok=True);return {'ok':False,'status':'bug_report_repair_failed_rolled_back','failure_digest':_d(type(e).__name__),'reproduction':repro,'action_executed':True,**DENIED}
 core={'contract_version':CONTRACT_VERSION,'bug_report_digest':_d(text),'visual_evidence_digest':visual_evidence_digest,'target_path':'money.py','target_before_digest':before,'target_after_digest':hashlib.sha256(target.read_bytes()).hexdigest(),'baseline_tests':baseline,'reproduction':repro,'post_repair_reproduction':after_repro,'final_tests':final,'regression_test_path':'tests/test_negative_currency.py','natural_language_grounded':True,'visual_evidence_bound':True,'defect_reproduced_before_repair':True,'repair_verified':True,'action_executed':True,**DENIED};core['task_digest']=_d(core)
 return {'ok':True,'status':'bug_report_repaired','bug_report_task':core,'action_executed':True,**DENIED}
def process_bug_report_task_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show bug report task','inspect bug report task','show gamma bug repair'}:return {'active':False}
 rec=dict((project_state or {}).get('bug_report_task') or {});return {'active':True,'ok':bool(rec),'status':'bug_report_task_found' if rec else 'bug_report_task_missing','bug_report_task':rec,'action_executed':False,**DENIED}
