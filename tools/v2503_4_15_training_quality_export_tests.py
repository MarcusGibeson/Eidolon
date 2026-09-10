from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'conscious_agent')]
from conscious_agent.model_training.training_record import record_training_interaction
from conscious_agent.model_training.training_sanitizer import sanitize_stored_training_record
from conscious_agent.model_training.training_quality import assess_training_record_quality
from conscious_agent.model_training.training_export import approve_training_record, export_approved_sft_jsonl

def main():
    checks=[]; check=lambda x: checks.append(bool(x))
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        made=record_training_interaction(runtime_root=root,capture_authorized=True,task_type='software_repair',input_payload={'task':'repair'},model_output={'bad':True},validation={'passed':True,'tests_passed':True,'deterministic':True},corrected_output={'good':True},provenance={'operator_reviewed':True})
        rid=made['record']['record_id']; clean=sanitize_stored_training_record(rid,runtime_root=root)['record']; quality=assess_training_record_quality(clean)
        check(quality['quality_score']>=70 and quality['eligible_for_operator_approval'] is True)
        denied=approve_training_record(rid,runtime_root=root,operator_approved=False); check(denied['ok'] is False)
        approved=approve_training_record(rid,runtime_root=root,operator_approved=True); check(approved['ok'] is True and approved['record']['approved_for_training'] is True)
        check(approved['record']['model_training_authorized'] is False)
        noexport=export_approved_sft_jsonl(runtime_root=root,operator_authorized=False); check(noexport['ok'] is False)
        exported=export_approved_sft_jsonl(runtime_root=root,operator_authorized=True); check(exported['ok'] is True and exported['record_count']==1)
        lines=Path(exported['runtime_path']).read_text(encoding='utf-8').splitlines(); row=json.loads(lines[0]); check(len(row['messages'])==2 and row['messages'][1]['role']=='assistant')
        check('good' in row['messages'][1]['content'] and 'bad' not in row['messages'][1]['content'])
        check(exported['model_training_authorized'] is False and exported['model_promotion_authorized'] is False)
    print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.15'})); raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__': main()
