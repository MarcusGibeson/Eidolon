from __future__ import annotations
"""Bounded practical-coding helpers for isolated project work (v1489 Bundle 15).

No function here installs, promotes, or mutates Eidolon's authoritative source.
Callers provide an explicit isolated project root.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
from typing import Any,Iterable,Mapping
import hashlib,json,re

ALLOWED_SUFFIXES={'.html','.css','.js','.json','.md','.txt','.py'}

def _safe_root(root:Path|str)->Path:
    p=Path(root).resolve()
    if not p.exists() or not p.is_dir(): raise ValueError('isolated project root required')
    return p

def inventory_project(root:Path|str,limit:int=200)->dict[str,Any]:
    r=_safe_root(root); rows=[]
    for p in sorted(r.rglob('*')):
        if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES:
            rel=p.relative_to(r).as_posix(); rows.append({'path':rel,'suffix':p.suffix.lower(),'size':p.stat().st_size})
            if len(rows)>=limit: break
    return {'root_digest':hashlib.sha256(str(r).encode()).hexdigest()[:24],'files':rows,'file_count':len(rows),'truncated':len(rows)>=limit,'content_free':True}

def bounded_implementation_plan(request:str,inventory:Mapping[str,Any])->dict[str,Any]:
    files=[row['path'] for row in inventory.get('files',[]) if isinstance(row,dict)]
    selected=[f for f in files if Path(f).suffix.lower() in {'.html','.css','.js'}][:6]
    return {'request_digest':hashlib.sha256(str(request or '').encode()).hexdigest()[:24],'inspect_first':True,'selected_files':selected,'test_required':True,'apply_to_authoritative_source':False,'content_free':True}

def write_calculator_webpage(root:Path|str)->list[str]:
    r=_safe_root(root)
    html=r/'index.html'; css=r/'style.css'; js=r/'app.js'
    if not html.exists(): html.write_text("<!doctype html><html><head><link rel='stylesheet' href='style.css'></head><body><main><h1>Calculator</h1><input id='display' aria-label='Calculator display' readonly><div id='keys'></div></main><script src='app.js'></script></body></html>\n")
    if not css.exists(): css.write_text("body{font-family:system-ui;margin:0;display:grid;place-items:center;min-height:100vh}main{width:min(92vw,24rem)}#display{width:100%;font-size:2rem;box-sizing:border-box}#keys{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;margin-top:.5rem}button{min-height:3rem}\n")
    if not js.exists(): js.write_text("const display=document.querySelector('#display');const keys=document.querySelector('#keys');const values=['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+'];let expr='';for(const value of values){const b=document.createElement('button');b.textContent=value;b.addEventListener('click',()=>{if(value==='='){try{expr=String(Function('return ('+expr+')')())}catch{expr=''};}else{expr+=value;}display.value=expr;});keys.appendChild(b);}\n")
    return [p.name for p in (html,css,js)]

def static_web_behavior_check(root:Path|str)->dict[str,Any]:
    r=_safe_root(root); h=(r/'index.html').read_text() if (r/'index.html').exists() else ''; c=(r/'style.css').read_text() if (r/'style.css').exists() else ''; j=(r/'app.js').read_text() if (r/'app.js').exists() else ''
    return {'ok':all(["id='display'" in h,"id='keys'" in h,"grid-template-columns:repeat(4,1fr)" in c,"addEventListener('click'" in j,"value==='='" in j]),'html_present':bool(h),'css_present':bool(c),'js_present':bool(j),'content_free':True}

def repair_known_defect(root:Path|str,kind:str)->dict[str,Any]:
    r=_safe_root(root); changed=[]; token=str(kind or '')
    if token=='functional_equal_missing':
        p=r/'app.js'; s=p.read_text();
        if "value==='='" not in s:
            s=s.replace("display.value=expr;","if(value==='='){try{expr=String(Function('return ('+expr+')')())}catch{expr=''};}display.value=expr;")
            p.write_text(s);changed.append('app.js')
    elif token=='responsive_overflow':
        p=r/'style.css'; s=p.read_text();
        if 'width:min(92vw,24rem)' not in s:
            s+='\nmain{width:min(92vw,24rem)}\n';p.write_text(s);changed.append('style.css')
    return {'defect_class':token,'changed_files':changed,'bounded':True,'authoritative_source_modified':False,'content_free':True}

def snapshot_digests(root:Path|str)->dict[str,str]:
    r=_safe_root(root); out={}
    for p in sorted(r.rglob('*')):
        if p.is_file(): out[p.relative_to(r).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def unrelated_changes_preserved(before:Mapping[str,str],after:Mapping[str,str],allowed_changed:Iterable[str])->bool:
    allowed=set(allowed_changed)
    for path,digest in before.items():
        if path not in allowed and after.get(path)!=digest: return False
    return True

def reviewable_patch_evidence(before:Mapping[str,str],after:Mapping[str,str])->dict[str,Any]:
    changed=sorted({*before,*after}, key=str)
    changed=[p for p in changed if before.get(p)!=after.get(p)]
    return {'changed_files':changed,'changed_file_count':len(changed),'patch_digest':hashlib.sha256(json.dumps({p:[before.get(p),after.get(p)] for p in changed},sort_keys=True).encode()).hexdigest(),'auto_apply_allowed':False,'rollback_required':True,'content_free':True}
