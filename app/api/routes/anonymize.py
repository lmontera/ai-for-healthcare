import base64
import binascii
import logging
import time

from fastapi import APIRouter, HTTPException, status

from app.core.registry import get_anonymization_service
from app.graphs.anonymize_graph import get_anonymize_graph
from app.schemas.anonymize import (
    AnonymizeRequest,
    AnonymizeResponse,
    AnonymizeTextRequest,
    AnonymizeTextResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anonymize", tags=["anonymize"])


@router.post("", response_model=AnonymizeResponse, status_code=status.HTTP_200_OK)
def anonymize_document(payload: AnonymizeRequest) -> AnonymizeResponse:
    logger.info("[anonymize] document request received: b64_len=%d", len(payload.image_base64))
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    logger.info("[anonymize] image decoded: bytes=%d", len(image_bytes))
    t0 = time.perf_counter()
    graph = get_anonymize_graph()
    result = graph.invoke({"image_bytes": image_bytes})
    logger.info(
        "[anonymize] document done: ocr_chars=%d anon_chars=%d elapsed=%.2fs",
        len(result["ocr_text"]),
        len(result["anonymized_text"]),
        time.perf_counter() - t0,
    )

    return AnonymizeResponse(
        ocr_text=result["ocr_text"],
        anonymized_text=result["anonymized_text"],
    )


@router.post("/text", response_model=AnonymizeTextResponse, status_code=status.HTTP_200_OK)
def anonymize_text(payload: AnonymizeTextRequest) -> AnonymizeTextResponse:
    logger.info("[anonymize:text] request received: chars=%d", len(payload.text))
    t0 = time.perf_counter()
    anonymizer = get_anonymization_service()
    anonymized = anonymizer.anonymize(payload.text)
    logger.info(
        "[anonymize:text] done: in=%d out=%d elapsed=%.2fs",
        len(payload.text),
        len(anonymized),
        time.perf_counter() - t0,
    )
    return AnonymizeTextResponse(anonymized_text=anonymized)
