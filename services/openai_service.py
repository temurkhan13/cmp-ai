"""Async OpenAI GPT wrapper — singleton client."""

import os
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


async def chat_completion(
    system_prompt: str,
    user_message: str,
    history: list[str] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Send a chat completion request and return the assistant message."""
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        for i, msg in enumerate(history):
            if not msg:
                continue
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})

    messages.append({"role": "user", "content": user_message})

    logger.info("OpenAI request: model=%s, messages=%d", MODEL, len(messages))

    response = await get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content
    logger.info("OpenAI response: tokens=%s", response.usage.total_tokens if response.usage else "?")
    return content
