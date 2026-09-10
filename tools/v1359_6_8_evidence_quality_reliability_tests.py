import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from evidence_quality import *
from v1359_test_support import *
P=0
cases=[(rec(source_manifest_digest='d'*64),'stale_source_lineage'),(rec(self_asserted=True),'self_asserted_claim'),(rec(complete=False),'incomplete_evidence'),(rec(reproducible=False),'not_reproducible'),(rec(raw_prompt='private'),'content_leak'),(rec(claim_digest='bad'),'claim_digest_invalid'),(rec(verification_method_digest='bad'),'verification_method_missing')]
for item,code in cases:
 r=evaluate_evidence_quality(source_manifest_digest=S,evidence_records=[item]);req(not r['ok'] and code in r['evidence_quality']['records'][0]['reason_codes'],code);P+=1
r=evaluate_evidence_quality(source_manifest_digest=S,evidence_records=[rec('a',provenance_ids=['b']),rec('b',provenance_ids=['a'])]);req(not r['ok'] and any('circular_provenance' in x['reason_codes'] for x in r['evidence_quality']['records']),'cycle');P+=1
req(not evaluate_evidence_quality(source_manifest_digest='bad',evidence_records=[rec()])['ok'],'lineage');P+=1
print({'ok':P==9,'passed':P,'total':9,'suite':'v1359.6-8-evidence-quality-reliability'})
