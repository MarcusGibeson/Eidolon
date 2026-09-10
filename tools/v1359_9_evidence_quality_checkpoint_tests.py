import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from evidence_quality import *
from v1359_test_support import *
P=0
rows=[rec('requirements'),rec('implementation',provenance_ids=['requirements']),rec('verification',provenance_ids=['implementation'])];r=evaluate_evidence_quality(source_manifest_digest=S,evidence_records=rows);v=r['evidence_quality'];req(r['ok'],'checkpoint');P+=1;req(v['accepted_count']==3,'accepted');P+=1;req(all(not x['reason_codes'] for x in v['records']),'clean');P+=1;req(v['content_free'] and not v['raw_content_persisted'],'privacy');P+=1;req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1359.9-evidence-quality-checkpoint'})
