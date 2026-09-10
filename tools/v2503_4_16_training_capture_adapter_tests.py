from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'conscious_agent')]
from conscious_agent.model_training.training_capture_adapters import capture_software_attempt, capture_research_synthesis
from conscious_agent.model_training.training_record import load_training_record
from conscious_agent.package_integrity import forbidden_runtime_path_matches

def main():
    checks=[]; check=lambda x: checks.append(bool(x))
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        denied=capture_software_attempt(runtime_root=root,capture_authorized=False,prompt_or_context='p',model_output='o',verification={'passed':True}); check(denied['ok'] is False)
        coding=capture_software_attempt(runtime_root=root,capture_authorized=True,prompt_or_context={'objective':'bounded repair'},model_output='bad anchor',verification={'passed':True,'tests_passed':True,'deterministic':True},corrected_output='good anchor',provenance={'request_digest':'a'*64}); check(coding['ok'] is True)
        research=capture_research_synthesis(runtime_root=root,capture_authorized=True,research_context={'evidence_digest':'b'*64},model_output={'recommendation':'tentative'},validation={'passed':True,'validator':'research_synthesis'},provenance={'session_digest':'c'*64}); check(research['ok'] is True)
        c=load_training_record(coding['record']['record_id'],runtime_root=root); r=load_training_record(research['record']['record_id'],runtime_root=root)
        check(c['task_type']=='software_repair' and c['source_system']=='isolated_coding_execution')
        check(r['task_type']=='research_synthesis' and r['source_system']=='governed_public_web_research_adapter')
        check(c['provenance']['adapter_contract']=='v2503.4.16' and r['provenance']['adapter_contract']=='v2503.4.16')
        check(c['provider_contact_authorized'] is False and r['model_training_authorized'] is False)
        check('Eidolon/data/model_training/raw/example.json' in forbidden_runtime_path_matches(['Eidolon/data/model_training/raw/example.json']))
    print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.16'})); raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__': main()
