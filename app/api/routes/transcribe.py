import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse

from app.core.registry import get_transcription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcribe"])


@router.post("")
async def transcribe(audio: UploadFile = File(...)) -> StreamingResponse:
    audio_bytes = await audio.read()
    service = get_transcription_service()

    def stream():
        start_dt = datetime.now()
        t0 = time.perf_counter()
        logger.info("[transcribe] start=%s", start_dt.strftime("%H:%M:%S"))

        for segment in service.transcribe(audio_bytes):
            yield json.dumps(segment.model_dump()) + "\n"

        logger.info(
            "[transcribe] finish=%s elapsed=%.2fs",
            datetime.now().strftime("%H:%M:%S"),
            time.perf_counter() - t0,
        )

    return StreamingResponse(stream(), media_type="application/x-ndjson")
