"""Anthropic client + helpers for structured output via tool use."""
from __future__ import annotations

import json
from typing import Type, TypeVar

from anthropic import Anthropic
from pydantic import BaseModel

from app.config import settings

_client: Anthropic | None = None

T = TypeVar("T", bound=BaseModel)


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def extract_structured(
    *,
    model: str,
    system: str,
    user_content: list[dict] | str,
    response_schema: Type[T],
    max_tokens: int = 2048,
) -> T:
    """Call Claude with a single forced tool-use and return a validated Pydantic model.

    - `user_content` can be a plain string or a list of content blocks (for vision).
    - The tool name is derived from the schema class name.
    - Claude is forced to call the tool via `tool_choice`.
    - Defensively handles Opus 4.7's occasional quirk of returning tool input
      as a JSON string rather than a dict for deeply nested schemas.
    """
    client = get_client()
    tool_name = f"record_{response_schema.__name__.lower()}"

    tool = {
        "name": tool_name,
        "description": f"Record a {response_schema.__name__} based on the input.",
        "input_schema": response_schema.model_json_schema(),
    }

    messages = [
        {
            "role": "user",
            "content": user_content if isinstance(user_content, list) else [
                {"type": "text", "text": user_content}
            ],
        }
    ]

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=messages,
    )

    for block in resp.content:
        if block.type == "tool_use" and block.name == tool_name:
            raw = block.input
            if isinstance(raw, str):
                raw = json.loads(raw)
            return response_schema.model_validate(raw)

    raise RuntimeError(f"Model did not call tool {tool_name}. Response: {resp.content}")