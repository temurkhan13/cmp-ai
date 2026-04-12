"""PDF text extraction and analysis service — supports file path and base64."""

import io
import base64
import logging
from PyPDF2 import PdfReader
from prompts.system_prompts import PDF_ANALYSIS_PROMPT
from .openai_service import chat_completion

logger = logging.getLogger(__name__)

MAX_PDF_CHARS = 50_000


def _extract_text_from_reader(reader: PdfReader) -> str:
    """Extract text from all pages of a PdfReader."""
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n\n".join(text_parts)


async def analyze_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file path and analyze it with Claude."""
    try:
        reader = PdfReader(pdf_path)
        full_text = _extract_text_from_reader(reader)

        if not full_text.strip():
            return "The PDF appears to be empty or contains only images/scanned content that cannot be extracted as text."

        if len(full_text) > MAX_PDF_CHARS:
            full_text = full_text[:MAX_PDF_CHARS] + "\n\n[... document truncated ...]"
            logger.info("PDF text truncated to %d characters", MAX_PDF_CHARS)

        user_msg = f"Please analyze the following document:\n\n{full_text}"
        return await chat_completion(PDF_ANALYSIS_PROMPT, user_msg)

    except FileNotFoundError:
        logger.error("PDF file not found: %s", pdf_path)
        return "Error: PDF file not found."
    except Exception as e:
        logger.error("Error analyzing PDF: %s", e)
        return f"Error analyzing PDF: {str(e)}"


async def analyze_pdf_base64(pdf_base64: str) -> str:
    """Extract text from a base64-encoded PDF and analyze it with Claude."""
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = _extract_text_from_reader(reader)

        if not full_text.strip():
            return "The PDF appears to be empty or contains only images/scanned content that cannot be extracted as text."

        if len(full_text) > MAX_PDF_CHARS:
            full_text = full_text[:MAX_PDF_CHARS] + "\n\n[... document truncated ...]"
            logger.info("PDF text truncated to %d characters", MAX_PDF_CHARS)

        user_msg = f"Please analyze the following document:\n\n{full_text}"
        return await chat_completion(PDF_ANALYSIS_PROMPT, user_msg)

    except Exception as e:
        logger.error("Error analyzing base64 PDF: %s", e)
        return f"Error analyzing PDF: {str(e)}"
