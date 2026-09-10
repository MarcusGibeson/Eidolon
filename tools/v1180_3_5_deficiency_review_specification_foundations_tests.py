from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_project_inspection import inspect_project_source
from supervised_deficiency_specification import *
checks=[]
def req(v): checks.append(bool(v)); assert v
with tempfile.TemporaryDirectory() as td:
 p=Path(td); (p/'pkg').mkdir(); (p/'data').mkdir()
 (p/'pkg'/'bad.py').write_text('def bad(:\n pass\n',encoding='utf-8')
 (p/'pkg'/'good.py').write_text('# TODO review\ndef ok(): return 1\n',encoding='utf-8')
 (p/'data'/'secret.json').write_text('{"secret":"NEVER_SHOW"}',encoding='utf-8')
 inspection=inspect_project_source(p)
 ids={r['category']:r['candidate_id'] for r in inspection['deficiency_candidates']}
 review=review_deficiency_candidates(inspection,{ids['python_syntax_error']:'confirm',ids['maintenance_marker']:'reject'})
 req(review['review_status']=='reviewed' and review['confirmed_count']==1 and review['rejected_count']==1)
 req(len(review['review_digest'])==64 and all(len(r['decision_digest'])==64 for r in review['review_rows']))
 req(not review['source_read'] and not review['project_registry_discovered'] and not review['source_modified'])
 req('NEVER_SHOW' not in json.dumps(review) and not review['raw_source_exposed'])
 specs=build_specification_candidates(review)
 req(specs['specification_status']=='candidate_ready' and specs['specification_count']==1)
 spec=specs['specifications'][0]
 req(spec['category']=='python_syntax_error' and 'restore_parseability' in spec['objective_codes'])
 req('python_compile' in spec['test_intent_codes'] and spec['reversibility_required'])
 req(not spec['implementation_allowed'] and specs['test_execution_allowed'] is False)
 req(len(spec['specification_digest'])==64 and spec['specification_id'].startswith('spec-'))
 pending=review_deficiency_candidates(inspection,{})
 req(pending['review_status']=='review_required' and pending['pending_count']==2)
 req(build_specification_candidates(pending)['specification_count']==0)
 deferred=review_deficiency_candidates(inspection,{ids['python_syntax_error']:'defer',ids['maintenance_marker']:'defer'})
 req(deferred['deferred_count']==2 and build_specification_candidates(deferred)['specification_status']=='no_confirmed_deficiency')
 bad=review_deficiency_candidates({'contract_version':'wrong'}, {})
 req(bad['review_status']=='blocked' and bad['block_reason']=='invalid_inspection_contract')
 tampered=dict(review); tampered['review_digest']='bad'
 req(build_specification_candidates(tampered)['specification_status']=='blocked')
 duplicated=dict(inspection); duplicated['deficiency_candidates']=inspection['deficiency_candidates']*4
 dedup=review_deficiency_candidates(duplicated,{ids['python_syntax_error']:'confirm',ids['maintenance_marker']:'reject'})
 req(dedup['review_row_count']==2)
 prompt=specification_foundation_prompt(specs)
 req('not patch instructions' in prompt and 'Do not claim implementation' in prompt)
 source=(ROOT/'conscious_agent'/'supervised_deficiency_specification.py').read_text(encoding='utf-8')
 req('read_text(' not in source and 'read_bytes(' not in source and 'write_text(' not in source and 'subprocess' not in source)
 req('implementation_allowed": False' in source and 'execution_invoked": False' in source)
 req(len(json.dumps(specs,sort_keys=True,separators=(',',':')).encode())<=MAX_REPORT_BYTES)
print(json.dumps({'ok':True,'suite':'v1180.3-v1180.5-deficiency-review-specification-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
