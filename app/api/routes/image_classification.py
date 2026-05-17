import base64
import binascii
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.core.registry import get_image_classification_service
from app.schemas.image_classification import (
    DEFAULT_LABELS,
    ImageClassifyRequest,
    ImageClassifyResponse,
    ImageClassifyScore,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image", tags=["image"])


@router.post("/classify", response_model=ImageClassifyResponse, status_code=status.HTTP_200_OK)
def classify_image(payload: ImageClassifyRequest) -> ImageClassifyResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    labels = payload.candidate_labels or DEFAULT_LABELS
    if not labels:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="candidate_labels must contain at least one label",
        )

    t0 = time.perf_counter()
    logger.info("[image-clf] start=%s labels=%s", datetime.now().strftime("%H:%M:%S"), labels)

    service = get_image_classification_service()
    scores = service.classify(image_bytes, labels)

    logger.info(
        "[image-clf] finish=%s elapsed=%.2fs",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
    )

    scores_sorted = sorted(scores, key=lambda s: s["score"], reverse=True)
    top_label = scores_sorted[0]["label"]
    is_medical = "medical" in top_label.lower() and "non" not in top_label.lower()

    return ImageClassifyResponse(
        top_label=top_label,
        is_medical=is_medical,
        scores=[ImageClassifyScore(**s) for s in scores_sorted],
    )
