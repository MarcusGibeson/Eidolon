from conscious_agent.verification_gap_priority_v2567 import rank_verification_gap_candidates

def main():
 c={'contract_version':'v2566.0','candidates':[{'candidate_digest':'a'*64,'target_path':'conscious_agent/release_authority.py','severity':'high','gap_kind':'no_focused_structural_coverage'},{'candidate_digest':'b'*64,'target_path':'conscious_agent/dashboard.py','severity':'medium','gap_kind':'generic_surface_only'}]}
 o=rank_verification_gap_candidates(c)
 checks=[o['ranked'][0]['candidate_digest']=='a'*64,o['ranked'][0]['authority_sensitive'],o['selection_performed'] is False,o['selected_candidate_digest']=='',not o['automatic_selection_authorized'],not o['test_creation_authorized'],len(o['ranking_digest'])==64]
 print({'suite':'v2567-verification-gap-priority','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
