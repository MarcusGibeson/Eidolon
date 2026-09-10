from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
import conscious_agent.dashboard_chat_console as chat
checks=[]
def req(v,n):checks.append(n);assert v,n
src=(ROOT/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8')
styles=(ROOT/'conscious_agent'/'dashboard_chat_styles.py').read_text(encoding='utf-8')
req("project_live_activity(item, operation_id=job.operation_id)" in src,'worker_projects_real_events')
req("type === 'activity'" in src and 'appendLiveActivity(payload)' in src,'client_consumes_activity')
req("id='chat-live-activity'" in src and "id='chat-live-activity-lines'" in src,'activity_surface_present')
req('resetLiveActivity();' in src,'activity_resets_per_turn')
req('children.length > 8' in src,'activity_ui_bounded')
req('.chat-live-activity' in styles and "data-active='true'" in styles,'activity_styles_present')
a=project_live_activity({'event':'status','stage':'governed_action','message':'do not expose me'},operation_id='op')
req(a['event']=='activity' and a['activity_kind']=='activity','activity_contract')
req('do not expose me' not in str(a),'raw_status_not_exposed')
req(not a['hidden_reasoning_exposed'],'no_chain_of_thought')
req(not a['raw_prompt_stored'] and not a['raw_provider_output_stored'] and not a['tool_arguments_stored'],'private_fields_excluded')
print({'ok':True,'checkpoint_version':'2510.9','passed':len(checks),'total':len(checks),'checks':checks})
