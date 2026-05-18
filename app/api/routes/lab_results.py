import base64
import binascii
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.graphs.lab_graph import get_lab_graph
from app.schemas.lab import LabResult, LabResultsRequest, LabResultsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lab-results", tags=["lab-results"])


@router.post("", response_model=LabResultsResponse, status_code=status.HTTP_200_OK)
def extract_lab_results(payload: LabResultsRequest) -> LabResultsResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    t0 = time.perf_counter()
    logger.info(
        "[lab-results] start=%s bytes=%d",
        datetime.now().strftime("%H:%M:%S"),
        len(image_bytes),
    )

    graph = get_lab_graph()
    state = graph.invoke(
        {"image_bytes": image_bytes, "max_new_tokens": payload.max_new_tokens}
    )

    logger.info(
        "[lab-results] finish=%s elapsed=%.2fs results=%d",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
        len(state.get("results", []) or []),
    )

    return LabResultsResponse(
        ocr_text=state.get("ocr_text", ""),
        results=[LabResult(**r) for r in state.get("results", []) or []],
        raw=state.get("raw", ""),
    )
