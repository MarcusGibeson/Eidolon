from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cognitive_coding_foundations import digest
from python_implementation import run_python_implementation
from html_css_implementation import run_html_css_implementation
from cross_platform_automation import run_cross_platform_automation
from cross_language_changes import run_cross_language_change
from framework_adaptation import run_framework_adaptation
from dependency_selection import create_dependency_selection
import v1341_python_implementation_test_support as pyfx
import v1343_html_css_test_support as webfx
import v1346_cross_platform_automation_test_support as clifx
import v1349_cross_language_test_support as mixfx
import v1347_framework_adaptation_test_support as fwfx
from v1348_dependency_selection_test_support import candidate

def _row(name,result,body,key,verification,clean=True,recover=True,selected=False):
 rec=dict(result.get(key) or {});return {'scenario':name,'ok':result.get('ok') is True,'verification_passed':bool(verification(rec)),'workspace_cleaned':rec.get('workspace_cleaned') is True if clean else True,'host_recoverable':rec.get('host_recoverable') is True if recover else True,'selected_source_content_modified':rec.get('selected_source_content_modified',False) is True if selected else False,'authority_safe':not bool(rec.get('release_authorized')) and not bool(rec.get('installation_authorized')),'evidence_digest':digest({'name':name,'id':rec.get(next((k for k in rec if k.endswith('_id')),''),''),'state':body(rec)})}
def run_real_scenarios(base:Path):
 rows=[]
 b=base/'python';b.mkdir();src,runtime,grant,pres,git=pyfx.source_fixture(b);r=run_python_implementation(**pyfx.implementation_args(src,runtime,grant,pres,git));rows.append(_row('python',r,lambda x:x.get('implementation_state'),'python_implementation',lambda x:x.get('compile_passed') and x.get('tests_passed')))
 b=base/'web';b.mkdir();src,runtime,grant,pres,git=webfx.source_fixture(b);r=run_html_css_implementation(**webfx.args(src,runtime,grant,pres,git));rows.append(_row('web',r,lambda x:x.get('implementation_state'),'html_css_implementation',lambda x:x.get('compatibility_passed') and x.get('browser_passed') and x.get('screenshot_captured')))
 b=base/'cli';b.mkdir();src,runtime,grant,pres,git=clifx.source_fixture(b);r=run_cross_platform_automation(**clifx.args(src,runtime,grant,pres,git));rows.append(_row('cli',r,lambda x:x.get('implementation_state'),'cross_platform_automation',lambda x:x.get('syntax_valid') and x.get('tests_passed')))
 b=base/'mixed';b.mkdir();src,runtime,grant,pres,git=mixfx.source_fixture(b);r=run_cross_language_change(**mixfx.args(src,runtime,grant,pres,git));rows.append(_row('mixed_stack',r,lambda x:x.get('transaction_state'),'cross_language_change',lambda x:x.get('validation_passed_count')==5 and x.get('verification_passed_count')==3))
 b=base/'framework';b.mkdir();src,runtime,grant,pres,git=fwfx.source_fixture(b);r=run_framework_adaptation(**fwfx.args(src,runtime,grant,pres,git));rows.append(_row('framework_adaptation',r,lambda x:x.get('adaptation_state'),'framework_adaptation',lambda x:x.get('tests_passed') and x.get('nested_python_state')=='completed'))
 b=base/'dependency';b.mkdir();r=create_dependency_selection(candidates=[candidate(existing=True),candidate(existing=False,capability_score=.98)],source_workspace_digest='d'*64,runtime_root=b/'runtime');rec=dict(r.get('dependency_selection') or {});rows.append({'scenario':'dependency_selection','ok':r.get('ok') is True,'verification_passed':rec.get('selection_status')=='selected_existing_dependency','workspace_cleaned':True,'host_recoverable':True,'selected_source_content_modified':False,'authority_safe':not rec.get('dependency_installation_authorized') and not rec.get('network_authorized') and not rec.get('release_authorized'),'evidence_digest':digest({'id':rec.get('dependency_selection_id'),'evaluation':rec.get('evaluation_digest')})})
 return rows

def synthetic_good():
 return [{'scenario':name,'ok':True,'verification_passed':True,'workspace_cleaned':True,'host_recoverable':True,'selected_source_content_modified':False,'authority_safe':True,'evidence_digest':hashlib.sha256(name.encode()).hexdigest()} for name in ('python','web','cli','mixed_stack','framework_adaptation','dependency_selection')]
