from pydantic import BaseModel, Field


class AnonymizeRequest(BaseModel):
    image_base64: str = Field(..., description="Document image encoded as base64 string")


class AnonymizeResponse(BaseModel):
    ocr_text: str
    anonymized_text: str


class AnonymizeTextRequest(BaseModel):
    text: str = Field(..., description="Plain text to anonymize")


class AnonymizeTextResponse(BaseModel):
    anonymized_text: str


class AnonymizeMaskedResponse(BaseModel):
    ocr_text: str
    anonymized_text: str
    masked_image_base64: str = Field(
        ..., description="PNG image with PII regions covered by black boxes (base64)"
    )
    entities_count: int
