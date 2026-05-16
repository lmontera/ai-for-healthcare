from fastapi import APIRouter, status

from app.core.registry import get_pii_detection_service
from app.schemas.pii import PIIDetectRequest, PIIDetectResponse

router = APIRouter(prefix="/pii", tags=["pii"])


@router.post("/detect", response_model=PIIDetectResponse, status_code=status.HTTP_200_OK)
def detect_pii(payload: PIIDetectRequest) -> PIIDetectResponse:
    service = get_pii_detection_service()
    entities = service.detect(payload.text)
    return PIIDetectResponse(entities=entities)
