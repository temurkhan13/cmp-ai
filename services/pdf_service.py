"""PDF text extraction and analysis service."""

import logging
from PyPDF2 import PdfReader
from prompts.system_prompts import PDF_ANALYSIS_PROMPT
from .openai_service import chat_completion

logger = logging.getLogger(__name__)

MAX_PDF_CHARS = 50_000


async def analyze_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file and analyze it with GPT."""
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

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
