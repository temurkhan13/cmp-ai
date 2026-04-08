"""Gemini Embeddings + Supabase pgvector for RAG."""

import os
import logging
import google.generativeai as genai
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase: Client | None = None
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


def _configure_gemini():
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))


def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text using Gemini."""
    _configure_gemini()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
    return result["embedding"]


def embed_query(text: str) -> list[float]:
    """Generate embedding for a search query using Gemini."""
    _configure_gemini()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query",
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
    return result["embedding"]


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
        embedding = embed_text(chunk)
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
    query_embedding = embed_query(query)

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
