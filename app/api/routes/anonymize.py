import base64
import binascii
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.core.registry import (
    get_anonymization_service,
    get_ocr_service,
    get_pii_detection_service,
)
from app.graphs.anonymize_graph import get_anonymize_graph
from app.schemas.anonymize import (
    AnonymizeMaskedResponse,
    AnonymizeRequest,
    AnonymizeResponse,
    AnonymizeTextRequest,
    AnonymizeTextResponse,
)
from app.services.anonymization.image_masker import mask_image_with_entities

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


@router.post(
    "/masked",
    response_model=AnonymizeMaskedResponse,
    status_code=status.HTTP_200_OK,
)
def anonymize_document_masked(payload: AnonymizeRequest) -> AnonymizeMaskedResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    start_dt = datetime.now()
    t0 = time.perf_counter()
    logger.info("[anonymize:masked] start=%s bytes=%d", start_dt.strftime("%H:%M:%S"), len(image_bytes))

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

    anonymizer = get_anonymization_service()
    anonymized_text = anonymizer.anonymize(text)

    masked_png = mask_image_with_entities(image_bytes, words, entities)

    logger.info(
        "[anonymize:masked] finish=%s elapsed=%.2fs entities=%d",
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
