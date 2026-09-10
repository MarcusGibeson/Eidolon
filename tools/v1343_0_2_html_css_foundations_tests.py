from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1343_html_css_test_support import *
from html_css_implementation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 req(REQUIRED_PRECONDITIONS==('git','file_read','file_patch','browser'),'preconditions_explicit')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));s=inspect_html_css_project(src);req(s['html_file_count']==1 and s['css_file_count']==1,'html_css_inventory');req(s['accessibility_issue_count']==0 and s['responsive_signal_count']>=3 and s['focus_style_count']>=1 and s['reduced_motion_count']>=1,'a11y_responsive_signals');req(s['inspection_only'] and not s['browser_launched'] and not s['network_contacted'],'inspection_side_effect_free');bad=args(src,runtime,grant,{k:v for k,v in pres.items() if k!='browser'},git);r=run_html_css_implementation(**bad);req(not r['ok'] and r['status']=='complete_html_css_preconditions_required' and not r['action_executed'],'missing_browser_precondition_blocks')
 print({'ok':True,'suite':'v1343.0-2-html-css-foundations','passed':p[0],'total':5})
if __name__=='__main__':main()
