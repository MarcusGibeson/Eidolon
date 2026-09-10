import tempfile
from conscious_agent.memory_retrieval_followup_learning_v2583 import learn_from_followup_correction
from conscious_agent.memory_retrieval_outcome_history_v2580 import load_memory_retrieval_outcome_history

def main():
 prior={'present':True,'operation_ref_digest':'a'*64,'feedback':{'state':'grounded_relevant_memory','selected_count':2}}
 correction={'candidate':{'candidate_type':'correction'}}
 with tempfile.TemporaryDirectory() as d:
  a=learn_from_followup_correction(prior,correction,runtime_root=d);h=load_memory_retrieval_outcome_history(d);b=learn_from_followup_correction(prior,{'candidate':None},runtime_root=d)
  checks=[a['evidence_recorded'],a['outcome_disposition']=='negative_evidence',len(h['rows'])==1,h['rows'][0]['correction_detected'],not b['evidence_recorded'],a['raw_memory_text_stored'] is False,a['raw_correction_text_stored'] is False,not a['memory_mutated'],not a['retrieval_policy_mutated']]
 print({'suite':'v2583-memory-retrieval-followup-learning','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
