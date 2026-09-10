from __future__ import annotations
"""v1358 bounded read-only security verification."""
import ast,hashlib,json,re
from pathlib import Path,PurePosixPath
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1358.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'dependency_install_authorized':False,'secret_access_authorized':False}
SECRET_PATTERNS=(re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(r'(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*["\'][^"\']{8,}["\']'))
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _safe(root:Path,rel:str)->Path:
 p=PurePosixPath(str(rel or '').replace('\\','/'))
 if p.is_absolute() or not p.parts or any(x in {'','..'} for x in p.parts):raise ValueError('security_path_invalid')
 out=(root/Path(*p.parts)).resolve();
 if root not in out.parents or not out.is_file() or out.is_symlink():raise ValueError('security_path_outside_project')
 return out
def _finding(category,severity,rel,line,text):return {'category':category,'severity':severity,'path_digest':hashlib.sha256(rel.encode()).hexdigest(),'line':int(line),'evidence_digest':hashlib.sha256(text.encode(errors='replace')).hexdigest(),'content_exposed':False}
def _python_findings(text,rel):
 rows=[]
 try:tree=ast.parse(text)
 except SyntaxError:return [_finding('python_parse_error','high',rel,0,'parse_error')]
 for node in ast.walk(tree):
  if isinstance(node,ast.Call):
   name=''
   if isinstance(node.func,ast.Name):name=node.func.id
   elif isinstance(node.func,ast.Attribute):name=node.func.attr
   if name in {'eval','exec','system'}:rows.append(_finding('unsafe_dynamic_execution','high',rel,getattr(node,'lineno',0),name))
   if name in {'run','Popen','call','check_call','check_output'} and any(k.arg=='shell' and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords):rows.append(_finding('unsafe_shell_construction','high',rel,getattr(node,'lineno',0),'shell_true'))
   if name=='extractall':rows.append(_finding('archive_extraction_requires_containment','high',rel,getattr(node,'lineno',0),'extractall'))
   if name in {'print','info','debug','warning','error','exception'}:
    for arg in node.args:
     if isinstance(arg,ast.Name) and re.search(r'(?i)(secret|token|password|credential|api_key)',arg.id):rows.append(_finding('possible_secret_logging','high',rel,getattr(node,'lineno',0),arg.id))
 return rows
def scan_security(*,project_root:str|Path,source_manifest_digest:str,file_paths:Sequence[str],dependency_evidence:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')):return {'ok':False,'status':'security_source_lineage_required','action_executed':False,**DENIED}
 root=Path(project_root).resolve()
 if not root.is_dir() or len(file_paths)>512:return {'ok':False,'status':'security_project_or_file_count_invalid','action_executed':False,**DENIED}
 findings=[];scanned=0
 try:
  for rel0 in file_paths:
   rel=PurePosixPath(str(rel0).replace('\\','/')).as_posix();p=_safe(root,rel);data=p.read_bytes()
   if len(data)>2*1024*1024:raise ValueError('security_file_too_large')
   text=data.decode('utf-8-sig',errors='replace');scanned+=1
   for pat in SECRET_PATTERNS:
    for m in pat.finditer(text):findings.append(_finding('secret_material','critical',rel,text.count('\n',0,m.start())+1,m.group(0)))
   if p.suffix.lower()=='.py':findings.extend(_python_findings(text,rel))
  dep_rows=[]
  for raw in dependency_evidence:
   ev=str(raw.get('evidence_digest') or '')
   if not re.fullmatch(r'[a-f0-9]{64}',ev):raise ValueError('dependency_evidence_invalid')
   vulns=int(raw.get('known_vulnerability_count') or 0);prov=raw.get('provenance_verified') is True;pinned=raw.get('lockfile_pinned') is True
   dep={'dependency_digest':_d(str(raw.get('dependency_id') or '')),'evidence_digest':ev,'known_vulnerability_count':vulns,'provenance_verified':prov,'lockfile_pinned':pinned,'passed':vulns==0 and prov and pinned};dep_rows.append(dep)
   if not dep['passed']:findings.append({'category':'dependency_risk','severity':'high','path_digest':'','line':0,'evidence_digest':_d(dep),'content_exposed':False})
 except (OSError,ValueError) as exc:return {'ok':False,'status':str(exc),'action_executed':False,**DENIED}
 critical=sum(x['severity']=='critical' for x in findings);high=sum(x['severity']=='high' for x in findings);passed=critical==0 and high==0
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'scanned_file_count':scanned,'dependency_evidence_count':len(dependency_evidence),'finding_count':len(findings),'critical_count':critical,'high_count':high,'findings':findings[:256],'verification_passed':passed,'read_only':True,'raw_source_persisted':False,'secret_values_exposed':False,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':passed,'status':'security_verification_passed' if passed else 'security_findings_detected','security_verification':rec,'action_executed':False,**DENIED}
def process_security_verification_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show security verification','inspect security verification','show security tests'}:return {'active':False}
 rec=dict((project_state or {}).get('security_verification') or {});return {'active':True,'ok':bool(rec),'status':'security_verification_found' if rec else 'security_verification_missing','security_verification':rec,'action_executed':False,**DENIED}
