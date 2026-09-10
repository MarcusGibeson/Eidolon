from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.supervised_sandbox_test_execution import review_sandbox_test_execution, execute_reviewed_sandbox_tests, sandbox_test_public_summary
checks=[]
def req(v): checks.append(bool(v))
def sha(b): return hashlib.sha256(b).hexdigest()
with tempfile.TemporaryDirectory() as td:
    root=Path(td); source=root/'source'; sandbox=root/'work'; source.mkdir(); (sandbox/'conscious_agent').mkdir(parents=True)
    target=sandbox/'conscious_agent/example.py'; target.write_text('VALUE = 1\n',encoding='utf-8')
    material={
      'contract_version':'v1181.8','materialization_status':'materialized','sandbox_materialized':True,'source_modified':False,
      'target_path':'conscious_agent/example.py','materialization_receipt_digest':'a'*64,'sandbox_marker_digest':'b'*64,
      'sandbox_target_digest':sha(target.read_bytes())}
    approve=review_sandbox_test_execution(material,decision='approve',operator_actor='operator',requested_tests=['python_compile','content_digest_match'])
    req(approve['review_status']=='approved_for_sandbox_tests' and approve['test_execution_authorized'])
    reject=review_sandbox_test_execution(material,decision='reject',operator_actor='operator',requested_tests=['content_digest_match'])
    req(reject['review_status']=='rejected' and not reject['test_execution_authorized'])
    req(review_sandbox_test_execution(material,decision='defer',operator_actor='operator',requested_tests=['content_digest_match'])['review_status']=='deferred')
    req(review_sandbox_test_execution(material,decision='approve',operator_actor='',requested_tests=['content_digest_match'])['block_reason']=='missing_operator_actor')
    req(review_sandbox_test_execution(material,decision='approve',operator_actor='operator',requested_tests=['shell_command'])['block_reason']=='unsupported_test_request')
    result=execute_reviewed_sandbox_tests(material,approve,sandbox_root=sandbox,source_root=source,timeout_seconds=5)
    req(result['execution_status']=='passed' and result['tests_executed'] and result['test_count']==2)
    req(result['production_source_untouched'] and not result['source_modified'] and not result['shell_invoked'])
    req(not any(source.rglob('*')))
    summary=sandbox_test_public_summary(result)
    req(summary['content_free'] and summary['sandbox_only'] and not summary['authority_granted'])
    req('stdout' not in json.dumps(summary).lower() and 'stderr' not in json.dumps(summary).lower())
    drift={**material,'sandbox_target_digest':'c'*64}
    req(execute_reviewed_sandbox_tests(drift,approve,sandbox_root=sandbox,source_root=source)['block_reason']=='invalid_test_review_binding')
    req(execute_reviewed_sandbox_tests(material,{**approve,'review_status':'rejected'},sandbox_root=sandbox,source_root=source)['block_reason']=='invalid_test_review_binding')
    req(execute_reviewed_sandbox_tests(material,approve,sandbox_root=source/'nested',source_root=source)['block_reason']=='sandbox_not_isolated')
    target.write_text('def broken(:\n',encoding='utf-8'); material2={**material,'sandbox_target_digest':sha(target.read_bytes()),'materialization_receipt_digest':'d'*64}
    approve2=review_sandbox_test_execution(material2,decision='approve',operator_actor='operator',requested_tests=['python_compile'])
    failed=execute_reviewed_sandbox_tests(material2,approve2,sandbox_root=sandbox,source_root=source)
    req(failed['execution_status']=='failed' and failed['test_results'][0]['error_class']=='python_compile_failed')
    req('def broken' not in json.dumps(failed))
    target.unlink(); req(execute_reviewed_sandbox_tests(material2,approve2,sandbox_root=sandbox,source_root=source)['block_reason']=='sandbox_target_missing_or_unsafe')
unsafe={**material,'target_path':'../secret.py'}
req(review_sandbox_test_execution(unsafe,decision='approve',operator_actor='operator',requested_tests=['python_compile'])['block_reason']=='invalid_materialization_contract')
source_text=(ROOT/'conscious_agent/supervised_sandbox_test_execution.py').read_text()
req('promotion_performed": False' in source_text and 'release_authorized": False' in source_text)
req('subprocess.run' in source_text and 'shell=True' not in source_text)
req('execute_reviewed_sandbox_tests' in source_text and 'source_modified": False' in source_text)
print(json.dumps({'ok':all(checks),'suite':'v1182.0-v1182.2-supervised-sandbox-test-execution-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
if not all(checks): print([i+1 for i,v in enumerate(checks) if not v]); raise SystemExit(1)
