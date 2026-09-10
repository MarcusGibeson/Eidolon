from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from supervised_project_inspection import *
checks=[]
def req(v): checks.append(bool(v)); assert v
with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 (p/'pkg').mkdir(); (p/'tests').mkdir(); (p/'data').mkdir()
 (p/'pkg'/'good.py').write_text('def ok():\n    return 1\n# TODO improve\n',encoding='utf-8')
 (p/'pkg'/'bad.py').write_text('def broken(:\n pass\n',encoding='utf-8')
 (p/'README.md').write_text('safe project\n',encoding='utf-8')
 (p/'data'/'secret.json').write_text('{"secret":"DO_NOT_EXPOSE"}',encoding='utf-8')
 r=inspect_project_source(p)
 req(r['inspection_status']=='review_required' and r['file_count']==3)
 req(r['deficiency_candidate_count']==2)
 cats={x['category'] for x in r['deficiency_candidates']}; req(cats=={'maintenance_marker','python_syntax_error'})
 req(all('data/' not in x['path'] for x in r['files']))
 req('DO_NOT_EXPOSE' not in json.dumps(r) and not r['raw_source_exposed'])
 req(not r['source_modified'] and not r['patch_created'] and not r['approval_created'] and not r['execution_invoked'])
 req(len(r['scope_digest'])==64 and len(r['inspection_digest'])==64)
 scoped=inspect_project_source(p,scope=['pkg/good.py'])
 req(scoped['file_count']==1 and scoped['files'][0]['path']=='pkg/good.py')
 traversal=inspect_project_source(p,scope=['../secret','/etc/passwd','C:/Windows','data/secret.json'])
 req(traversal['file_count']==0 and traversal['rejected_scope_count']>=4)
 missing=inspect_project_source(p/'missing')
 req(missing['inspection_status']=='blocked' and missing['block_reason']=='source_root_unavailable')
 many=p/'many'; many.mkdir()
 for i in range(20): (many/f'f{i}.py').write_text('x=1\n',encoding='utf-8')
 bounded=inspect_project_source(p,scope=['many'],max_files=5)
 req(bounded['file_count']==5 and bounded['input_truncated'])
 req(len(json.dumps(bounded,sort_keys=True,separators=(',',':')).encode())<=MAX_REPORT_BYTES)
 prompt=project_inspection_prompt(r)
 req('candidates, not proven defects' in prompt and 'Do not claim a patch' in prompt)
 source=(ROOT/'conscious_agent'/'supervised_project_inspection.py').read_text(encoding='utf-8')
 req('write_text(' not in source and 'write_bytes(' not in source and 'subprocess' not in source)
 req('project_registry_discovered": False' in source and 'implementation_allowed": False' in source)
print(json.dumps({'ok':True,'suite':'v1180.0-v1180.2-supervised-project-inspection-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
