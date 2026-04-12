"""Gemini Embeddings + Supabase pgvector for RAG."""

import os
import logging
from google import genai
from google.genai.types import EmbedContentConfig
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase: Client | None = None
_genai_client: genai.Client | None = None
EMBEDDING_MODEL = "models/gemini-embedding-2-preview"
EMBEDDING_DIMENSIONS = 1536
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
    return _supabase


def _get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
    return _genai_client


import asyncio
import functools

def _embed_text_sync(text: str) -> list[float]:
    """Generate embedding for a single text using Gemini (sync)."""
    client = _get_genai_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )
    return result.embeddings[0].values


def _embed_query_sync(text: str) -> list[float]:
    """Generate embedding for a search query using Gemini (sync)."""
    client = _get_genai_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )
    return result.embeddings[0].values


async def embed_text(text: str) -> list[float]:
    """Async wrapper — runs sync Gemini call in thread pool to avoid blocking event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(_embed_text_sync, text))


async def embed_query(text: str) -> list[float]:
    """Async wrapper — runs sync Gemini call in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(_embed_query_sync, text))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


async def ingest_document(
    user_id: str,
    workspace_id: str,
    folder_id: str,
    filename: str,
    content: str,
) -> dict:
    """Chunk text, embed each chunk, store in Supabase pgvector."""
    sb = get_supabase()

    # Create document record
    doc_result = sb.table("documents").insert({
        "user_id": user_id,
        "workspace_id": workspace_id,
        "folder_id": folder_id,
        "filename": filename,
        "file_type": filename.rsplit(".", 1)[-1] if "." in filename else "txt",
        "content_preview": content[:500],
    }).execute()

    document_id = doc_result.data[0]["id"]
    chunks = chunk_text(content)

    logger.info("Ingesting document %s: %d chunks", filename, len(chunks))

    for i, chunk in enumerate(chunks):
        embedding = await embed_text(chunk)
        sb.table("document_chunks").insert({
            "document_id": document_id,
            "user_id": user_id,
            "chunk_text": chunk,
            "chunk_index": i,
            "embedding": embedding,
        }).execute()

    logger.info("Document %s ingested: %d chunks embedded", filename, len(chunks))

    return {
        "document_id": document_id,
        "chunks_created": len(chunks),
        "filename": filename,
    }


async def search_similar(
    user_id: str,
    query: str,
    limit: int = 5,
    workspace_id: str | None = None,
) -> list[dict]:
    """Search for similar document chunks using vector similarity."""
    sb = get_supabase()
    query_embedding = await embed_query(query)

    # Call Supabase RPC function for vector similarity search
    result = sb.rpc("match_document_chunks", {
        "query_embedding": query_embedding,
        "match_count": limit,
        "filter_user_id": user_id,
        "filter_workspace_id": workspace_id,
    }).execute()

    return result.data if result.data else []


def build_rag_context(chunks: list[dict]) -> str:
    """Build context string from retrieved chunks for prompt injection."""
    if not chunks:
        return ""

    context_parts = ["--- RELEVANT ORGANIZATIONAL CONTEXT ---"]
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("filename", "document")
        text = chunk.get("chunk_text", "")
        context_parts.append(f"[Source {i}: {source}]\n{text}")
    context_parts.append("--- END CONTEXT ---")

    return "\n\n".join(context_parts)
