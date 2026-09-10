from __future__ import annotations
"""v1392 representative bounded feature addition to an unfamiliar Python project."""
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
from typing import Any
CONTRACT_VERSION='v1392.8'
DENIED={'eidolon_source_mutation_authorized':False,'release_authorized':False,'promotion_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _run_tests(root:Path,timeout:int)->dict[str,Any]:
 st=time.monotonic()
 try:cp=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=root,capture_output=True,timeout=timeout,env={'PYTHONDONTWRITEBYTECODE':'1'})
 except Exception as e:return {'passed':False,'exit_code':None,'error_digest':_d(type(e).__name__),'duration_ms':int((time.monotonic()-st)*1000)}
 blob=(cp.stdout or b'')+(cp.stderr or b'');return {'passed':cp.returncode==0,'exit_code':cp.returncode,'output_digest':hashlib.sha256(blob[:1048576]).hexdigest(),'duration_ms':int((time.monotonic()-st)*1000)}
def run_existing_project_feature(*,project_root:str|Path,request:str,operator_authorized:bool,target_file:str='src/text_utils.py',timeout_seconds:int=30)->dict[str,Any]:
 root=Path(project_root).expanduser().resolve();active=Path(__file__).resolve().parents[1];text=' '.join(str(request or '').split())
 if not operator_authorized or not root.is_dir() or not re.search(r'\bslugify\b',text,re.I):return {'ok':False,'status':'existing_feature_not_authorized_or_unsupported','action_executed':False,**DENIED}
 try:root.relative_to(active);return {'ok':False,'status':'existing_feature_eidolon_source_blocked','action_executed':False,**DENIED}
 except ValueError:pass
 rel=Path(target_file)
 if rel.is_absolute() or '..' in rel.parts:return {'ok':False,'status':'existing_feature_target_invalid','action_executed':False,**DENIED}
 target=(root/rel).resolve();new_test=root/'tests'/'test_slugify.py'
 try:target.relative_to(root)
 except ValueError:return {'ok':False,'status':'existing_feature_target_escape','action_executed':False,**DENIED}
 if not target.is_file() or new_test.exists():return {'ok':False,'status':'existing_feature_target_state_invalid','action_executed':False,**DENIED}
 original=target.read_text(encoding='utf-8');before_digest=hashlib.sha256(original.encode()).hexdigest()
 if 'def slugify(' in original:return {'ok':False,'status':'existing_feature_already_present','action_executed':False,**DENIED}
 baseline=_run_tests(root,timeout_seconds)
 if not baseline['passed']:return {'ok':False,'status':'existing_feature_baseline_tests_failed','baseline_tests':baseline,'action_executed':False,**DENIED}
 uses_annotations=bool(re.search(r'def\s+\w+\([^)]*:\s*str[^)]*\)\s*->\s*str',original));reuses_normalizer='def normalize_text(' in original
 modified=original
 if not re.search(r'^import re\s*$',modified,re.M): modified='import re\n'+modified
 annotation='text: str' if uses_annotations else 'text';ret=' -> str' if uses_annotations else ''
 body='''\n\ndef slugify(%s)%s:\n    """Return a lowercase, hyphen-separated URL slug."""\n    value = %s\n    value = re.sub(r"[^a-z0-9]+", "-", value)\n    return value.strip("-")\n'''%(annotation,ret,'normalize_text(text)' if reuses_normalizer else '" ".join(text.strip().lower().split())')
 modified=modified.rstrip()+body
 test='''import unittest\nfrom src.text_utils import slugify\n\nclass SlugifyTests(unittest.TestCase):\n    def test_slugify_words_and_symbols(self):\n        self.assertEqual(slugify("  Hello, Existing Project!  "), "hello-existing-project")\n    def test_slugify_collapses_separators(self):\n        self.assertEqual(slugify("one___two   three"), "one-two-three")\n\nif __name__ == "__main__": unittest.main()\n'''
 try:
  target.write_text(modified,encoding='utf-8');new_test.parent.mkdir(parents=True,exist_ok=True);new_test.write_text(test,encoding='utf-8');after=_run_tests(root,timeout_seconds)
  if not after['passed']:raise RuntimeError('feature tests failed')
 except Exception as e:
  target.write_text(original,encoding='utf-8');new_test.unlink(missing_ok=True)
  return {'ok':False,'status':'existing_feature_failed_rolled_back','failure_digest':_d(type(e).__name__),'baseline_tests':baseline,'action_executed':True,**DENIED}
 after_digest=hashlib.sha256(target.read_bytes()).hexdigest();core={'contract_version':CONTRACT_VERSION,'request_digest':_d(text),'project_root_digest':_d(str(root)),'target_path':rel.as_posix(),'target_before_digest':before_digest,'target_after_digest':after_digest,'baseline_tests':baseline,'final_tests':after,'new_test_path':'tests/test_slugify.py','existing_type_annotation_convention_preserved':uses_annotations,'existing_normalization_helper_reused':reuses_normalizer,'existing_tests_preserved':True,'feature_complete':True,'rollback_available_from_before_digest':True,'action_executed':True,**DENIED};core['task_digest']=_d(core)
 return {'ok':True,'status':'existing_project_feature_complete','existing_project_feature':core,'action_executed':True,**DENIED}
def process_existing_project_feature_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show existing project feature','inspect existing project feature','show gamma feature task'}:return {'active':False}
 rec=dict((project_state or {}).get('existing_project_feature') or {});return {'active':True,'ok':bool(rec),'status':'existing_project_feature_found' if rec else 'existing_project_feature_missing','existing_project_feature':rec,'action_executed':False,**DENIED}
