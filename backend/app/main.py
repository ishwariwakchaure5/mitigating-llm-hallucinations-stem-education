import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("STEM Hallucination Mitigation API starting up...")
    os.makedirs(settings.upload_dir, exist_ok=True)
    await create_tables()
    logger.info("Database tables created/verified")

    from app.tasks.dispatch import requeue_pending_documents

    asyncio.create_task(requeue_pending_documents())

    yield
    logger.info("STEM Hallucination Mitigation API shutting down...")


app = FastAPI(
    title="STEM Hallucination Mitigation API",
    description="Evidence-based verification system for mitigating LLM hallucinations in STEM education",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.2:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


from app.routers import auth, knowledge_base, documents, verify  # noqa: E402

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(knowledge_base.router, prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(verify.router, prefix="/api/v1/verify", tags=["verify"])
