from pathlib import Path
import tempfile
from conscious_agent.inquiry_evidence_assimilation_v1113 import InquiryEvidenceAssimilationStore

def req(x):
 if not x: raise AssertionError(x)
def main():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);s=InquiryEvidenceAssimilationStore(root)
  s.receipts._load=lambda:{'receipts':[{'receipt_id':'r1','state':'active','active_inquiry_id':'a1','evidence_kind':'operator_supplied_evidence','reliability':.8,'relevance':.9,'contradiction':.1},{'receipt_id':'r2','state':'active','active_inquiry_id':'a1','evidence_kind':'operator_supplied_evidence','reliability':.8,'relevance':.9,'contradiction':.8},{'receipt_id':'r3','state':'active','active_inquiry_id':'a1','evidence_kind':'operator_supplied_evidence','reliability':.2,'relevance':.9,'contradiction':0}]}
  a=s.assimilate('e1',receipt_id='r1');req(a['result']['outcome']=='assimilated')
  b=s.assimilate('e2',receipt_id='r2');req(b['result']['outcome']=='assimilated_with_uncertainty')
  c=s.assimilate('e3',receipt_id='r3');req(c['result']['outcome']=='deferred')
  d=s.assimilate('e4',receipt_id='r1');req(d['result']['status']=='duplicate_assimilation_ignored')
  i=s.inspection_summary();req(i['assimilation_count']==3);req(not i['belief_changed']);req(not i['inquiry_resolved']);req(not i['provider_contacted'])
 print('v1113.7 focused tests: 8/8')
if __name__=='__main__':main()
