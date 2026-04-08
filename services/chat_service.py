"""General chat and inspire services — now with RAG context."""

from prompts.system_prompts import CHAT_SYSTEM_PROMPT, INSPIRE_PROMPT
from .openai_service import chat_completion
from . import embedding_service


async def chat(
    message: str,
    history: list[str] | None = None,
    user_id: str = "",
) -> str:
    # RAG: retrieve relevant context from user's documents
    rag_context = ""
    if user_id:
        try:
            chunks = await embedding_service.search_similar(user_id, message, limit=5)
            rag_context = embedding_service.build_rag_context(chunks)
        except Exception:
            pass  # RAG is best-effort — don't break chat if it fails

    prompt = CHAT_SYSTEM_PROMPT
    if rag_context:
        prompt += f"\n\n{rag_context}\n\nUse the above context to inform your responses when relevant."

    return await chat_completion(prompt, message, history=history)


async def inspire(
    message: str,
    history: list[str] | None = None,
    general_info: str = "",
    bussiness_info: str = "",
    user_id: str = "",
) -> str:
    # RAG context
    rag_context = ""
    if user_id:
        try:
            chunks = await embedding_service.search_similar(user_id, message, limit=3)
            rag_context = embedding_service.build_rag_context(chunks)
        except Exception:
            pass

    context_parts = []
    if general_info:
        context_parts.append(f"General context: {general_info}")
    if bussiness_info:
        context_parts.append(f"Business context: {bussiness_info}")

    user_msg = message
    if context_parts:
        user_msg = "\n".join(context_parts) + f"\n\nUser request: {message}"

    prompt = INSPIRE_PROMPT
    if rag_context:
        prompt += f"\n\n{rag_context}\n\nUse this organizational context to make your suggestions specific and relevant."

    return await chat_completion(prompt, user_msg, history=history)
