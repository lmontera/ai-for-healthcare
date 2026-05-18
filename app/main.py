import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    anonymize,
    anonymize_llm,
    document_classify,
    fhir,
    image_classification,
    lab_results,
    pii,
    transcribe,
    transcription_extract,
    transcription_refine,
)
from app.whisperlive_server import start_whisperlive_background

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

for noisy in ("httpx", "httpcore", "faster_whisper", "transformers", "urllib3", "uvicorn.access"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_whisperlive_background(
        host=os.getenv("WHISPERLIVE_HOST", "0.0.0.0"),
        port=int(os.getenv("WHISPERLIVE_PORT", "9090")),
    )
    yield


app = FastAPI(title="AI for Healthcare", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(anonymize.router)
app.include_router(anonymize_llm.router)
app.include_router(pii.router)
app.include_router(transcribe.router)
app.include_router(fhir.router)
app.include_router(image_classification.router)
app.include_router(transcription_refine.router)
app.include_router(transcription_extract.router)
app.include_router(lab_results.router)
app.include_router(document_classify.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
