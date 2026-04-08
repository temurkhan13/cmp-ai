"""Text transformation services — tone, grammar, summarize, etc."""

from prompts.system_prompts import (
    CHANGE_TONE_PROMPT, TRANSLATE_PROMPT, IMPROVE_WRITING_PROMPT,
    FIX_GRAMMAR_PROMPT, MAKE_SHORTER_PROMPT, MAKE_LONGER_PROMPT,
    SIMPLIFY_LANGUAGE_PROMPT, SUMMARIZE_PROMPT, EXPLAIN_THIS_PROMPT,
    COMPREHENSIVE_TEXT_PROMPT, AUTO_TEXT_PROMPT,
)
from .openai_service import chat_completion


async def change_tone(text: str, tone: str = "Professional") -> str:
    prompt = f"{CHANGE_TONE_PROMPT}\n\nRequested tone: {tone}"
    return await chat_completion(prompt, text, temperature=0.6)


async def translate(text: str, language: str = "English") -> str:
    prompt = f"{TRANSLATE_PROMPT}\n\nTarget language: {language}"
    return await chat_completion(prompt, text, temperature=0.3)


async def improve_writing(text: str) -> str:
    return await chat_completion(IMPROVE_WRITING_PROMPT, text, temperature=0.6)


async def fix_grammar(text: str) -> str:
    return await chat_completion(FIX_GRAMMAR_PROMPT, text, temperature=0.2)


async def make_shorter(text: str) -> str:
    return await chat_completion(MAKE_SHORTER_PROMPT, text, temperature=0.5)


async def make_longer(text: str) -> str:
    return await chat_completion(MAKE_LONGER_PROMPT, text, temperature=0.7)


async def simplify_language(text: str) -> str:
    return await chat_completion(SIMPLIFY_LANGUAGE_PROMPT, text, temperature=0.5)


async def summarize(text: str) -> str:
    return await chat_completion(SUMMARIZE_PROMPT, text, temperature=0.4)


async def explain_this(text: str) -> str:
    return await chat_completion(EXPLAIN_THIS_PROMPT, text, temperature=0.6)


async def comprehensive_text(text: str) -> str:
    return await chat_completion(COMPREHENSIVE_TEXT_PROMPT, text, temperature=0.7)


async def auto_text(text: str) -> str:
    return await chat_completion(AUTO_TEXT_PROMPT, text, temperature=0.8)
