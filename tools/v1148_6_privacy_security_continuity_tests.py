from pathlib import Path
import tempfile
from conscious_agent.privacy_security_continuity import PrivacySecurityContinuityStore,build_privacy_security_continuity_inspection

def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'cognition';s=PrivacySecurityContinuityStore(root,clock=lambda:'2026-07-30T00:00:00.000Z')
  r=s.record_cycle('cycle-a');checks += [r['ok'],r['status']=='continuity_recorded']
  d=s.record_cycle('cycle-a');checks += [d['idempotent'],d['status']=='duplicate_suppressed']
  x=build_privacy_security_continuity_inspection(root);row=x['recent_records'][0]
  checks += [x['contract_version']=='v1148.6',x['record_count']==1,row['visible_state'] in {'steady','changed','attention'},not row['raw_content_recorded'],not row['provider_payload_recorded'],not row['source_modified'],bool(row['structural_digest'])]
 print(f'v1148.6 privacy/security continuity tests: {sum(checks)}/{len(checks)} passed')
 return 0 if all(checks) else 1
if __name__=='__main__': raise SystemExit(main())
