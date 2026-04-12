"""Sitemap and wireframe generation services."""

import json
import re
import logging
from prompts.system_prompts import SITEMAP_PROMPT, WIREFRAME_PROMPT, PLAYBOOK_INSPIRE_PROMPT
from .openai_service import chat_completion

logger = logging.getLogger(__name__)

# Basic HTML tags allowed in playbook content
_ALLOWED_TAGS = {"p", "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
                 "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em", "br", "a", "span", "div"}


def _extract_json(text: str) -> dict:
    """Robustly extract JSON from LLM response.
    Tries multiple strategies: direct parse, code fence strip, brace matching.
    """
    text = text.strip()

    # Strategy 1: Direct parse (works if LLM returned clean JSON)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Find JSON object boundaries with proper string handling
    start = cleaned.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", cleaned, 0)

    # Use a state machine that respects string literals
    depth = 0
    in_string = False
    escape = False
    end = start

    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    extracted = cleaned[start:end]
    return json.loads(extracted)


def _sanitize_html(html: str) -> str:
    """Basic HTML sanitization — strip tags not in the allowed set."""
    def replace_tag(match):
        tag_name = match.group(1).lower().strip().split()[0]  # Get tag name without attrs
        if tag_name.lstrip("/") in _ALLOWED_TAGS:
            return match.group(0)
        return ""  # Strip disallowed tags

    return re.sub(r"<(/?\w[^>]*)>", replace_tag, html)


async def generate_sitemap(message: str, sitemap_name: str) -> dict:
    user_msg = f"Generate a detailed playbook stage for: {sitemap_name}"
    if message:
        user_msg += f"\n\nAdditional context: {message}"

    result = await chat_completion(SITEMAP_PROMPT, user_msg, temperature=0.7, max_tokens=2048)

    try:
        parsed = _extract_json(result)
        return {"message": json.dumps(parsed)}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Sitemap response was not valid JSON (%s), wrapping as string", e)
        return {"message": result}


async def playbook_inspire(heading: str, playbook_name: str = "") -> dict:
    user_msg = f"Generate content for the playbook section: {heading}"
    if playbook_name:
        user_msg += f"\n\nThis is part of the playbook: {playbook_name}"

    result = await chat_completion(PLAYBOOK_INSPIRE_PROMPT, user_msg, temperature=0.7, max_tokens=1024)

    # Sanitize HTML output before returning to frontend
    sanitized = _sanitize_html(result)
    return {"content": sanitized, "message": sanitized}


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
        parsed = _extract_json(result)
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Wireframe response was not valid JSON (%s), returning as-is", e)
        return {"message": result}
