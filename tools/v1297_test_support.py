from __future__ import annotations
import base64,hashlib,tempfile,time
from pathlib import Path
from isolated_self_modification_foundations import source_only_manifest
from governed_self_update_foundations import DENIED_AUTHORITY,_digest,_record_digest,_write_json,_update_path,_backup_path

def d(v:object)->str:return hashlib.sha256(str(v).encode()).hexdigest()
def make_applied_fixture(*,authorization_consumed:bool=True,phase:str='applied_verified'):
 td=tempfile.TemporaryDirectory(prefix='eidolon-v1297-');base=Path(td.name);source=base/'source';runtime=base/'runtime';source.mkdir();runtime.mkdir()
 target=source/'main.py';before=b"VALUE = 'baseline'\n";after=b"VALUE = 'candidate'\n";target.write_bytes(before);bm=source_only_manifest(source);target.write_bytes(after);cm=source_only_manifest(source)
 update_id='selfupdate_'+hashlib.sha256(str(base).encode()).hexdigest()[:24];changed=[{'relative_path':'main.py','action':'modify','before_digest':hashlib.sha256(before).hexdigest(),'after_digest':hashlib.sha256(after).hexdigest(),'before_size_bytes':len(before),'after_size_bytes':len(after),'content_exposed':False}]
 result={'ok':True,'status':'governed_self_update_applied_and_verified','update_id':update_id,'source_manifest_before':bm['source_manifest_digest'],'source_manifest_after':cm['source_manifest_digest'],'candidate_manifest_digest':cm['source_manifest_digest'],'backup_prepared':True,'restart_health_passed':True}
 rec={'ok':True,'schema_version':'1','contract_version':'v1269.5','status':result['status'],'phase':phase,'update_id':update_id,'review_id':'selfreview_fixture','source_operation_id':'selfmod_fixture','source_manifest_digest':bm['source_manifest_digest'],'candidate_manifest_digest':cm['source_manifest_digest'],'changed_files':changed,'changed_file_count':1,'changed_files_digest':_digest(changed),'fresh_preflight_passed':True,'backup_required_before_first_write':True,'restart_health_verification_required':True,'automatic_rollback_on_failure_required':True,'authorization_consumed':authorization_consumed,'active_source_modified':True,'result':result,'result_digest':_digest(result),'content_minimized':True,**DENIED_AUTHORITY};rec['record_digest']=_record_digest(rec);_write_json(_update_path(update_id,runtime),rec)
 backup={'schema_version':'1','update_id':update_id,'source_manifest_digest':bm['source_manifest_digest'],'entry_count':1,'total_bytes':len(before),'entries':[{'relative_path':'main.py','existed':True,'content_digest':hashlib.sha256(before).hexdigest(),'content_b64':base64.b64encode(before).decode()}],'private_backup':True,'content_exposed':False};backup['backup_digest']=_digest({k:v for k,v in backup.items() if k!='backup_digest'});_write_json(_backup_path(update_id,runtime),backup)
 return td,source,runtime,update_id,bm,cm,before,after
