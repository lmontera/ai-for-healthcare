import base64
import binascii
import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.registry import (
    get_llm_service,
    get_ocr_service,
    get_pii_detection_service,
)
from app.graphs.anonymize_llm_graph import get_anonymize_llm_graph
from app.schemas.anonymize import (
    AnonymizeMaskedResponse,
    AnonymizeRequest,
    AnonymizeResponse,
)
from app.services.anonymization.image_masker import mask_image_with_entities
from app.services.anonymization.llm_anonymizer import LLMAnonymizationService
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


@router.post(
    "/masked",
    response_model=AnonymizeMaskedResponse,
    status_code=status.HTTP_200_OK,
)
def anonymize_document_llm_masked(payload: AnonymizeRequest) -> AnonymizeMaskedResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    start_dt = datetime.now()
    t0 = time.perf_counter()
    logger.info("[anonymize-llm:masked] start=%s bytes=%d", start_dt.strftime("%H:%M:%S"), len(image_bytes))

    ocr = get_ocr_service()
    if not hasattr(ocr, "extract_text_and_words"):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OCR service does not expose word-level bounding boxes",
        )
    ocr_result = ocr.extract_text_and_words(image_bytes)
    text = ocr_result["text"]
    words = ocr_result["words"]

    pii = get_pii_detection_service()
    entities = pii.detect(text)

    anonymizer = LLMAnonymizationService(get_llm_service())
    anonymized_text = anonymizer.anonymize(text)

    masked_png = mask_image_with_entities(image_bytes, words, entities)

    logger.info(
        "[anonymize-llm:masked] finish=%s elapsed=%.2fs entities=%d",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
        len(entities),
    )

    return AnonymizeMaskedResponse(
        ocr_text=text,
        anonymized_text=anonymized_text,
        masked_image_base64=base64.b64encode(masked_png).decode("ascii"),
        entities_count=len(entities),
    )
