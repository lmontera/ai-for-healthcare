import base64
import binascii

from fastapi import APIRouter, HTTPException, status

from app.graphs.anonymize_graph import get_anonymize_graph
from app.schemas.anonymize import AnonymizeRequest, AnonymizeResponse

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

    graph = get_anonymize_graph()
    result = graph.invoke({"image_bytes": image_bytes})

    return AnonymizeResponse(
        ocr_text=result["ocr_text"],
        anonymized_text=result["anonymized_text"],
    )
