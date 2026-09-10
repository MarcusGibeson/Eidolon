from __future__ import annotations
"""Content-free accessibility and input-hardening contract for chat surfaces."""
from dataclasses import dataclass,asdict
from typing import Any,Iterable
import hashlib,json

FOCUS_ORDER=("session_selector","message_composer","send_button","cancel_button","jump_latest","tools","diagnostics")

@dataclass(frozen=True)
class AccessibilityProjection:
    focus_order:tuple[str,...]=FOCUS_ORDER
    live_region_mode:str="polite"
    live_atomic:bool=False
    ime_safe:bool=True
    mobile_keyboard_safe:bool=True
    reduced_motion_supported:bool=True
    forced_colors_supported:bool=True
    content_free:bool=True
    def public_summary(self)->dict[str,Any]:
        row=asdict(self); row['focus_order']=list(self.focus_order); row['projection_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return row

def keyboard_send_action(*, key:str, shift:bool=False, composing:bool=False, mobile_send_hint:bool=False)->str:
    if composing: return 'noop'
    if str(key or '') not in {'Enter','Return'}: return 'noop'
    return 'newline' if shift else 'send'

def announcement_key(*, event_kind:str, operation_id:str='', state:str='')->str:
    """Stable key lets UI layers announce a response/error/action state once."""
    raw=f"{str(event_kind)}|{str(operation_id)}|{str(state)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]

def should_announce(*, key:str, announced:Iterable[str])->bool:
    return bool(key) and key not in set(str(v) for v in announced)

def narrow_layout_ok(*, width_px:int, composer_width_px:int, overlap_detected:bool=False)->bool:
    return int(width_px or 0)>=280 and int(composer_width_px or 0)>0 and int(composer_width_px)<=int(width_px) and not overlap_detected

def semantic_label_audit(labels:dict[str,str])->dict[str,Any]:
    required=('message_composer','send_button','cancel_button','status_region')
    missing=[k for k in required if not str(labels.get(k) or '').strip()]
    return {'ok':not missing,'missing_count':len(missing),'required_count':len(required),'content_free':True}

def accessibility_projection()->AccessibilityProjection:
    return AccessibilityProjection()
