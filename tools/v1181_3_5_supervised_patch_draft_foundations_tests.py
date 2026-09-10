from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_patch_draft_foundations import *
checks=[]
def req(v): checks.append(bool(v)); assert v

def h(s): return hashlib.sha256(s.encode()).hexdigest()
before='def answer():\n    return 1\n'
after='def answer():\n    return 2\n'
prep={
 'preparation_id':'prep-abc','preparation_digest':'a'*64,'target_path':'conscious_agent/example.py',
 'baseline_file_digest':h(before),'patch_creation_allowed':False,'implementation_authorized':False,
}
bundle={'contract_version':'v1181.2','content_free':True,'source_modified':False,'patch_created':False,'tests_executed':False,'preparation_bundle_digest':'b'*64,'preparations':[prep]}
result=draft_supervised_patch(bundle,'prep-abc',before,after)
req(result['draft_status']=='draft_ready' and result['target_path']=='conscious_agent/example.py')
req(result['patch_text'].startswith('--- a/conscious_agent/example.py'))
req('+++ b/conscious_agent/example.py' in result['patch_text'] and '+    return 2' in result['patch_text'])
req(result['before_digest']==h(before) and result['after_digest']==h(after) and len(result['patch_digest'])==64)
req(result['single_target'] and result['reversible'] and result['sandbox_required'])
req(result['operator_review_required'] and result['separate_application_approval_required'])
req(not result['application_authorized'] and not result['test_execution_authorized'])
req(not result['repository_read'] and not result['source_modified'] and not result['patch_written'] and not result['patch_applied'])
req(not result['tests_executed'] and not result['shell_invoked'] and not result['tool_invoked'])
req(result['contains_source_content'] and result['private_artifact'] and not result['public_diagnostics_safe'])
summary=patch_draft_public_summary(result)
req(summary['content_free'] and not summary['patch_text_included'] and 'patch_text' not in summary)
req(not summary['raw_source_included'] and not summary['authority_granted'])
req('not applied, tested, approved' in patch_draft_prompt(summary))
stale=draft_supervised_patch(bundle,'prep-abc',before+'# drift\n',after)
req(stale['draft_status']=='stale_source' and stale['block_reason']=='baseline_text_digest_mismatch')
req(draft_supervised_patch(bundle,'missing',before,after)['block_reason']=='invalid_preparation_contract')
req(draft_supervised_patch({**bundle,'contract_version':'bad'},'prep-abc',before,after)['block_reason']=='invalid_preparation_contract')
req(draft_supervised_patch(bundle,'prep-abc',before,before)['block_reason']=='no_change')
req(draft_supervised_patch(bundle,'prep-abc',before+'\x00',after)['block_reason']=='invalid_source_text')
unsafe={**bundle,'preparations':[{**prep,'target_path':'../secret.py'}]}
req(draft_supervised_patch(unsafe,'prep-abc',before,after)['block_reason']=='invalid_target_binding')
unsafe_auth={**bundle,'preparations':[{**prep,'implementation_authorized':True}]}
req(draft_supervised_patch(unsafe_auth,'prep-abc',before,after)['block_reason']=='unsafe_preparation_authority')
req(result['patch_line_count']<=MAX_PATCH_LINES and len(result['patch_text'].encode())<=MAX_PATCH_BYTES)
source=(ROOT/'conscious_agent'/'supervised_patch_draft_foundations.py').read_text(encoding='utf-8')
req('read_text(' not in source and 'read_bytes(' not in source and 'write_text(' not in source and 'subprocess' not in source)
req('patch_applied": False' in source and 'tests_executed": False' in source and 'application_authorized": False' in source)
print(json.dumps({'ok':True,'suite':'v1181.3-v1181.5-supervised-patch-draft-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
