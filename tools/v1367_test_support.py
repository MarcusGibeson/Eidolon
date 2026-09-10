from data_diagnosis import *
def req(x,m):
 if not x: raise AssertionError(m)
EXP={'schema_digest':'a'*64,'row_count':3,'index_entry_count':3,'index_digest':'b'*64,'schema_version':2}
def clean():return {'schema_digest':'a'*64,'row_count':3,'transaction_state':'committed','index_entry_count':3,'index_digest':'b'*64,'schema_version':2,'applied_migrations':[1,2],'public_evidence_contains_content':False,'content_digest':'c'*64,'metadata_content_digest':'c'*64}
def defective(code):
 x=clean()
 if code=='schema_drift':x['schema_digest']='d'*64
 elif code=='partial_write':x['transaction_state']='started'
 elif code=='index_corruption':x['index_entry_count']=2
 elif code=='migration_gap':x['applied_migrations']=[1]
 elif code=='content_metadata_boundary_failure':x['public_evidence_contains_content']=True
 return x
