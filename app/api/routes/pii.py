import logging
import time
from datetime import datetime

from fastapi import APIRouter, status

from app.core.registry import get_pii_detection_service
from app.schemas.pii import PIIDetectRequest, PIIDetectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pii", tags=["pii"])


@router.post("/detect", response_model=PIIDetectResponse, status_code=status.HTTP_200_OK)
def detect_pii(payload: PIIDetectRequest) -> PIIDetectResponse:
    start_dt = datetime.now()
    t0 = time.perf_counter()
    logger.info("[pii] start=%s", start_dt.strftime("%H:%M:%S"))

    service = get_pii_detection_service()
    entities = service.detect(payload.text)

    logger.info(
        "[pii] finish=%s elapsed=%.2fs",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
    )
    return PIIDetectResponse(entities=entities)
