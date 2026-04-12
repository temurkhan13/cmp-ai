"""Async Claude (Anthropic) wrapper — singleton client with caching and retry."""

import os
import logging
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Approximate tokens per character for context window management
CHARS_PER_TOKEN = 4
MAX_CONTEXT_TOKENS = 180_000  # Claude Sonnet context window, leave headroom
MAX_HISTORY_TOKENS = 100_000  # Reserve space for system prompt + RAG + response


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_retries=2,  # Retry on transient failures (rate limits, network)
        )
    return _client


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return len(text) // CHARS_PER_TOKEN


def _truncate_history(messages: list[dict], max_tokens: int = MAX_HISTORY_TOKENS) -> list[dict]:
    """Keep the most recent messages that fit within the token budget.
    Always preserves the last message (the current user message).
    Removes oldest messages first, always in pairs to maintain alternation.
    """
    if not messages:
        return messages

    total = sum(_estimate_tokens(m["content"]) for m in messages)
    if total <= max_tokens:
        return messages

    # Always keep the last message; trim from the front in pairs
    current = messages[-1:]
    history = messages[:-1]

    # Remove from front (oldest) in pairs to maintain role alternation
    while history and sum(_estimate_tokens(m["content"]) for m in history + current) > max_tokens:
        # Remove a pair (user + assistant) from the front
        if len(history) >= 2:
            history = history[2:]
        elif len(history) == 1:
            history = []
        else:
            break

    logger.info("History truncated: %d messages kept out of %d", len(history) + len(current), len(messages) + 1)
    return history + current


def _build_history_messages(history: list[str] | None) -> list[dict]:
    """Convert flat history list to role-alternating messages.
    Handles empty strings by preserving role parity (uses placeholder).
    Ensures strict user/assistant alternation required by Claude API.
    """
    if not history:
        return []

    messages = []
    for i, msg in enumerate(history):
        role = "user" if i % 2 == 0 else "assistant"
        # Never skip — use placeholder to preserve alternation parity
        content = msg if msg and msg.strip() else "(no message)"
        messages.append({"role": role, "content": content})

    # Enforce alternation: merge consecutive same-role messages
    deduped = []
    for m in messages:
        if deduped and deduped[-1]["role"] == m["role"]:
            deduped[-1]["content"] += "\n" + m["content"]
        else:
            deduped.append(m)

    # Claude requires first message to be "user" — if it starts with assistant, prepend
    if deduped and deduped[0]["role"] == "assistant":
        deduped.insert(0, {"role": "user", "content": "(conversation start)"})

    return deduped


async def chat_completion(
    system_prompt: str,
    user_message: str,
    history: list[str] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    default_user_message: str | None = None,
) -> str:
    """Send a message to Claude and return the assistant response.

    Args:
        system_prompt: The system instruction for Claude.
        user_message: The current user message.
        history: Flat list of alternating user/assistant messages.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
        max_tokens: Max response tokens.
        default_user_message: Fallback if user_message is empty. If None, uses generic.
    """
    messages = _build_history_messages(history)

    # Handle empty user message with endpoint-specific fallback
    if not user_message or not user_message.strip():
        if default_user_message:
            user_message = default_user_message
        else:
            user_message = "Please proceed."

    messages.append({"role": "user", "content": user_message})

    # Truncate history to fit context window
    messages = _truncate_history(messages)

    logger.info("Claude request: model=%s, messages=%d, max_tokens=%d", MODEL, len(messages), max_tokens)

    # Use prompt caching for system prompts (Anthropic caches identical system prompts)
    response = await get_client().messages.create(
        model=MODEL,
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response.content[0].text

    cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    cache_create = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
    logger.info(
        "Claude response: input=%s, output=%s tokens (cache_read=%s, cache_create=%s)",
        response.usage.input_tokens, response.usage.output_tokens,
        cache_read, cache_create,
    )
    return content
