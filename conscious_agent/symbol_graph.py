from __future__ import annotations
"""v1312 symbol/reference/import graph with freshness and bounded deduplication."""
import ast,re
from pathlib import Path
from typing import Any
from project_evidence_store import *
from repository_inventory import build_repository_inventory,load_repository_inventory
CONTRACT_VERSION='v1312.8';ROUTE_OWNER_HINTS={'app','router','api','server','blueprint','bp','application'};MAX_SCAN_BYTES=512*1024
PY_IMPORT=re.compile(r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))',re.M);JS_IMPORT=re.compile(r'(?:from\s+["\']([^"\']+)["\']|require\(["\']([^"\']+)["\']\))')
def _path(wid,runtime_root=None):return evidence_root('symbol_graph',runtime_root)/'records'/f'{wid}.json'
def _python_rows(rel,text,pdigest):
 symbols=[];edges=[];degraded=False
 try:tree=ast.parse(text)
 except (SyntaxError,ValueError):return symbols,edges,True
 try:nodes=list(ast.walk(tree))
 except RecursionError:
  nodes=[];stack=[tree];degraded=True
  while stack:
   n=stack.pop();nodes.append(n);stack.extend(ast.iter_child_nodes(n))
 names={}
 for n in nodes:
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
   sid=digest({'path':pdigest,'name':n.name,'line':getattr(n,'lineno',0),'kind':type(n).__name__});symbols.append({'symbol_id':sid,'name':n.name,'kind':'class' if isinstance(n,ast.ClassDef) else 'function','relative_path_digest':pdigest});names[n.name]=sid
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr.lower() in {'get','post','put','delete','patch'} and isinstance(n.func.value,ast.Name) and n.func.value.id.lower() in ROUTE_OWNER_HINTS:
   route='route_'+digest({'path':pdigest,'line':getattr(n,'lineno',0)})[:20];symbols.append({'symbol_id':route,'name':n.func.attr.lower(),'kind':'route','relative_path_digest':pdigest})
 for m in PY_IMPORT.finditer(text):edges.append({'edge_kind':'import','source_path_digest':pdigest,'target':m.group(1) or m.group(2)})
 counts={}
 for n in nodes:
  if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load):counts[n.id]=counts.get(n.id,0)+1
 for name,count in counts.items():edges.append({'edge_kind':'reference','source_path_digest':pdigest,'target_name':name,'occurrence_count':count})
 return symbols,edges,degraded
def build_symbol_graph(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None):
 root=Path(source_root).resolve();pub=build_repository_inventory(root,runtime_root=runtime_root,now_unix=now_unix)['inventory'];wid=pub['workspace_digest'];existing=load_symbol_graph(wid,runtime_root=runtime_root);
 if existing and existing.get('source_manifest_digest')==pub.get('source_manifest_digest'):return {'ok':True,'status':'symbol_graph_current','symbol_graph':existing,'action_executed':False,**DENIED_AUTHORITY}
 inv=load_repository_inventory(wid,runtime_root=runtime_root,include_private=True);symbols=[];edges=[];degraded=0
 for f in inv.get('files') or []:
  rel=f['relative_path'];p=root/rel
  if f['size_bytes']>MAX_SCAN_BYTES or f['suffix'] not in {'.py','.js','.ts','.jsx','.tsx'}:continue
  try:text=p.read_text(encoding='utf-8')
  except (OSError,UnicodeDecodeError):continue
  if f['suffix']=='.py':s,e,d=_python_rows(rel,text,f['relative_path_digest']);symbols+=s;edges+=e;degraded+=int(d)
  else:
   for m in JS_IMPORT.finditer(text):edges.append({'edge_kind':'import','source_path_digest':f['relative_path_digest'],'target':m.group(1) or m.group(2)})
 # dedup
 symbols=list({x['symbol_id']:x for x in symbols}.values());agg={}
 for e in edges:
  key=(e.get('edge_kind'),e.get('source_path_digest'),e.get('target'),e.get('target_name'))
  count=int(e.get('occurrence_count',1))
  if key in agg:
   agg[key]['occurrence_count']=int(agg[key].get('occurrence_count',1))+count
  else:
   row=dict(e)
   if row.get('edge_kind')=='reference':row['occurrence_count']=count
   agg[key]=row
 edges=list(agg.values());names={x.get('name'):x['symbol_id'] for x in symbols if x.get('name')};coverage=[];seen_cov=set()
 for f in inv.get('files') or []:
  if not f.get('test'):continue
  try:text=(root/f['relative_path']).read_text(encoding='utf-8')
  except Exception:continue
  tokens=set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b',text))
  for name in tokens & names.keys():
   key=(f['relative_path_digest'],names[name])
   if key in seen_cov:continue
   seen_cov.add(key);coverage.append({'test_file_digest':key[0],'symbol_id':key[1]})
   if len(coverage)>=4096:break
  if len(coverage)>=4096:break
 sdesc=write_collection('symbol_graph',wid,'symbols',symbols,runtime_root) if len(symbols)>128 else {'sharded':False,'items':symbols};edesc=write_collection('symbol_graph',wid,'edges',edges,runtime_root) if len(edges)>256 else {'sharded':False,'items':edges};row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':pub['source_manifest_digest'],'symbol_collection':sdesc,'edge_collection':edesc,'coverage_link_candidates':coverage[:4096],'symbol_count':len(symbols),'edge_count':len(edges),'degraded_parser_count':degraded,'graph_sharded':bool(sdesc.get('sharded') or edesc.get('sharded')),'measured_test_coverage':False,'raw_source_content_persisted':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'symbol_graph_ready','symbol_graph':public_symbol_graph(row),'action_executed':False,**DENIED_AUTHORITY}
def _inflate(row,runtime_root=None):out=dict(row);out['symbols']=read_collection('symbol_graph',row['workspace_digest'],'symbols',row.get('symbol_collection') or {},runtime_root);out['edges']=read_collection('symbol_graph',row['workspace_digest'],'edges',row.get('edge_collection') or {},runtime_root);return out
def public_symbol_graph(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'symbol_count':row.get('symbol_count',0),'edge_count':row.get('edge_count',0),'coverage_candidate_count':len(row.get('coverage_link_candidates') or []),'graph_sharded':bool(row.get('graph_sharded')),'degraded_parser_count':int(row.get('degraded_parser_count',0)),'measured_test_coverage':False,'source_paths_exposed':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_symbol_graph(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (_inflate(row,runtime_root) if include_private else public_symbol_graph(row)) if row and valid(row) else {}
__all__=['CONTRACT_VERSION','ROUTE_OWNER_HINTS','build_symbol_graph','load_symbol_graph','public_symbol_graph']
