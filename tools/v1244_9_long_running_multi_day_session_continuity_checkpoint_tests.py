from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from long_running_multi_day_session_continuity import AUTHORITY_FLAGS
from long_running_multi_day_session_continuity_checkpoint import build_long_running_multi_day_session_continuity_checkpoint
c=[];ck=lambda v:c.append(bool(v));row=build_long_running_multi_day_session_continuity_checkpoint(source_root=R)
for v in (row['ok'],row['status']=='long_running_multi_day_session_continuity_checkpoint_ready',row['checkpoint_id']=='long-running-multi-day-session-continuity-checkpoint',row['contract_version']=='v1244.9',row['retained_contract_version']=='v1244.8',row['passed']==row['total'],row['source_signature_unchanged'],row['source_file_count_before']==row['source_file_count_after'],row['read_only'],row['content_free'],not row['runtime_data_read'],not row['runtime_data_written'],not row['provider_contacted'],not row['commands_executed'],not row['tests_executed'],not row['project_modified'],not row['source_modified'],not row['cognition_written'],not row['authority_granted']):ck(v)
for value in row['checks'].values():ck(value)
for k,e in AUTHORITY_FLAGS.items():ck(row.get(k) is e)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c),'checkpoint_passed':row['passed'],'checkpoint_total':row['total']},sort_keys=True));raise SystemExit(0 if all(c) else 1)
