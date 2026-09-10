from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.foreground_cognitive_observability_v2536 import record_foreground_observability_event
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
from conscious_agent.state_grounded_internal_voice_v2523 import project_activity_internal_voice_beta

def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        activity=project_live_activity({'event':'meta'},operation_id='op-1')
        voice=project_activity_internal_voice_beta(activity)
        a=record_foreground_observability_event(activity,operation_id='op-1',runtime_root=root)
        v=record_foreground_observability_event(voice,operation_id='op-1',runtime_root=root)
        recent=MentalActivityTimeline(root).recent(limit=10)
        checks += [a['ok'],v['ok'],recent['event_count']==2]
        rows=recent['events']
        checks += [rows[0]['event_kind']=='cognitive',rows[1]['event_kind']=='voice']
        blob=str(rows).lower()
        checks += ['voice_text' not in blob,'request accepted' not in blob,'raw_prompt' not in blob]
        replay=record_foreground_observability_event(activity,operation_id='op-1',runtime_root=root)
        checks += [replay['idempotent'] is True,MentalActivityTimeline(root).recent(limit=10)['event_count']==2]
        try:
            record_foreground_observability_event({'event':'delta','activity_digest':'a'*64},operation_id='op-1',runtime_root=root); checks.append(False)
        except ValueError: checks.append(True)
    source=Path('conscious_agent/dashboard_chat_console.py').read_text()
    checks += ['record_foreground_observability_event(activity' in source,'record_foreground_observability_event(voice' in source]
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
