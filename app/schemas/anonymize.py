from pydantic import BaseModel, Field


class AnonymizeRequest(BaseModel):
    image_base64: str = Field(..., description="Document image encoded as base64 string")
    model: str | None = Field(
        default=None,
        description="Anonymization model key (see /anonymize/models). If null uses the default.",
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score (0-1). Entities below threshold are NOT masked.",
    )


class AnonymizeResponse(BaseModel):
    ocr_text: str
    anonymized_text: str


class AnonymizeTextRequest(BaseModel):
    text: str = Field(..., description="Plain text to anonymize")


class AnonymizeTextResponse(BaseModel):
    anonymized_text: str


class EntityWithScore(BaseModel):
    label: str
    text: str
    start: int
    end: int
    score: float


class AnonymizeMaskedResponse(BaseModel):
    ocr_text: str
    anonymized_text: str
    masked_image_base64: str = Field(
        ..., description="PNG image with PII regions covered by black boxes (base64)"
    )
    entities_count: int
    entities: list[EntityWithScore] = Field(
        default_factory=list,
        description="All entities detected by the chosen model (including below-threshold).",
    )
    min_score: float = 0.0
