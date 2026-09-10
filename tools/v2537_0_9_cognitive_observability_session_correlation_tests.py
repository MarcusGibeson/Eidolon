from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.foreground_cognitive_observability_v2536 import record_foreground_observability_event
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
from conscious_agent.state_grounded_internal_voice_v2523 import project_activity_internal_voice_beta
from conscious_agent.cognitive_observability_sessions_v2537 import build_cognitive_observability_sessions

def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        for op in ('op-a','op-b'):
            act=project_live_activity({'event':'meta'},operation_id=op); voice=project_activity_internal_voice_beta(act)
            record_foreground_observability_event(act,operation_id=op,runtime_root=root)
            record_foreground_observability_event(voice,operation_id=op,runtime_root=root)
        result=build_cognitive_observability_sessions(root,limit=5)
        checks += [result['ok'],result['session_count']==2,result['available_session_count']==2]
        refs={r['session_ref'] for r in result['sessions']}; checks += [refs=={'op-a','op-b'}]
        checks += [all(r['event_count']==2 for r in result['sessions']),all(r['contains_voice_projection'] for r in result['sessions'])]
        checks += [all('voice_text' not in row for row in result['sessions']), result['authority_boundary']['response_text_stored'] is False]
        checks += [result['authority_boundary']['read_only'],not result['authority_boundary']['hidden_reasoning_exposed'],len(result['result_digest'])==64]
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
