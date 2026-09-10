from __future__ import annotations
import json,os,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1252-0-2-')
from conversation_sessions import create_conversation_session,append_conversation_turn,list_conversation_sessions,bounded_cross_session_candidates,conversation_session_summary,archive_conversation_session,restore_conversation_session,CONVERSATION_SESSIONS_DIR
from session_metadata_index import session_metadata_index_report
from bounded_cross_session_retrieval import bounded_cross_session_retrieval,MAX_CROSS_SESSION_TRANSCRIPTS
from persistent_session_summaries import persistent_session_summary
from persistent_state_index import INDEX_FILENAME,persistent_state_index_status
checks=[]
def req(v): checks.append(bool(v)); assert v
for i in range(120):
    row=create_conversation_session(f'Project alpha topic {i%17}',select_session=False)
    append_conversation_turn(row['id'],turn_id=f'turn-{i}',user_message=f'Discuss alpha topic {i%17} migration',assistant_response=f'Answer {i}',completion_state='completed',success=True,select_session=False)
rows=list_conversation_sessions(); req(len(rows)==120); req(all('turns' not in r for r in rows))
req((Path(os.environ['EIDOLON_DATA_DIR'])/INDEX_FILENAME).is_file())
report=session_metadata_index_report(CONVERSATION_SESSIONS_DIR); req(report['ok']); req(report['session_count']==120); req(report['transcripts_loaded_for_listing'] is False)
selected=bounded_cross_session_candidates('alpha topic 4 migration',limit=6); req(1<=len(selected)<=6)
retrieval=bounded_cross_session_retrieval(CONVERSATION_SESSIONS_DIR,'alpha topic 4 migration',limit=99); req(retrieval['selected_count']<=MAX_CROSS_SESSION_TRANSCRIPTS==6); req(retrieval['full_catalog_transcript_scan'] is False)
summary=conversation_session_summary(selected[0]['id']); req(summary is not None); req('User:' in summary['summary']); req(len(summary['topics'])>0)
wrapped=persistent_session_summary(CONVERSATION_SESSIONS_DIR,selected[0]['id']); req(wrapped['ok']); req(wrapped['provider_invoked'] is False)
arch=archive_conversation_session(rows[0]['id']); req(arch['status']=='archived'); req(all(r['id']!=rows[0]['id'] for r in list_conversation_sessions()))
rest=restore_conversation_session(rows[0]['id']); req(rest['status']=='active'); req(any(r['id']==rows[0]['id'] for r in list_conversation_sessions()))
status=persistent_state_index_status(Path(os.environ['EIDOLON_DATA_DIR'])); req(status['counts']['sessions']==120); req(status['canonical_json_preserved'])
source=(ROOT/'conscious_agent/conversation_runtime.py').read_text(); req('bounded_cross_session_candidates' in source); req('limit=6' in source)
r={'suite':'v1252.0-v1252.2-conversation-indexing','ok':all(checks),'passed':sum(checks),'total':len(checks)}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
