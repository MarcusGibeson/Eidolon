from conscious_agent.verification_confidence_advisory_v2563 import build_verification_confidence_advisory

def main():
 c={'contract_version':'v2561.0','confidence':'weak'}; b={'contract_version':'v2562.0','blind_spots':[{'severity':'high'},{'severity':'medium'}]}
 out=build_verification_confidence_advisory(c,b)
 checks=[out['recommendation']=='focused_coverage_required_before_fast_confidence',out['high_blind_spot_count']==1,out['tier1_tests_preserved'],out['tier2_not_waived'],out['release_certification_still_required'],not out['test_suppression_authorized'],not out['automatic_test_creation_authorized'],len(out['advisory_digest'])==64]
 print({'suite':'v2563-verification-confidence-advisory','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
