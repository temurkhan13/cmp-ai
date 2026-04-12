"""Assessment Q&A, survey, and check-chat services — with RAG context."""

from prompts.system_prompts import SURVEY_CHAT_PROMPT, CHECK_CHAT_PROMPT
from prompts.assessment_prompts import get_assessment_prompt
from .openai_service import chat_completion
from . import embedding_service


async def assessment_chat(
    message: str,
    history: list[str] | None = None,
    general_info: str = "",
    business_info: str = "",
    assessment_name: str = "",
    user_id: str = "",
) -> dict:
    system_prompt = get_assessment_prompt(assessment_name)

    # RAG: pull relevant org context
    rag_context = ""
    if user_id:
        try:
            search_query = f"{assessment_name} {message}"
            chunks = await embedding_service.search_similar(user_id, search_query, limit=5)
            rag_context = embedding_service.build_rag_context(chunks)
        except Exception:
            pass

    if rag_context:
        system_prompt += f"\n\n{rag_context}\n\nUse this organizational context to ask better questions and generate more relevant reports."

    context_parts = []
    if general_info:
        context_parts.append(f"Organization info: {general_info}")
    if business_info:
        context_parts.append(f"Business info: {business_info}")

    user_msg = message
    if context_parts:
        user_msg = "\n".join(context_parts) + f"\n\nUser response: {message}"

    result = await chat_completion(
        system_prompt,
        user_msg,
        history=history,
        max_tokens=8192,  # Assessment reports need more space
        default_user_message="Begin the assessment. Ask me the first question.",
    )

    response = {"message": result}
    if result.strip().startswith("## "):
        lines = result.strip().split("\n")
        title = lines[0].lstrip("# ").strip()
        response["title"] = title

    return response


async def survey_chat(
    message: str,
    history: list[str] | None = None,
    general_info: str = "",
    survey_type: str = "",
    user_id: str = "",
) -> str:
    if not survey_type or not survey_type.strip():
        survey_type = "General Change Management Survey"

    prompt = SURVEY_CHAT_PROMPT.replace("{{survey_type}}", survey_type)

    if user_id:
        try:
            chunks = await embedding_service.search_similar(user_id, message, limit=3)
            rag_context = embedding_service.build_rag_context(chunks)
            if rag_context:
                prompt += f"\n\n{rag_context}"
        except Exception:
            pass

    user_msg = message
    if general_info:
        user_msg = f"Context: {general_info}\n\nUser message: {message}"

    return await chat_completion(
        prompt,
        user_msg,
        history=history,
        default_user_message="Begin the survey. Ask me the first question.",
    )


async def check_chat(
    message: str,
    history: list[str] | None = None,
    general_info: str = "",
    check_type: str = "",
    bussiness_info: str = "",
    user_id: str = "",
) -> str:
    if not check_type or not check_type.strip():
        check_type = "General Change Health Check"

    prompt = CHECK_CHAT_PROMPT.replace("{{check_type}}", check_type)

    if user_id:
        try:
            chunks = await embedding_service.search_similar(user_id, message, limit=3)
            rag_context = embedding_service.build_rag_context(chunks)
            if rag_context:
                prompt += f"\n\n{rag_context}"
        except Exception:
            pass

    context_parts = []
    if general_info:
        context_parts.append(f"Context: {general_info}")
    if bussiness_info:
        context_parts.append(f"Business info: {bussiness_info}")

    user_msg = message
    if context_parts:
        user_msg = "\n".join(context_parts) + f"\n\nUser message: {message}"

    return await chat_completion(
        prompt,
        user_msg,
        history=history,
        default_user_message="Begin the check. Ask me the first question.",
    )
