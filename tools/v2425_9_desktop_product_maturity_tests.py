from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
from product_maturity_v2400 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
D='a'*64
shell=build_chat_first_shell_projection(width_px=1280,height_px=800,scaling_percent=100)
req(shell['ok'] and shell['chat_first'],'chat_first_default')
req(shell['advanced_controls_collapsed'],'advanced_quiet_by_default')
req(shell['quiet_status'],'quiet_status_without_attention')
req(shell['chat_column_max_px']==980,'spacious_chat_column_bounded')
compact=build_chat_first_shell_projection(width_px=390,height_px=844,scaling_percent=100,pending_review_count=2)
req(compact['ok'] and compact['viewport']['compact'],'narrow_layout_supported')
req(not compact['quiet_status'] and compact['attention_badges']['pending_reviews']==2,'attention_badge_breaks_quiet_status')
req(not build_chat_first_shell_projection(width_px=float('nan'),height_px=800)['ok'],'nonfinite_width_rejected')
req(not build_chat_first_shell_projection(width_px=1280,height_px=800,primary_surface='chaos')['ok'],'unknown_primary_surface_rejected')
a11y=build_accessibility_fixture(width_px=390,height_px=844,scaling_percent=200,keyboard_only=True,reduced_motion=True,high_contrast=True)
req(a11y['ok'] and a11y['visible_focus'],'portable_accessibility_pass')
bad=build_accessibility_fixture(width_px=390,height_px=844,scaling_percent=100,keyboard_only=True,reduced_motion=True,high_contrast=False,visible_focus=False)
req(not bad['ok'] and 'keyboard_focus_not_visible' in bad['failure_codes'],'keyboard_focus_failure_visible')
start=advance_desktop_product_lifecycle(current_state='cold',event='start',evidence_digest=D)
req(start['ok'] and start['next_state']=='starting','cold_start_transition')
ready=advance_desktop_product_lifecycle(current_state='starting',event='startup_ready',evidence_digest=D)
req(ready['next_state']=='ready','startup_ready_transition')
upd=advance_desktop_product_lifecycle(current_state='ready',event='update_detected',evidence_digest=D)
req(upd['next_state']=='update_available','update_detected_is_review_path')
review=advance_desktop_product_lifecycle(current_state='update_available',event='review_update',evidence_digest=D)
req(review['next_state']=='update_review' and review['operator_install_decision_required'],'update_review_requires_operator')
req(not advance_desktop_product_lifecycle(current_state='update_review',event='install_update',evidence_digest=D)['ok'],'install_event_rejected')
req(not advance_desktop_product_lifecycle(current_state='ready',event='wat',evidence_digest=D)['ok'],'unsupported_transition_rejected')
accept=build_product_maturity_acceptance(shell=shell,accessibility=a11y,lifecycle_scenarios=[start,ready,upd,review])
req(accept['ok'] and accept['valid_lifecycle_scenario_count']==4,'portable_acceptance_composes')
req(accept['windows_desktop_trial_required'],'native_trial_not_manufactured')
layout=(ROOT/'conscious_agent/dashboard_layout.py').read_text(encoding='utf-8')
req("data-era10-chat-first='true'" in layout,'dashboard_marks_chat_first_product_shell')
req('.era10-product-maturity .realtime-chat-shell' in layout,'dashboard_has_era10_chat_first_css')
import ast
ast.parse((ROOT/'conscious_agent/dashboard_layout.py').read_text(encoding='utf-8'))
req(True,'dashboard_layout_python_syntax_valid')
req(all(not shell[k] for k in ('desktop_launched','tray_modified','update_installed','installation_authorized','authority_expanded')),'product_contract_non_authorizing')
print(json.dumps({'suite':'v2425.9-desktop-product-maturity','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
