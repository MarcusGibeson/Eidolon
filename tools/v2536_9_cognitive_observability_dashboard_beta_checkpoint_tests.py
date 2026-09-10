from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.cognitive_observability_v2533 import build_cognitive_observability_snapshot
from conscious_agent.foreground_cognitive_observability_v2536 import record_foreground_observability_event
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
from conscious_agent.state_grounded_internal_voice_v2523 import project_activity_internal_voice_beta
from conscious_agent.api_server import handle_api_get
from conscious_agent import dashboard


def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        activity=project_live_activity({'event':'meta'},operation_id='cp-op')
        voice=project_activity_internal_voice_beta(activity)
        record_foreground_observability_event(activity,operation_id='cp-op',runtime_root=root)
        record_foreground_observability_event(voice,operation_id='cp-op',runtime_root=root)
        snap=build_cognitive_observability_snapshot(root,limit=20)
        checks += [snap['ok'], snap['recent_count']==2, snap['authority_boundary']['read_only'], not snap['authority_boundary']['hidden_reasoning_exposed']]
        checks += [snap['trends']['event_kind_counts']['cognitive']==1, snap['trends']['event_kind_counts']['voice']==1]
    status,payload=handle_api_get('/api/cognition/observability?limit=3')
    checks += [status==200, payload.get('ok') is True]
    html=dashboard.render_cognitive_observability_dashboard()
    checks += ['/api/cognition/observability' in html, 'Cognitive observability' in html, 'This is not hidden chain-of-thought' in html]
    source=Path('conscious_agent/dashboard_chat_console.py').read_text()
    checks += ['record_foreground_observability_event(activity' in source, 'record_foreground_observability_event(voice' in source]
    passed=sum(bool(x) for x in checks)
    print({'suite':'v2536.9-cognitive-observability-dashboard-beta','ok':passed==len(checks),'passed':passed,'total':len(checks)})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
