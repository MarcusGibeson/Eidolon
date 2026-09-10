import sys,tempfile,json;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_change_isolation import *;from v1383_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);s=source(r)
 req(not create_self_change_workspace(source_root=s,runtime_root=s/'runtime',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC)['ok'],'external');N+=1
 req(not create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id='bad',self_model_digest=SM,backlog_candidate_digest=BC)['ok'],'id');N+=1
 x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);pw=x['private_workspace'];ld=x['self_change_workspace']['lineage_digest'];req(x['ok'],'create');N+=1
 req(not create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC)['ok'],'duplicate');N+=1
 (Path(pw['input_root'])/'app.py').chmod(0o600);(Path(pw['input_root'])/'app.py').write_text('tampered\n');req(not verify_self_change_isolation(private_workspace=pw,expected_lineage_digest=ld)['ok'],'input tamper');N+=1
 t=dict(pw);t['lineage']=dict(pw['lineage']);t['lineage']['candidate_id']='selfc_ffffffffffff';req(not verify_self_change_isolation(private_workspace=t,expected_lineage_digest=ld)['ok'],'lineage');N+=1
 req(not create_self_change_workspace(source_root=s,runtime_root=r/'rt2',candidate_id='selfc_abcdefabcdef',self_model_digest='bad',backlog_candidate_digest=BC)['ok'],'digest');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1383-reliability'})
