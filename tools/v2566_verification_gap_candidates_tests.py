from conscious_agent.verification_gap_candidates_v2566 import build_verification_gap_candidates

def main():
 b={'contract_version':'v2562.0','blind_spots':[{'path':'conscious_agent/foo.py','kind':'no_focused_structural_coverage','severity':'high','recommended_evidence':'add direct test'}]}
 o=build_verification_gap_candidates(b);c=o['candidates'][0]
 checks=[o['candidate_count']==1,c['target_path']=='conscious_agent/foo.py',c['candidate_only'],not c['source_content_proposed'],not c['test_body_generated'],o['tests_created']==0,not o['test_creation_authorized'],not o['source_mutation_authorized'],len(c['candidate_digest'])==64]
 print({'suite':'v2566-verification-gap-candidates','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
