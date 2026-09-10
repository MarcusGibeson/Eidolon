from __future__ import annotations
import inspect, json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent import isolated_coding_execution as coding
from conscious_agent import bounded_autonomous_web_research as research
from conscious_agent.model_training.training_record import load_training_record

def main():
    checks=[]; check=lambda x: checks.append(bool(x))
    check('capture_training_evidence' in inspect.signature(coding.authorize_and_run_isolated_coding_execution).parameters)
    check(inspect.signature(coding.authorize_and_run_isolated_coding_execution).parameters['capture_training_evidence'].default is False)
    check('capture_training_evidence' in inspect.signature(research.BoundedResearchSessionStore.execute_session).parameters)
    check(inspect.signature(research.BoundedResearchSessionStore.execute_session).parameters['capture_training_evidence'].default is False)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        current={'changes':[{'relative_path':'x.py','operation':'replace','old':'a','new':'b'}],'attempt_number':2,'change_manifest_digest':'a'*64,'execution_digest':'b'*64,'attempt_record_digest':'c'*64}
        previous={'changes':[{'relative_path':'x.py','operation':'replace','old':'a','new':'broken'}],'attempt_number':1,'change_manifest_digest':'d'*64,'execution_digest':'b'*64,'attempt_record_digest':'e'*64}
        denied=coding._capture_isolated_coding_training_evidence(runtime_root=root,capture_authorized=False,request={'request_id':'devc_'+'1'*24},plan={'kind':'test'},current_attempt=current,verification={'passed':True},previous_attempt=previous)
        check(denied['status']=='training_capture_not_requested')
        made=coding._capture_isolated_coding_training_evidence(runtime_root=root,capture_authorized=True,request={'request_id':'devc_'+'1'*24,'objective':'repair'},plan={'kind':'test'},current_attempt=current,verification={'passed':True,'status':'passed','verification_digest':'f'*64},previous_attempt=previous)
        check(made['ok'] is True)
        record=load_training_record(made['record']['record_id'],runtime_root=root)
        check(record['task_type']=='software_repair' and record['has_correction'] is True)
        check(record['model_output']['changes'][0]['new']=='broken')
        check(record['corrected_output']['changes'][0]['new']=='b')
        check(record['model_training_authorized'] is False and record['source_mutation_authorized'] is False)
    source=(ROOT/'conscious_agent/bounded_autonomous_web_research.py').read_text(encoding='utf-8')
    check('capture_research_synthesis(' in source and 'validate_research_synthesis' in source)
    check('capture_training_evidence' in source and 'capture_authorized=True' in source)
    print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.17'})); raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__': main()
