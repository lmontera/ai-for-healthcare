import base64
import binascii
import json
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.registry import (
    get_anonymization_service,
    get_llm_service,
    get_ocr_service,
)
from app.graphs.fhir_graph import get_fhir_graph
from app.schemas.fhir import FHIRDocumentRequest, FHIRDocumentResponse
from app.services.fhir.llm_structurer import (
    _MAX_INPUT_CHARS,
    _SYSTEM_PROMPT,
    _extract_json,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fhir", tags=["fhir"])


def _decode_image(image_b64: str) -> bytes:
    try:
        return base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="image_base64 is not a valid base64 string",
        ) from exc


@router.post("/document", response_model=FHIRDocumentResponse, status_code=status.HTTP_200_OK)
def structure_document(payload: FHIRDocumentRequest) -> FHIRDocumentResponse:
    image_bytes = _decode_image(payload.image_base64)
    logger.info("[fhir] request received: bytes=%d", len(image_bytes))
    graph = get_fhir_graph()
    result = graph.invoke({"image_bytes": image_bytes})

    return FHIRDocumentResponse(
        ocr_text=result.get("ocr_text", ""),
        anonymized_text=result.get("anonymized_text", ""),
        fhir=result.get("fhir"),
        fhir_raw=result.get("fhir_raw", ""),
    )


@router.post("/document/stream")
def structure_document_stream(payload: FHIRDocumentRequest) -> StreamingResponse:
    image_bytes = _decode_image(payload.image_base64)
    logger.info("[fhir] stream request received: bytes=%d", len(image_bytes))

    def emit(event: dict) -> str:
        return json.dumps(event, ensure_ascii=False) + "\n"

    def event_iter():
        try:
            ocr_text = get_ocr_service().extract_text(image_bytes)
            yield emit({"event": "ocr", "text": ocr_text})

            anonymized = get_anonymization_service().anonymize(ocr_text)
            yield emit({"event": "anonymized", "text": anonymized})

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": anonymized[:_MAX_INPUT_CHARS]},
            ]
            llm = get_llm_service()
            raw_parts: list[str] = []

            if hasattr(llm, "chat_stream"):
                for delta in llm.chat_stream(messages, max_new_tokens=2048):
                    raw_parts.append(delta)
                    yield emit({"event": "fhir_delta", "delta": delta})
            else:
                raw = llm.chat(messages, max_new_tokens=2048)
                raw_parts.append(raw)
                yield emit({"event": "fhir_delta", "delta": raw})

            raw = "".join(raw_parts)
            yield emit({"event": "fhir_done", "fhir": _extract_json(raw), "raw": raw})
        except Exception as exc:
            logger.exception("[fhir] stream error")
            yield emit({"event": "error", "detail": str(exc)})

    return StreamingResponse(event_iter(), media_type="application/x-ndjson")
