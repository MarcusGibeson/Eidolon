from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from cross_language_changes import *
from v1349_cross_language_test_support import *
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_cross_language_change(**args(src,runtime,grant,pres,git));row=r['cross_language_change'];req(r['ok']);req(row['validation_passed_count']==5 and row['verification_passed_count']==3);req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before);req(not row['partial_commit_created'] and not row['raw_content_exposed']);req(all(not CROSS_LANGUAGE_DENIED_AUTHORITY[k] for k in ('network_authorized','dependency_installation_authorized','release_authorized','independent_authority_granted')))
 print({'ok':True,'suite':'v1349.9-cross-language-checkpoint','passed':p,'total':5})
if __name__=='__main__':main()
