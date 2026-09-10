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
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);c=[change(src/'index.html','<img alt="Decorative"','<img')];r=run_html_css_implementation(**args(src,runtime,grant,pres,git,changes=c));req(not r['ok'] and r['html_css_implementation']['failure_stage']=='accessibility_regression','missing_alt_regression_blocked');req(manifest(src)==before,'a11y_failure_source_immutable')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));c=[change(src/'index.html','<button id="go"','<div id="go"')];r=run_html_css_implementation(**args(src,runtime,grant,pres,git,changes=c));req(not r['ok'] and r['html_css_implementation']['failure_stage']=='accessibility_regression','keyboard_regression_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));c=[change(src/'styles.css',CSS,'.card { width: 400px; }\nbutton:focus-visible { outline: 2px solid currentColor; }\n')];r=run_html_css_implementation(**args(src,runtime,grant,pres,git,changes=c));req(not r['ok'] and r['html_css_implementation']['failure_stage']=='responsive_contract_regression','responsive_loss_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));c=[change(src/'styles.css','width: min(90vw, 32rem);','width: 420px;')];r=run_html_css_implementation(**args(src,runtime,grant,pres,git,changes=c));req(not r['ok'] and r['html_css_implementation']['failure_stage']=='rigid_layout_regression','rigid_width_increase_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_html_css_implementation(**args(src,runtime,grant,pres,git,expected_screenshot_digest='0'*64));row=r['html_css_implementation'];req(not r['ok'] and row['failure_stage']=='visual_regression_detected' and row['browser_passed'] and row['screenshot_captured'] and row['workspace_cleaned'],'visual_baseline_mismatch_blocks_commit')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_html_css_implementation(**args(src,runtime,grant,pres,git,checks=[{'kind':'visible','selector':'#missing'}]));req(not r['ok'] and r['html_css_implementation']['failure_stage']=='html_css_browser_validation_failed' and r['html_css_implementation']['workspace_cleaned'],'browser_ui_failure_cleans')
 req(not HTML_CSS_DENIED_AUTHORITY['network_authorized'] and not HTML_CSS_DENIED_AUTHORITY['release_authorized'],'no_network_release_authority')
 print({'ok':True,'suite':'v1343.6-8-html-css-reliability','passed':p[0],'total':8})
if __name__=='__main__':main()
