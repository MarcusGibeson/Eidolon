"""Direct-tool execution bridge for the Eidolon runtime package.

When Python executes ``tools/<suite>.py`` directly, ``tools/`` is sys.path[0]
and the repository root is otherwise not importable.  This tiny package bridge
makes ``import conscious_agent.<module>`` resolve to the real source directory
and exposes the historical top-level module directory expected by Eidolon's
runtime import convention.  It exists only under tools/ and is not used by the
product launchers.
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
ROOT = TOOLS.parent
AGENT = ROOT / "conscious_agent"
agent = str(AGENT)
root = str(ROOT)
if agent not in sys.path:
    sys.path.insert(0, agent)
if root not in sys.path:
    sys.path.insert(0, root)
__path__ = [agent]
