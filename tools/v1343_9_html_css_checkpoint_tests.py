from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1343_html_css_test_support import *
from html_css_implementation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_html_css_implementation(**args(src,runtime,grant,pres,git));row=r['html_css_implementation'];req(r['ok'] and row['implementation_state']=='completed','html_css_checkpoint_completed');req(row['compatibility_passed'] and row['browser_passed'],'static_and_browser_checks_passed');req(row['screenshot_captured'] and len(row['screenshot_digest'])==64,'visual_evidence_captured');req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before,'known_recoverable_source_state');req(row['candidate_only'] and not row['network_contacted'] and not row['release_authorized'] and row['raw_html_css_exposed'] is False,'privacy_authority_boundaries')
 print({'ok':True,'suite':'v1343.9-html-css-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
