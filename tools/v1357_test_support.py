from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
SOURCE='a'*64;E='b'*64;HW={'cpu_class':'desktop_mid','memory_gb':16,'storage_class':'ssd','power_profile':'balanced'}
B={'startup_ms':2000,'first_visible_ms':500,'total_ms':4000,'peak_memory_mb':512,'disk_delta_mb':25,'queue_delay_ms':250,'long_session_degradation_ratio':1.5}
def obs(n=7):return [{'startup_ms':900+i*10,'first_visible_ms':180+i*3,'total_ms':1500+i*20,'peak_memory_mb':180+i,'disk_delta_mb':3+i*.1,'queue_delay_ms':40+i,'long_session_degradation_ratio':1.05+i*.01} for i in range(n)]
def req(v,m):
 if not v:raise AssertionError(m)
