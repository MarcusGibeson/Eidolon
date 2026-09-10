from provider_diagnosis import *
def req(x,m):
 if not x:raise AssertionError(m)
CASES={
'configuration':{'configured':False},
'endpoint':{'configured':True,'endpoint_resolved':False},
'model':{'configured':True,'endpoint_resolved':True,'model_present':False},
'transport':{'configured':True,'endpoint_resolved':True,'model_present':True,'transport_connected':False},
'streaming':{'transport_connected':True,'streaming_expected':True,'streaming_valid':False},
'embedding':{'transport_connected':True,'embedding_expected':True,'embedding_valid':False},
'timeout':{'transport_connected':True,'timed_out':True},
'model_quality':{'transport_connected':True,'response_schema_valid':True,'quality_acceptable':False},
}
