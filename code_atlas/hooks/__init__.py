"""Opt-in client hooks — outside the MCP tool surface (tasks 036, 053)."""

from __future__ import annotations

import json


def additional_context(event: str, line: str) -> str:
    """The one stdout shape a tool-event hook's line reaches the model in (345-C1, 346)."""
    return json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": line}})
