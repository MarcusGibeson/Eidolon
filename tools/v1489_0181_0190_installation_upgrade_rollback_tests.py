from __future__ import annotations
import os,sys,tempfile,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b19-'));AUTH=R/'Eidolon';CAND=R/'candidate';RUN=R/'runtime'
for p in (AUTH,CAND,RUN):p.mkdir()
(AUTH/'version.txt').write_text('old');(CAND/'version.txt').write_text('new');(AUTH/'conscious_agent').mkdir();(AUTH/'conscious_agent'/'main.py').write_text('print(1)');(CAND/'conscious_agent').mkdir();(CAND/'conscious_agent'/'main.py').write_text('print(2)')
for name in ('settings','conversations','memories','projects','approvals'):(RUN/name).mkdir();((RUN/name)/'state.json').write_text('{}')
os.environ['EIDOLON_DATA_DIR']=str(RUN);os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(AGENT))
from installation_upgrade_rollback_contract import *
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 a=tree_digest(AUTH);c=tree_digest(CAND);b=upgrade_boundary(authoritative_digest=a,candidate_digest=c);ck('0181 authoritative/candidate boundary explicit',not b['same_source'] and not b['candidate_authoritative'] and b['operator_approval_required'],b)
 z=R/'candidate.zip'
 with zipfile.ZipFile(z,'w') as out:
  for p in CAND.rglob('*'):
   if p.is_file():out.write(p,Path('Eidolon')/p.relative_to(CAND))
 ck('0182 source-only extraction audit',source_only_archive_audit(z)['ok'],source_only_archive_audit(z))
 priv=private_runtime_preservation(RUN);ck('0183 private settings/conversations/memories/projects/approvals preserved',priv['target_count']==5 and not priv['source_upgrade_may_delete_private_data'],priv)
 comp=schema_compatibility(current=4,candidate_min=3,candidate_max=5);ck('0184 compatible schema starts',comp['compatible'] and comp['startup_allowed'],comp)
 stale=schema_compatibility(current=2,candidate_min=3,candidate_max=5);ck('0184 incompatible schema blocked before startup',not stale['startup_allowed'] and stale['migration_required'],stale)
 mig=migration_preview(current=2,target=3);ck('0185 migration is preview only',mig['preview_only'] and not mig['applied'] and mig['operator_approval_required'],mig)
 rb=rollback_preview(source_backup_available=True,private_data_compatible=True);ck('0186 rollback preserves compatible private data',rb['rollback_possible'] and rb['preserve_private_data'] and not rb['apply_now'],rb)
 ep=locate_entrypoints(AUTH);ck('0187 desktop/entrypoint locator finds main',ep['count']>=1 and 'conscious_agent/main.py' in ep['entrypoints'],ep)
 coh=installation_coherence(expected_root_name='Eidolon',actual_root=AUTH,expected_manifest=a,actual_manifest=a);ck('0188 coherent root/version accepted',coh['coherent'],coh)
 bad=installation_coherence(expected_root_name='Eidolon',actual_root=CAND,expected_manifest=a,actual_manifest=c);ck('0188 wrong-root/mixed version detected',bad['wrong_root'] and bad['mixed_or_partial_version'] and not bad['automatic_repair_allowed'],bad)
 sim=simulate_upgrade_rollback(AUTH,CAND,RUN,R/'work');ck('0189 fresh-install upgrade restart rollback simulation',all(sim[k] for k in ('fresh_install_simulated','upgrade_candidate_matches','restart_source_available','rollback_matches_authoritative','private_runtime_unchanged')) and not sim['live_install_modified'],sim)
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)
