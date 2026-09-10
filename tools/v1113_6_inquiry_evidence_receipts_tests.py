from pathlib import Path
import tempfile
from conscious_agent.inquiry_evidence_receipts import InquiryEvidenceReceiptStore

def req(x):
 if not x: raise AssertionError(x)
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);s=InquiryEvidenceReceiptStore(root)
  s.inquiries._load=lambda:{'records':[{'active_inquiry_id':'a1','inquiry_candidate_id':'c1','state':'active_internal'}]}
  r=s.record('e1',active_inquiry_id='a1',evidence_kind='operator_supplied_evidence',source_digest='s',evidence_digest='e',reliability=.8,relevance=.9);req(r['ok']);req(r['result']['status']=='evidence_receipt_recorded')
  d=s.record('e2',active_inquiry_id='a1',evidence_kind='operator_supplied_evidence',source_digest='s',evidence_digest='e');req(d['result']['status']=='duplicate_evidence_ignored')
  dup=s.record('e1',active_inquiry_id='a1',evidence_kind='operator_supplied_evidence',source_digest='s',evidence_digest='e');req(dup['idempotent'])
  try:s.record('e3',active_inquiry_id='a1',evidence_kind='approved_browsing_result',source_digest='s2',evidence_digest='e2');raise AssertionError('missing authorization accepted')
  except ValueError:pass
  i=s.inspection_summary();req(i['receipt_count']==1);req(not i['external_browsing_performed']);req(not i['provider_contacted']);req(not i['private_content_exposed'])
 print('v1113.6 focused tests: 8/8')
if __name__=='__main__':main()
