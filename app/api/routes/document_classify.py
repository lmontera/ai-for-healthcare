import base64
import binascii
import logging
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.graphs.classify_graph import get_classify_graph
from app.schemas.document_classification import (
    DocumentClassifyRequest,
    DocumentClassifyResponse,
)
from app.services.document_classification.categories import DEFAULT_CATEGORIES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document", tags=["document"])


@router.get("/categories")
def list_categories() -> dict:
    return {"categories": DEFAULT_CATEGORIES}


@router.post(
    "/classify",
    response_model=DocumentClassifyResponse,
    status_code=status.HTTP_200_OK,
)
def classify_document(payload: DocumentClassifyRequest) -> DocumentClassifyResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    categories_in = (
        [c.model_dump() for c in payload.categories]
        if payload.categories
        else DEFAULT_CATEGORIES
    )
    if not categories_in:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one category is required",
        )

    t0 = time.perf_counter()
    logger.info(
        "[document:classify] start=%s bytes=%d categories=%d",
        datetime.now().strftime("%H:%M:%S"),
        len(image_bytes),
        len(categories_in),
    )

    graph = get_classify_graph()
    state = graph.invoke(
        {
            "image_bytes": image_bytes,
            "categories": categories_in,
            "max_new_tokens": payload.max_new_tokens,
        }
    )

    res = state.get("result", {}) or {}
    chosen = res.get("category", "other")
    cat_map = {c["key"]: c for c in categories_in}
    label = cat_map.get(chosen, {}).get("label", chosen)

    logger.info(
        "[document:classify] finish=%s elapsed=%.2fs category=%s confidence=%.2f",
        datetime.now().strftime("%H:%M:%S"),
        time.perf_counter() - t0,
        chosen,
        float(res.get("confidence") or 0.0),
    )

    return DocumentClassifyResponse(
        ocr_text=state.get("ocr_text", ""),
        category=chosen,
        label=label,
        confidence=res.get("confidence"),
        reasoning=res.get("reasoning"),
        scores=res.get("scores", {}) or {},
        raw=state.get("raw", ""),
    )
