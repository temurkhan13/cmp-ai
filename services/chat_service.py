"""General chat and inspire services."""

from prompts.system_prompts import CHAT_SYSTEM_PROMPT, INSPIRE_PROMPT
from .openai_service import chat_completion


async def chat(message: str, history: list[str] | None = None) -> str:
    return await chat_completion(CHAT_SYSTEM_PROMPT, message, history=history)


async def inspire(
    message: str,
    history: list[str] | None = None,
    general_info: str = "",
    bussiness_info: str = "",
) -> str:
    context_parts = []
    if general_info:
        context_parts.append(f"General context: {general_info}")
    if bussiness_info:
        context_parts.append(f"Business context: {bussiness_info}")

    user_msg = message
    if context_parts:
        user_msg = "\n".join(context_parts) + f"\n\nUser request: {message}"

    return await chat_completion(INSPIRE_PROMPT, user_msg, history=history)
