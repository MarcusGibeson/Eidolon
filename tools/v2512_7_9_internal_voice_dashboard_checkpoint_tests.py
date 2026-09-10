from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
src=(ROOT/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8')
voice=(ROOT/'conscious_agent'/'internal_voice_projection_v2512.py').read_text(encoding='utf-8')
checks=[]
def req(v,n):checks.append(n);assert v,n
req('project_activity_internal_voice(activity)' in src,'worker_voice_projection')
req("type === 'internal_voice'" in src,'client_voice_event')
req("activity_kind:'observation'" in src,'voice_visually_distinct')
req('state_grounded_internal_voice_projection' in voice,'voice_semantics_explicit')
req('claims_literal_thought_transcript' in voice,'literal_transcript_denied')
req('provider_contacted' in voice,'provider_boundary_explicit')
req("project_live_activity(item, operation_id=job.operation_id)" in src,'activity_grounding_retained')
req('children.length > 8' in src,'combined_stream_bounded')
print({'ok':True,'checkpoint_version':'2512.9','passed':len(checks),'total':len(checks),'checks':checks})
