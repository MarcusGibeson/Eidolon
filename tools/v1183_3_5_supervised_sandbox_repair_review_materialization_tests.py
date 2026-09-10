from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.supervised_sandbox_repair_draft_checkpoint import _lineage
from conscious_agent.supervised_sandbox_repair_draft_foundations import draft_supervised_sandbox_repair
from conscious_agent.supervised_sandbox_repair_review_materialization import *
from conscious_agent.supervised_sandbox_repair_materialization_checkpoint import build_supervised_sandbox_repair_materialization_checkpoint
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import dispatch_api
checks=[]
def req(v): checks.append(bool(v)); assert v
def h(v): return hashlib.sha256(v.encode()).hexdigest()
def make(target='pkg/case.py',before='def broken(:\n pass\n',after='def fixed():\n return 1\n',status='failed',error='python_compile_failed',block=''):
    lineage=_lineage(target,before,status=status,error_class=error,block_reason=block)
    return draft_supervised_sandbox_repair(*lineage,before,after),before,after
for args in [({},),({'status':'timed_out','error':'test_timeout'},),({'status':'blocked','error':'','block':'sandbox_target_drift'},)]:
    draft,before,after=make(**args[0]); req(draft['draft_status']=='private_draft_ready')
    review=review_repair_draft(draft,decision='approve',operator_actor='operator'); req(review['review_status']=='approved_for_sandbox_repair')
    req(review['content_free'] and review['sandbox_repair_materialization_authorized']); req(not review['retest_authorized'] and not review['source_application_authorized'])
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); source=root/'source'; sandbox=root/'sandbox'; source.mkdir(); dest=sandbox/draft['target_path']; dest.parent.mkdir(parents=True); dest.write_text(before)
        result=materialize_reviewed_sandbox_repair(draft,review,sandbox_root=sandbox,source_root=source,current_target_text=before,replacement_text=after)
        req(result['materialization_status']=='materialized' and dest.read_text()==after)
        req(result['rollback_artifact_present'] and result['rollback_artifact_digest_verified'] and not result['rollback_executed'])
        req(not result['tests_rerun'] and not result['provider_contacted'] and not result['model_contacted'])
        req(not result['production_source_modified'] and not any(source.rglob('*')))
        summary=sandbox_repair_materialization_public_summary(result); encoded=json.dumps(summary)
        req(summary['content_free'] and not summary['authority_granted']); req(before not in encoded and after not in encoded)
        again=materialize_reviewed_sandbox_repair(draft,review,sandbox_root=sandbox,source_root=source,current_target_text=before,replacement_text=after)
        req(again['materialization_status']=='already_materialized' and not again['sandbox_file_written'])
# review boundaries
draft,before,after=make()
req(review_repair_draft(draft,decision='reject',operator_actor='x')['review_status']=='rejected')
req(review_repair_draft(draft,decision='defer',operator_actor='x')['review_status']=='deferred')
req(review_repair_draft(draft,decision='ship',operator_actor='x')['block_reason']=='invalid_review_decision')
req(review_repair_draft(draft,decision='approve',operator_actor='')['block_reason']=='missing_operator_actor')
req(review_repair_draft({**draft,'draft_receipt_digest':'0'*64},decision='approve',operator_actor='x')['block_reason']=='invalid_or_tampered_repair_draft')
review=review_repair_draft(draft,decision='approve',operator_actor='x')
with tempfile.TemporaryDirectory() as td:
 root=Path(td); source=root/'source'; sandbox=root/'sandbox'; source.mkdir(); dest=sandbox/draft['target_path']; dest.parent.mkdir(parents=True); dest.write_text('drift')
 req(materialize_reviewed_sandbox_repair(draft,review,sandbox_root=sandbox,source_root=source,current_target_text=before,replacement_text=after)['block_reason']=='stale_sandbox_target_or_drift')
with tempfile.TemporaryDirectory() as td:
 root=Path(td); source=root/'source'; source.mkdir()
 req(materialize_reviewed_sandbox_repair(draft,review,sandbox_root=source/'nested',source_root=source,current_target_text=before,replacement_text=after)['block_reason']=='sandbox_not_isolated')
with tempfile.TemporaryDirectory() as td:
 root=Path(td); source=root/'source'; sandbox=root/'sandbox'; source.mkdir(); sandbox.mkdir(); outside=root/'outside'; outside.mkdir()
 try:
  (sandbox/'pkg').symlink_to(outside,target_is_directory=True)
 except OSError as error:
  # Standard Windows accounts may not hold SeCreateSymbolicLinkPrivilege. The
  # product guard is retained; this environment cannot construct the fixture.
  req(os.name=='nt' and getattr(error,'winerror',None)==1314)
 else:
  req(materialize_reviewed_sandbox_repair(draft,review,sandbox_root=sandbox,source_root=source,current_target_text=before,replacement_text=after)['block_reason']=='sandbox_symlink_boundary')
req(materialize_reviewed_sandbox_repair(draft,{**review,'review_status':'rejected'},sandbox_root='/tmp/a',source_root='/tmp/b',current_target_text=before,replacement_text=after)['block_reason']=='invalid_or_tampered_repair_review_binding')
req(materialize_reviewed_sandbox_repair(draft,review,sandbox_root='/tmp/a',source_root='/tmp/b',current_target_text=before+'x',replacement_text=after)['block_reason']=='private_content_digest_or_binding_mismatch')
for unsafe in ('../x.py','/x.py','C:/x.py','private/x.py','runtime/x.py'):
 d,_,_=make(target=unsafe); req(review_repair_draft(d,decision='approve',operator_actor='x')['block_reason']=='invalid_or_tampered_repair_draft')
with tempfile.TemporaryDirectory() as td:
 runtime=Path(td)/'runtime'; cp=build_supervised_sandbox_repair_materialization_checkpoint(source_root=ROOT,runtime_root=runtime); req(cp['ok'] and cp['passed']==cp['total']); req(cp['total']>=20); req(not runtime.exists())
 dispatched=dispatch_registered_checkpoint('supervised-sandbox-repair-materialization-checkpoint',source_root=ROOT,runtime_root=runtime); req(dispatched['checkpoint_summary']['ok'])
registry=inspect_checkpoint_registry(source_root=ROOT); row=next(r for r in registry['checkpoints'] if r['checkpoint_id']=='supervised-sandbox-repair-materialization-checkpoint'); req(row['contract_version']==CONTRACT_VERSION)
status,payload=dispatch_api('GET','/api/cognition/supervised-sandbox-repair-materialization-checkpoint'); req(status==200 and payload['data']['contract_version']==CONTRACT_VERSION)
post,_=dispatch_api('POST','/api/cognition/supervised-sandbox-repair-materialization-checkpoint',body={'confirm':True}); req(post in (404,405))
source=(ROOT/'conscious_agent/supervised_sandbox_repair_review_materialization.py').read_text(); req('subprocess' not in source and 'tests_rerun": False' in source)
rv=(ROOT/'tools/release_verify.py').read_text(); req(rv.count('tools/v1183_3_5_supervised_sandbox_repair_review_materialization_tests.py')==1)
print(json.dumps({'ok':all(checks),'suite':'v1183.3-v1183.5-supervised-sandbox-repair-review-materialization','passed':sum(checks),'total':len(checks),'production_source_modified':False,'tests_rerun':False,'authority_expanded':False},sort_keys=True))
