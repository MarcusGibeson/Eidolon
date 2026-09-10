from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'conscious_agent')]
from conscious_agent.model_training.training_record import record_training_interaction, load_training_record
from conscious_agent.model_training.training_sanitizer import sanitize_stored_training_record

def main():
    checks=[]; check=lambda x: checks.append(bool(x))
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        made=record_training_interaction(runtime_root=root,capture_authorized=True,task_type='research_synthesis',input_payload={'email':'person@example.com','api_key':'sk-abcdefghijklmnopqrstuvwxyz','path':r'C:\\Users\\human\\secret.txt'},model_output='Bearer ABCDEFGHIJKLMNOPQRST',validation={'passed':True,'deterministic':True})
        rid=made['record']['record_id']; clean=sanitize_stored_training_record(rid,runtime_root=root); check(clean['ok'] is True)
        rec=clean['record']; text=json.dumps(rec,sort_keys=True)
        check(rec['sanitized'] is True and rec['approved_for_training'] is False)
        check('person@example.com' not in text and 'sk-abcdefghijklmnopqrstuvwxyz' not in text and 'Bearer ABCD' not in text)
        check('C:\\\\Users' not in text and '[REDACTED_' in text)
        check(rec['sanitization']['human_review_required_before_training'] is True)
        check(load_training_record(rid,runtime_root=root,stage='sanitized').get('record_digest')==rec['record_digest'])
        check(load_training_record(rid,runtime_root=root,stage='raw').get('sanitized') is False)
    print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.14'})); raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__': main()
