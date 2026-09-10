from __future__ import annotations
import hashlib, json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_patch_review_sandbox_materialization import *
checks=[]
def req(v): checks.append(bool(v)); assert v
def h(s): return hashlib.sha256(s.encode()).hexdigest()

before='def answer():\n    return 1\n'
after='def answer():\n    return 2\n'
draft={
 'contract_version':'v1181.5','draft_status':'draft_ready','private_artifact':True,'contains_source_content':True,
 'patch_applied':False,'application_authorized':False,'test_execution_authorized':False,
 'draft_id':'patch-draft-abc','draft_digest':'a'*64,'patch_digest':'b'*64,'preparation_digest':'c'*64,
 'target_path':'conscious_agent/example.py','before_digest':h(before),'after_digest':h(after),
 'patch_text':'--- a/conscious_agent/example.py\n+++ b/conscious_agent/example.py\n@@ -1,2 +1,2 @@\n def answer():\n-    return 1\n+    return 2',
}
review=review_patch_draft(draft,decision='approve',operator_actor='operator')
req(review['review_status']=='approved_for_sandbox' and review['sandbox_materialization_authorized'])
req(review['content_free'] and len(review['review_digest'])==64 and len(review['operator_actor_digest'])==64)
req(not review['source_application_authorized'] and not review['test_execution_authorized'])
req(review_patch_draft(draft,decision='reject',operator_actor='operator')['review_status']=='rejected')
req(review_patch_draft(draft,decision='defer',operator_actor='operator')['review_status']=='deferred')
req(review_patch_draft(draft,decision='approve',operator_actor='')['block_reason']=='missing_operator_actor')
req(review_patch_draft(draft,decision='ship',operator_actor='operator')['block_reason']=='invalid_review_decision')
req(review_patch_draft({**draft,'draft_status':'blocked'},decision='approve',operator_actor='operator')['block_reason']=='invalid_patch_draft_contract')

with tempfile.TemporaryDirectory() as td:
    root=Path(td); source=root/'source'; sandbox=root/'isolated'; source.mkdir()
    result=materialize_reviewed_patch(draft,review,sandbox_root=sandbox,source_root=source,before_text=before,after_text=after)
    req(result['materialization_status']=='materialized' and result['sandbox_materialized'])
    req((sandbox/'conscious_agent/example.py').read_text()==after)
    req((sandbox/'.eidolon_sandbox_materialization.json').is_file())
    req(not result['source_modified'] and not result['patch_applied_to_source'])
    req(not result['tests_executed'] and not result['shell_invoked'] and not result['tool_invoked'])
    req(result['sandbox_target_digest']==h(after) and len(result['sandbox_marker_digest'])==64)
    again=materialize_reviewed_patch(draft,review,sandbox_root=sandbox,source_root=source,before_text=before,after_text=after)
    req(again['materialization_status']=='already_materialized' and not again['sandbox_file_written'])
    req(not any(source.rglob('*')))
    summary=sandbox_materialization_public_summary(result)
    req(summary['content_free'] and summary['sandbox_only'] and not summary['source_modified'])
    req('patch_text' not in summary and not summary['tests_executed'] and not summary['authority_granted'])

with tempfile.TemporaryDirectory() as td:
    root=Path(td); source=root/'source'; source.mkdir()
    req(materialize_reviewed_patch(draft,review,sandbox_root=source/'sandbox',source_root=source,before_text=before,after_text=after)['block_reason']=='sandbox_not_isolated')
with tempfile.TemporaryDirectory() as td:
    root=Path(td); source=root/'source'; sandbox=root/'sandbox'; source.mkdir(); sandbox.mkdir()
    (sandbox/'conscious_agent').mkdir(); (sandbox/'conscious_agent/example.py').write_text('drift')
    req(materialize_reviewed_patch(draft,review,sandbox_root=sandbox,source_root=source,before_text=before,after_text=after)['block_reason']=='sandbox_target_drift')
with tempfile.TemporaryDirectory() as td:
    root=Path(td); source=root/'source'; sandbox=root/'sandbox'; source.mkdir(); sandbox.mkdir()
    outside=root/'outside'; outside.mkdir()
    try:
        (sandbox/'conscious_agent').symlink_to(outside, target_is_directory=True)
    except OSError as error:
        req(os.name=='nt' and getattr(error,'winerror',None)==1314)
    else:
        req(materialize_reviewed_patch(draft,review,sandbox_root=sandbox,source_root=source,before_text=before,after_text=after)['block_reason']=='sandbox_symlink_boundary')
req(materialize_reviewed_patch(draft,{**review,'review_status':'rejected'},sandbox_root='/tmp/x',source_root='/tmp/y',before_text=before,after_text=after)['block_reason']=='invalid_review_binding')
req(materialize_reviewed_patch(draft,review,sandbox_root='/tmp/x',source_root='/tmp/y',before_text=before+'x',after_text=after)['block_reason']=='source_text_digest_mismatch')
unsafe={**draft,'target_path':'../secret.py'}
req(review_patch_draft(unsafe,decision='approve',operator_actor='operator')['block_reason']=='invalid_patch_draft_contract')
source=(ROOT/'conscious_agent'/'supervised_patch_review_sandbox_materialization.py').read_text(encoding='utf-8')
req('subprocess' not in source and 'source_application_authorized": False' in source)
req('tests_executed": False' in source and 'provider_contacted": False' in source)
print(json.dumps({'ok':True,'suite':'v1181.6-v1181.8-supervised-patch-review-sandbox-materialization','passed':sum(checks),'total':len(checks)},sort_keys=True))
