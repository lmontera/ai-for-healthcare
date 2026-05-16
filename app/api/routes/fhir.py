import base64
import binascii
import logging

from fastapi import APIRouter, HTTPException, status

from app.graphs.fhir_graph import get_fhir_graph
from app.schemas.fhir import FHIRDocumentRequest, FHIRDocumentResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fhir", tags=["fhir"])


@router.post("/document", response_model=FHIRDocumentResponse, status_code=status.HTTP_200_OK)
def structure_document(payload: FHIRDocumentRequest) -> FHIRDocumentResponse:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc

    logger.info("[fhir] request received: bytes=%d", len(image_bytes))
    graph = get_fhir_graph()
    result = graph.invoke({"image_bytes": image_bytes})

    return FHIRDocumentResponse(
        ocr_text=result.get("ocr_text", ""),
        anonymized_text=result.get("anonymized_text", ""),
        fhir=result.get("fhir"),
        fhir_raw=result.get("fhir_raw", ""),
    )
