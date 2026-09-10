from conscious_agent.ui_diagnosis import *
def req(x,m):
    if not x: raise AssertionError(m)
CASES={
'layout':{'product_runtime_observed':True,'overlap_detected':True},
'focus':{'product_runtime_observed':True,'focus_visible':False},
'state_ownership':{'product_runtime_observed':True,'duplicate_state_owner':True},
'navigation':{'product_runtime_observed':True,'route_resolved':False},
'request_lifecycle':{'product_runtime_observed':True,'stuck_loading':True},
'rendering':{'product_runtime_observed':True,'render_error':True},
}
