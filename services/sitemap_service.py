"""Sitemap and wireframe generation services."""

import json
import re
import logging
from prompts.system_prompts import SITEMAP_PROMPT, WIREFRAME_PROMPT
from .openai_service import chat_completion

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Strip markdown code fences and extract JSON."""
    # Remove ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned.strip())
    return cleaned.strip()


async def generate_sitemap(message: str, sitemap_name: str) -> dict:
    user_msg = f"Generate a detailed playbook stage for: {sitemap_name}"
    if message:
        user_msg += f"\n\nAdditional context: {message}"

    result = await chat_completion(SITEMAP_PROMPT, user_msg, temperature=0.7)

    try:
        json_str = _extract_json(result)
        parsed = json.loads(json_str)
        return {"message": json.dumps(parsed)}
    except json.JSONDecodeError:
        logger.warning("Sitemap response was not valid JSON, wrapping as string")
        return {"message": result}


async def generate_wireframe(
    message: str,
    wireframe_name: str = "",
    playbook: str = "",
) -> dict:
    user_msg = f"Generate wireframe for: {wireframe_name}"
    if message:
        user_msg += f"\n\nDescription: {message}"
    if playbook:
        user_msg += f"\n\nPlaybook context: {playbook}"

    result = await chat_completion(WIREFRAME_PROMPT, user_msg, temperature=0.7)

    try:
        json_str = _extract_json(result)
        parsed = json.loads(json_str)
        return parsed
    except json.JSONDecodeError:
        logger.warning("Wireframe response was not valid JSON, returning as-is")
        return {"message": result}
