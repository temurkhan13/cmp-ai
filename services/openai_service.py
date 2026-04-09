"""Async Claude (Anthropic) wrapper — singleton client."""

import os
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


async def chat_completion(
    system_prompt: str,
    user_message: str,
    history: list[str] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Send a message to Claude and return the assistant response."""
    messages = []

    if history:
        for i, msg in enumerate(history):
            if not msg:
                continue
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})

    messages.append({"role": "user", "content": user_message or "Begin the assessment. Ask me the first question."})

    logger.info("Claude request: model=%s, messages=%d", MODEL, len(messages))

    response = await get_client().messages.create(
        model=MODEL,
        system=system_prompt,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response.content[0].text
    logger.info("Claude response: input=%s, output=%s tokens",
                response.usage.input_tokens, response.usage.output_tokens)
    return content
