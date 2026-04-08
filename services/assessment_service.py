"""Assessment Q&A, survey, and check-chat services."""

from prompts.system_prompts import SURVEY_CHAT_PROMPT, CHECK_CHAT_PROMPT
from prompts.assessment_prompts import get_assessment_prompt
from .openai_service import chat_completion


async def assessment_chat(
    message: str,
    history: list[str] | None = None,
    general_info: str = "",
    business_info: str = "",
    assessment_name: str = "",
) -> dict:
    system_prompt = get_assessment_prompt(assessment_name)

    context_parts = []
    if general_info:
        context_parts.append(f"Organization info: {general_info}")
    if business_info:
        context_parts.append(f"Business info: {business_info}")

    user_msg = message
    if context_parts:
        user_msg = "\n".join(context_parts) + f"\n\nUser response: {message}"

    result = await chat_completion(system_prompt, user_msg, history=history)

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
) -> str:
    prompt = SURVEY_CHAT_PROMPT.replace("{{survey_type}}", survey_type)

    user_msg = message
    if general_info:
        user_msg = f"Context: {general_info}\n\nUser message: {message}"

    return await chat_completion(prompt, user_msg, history=history)


async def check_chat(
    message: str,
    history: list[str] | None = None,
    general_info: str = "",
    check_type: str = "",
    bussiness_info: str = "",
) -> str:
    prompt = CHECK_CHAT_PROMPT.replace("{{check_type}}", check_type)

    context_parts = []
    if general_info:
        context_parts.append(f"Context: {general_info}")
    if bussiness_info:
        context_parts.append(f"Business info: {bussiness_info}")

    user_msg = message
    if context_parts:
        user_msg = "\n".join(context_parts) + f"\n\nUser message: {message}"

    return await chat_completion(prompt, user_msg, history=history)
