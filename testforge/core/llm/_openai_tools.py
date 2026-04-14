"""Small OpenAI helper for structured tool-calling (bounded loop)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from testforge.core.exceptions import ConfigError


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]


def _require_api_key(config: dict) -> str:
    key = str(config.get("llm_api_key") or "").strip()
    if not key:
        raise ConfigError("llm_api_key is empty; run `testforge init` to set it.")
    return key


def _client(config: dict):
    _require_api_key(config)
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ConfigError("Missing dependency: install the 'openai' package.") from exc
    return OpenAI(api_key=str(config.get("llm_api_key") or "").strip())


def run_with_tools(
    *,
    config: dict,
    system: str,
    user: str,
    tools: List[ToolSpec],
    max_tool_rounds: int = 4,
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> str:
    """
    Run a bounded tool-calling loop and return the assistant's final text output.
    """
    client = _client(config)
    model_name = model or str(config.get("default_model") or "gpt-4o-mini").strip()

    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]
    handlers: Dict[str, Callable[..., Any]] = {t.name: t.handler for t in tools}

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for _ in range(max_tool_rounds):
        resp = client.chat.completions.create(
            model=model_name,
            temperature=temperature,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return (msg.content or "").strip()

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            },
        )

        for tc in tool_calls:
            name = tc.function.name
            raw_args = tc.function.arguments or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            handler = handlers.get(name)
            if handler is None:
                out = f"ERROR: unknown tool {name!r}"
            else:
                try:
                    out = handler(**args)
                except Exception as exc:  # keep loop deterministic-ish
                    out = f"ERROR: tool failed: {exc}"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(out, ensure_ascii=False),
                },
            )

    # If the model keeps calling tools, force a final response.
    messages.append(
        {
            "role": "user",
            "content": "Stop calling tools. Provide the final answer now.",
        },
    )
    resp = client.chat.completions.create(
        model=model_name,
        temperature=temperature,
        messages=messages,
        tools=openai_tools,
        tool_choice="none",
    )
    return (resp.choices[0].message.content or "").strip()

