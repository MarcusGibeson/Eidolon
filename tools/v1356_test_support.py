from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1337_browser_validation_test_support import browser_candidate
HTML='''<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>:focus-visible{outline:2px solid currentColor}@media (max-width:500px){main{max-width:95vw}}@media (prefers-reduced-motion: reduce){*{transition:none!important}}#scroll{height:40px;overflow:auto}</style></head><body><nav>Primary</nav><main><label for="ime">Text</label><input id="ime" oninput="document.getElementById('out').textContent=this.value"><div id="out"></div><button id="go" onkeydown="if(event.key==='Enter')document.getElementById('kbd').textContent='activated'">Go</button><div id="kbd">idle</div><div id="scroll" tabindex="0" onkeydown="if(event.key==='End'){this.scrollTop=this.scrollHeight;document.getElementById('sc').textContent='scrolled'}"><div style="height:300px">long</div></div><div id="sc">idle</div></main></body></html>'''
def fixture(base:Path):
 src,runtime,grant,wid,candidate,browserpre=browser_candidate(base);(candidate/'ui.html').write_text(HTML,encoding='utf-8');return src,runtime,grant,wid,candidate,browserpre
def req(v,m):
 if not v:raise AssertionError(m)
INTER=[{'op':'fill','selector':'#ime','value':'かな漢字🙂'},{'op':'press','selector':'#go','value':'Enter'},{'op':'press','selector':'#scroll','value':'End'}]
CHECK=[{'kind':'text_equals','selector':'#out','expected':'かな漢字🙂'},{'kind':'text_equals','selector':'#kbd','expected':'activated'},{'kind':'text_equals','selector':'#sc','expected':'scrolled'}]
