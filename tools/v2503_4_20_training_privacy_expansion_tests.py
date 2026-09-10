from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT)]
from conscious_agent.model_training.training_record import create_training_record
from conscious_agent.model_training.training_sanitizer import sanitize_training_record
raw=create_training_record(task_type='conversation',input_payload='Call 614-555-1212 from 192.168.1.5 and https://u:p@example.com '+"-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",model_output='ok',validation={'passed':True},capture_authorized=True,created_at_ns=1)
r=sanitize_training_record(raw); t=json.dumps(r); checks=[r['sanitized'] is True,'614-555-1212' not in t,'192.168.1.5' not in t,'https://u:p@' not in t,'BEGIN PRIVATE KEY' not in t,'[REDACTED_' in t,r['approved_for_training'] is False]
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.20'}));raise SystemExit(0 if all(checks) else 1)
