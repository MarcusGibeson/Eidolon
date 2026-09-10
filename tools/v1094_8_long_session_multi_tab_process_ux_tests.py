from __future__ import annotations
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path:sys.path.insert(0,str(AGENT))
RESULTS=[]
def require(c,m):
 if not c:raise AssertionError(m)
def check(n,f):
 try:f();RESULTS.append({'name':n,'ok':True})
 except Exception as e:RESULTS.append({'name':n,'ok':False,'error':f'{type(e).__name__}: {e}'})
def main():
 console=(AGENT/'dashboard_chat_console.py').read_text();styles=(AGENT/'dashboard_chat_styles.py').read_text();dash=(AGENT/'dashboard.py').read_text();recovery=(AGENT/'process_recovery.py').read_text()
 def unified_route():require('build_unified_process_recovery_state' in dash and '/api/process-recovery-state' in dash,'unified route')
 def escalation_route():require('cancel_process_operation_with_escalation' in dash and 'cooperative_wait_seconds' in dash and "action == \"cancel\"" in dash,'escalation route')
 def stale_controls():require('stale_tab' in recovery and 'control_context_matches' in recovery and 'cancellation_available' in console,'stale control')
 def async_speech_separation():require("window.setTimeout(refreshProcessRecoveryState, 0)" in console and 'Process operations' in console and 'assistant' not in dash[dash.find('/api/process-operation/cancel'):dash.find('/api/process-recovery/reconcile')],'speech separation')
 def history_bound():require('history_limit = 50' in recovery and 'history_truncated' in recovery and 'Recent exact operation state restored' in console,'history bound')
 def accessibility():require("role='status'" in console and "aria-live='polite'" in console and ':focus-visible' in styles and '@media(max-width:700px)' in styles,'accessibility')
 def status_styles():require("data-status='" in console and "data-status='uncertain'" in styles,'status style')
 def real_imports():ast.parse(console);__import__('dashboard_chat_styles');__import__('process_recovery')
 def privacy_contract():
  forbidden=('owner_nonce','process_start_identity','cancellation_owner_nonce_digest','output_path','result_path','environment_returned": true');source=console+dash
  require(all(x not in source for x in forbidden),'private UI contract')
 def version():
  from release_metadata import RUNTIME_VERSION;require(tuple(map(int,RUNTIME_VERSION.split('.'))) >= tuple(map(int,'1094.8'.split('.'))),RUNTIME_VERSION)
 for n,f in [('unified state route',unified_route),('bounded escalation route',escalation_route),('stale tab controls',stale_controls),('async spoken-response separation',async_speech_separation),('bounded long-session history',history_bound),('keyboard and narrow layout',accessibility),('status-specific styles',status_styles),('real module imports',real_imports),('public privacy contract',privacy_contract),('runtime version',version)]:check(n,f)
 passed=sum(r['ok'] for r in RESULTS);report={'version':'1094.8','status':'pass' if passed==len(RESULTS) else 'fail','passed':passed,'total':len(RESULTS),'checks':RESULTS};print(json.dumps(report,indent=2,sort_keys=True));return 0 if passed==len(RESULTS) else 1
if __name__=='__main__':raise SystemExit(main())
