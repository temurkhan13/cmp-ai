"""CMP AI Service — FastAPI application with AI + RAG endpoints."""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services import text_service, chat_service, assessment_service, sitemap_service, pdf_service, embedding_service

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set — AI calls will fail")
    else:
        logger.info("Anthropic API key configured (Claude Sonnet)")
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not set — embeddings will fail")
    else:
        logger.info("Google API key configured (Gemini Embeddings)")
    if not os.getenv("SUPABASE_URL"):
        logger.warning("SUPABASE_URL not set — RAG disabled")
    else:
        logger.info("Supabase configured for RAG/pgvector")
    logger.info("CMP AI Service starting up")
    yield
    logger.info("CMP AI Service shutting down")


app = FastAPI(title="CMP AI Service", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str = ""
    chat_id: str = ""
    message: str = ""
    history: list[str] = Field(default_factory=list)

class TextRequest(BaseModel):
    text: str = ""
    tone: str = "Professional"
    language: str = "English"

class InspireRequest(BaseModel):
    message: str = ""
    history: list[str] = Field(default_factory=list)
    general_info: str = ""
    bussiness_info: str = ""
    user_id: str = ""

class AssessmentRequest(BaseModel):
    userId: str = ""
    user_id: str = ""
    chat_id: str = ""
    message: str = ""
    history: list[str] = Field(default_factory=list)
    general_info: str = ""
    business_info: str = ""
    bussiness_info: str = ""
    assessment_name: str = ""

class SurveyRequest(BaseModel):
    user_id: str = ""
    chat_id: str = ""
    message: str = ""
    history: list[str] = Field(default_factory=list)
    general_info: str = ""
    survey_type: str = ""

class CheckRequest(BaseModel):
    user_id: str = ""
    chat_id: str = ""
    message: str = ""
    history: list[str] = Field(default_factory=list)
    general_info: str = ""
    check_type: str = ""
    bussiness_info: str = ""

class SitemapRequest(BaseModel):
    user_id: str = ""
    chat_id: str = ""
    message: str = ""
    sitemap_name: str = ""

class WireframeRequest(BaseModel):
    user_id: str = ""
    chat_id: str = ""
    message: str = ""
    wireframe_name: str = ""
    playbook: str = ""

class PdfRequest(BaseModel):
    pdf_file: str = ""
    user_id: str = ""
    chat_id: str = ""

class IngestRequest(BaseModel):
    user_id: str
    workspace_id: str = ""
    folder_id: str = ""
    filename: str
    content: str

class SearchRequest(BaseModel):
    user_id: str
    query: str
    limit: int = 5
    workspace_id: str | None = None

class MessageResponse(BaseModel):
    message: str

class AssessmentResponse(BaseModel):
    message: str
    title: str | None = None


# ── Health ───────────────────────────────────────────────────────────

@app.get("/health")
@app.post("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0", "llm": "claude-sonnet", "embeddings": "gemini"}


# ── RAG: Ingest & Search ────────────────────────────────────────────

@app.post("/ingest")
async def ingest(req: IngestRequest):
    try:
        result = await embedding_service.ingest_document(
            user_id=req.user_id,
            workspace_id=req.workspace_id,
            folder_id=req.folder_id,
            filename=req.filename,
            content=req.content,
        )
        return result
    except Exception as e:
        logger.error("Ingest error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search(req: SearchRequest):
    try:
        results = await embedding_service.search_similar(
            user_id=req.user_id,
            query=req.query,
            limit=req.limit,
            workspace_id=req.workspace_id,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error("Search error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Chat ─────────────────────────────────────────────────────────────

@app.post("/chat", response_model=MessageResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        result = await chat_service.chat(req.message, history=req.history, user_id=req.user_id)
        return {"message": result}
    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-files", response_model=MessageResponse)
async def upload_files(req: PdfRequest):
    try:
        result = await pdf_service.analyze_pdf(req.pdf_file)
        return {"message": result}
    except Exception as e:
        logger.error("PDF analysis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Text Transformations ─────────────────────────────────────────────

@app.post("/change-tone", response_model=MessageResponse)
async def change_tone(req: TextRequest):
    try:
        result = await text_service.change_tone(req.text, req.tone)
        return {"message": result}
    except Exception as e:
        logger.error("Change tone error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/translate", response_model=MessageResponse)
async def translate(req: TextRequest):
    try:
        result = await text_service.translate(req.text, req.language)
        return {"message": result}
    except Exception as e:
        logger.error("Translate error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/improve-writing", response_model=MessageResponse)
async def improve_writing(req: TextRequest):
    try:
        result = await text_service.improve_writing(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Improve writing error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fix-grammar", response_model=MessageResponse)
async def fix_grammar(req: TextRequest):
    try:
        result = await text_service.fix_grammar(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Fix grammar error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/make-shorter", response_model=MessageResponse)
async def make_shorter(req: TextRequest):
    try:
        result = await text_service.make_shorter(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Make shorter error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/make-longer", response_model=MessageResponse)
async def make_longer(req: TextRequest):
    try:
        result = await text_service.make_longer(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Make longer error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simplify-language", response_model=MessageResponse)
async def simplify_language(req: TextRequest):
    try:
        result = await text_service.simplify_language(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Simplify error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/summarize", response_model=MessageResponse)
async def summarize(req: TextRequest):
    try:
        result = await text_service.summarize(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Summarize error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/explain-this", response_model=MessageResponse)
async def explain_this(req: TextRequest):
    try:
        result = await text_service.explain_this(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Explain error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comprehensive-text", response_model=MessageResponse)
async def comprehensive_text(req: TextRequest):
    try:
        result = await text_service.comprehensive_text(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Comprehensive error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auto-text", response_model=MessageResponse)
async def auto_text(req: TextRequest):
    try:
        result = await text_service.auto_text(req.text)
        return {"message": result}
    except Exception as e:
        logger.error("Auto text error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Inspire ──────────────────────────────────────────────────────────

@app.post("/inspire", response_model=MessageResponse)
async def inspire(req: InspireRequest):
    try:
        result = await chat_service.inspire(
            req.message,
            history=req.history,
            general_info=req.general_info,
            bussiness_info=req.bussiness_info,
            user_id=req.user_id,
        )
        return {"message": result}
    except Exception as e:
        logger.error("Inspire error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Assessments ──────────────────────────────────────────────────────

@app.post("/assesment-chat", response_model=AssessmentResponse)
async def assessment_chat(req: AssessmentRequest):
    try:
        biz_info = req.business_info or req.bussiness_info
        uid = req.userId or req.user_id
        result = await assessment_service.assessment_chat(
            message=req.message,
            history=req.history,
            general_info=req.general_info,
            business_info=biz_info,
            assessment_name=req.assessment_name,
            user_id=uid,
        )
        return result
    except Exception as e:
        logger.error("Assessment chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/survey-chat", response_model=MessageResponse)
async def survey_chat(req: SurveyRequest):
    try:
        result = await assessment_service.survey_chat(
            message=req.message,
            history=req.history,
            general_info=req.general_info,
            survey_type=req.survey_type,
            user_id=req.user_id,
        )
        return {"message": result}
    except Exception as e:
        logger.error("Survey chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/check-chat", response_model=MessageResponse)
async def check_chat(req: CheckRequest):
    try:
        result = await assessment_service.check_chat(
            message=req.message,
            history=req.history,
            general_info=req.general_info,
            check_type=req.check_type,
            bussiness_info=req.bussiness_info,
            user_id=req.user_id,
        )
        return {"message": result}
    except Exception as e:
        logger.error("Check chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Sitemap & Wireframe ──────────────────────────────────────────────

@app.post("/sitemap")
async def sitemap(req: SitemapRequest):
    try:
        result = await sitemap_service.generate_sitemap(req.message, req.sitemap_name)
        return result
    except Exception as e:
        logger.error("Sitemap error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/wireframe")
async def wireframe(req: WireframeRequest):
    try:
        result = await sitemap_service.generate_wireframe(
            req.message, req.wireframe_name, req.playbook
        )
        return result
    except Exception as e:
        logger.error("Wireframe error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
