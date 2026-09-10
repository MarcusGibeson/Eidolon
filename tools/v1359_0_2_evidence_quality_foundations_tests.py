import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from evidence_quality import *
from v1359_test_support import *
P=0
r=evaluate_evidence_quality(source_manifest_digest=S,evidence_records=[rec()]);req(r['ok'],'pass');P+=1;v=r['evidence_quality'];req(v['accepted_count']==1 and v['rejected_count']==0,'counts');P+=1;req(v['raw_content_persisted'] is False and v['content_free'],'redact');P+=1;req(v['read_only'] and not v['evidence_authority_granted'],'authority');P+=1;req('evidence_id' not in v['records'][0] and 'evidence_id_digest' in v['records'][0],'id hashed');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1359.0-2-evidence-quality-foundations'})
