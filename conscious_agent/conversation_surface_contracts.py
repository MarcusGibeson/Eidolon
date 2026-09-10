from __future__ import annotations

"""Lightweight conversation-surface contracts shared by deferred services.

This module contains only stable values and exception types needed before the
heavier conversation, action, evaluation, and relationship services are loaded.
It performs no provider calls and no runtime writes.
"""

ACTION_RETRY = "action_retry"
ACTION_CANCEL = "action_cancel"

CURATABLE_RELATIONSHIP_TYPES: dict[str, str] = {
    "nickname": "Preferred name or nickname",
    "preference": "Established preference",
    "relationship": "Relationship fact",
    "important_moment": "Important shared moment",
    "commitment": "Established commitment",
    "personal_fact": "Relevant personal fact",
    "user_mood": "Explicit user mood",
}


class DailyEvaluationError(ValueError):
    pass


class RelationshipMemoryCurationError(ValueError):
    pass
