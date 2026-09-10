from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.cognitive_observability_v2533 import build_cognitive_observability_snapshot
from conscious_agent.cognitive_observability_sessions_v2537 import build_cognitive_observability_sessions
from conscious_agent.cognitive_observability_signals_v2539 import build_cognitive_observability_signals
from conscious_agent.foreground_cognitive_observability_v2536 import record_foreground_observability_event
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
from conscious_agent.state_grounded_internal_voice_v2523 import project_activity_internal_voice_beta
from conscious_agent.api_server import handle_api_get
from conscious_agent import dashboard

def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        act=project_live_activity({'event':'meta'},operation_id='obs-op'); voice=project_activity_internal_voice_beta(act)
        record_foreground_observability_event(act,operation_id='obs-op',runtime_root=root)
        record_foreground_observability_event(voice,operation_id='obs-op',runtime_root=root)
        snap=build_cognitive_observability_snapshot(root,limit=10)
        sessions=build_cognitive_observability_sessions(root)
        signals=build_cognitive_observability_signals(snap)
        checks += [snap['ok'],snap['recent_count']==2,'signals' in snap,sessions['session_count']==1,sessions['sessions'][0]['contains_voice_projection'],signals['authority_boundary']['advisory_only']]
        checks += [not snap['authority_boundary']['hidden_reasoning_exposed'],not sessions['authority_boundary']['hidden_reasoning_exposed'],not signals['authority_boundary']['can_execute_action']]
    status,payload=handle_api_get('/api/cognition/observability/sessions?limit=4')
    checks += [status==200,payload.get('ok') is True]
    html=dashboard.render_cognitive_observability_dashboard()
    checks += ['mind-signals' in html,'mind-session-count' in html,'not hidden chain-of-thought' in html.lower()]
    passed=sum(bool(x) for x in checks)
    print({'suite':'v2539.9-cognitive-observability-dashboard-beta-ii','ok':passed==len(checks),'passed':passed,'total':len(checks)})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
