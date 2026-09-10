from __future__ import annotations
import copy,hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.supervised_sandbox_repair_draft_checkpoint import _lineage
from conscious_agent.supervised_sandbox_repair_draft_foundations import draft_supervised_sandbox_repair
from conscious_agent.supervised_sandbox_repair_review_materialization import review_repair_draft,materialize_reviewed_sandbox_repair
from conscious_agent.supervised_sandbox_retesting import *
from conscious_agent.supervised_sandbox_retesting import _base
from conscious_agent.supervised_sandbox_retesting_checkpoint import build_supervised_sandbox_retesting_checkpoint
checks=[]
def req(v):checks.append(bool(v));assert v
def make(status='failed',error='python_compile_failed',block='',before='def broken(:\n pass\n',after='def fixed():\n return 1\n'):
 target='pkg/case.py';lin=_lineage(target,before,status=status,error_class=error,block_reason=block);d=draft_supervised_sandbox_repair(*lin,before,after)
 r=review_repair_draft(d,decision='approve',operator_actor='operator')
 td=tempfile.TemporaryDirectory();sd=tempfile.TemporaryDirectory();sandbox=Path(td.name);source=Path(sd.name);p=sandbox/target;p.parent.mkdir(parents=True);p.write_text(before)
 m=materialize_reviewed_sandbox_repair(d,r,sandbox_root=sandbox,source_root=source,current_target_text=before,replacement_text=after)
 return d,m,sandbox,source,td,sd
for cfg in [dict(),dict(status='timed_out',error='test_timeout'),dict(status='blocked',error='',block='sandbox_target_drift')]:
 d,m,sandbox,source,td,sd=make(**cfg);req(m['sandbox_repair_materialized'])
 rv=review_sandbox_retest(d,m,decision='approve',operator_actor='operator',requested_tests=['python_compile','content_digest_match']);req(rv['retest_authorized']);req(rv['single_use'])
 rt=execute_reviewed_sandbox_retest(d,m,rv,sandbox_root=sandbox,source_root=source);req(rt['retest_status']=='passed');req(rt['tests_rerun']);req(rt['test_count']==2)
 result=build_bounded_repair_result(d,m,rt);req(result['repair_classification']=='repair_succeeded');req(result['repair_accepted']);req(not result['regression_detected']);req(result['rollback_available'])
 pub=sandbox_repair_result_public_summary(result);req(pub['content_free']);req(not pub['authority_granted']);req('replacement_text' not in pub)
 td.cleanup();sd.cleanup()
d,m,sandbox,source,td,sd=make()
for decision,status in [('reject','rejected'),('defer','deferred')]:req(review_sandbox_retest(d,m,decision=decision,operator_actor='operator',requested_tests=['python_compile'])['review_status']==status)
req(review_sandbox_retest({},m,decision='approve',operator_actor='operator',requested_tests=['python_compile'])['block_reason']=='invalid_repair_materialization_lineage')
req(review_sandbox_retest(d,m,decision='approve',operator_actor='',requested_tests=['python_compile'])['block_reason']=='missing_operator_actor')
req(review_sandbox_retest(d,m,decision='approve',operator_actor='operator',requested_tests=['shell'])['block_reason']=='unsupported_retest_request')
rv=review_sandbox_retest(d,m,decision='approve',operator_actor='operator',requested_tests=['python_compile'])
tam=copy.deepcopy(rv);tam['draft_digest']='0'*64;req(execute_reviewed_sandbox_retest(d,m,tam,sandbox_root=sandbox,source_root=source)['block_reason']=='invalid_retest_review_binding')
(sandbox/'pkg/case.py').write_text('drift');blocked=execute_reviewed_sandbox_retest(d,m,rv,sandbox_root=sandbox,source_root=source);req(blocked['block_reason']=='sandbox_target_drift');req(not blocked['tests_rerun'])
req(execute_reviewed_sandbox_retest(d,m,rv,sandbox_root=source,source_root=source)['block_reason']=='sandbox_not_isolated')
synthetic={**_base(),'retest_status':'failed','tests_rerun':True,'draft_digest':d['draft_digest'],'materialization_receipt_digest':m['materialization_receipt_digest']};synthetic['retest_receipt_digest']=hashlib.sha256(json.dumps(synthetic,sort_keys=True,separators=(',',':')).encode()).hexdigest()
res=build_bounded_repair_result(d,m,synthetic);req(res['repair_classification']=='original_failure_persists');req(not res['repair_accepted'])
synthetic['retest_status']='timed_out';synthetic['retest_receipt_digest']=hashlib.sha256(json.dumps({k:v for k,v in synthetic.items() if k!='retest_receipt_digest'},sort_keys=True,separators=(',',':')).encode()).hexdigest();res=build_bounded_repair_result(d,m,synthetic);req(res['repair_classification']=='regression_or_different_failure');req(res['regression_detected'])
req(build_bounded_repair_result({},m,synthetic)['block_reason']=='invalid_retest_lineage')
cp=build_supervised_sandbox_retesting_checkpoint(source_root=ROOT,runtime_root=ROOT/'data');req(cp['ok']);req(cp['read_only']);req(cp['production_source_modified'] is False)
td.cleanup();sd.cleanup()
print(json.dumps({'ok':all(checks),'suite':'v1183.6-v1183.8-supervised-sandbox-retesting','passed':sum(checks),'total':len(checks),'production_source_modified':False,'authority_expanded':False},sort_keys=True))
