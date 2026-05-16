import json
import logging

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse

from app.core.registry import get_transcription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcribe"])


@router.post("")
async def transcribe(audio: UploadFile = File(...)) -> StreamingResponse:
    logger.info(
        "[transcribe] request received: filename=%s content_type=%s",
        audio.filename,
        audio.content_type,
    )
    audio_bytes = await audio.read()
    logger.info("[transcribe] audio loaded: bytes=%d", len(audio_bytes))

    service = get_transcription_service()

    def stream():
        emitted = 0
        for segment in service.transcribe(audio_bytes):
            emitted += 1
            yield json.dumps(segment.model_dump()) + "\n"
        logger.info("[transcribe] stream closed: emitted=%d segments", emitted)

    return StreamingResponse(stream(), media_type="application/x-ndjson")
