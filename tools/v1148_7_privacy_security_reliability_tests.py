from pathlib import Path
import tempfile
from conscious_agent.privacy_security_continuity import PrivacySecurityContinuityStore
from conscious_agent.privacy_security_reliability import build_privacy_security_reliability

def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'cognition';PrivacySecurityContinuityStore(root).record_cycle('cycle-a');r=build_privacy_security_reliability(root)
  checks += [r['contract_version']=='v1148.7',r['classification'] in {'reliable','review_required'},r['operator_visible_state'] in {'ready','attention'},0<=r['reliability_score']<=100,0<=r['uncertainty']<=100,r['continuity_record_count']==1,not r['raw_content_exposed'],not r['provider_payload_exposed'],not r['hidden_reasoning_exposed'],not r['provider_contacted'],not r['runtime_mutated'],not r['source_modified'],r['read_only'],bool(r['structural_digest'])]
 print(f'v1148.7 privacy/security reliability tests: {sum(checks)}/{len(checks)} passed')
 return 0 if all(checks) else 1
if __name__=='__main__': raise SystemExit(main())
