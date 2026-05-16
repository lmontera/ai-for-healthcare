from typing import Any

from pydantic import BaseModel, Field


class FHIRDocumentRequest(BaseModel):
    image_base64: str = Field(..., description="Document image encoded as base64 string")


class FHIRDocumentResponse(BaseModel):
    ocr_text: str
    anonymized_text: str
    fhir: dict[str, Any] | None
    fhir_raw: str
