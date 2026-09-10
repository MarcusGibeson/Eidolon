from __future__ import annotations
import hashlib,json
from pathlib import Path

def tree_signature(root:Path)->str:
    rows=[]
    for p in sorted(root.rglob('*'),key=lambda p:p.as_posix().casefold()):
        if p.is_file() and not p.is_symlink(): rows.append((p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def make_project(base:Path)->Path:
    p=base/'calculator-web'; p.mkdir(parents=True,exist_ok=True)
    (p/'index.html').write_text("<!doctype html><html><head><meta charset='utf-8'><title>Calculator</title></head><body><h1>Calculator</h1></body></html>\n",encoding='utf-8')
    return p

GOOD_HTML="""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calculator</title><link rel="stylesheet" href="styles.css"></head>
<body><main class="app"><h1>Calculator</h1><label for="a">First number</label><input id="a" inputmode="decimal"><label for="b">Second number</label><input id="b" inputmode="decimal"><label for="op">Operation</label><select id="op"><option value="add">Add</option><option value="subtract">Subtract</option><option value="multiply">Multiply</option><option value="divide">Divide</option></select><button id="calculate" type="button">Calculate</button><button id="clear" type="button">Clear</button><output id="result" aria-live="polite"></output></main><script src="app.js"></script></body></html>
"""
APP_JS="""function calculate(a,b,operation){
 const x=Number(a),y=Number(b); if(!Number.isFinite(x)||!Number.isFinite(y)) throw new Error('invalid-number');
 if(operation==='add') return x+y; if(operation==='subtract') return x-y; if(operation==='multiply') return x*y;
 if(operation==='divide'){if(y===0) throw new Error('divide-by-zero'); return x/y;} throw new Error('unknown-operation');
}
function clearCalculator(){return {a:'',b:'',result:''};}
if(typeof document!=='undefined'){const byId=id=>document.getElementById(id);byId('calculate').addEventListener('click',()=>{try{byId('result').textContent=String(calculate(byId('a').value,byId('b').value,byId('op').value));}catch(e){byId('result').textContent=e.message;}});byId('clear').addEventListener('click',()=>{byId('a').value='';byId('b').value='';byId('result').textContent='';byId('a').focus();});}
if(typeof module!=='undefined') module.exports={calculate,clearCalculator};
"""
BAD_CSS="*{box-sizing:border-box}body{font-family:system-ui,sans-serif;margin:0;padding:1rem}.app{width:90%;max-width:32rem;margin:auto;display:grid;gap:.75rem}input,select,button{font:inherit;padding:.65rem}output{min-height:2rem}\n"
GOOD_CSS=BAD_CSS+"button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid currentColor;outline-offset:2px}@media (max-width:36rem){.app{width:100%;margin:0}button{width:100%}}\n"
PACKAGE=json.dumps({'name':'bounded-calculator','private':True,'scripts':{'test':'node --test'},'dependencies':{},'devDependencies':{}},sort_keys=True,indent=2)+'\n'
TEST_JS="""const test=require('node:test');const assert=require('node:assert/strict');const {calculate,clearCalculator}=require('../app.js');
test('calculator operations',()=>{assert.equal(calculate(2,3,'add'),5);assert.equal(calculate(7,2,'subtract'),5);assert.equal(calculate(4,3,'multiply'),12);assert.equal(calculate(8,2,'divide'),4)});
test('clear state',()=>assert.deepEqual(clearCalculator(),{a:'',b:'',result:''}));
"""
README="""# Calculator Web Application

A dependency-free calculator using plain HTML, CSS, and JavaScript.

## Run
Open `index.html` in a browser.

## Test
Run `node --test` from the project directory. The suite covers arithmetic and clear-state behavior.
"""

class CodingAlphaProvider:
    def __init__(self,*,always_fail=False): self.calls=0; self.prompts=[]; self.always_fail=always_fail
    def __call__(self,prompt:str)->str:
        payload=json.loads(prompt); self.calls+=1; self.prompts.append(payload); auth=payload['authority']
        construction=payload.get('application_construction') or {}
        if construction.get('construction_profile')!='web_application': raise AssertionError('complete application contract missing')
        if self.calls==1 or self.always_fail:
            files=[{'path':'index.html','operation':'modify','content':GOOD_HTML},{'path':'app.js','operation':'create','content':APP_JS},{'path':'styles.css','operation':'create','content':BAD_CSS},{'path':'package.json','operation':'create','content':PACKAGE},{'path':'tests/app.test.js','operation':'create','content':TEST_JS},{'path':'README.md','operation':'create','content':README}]
        else:
            diag=(payload.get('previous_outcome') or {}).get('diagnostic_context') or {}
            codes=set(diag.get('quality_failure_codes') or [])
            if not {'keyboard_focus_visible','responsive_breakpoint_present'} <= codes: raise AssertionError(f'diagnostic evidence missing: {codes}')
            files=[{'path':'styles.css','operation':'modify','content':GOOD_CSS}]
        return json.dumps({'authority':{'request_id':auth['request_id'],'execution_digest':auth['execution_digest'],'attempt':auth['attempt']},'files':files})
