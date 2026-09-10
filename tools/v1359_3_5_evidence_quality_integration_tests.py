import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from evidence_quality import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1359_test_support import *
P=0
r=evaluate_evidence_quality(source_manifest_digest=S,evidence_records=[rec('a'),rec('b',provenance_ids=['a'])]);v=r['evidence_quality'];req(r['ok'],'chain');P+=1;req(v['record_count']==2,'count');P+=1;c=process_ordinary_chat_development_turn('show evidence checks',project_state={'evidence_quality':v});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'readonly');P+=1;req(v['source_manifest_digest']==S,'lineage');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1359.3-5-evidence-quality-integration'})
