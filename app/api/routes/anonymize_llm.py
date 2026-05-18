import base64
import binascii
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.graphs.anonymize_llm_graph import get_anonymize_llm_graph
from app.schemas.anonymize import AnonymizeRequest, AnonymizeResponse

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
