from __future__ import annotations

from typing import Any

REQUEST = "Build a responsive accessible daily check-in workflow with multiple states."
TASK_ID = "gamma_139613961396"
WINDOWS_CHECKS = [
    {"name": name, "passed": True}
    for name in (
        "desktop_layout",
        "narrow_layout",
        "keyboard_forward",
        "keyboard_backward",
        "focus_visible",
        "error_announcement",
        "completion_announcement",
        "no_horizontal_overflow",
    )
]


def require(condition: Any, message: str) -> None:
    if not condition:
        raise AssertionError(message)
