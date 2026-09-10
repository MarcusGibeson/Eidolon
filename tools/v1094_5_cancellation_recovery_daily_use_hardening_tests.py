from __future__ import annotations
import ast,json,os,sys,tempfile,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path:sys.path.insert(0,str(AGENT))
RESULTS=[]
def require(c,m):
    if not c:raise AssertionError(m)
def check(n,f):
    try:f();RESULTS.append({'name':n,'ok':True})
    except Exception as e:RESULTS.append({'name':n,'ok':False,'error':f'{type(e).__name__}: {e}'})
def main():
  with tempfile.TemporaryDirectory(prefix='eidolon-v1094-5-') as td:
    os.environ['EIDOLON_PROCESS_RUNTIME_ROOT']=str(Path(td)/'runtime');os.environ['EIDOLON_METADATA_LOCK_DIR']=str(Path(td)/'locks')
    console=(AGENT/'dashboard_chat_console.py').read_text(); styles=(AGENT/'dashboard_chat_styles.py').read_text(); dashboard=(AGENT/'dashboard.py').read_text()
    def panel_markup():require("id='chat-process-recovery'" in console and "id='chat-process-recovery-rows'" in console,'panel missing')
    def async_provider_free():require("fetch('/api/process-recovery-state?'" in console and 'window.setTimeout(refreshProcessRecoveryState, 0)' in console,'async refresh missing')
    def exact_cancel_payload():
        for token in ('operation_id','generation','project_id','session_id','tab_id','tab_revision','operator_confirmed','force_termination_permitted'):
            require(token in console,f'{token} missing')
    def stale_control_boundary():require('cancellation_available' in console and 'force_termination_available' in console and 'stale_tab' in (AGENT/'process_recovery.py').read_text(),'stale controls missing')
    def accessible_layout():require('role=\'status\'' in console and 'aria-live=\'polite\'' in console and ':focus-visible' in styles and '@media(max-width:700px)' in styles,'accessibility missing')
    def spoken_response_separation():require('Process operations' in console and 'processRecoveryMessage' in console and 'assistant' not in dashboard[dashboard.find('/api/process-operation/cancel'):dashboard.find('/api/process-recovery/reconcile')],'process state mixed with speech')
    def route_methods():require('/api/process-recovery-state' in dashboard and '/api/process-operation/cancel' in dashboard and 'do_POST' in dashboard,'route method boundary missing')
    def module_imports():
        ast.parse(console); __import__('dashboard_chat_styles'); __import__('process_ownership'); __import__('process_recovery')
    def privacy_terms():
        from process_recovery import build_process_restart_state
        enc=json.dumps(build_process_restart_state(project_id='eidolon')); require('owner_pid' not in enc and 'child_pid' not in enc and 'acceptance_key' not in enc,'private process detail leaked')
    for n,f in [('process recovery panel markup',panel_markup),('async provider-free status',async_provider_free),('exact cancellation payload',exact_cancel_payload),('stale control boundary',stale_control_boundary),('keyboard and narrow layout',accessible_layout),('spoken response separation',spoken_response_separation),('GET and POST route boundary',route_methods),('real module import and parse',module_imports),('content-free public status',privacy_terms)]:check(n,f)
  passed=sum(1 for r in RESULTS if r['ok']);report={'version':'1094.5','status':'pass' if passed==len(RESULTS) else 'fail','passed':passed,'total':len(RESULTS),'checks':RESULTS};print(json.dumps(report,indent=2,sort_keys=True));return 0 if passed==len(RESULTS) else 1
if __name__=='__main__':raise SystemExit(main())
