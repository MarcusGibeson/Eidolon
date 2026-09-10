"""Display-only chat labels; persisted timestamps are never rewritten."""
from datetime import date


def day_label(year: int, month: int, day: int) -> str:
    value = date(year, month, day)
    suffix = "th" if 10 <= day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{value.strftime('%B')} {day}{suffix}, {year}"


def time_label(hour: int, minute: int) -> str:
    return f"[{hour % 12 or 12}:{minute:02d}{'am' if hour < 12 else 'pm'}]"
