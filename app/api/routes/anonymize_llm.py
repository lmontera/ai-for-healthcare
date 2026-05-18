import base64
import binascii
import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.registry import get_llm_service, get_ocr_service
from app.graphs.anonymize_llm_graph import get_anonymize_llm_graph
from app.schemas.anonymize import AnonymizeRequest, AnonymizeResponse
from app.services.anonymization.llm_anonymizer import _SYSTEM_PROMPT as _ANONYMIZE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anonymize-llm", tags=["anonymize-llm"])


@router.post("", response_model=AnonymizeResponse, status_code=status.HTTP_200_OK)
def anonymize_document_llm(payload: AnonymizeRequest) -> AnonymizeResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    start_dt = datetime.now()
    t0 = time.perf_counter()
    logger.info("[anonymize-llm] start=%s bytes=%d", start_dt.strftime("%H:%M:%S"), len(image_bytes))

    graph = get_anonymize_llm_graph()
    result = graph.invoke({"image_bytes": image_bytes})

    logger.info(
        "[anonymize-llm] finish=%s elapsed=%.2fs",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
    )

    return AnonymizeResponse(
        ocr_text=result.get("ocr_text", ""),
        anonymized_text=result.get("anonymized_text", ""),
    )


@router.post("/stream")
def anonymize_document_llm_stream(payload: AnonymizeRequest) -> StreamingResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    logger.info("[anonymize-llm:stream] request received: bytes=%d", len(image_bytes))

    def emit(event: dict) -> str:
        return json.dumps(event, ensure_ascii=False) + "\n"

    def event_iter():
        try:
            ocr_text = get_ocr_service().extract_text(image_bytes)
            yield emit({"event": "ocr", "text": ocr_text})

            messages = [
                {"role": "system", "content": _ANONYMIZE_SYSTEM_PROMPT},
                {"role": "user", "content": ocr_text},
            ]
            llm = get_llm_service()
            full_parts: list[str] = []
            if hasattr(llm, "chat_stream"):
                for delta in llm.chat_stream(messages, max_new_tokens=4096, json_mode=False):
                    full_parts.append(delta)
                    yield emit({"event": "anonymize_delta", "delta": delta})
            else:
                txt = llm.chat(messages, max_new_tokens=4096)
                full_parts.append(txt)
                yield emit({"event": "anonymize_delta", "delta": txt})

            yield emit({"event": "anonymize_done", "anonymized_text": "".join(full_parts).strip()})
        except Exception as exc:
            logger.exception("[anonymize-llm:stream] error")
            yield emit({"event": "error", "detail": str(exc)})

    return StreamingResponse(event_iter(), media_type="application/x-ndjson")
