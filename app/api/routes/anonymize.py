import base64
import binascii
import logging
import time
from datetime import datetime

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
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    start_dt = datetime.now()
    t0 = time.perf_counter()
    logger.info("[anonymize] start=%s", start_dt.strftime("%H:%M:%S"))

    graph = get_anonymize_graph()
    result = graph.invoke({"image_bytes": image_bytes})

    logger.info(
        "[anonymize] finish=%s elapsed=%.2fs",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
    )

    return AnonymizeResponse(
        ocr_text=result["ocr_text"],
        anonymized_text=result["anonymized_text"],
    )


@router.post("/text", response_model=AnonymizeTextResponse, status_code=status.HTTP_200_OK)
def anonymize_text(payload: AnonymizeTextRequest) -> AnonymizeTextResponse:
    start_dt = datetime.now()
    t0 = time.perf_counter()
    logger.info("[anonymize:text] start=%s", start_dt.strftime("%H:%M:%S"))

    anonymizer = get_anonymization_service()
    anonymized = anonymizer.anonymize(payload.text)

    logger.info(
        "[anonymize:text] finish=%s elapsed=%.2fs",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
    )
    return AnonymizeTextResponse(anonymized_text=anonymized)
