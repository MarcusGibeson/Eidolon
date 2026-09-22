"""Shared dashboard activity mounts; all state comes from the read-only API."""


def with_activity(content):
    return "<div class='chat-with-activity'><div>" + content + "</div><aside>" + activity_surface() + "</aside></div>"


def activity_surface(*, detail=False):
    return ("<link rel='stylesheet' href='/assets/activity.css?v=2'>"
            "<section id='activity-surface' data-detail='" + ("true" if detail else "false") +
            "' aria-label='Activity'><div id='activity-status' role='status'>Loading activity...</div>"
            "<div id='activity-current'></div>" +
            ("<div class='activity-detail-layout'><nav id='activity-history' aria-label='Activity history'></nav>"
             "<article id='activity-detail'></article></div>" if detail else "") +
            "</section><script src='/assets/activity.js?v=2' defer></script>")
