from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'conscious_agent')]

from conscious_agent.model_training.training_record import (
    create_training_record, load_training_record, record_training_interaction,
    training_record_path, validate_training_record,
)

def main():
    checks=[]
    def check(x): checks.append(bool(x))
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        denied=record_training_interaction(runtime_root=root,capture_authorized=False,task_type='software_repair',input_payload='x',model_output='y',validation={'passed':True})
        check(denied['ok'] is False and denied['status']=='training_capture_authorization_required')
        made=record_training_interaction(runtime_root=root,capture_authorized=True,task_type='software_repair',input_payload={'prompt':'fix anchor'},model_output={'old':'a'},validation={'passed':False,'failure_code':'missing_anchor'},corrected_output={'old':'b'},provenance={'test':'v2503.4.13'})
        check(made['ok'] is True and made['status']=='training_record_created')
        rec=made['record']; check(validate_training_record(rec)); check(rec['runtime_only'] is True and rec['source_package_allowed'] is False)
        check(rec['model_training_authorized'] is False and rec['model_promotion_authorized'] is False)
        path=training_record_path(rec['record_id'],runtime_root=root); check(path.exists() and str(path).startswith(str(root.resolve())))
        loaded=load_training_record(rec['record_id'],runtime_root=root); check(loaded.get('record_digest')==rec['record_digest'])
        tampered=json.loads(path.read_text()); tampered['task_type']='conversation'; path.write_text(json.dumps(tampered),encoding='utf-8'); check(load_training_record(rec['record_id'],runtime_root=root)=={})
        in_memory=create_training_record(task_type='research_synthesis',input_payload='i',model_output='o',validation={'ok':True},capture_authorized=True,created_at_ns=1)
        check(in_memory['record_id'].startswith('trn_') and validate_training_record(in_memory))
    print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.13'}))
    raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__': main()
