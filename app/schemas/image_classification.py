from pydantic import BaseModel, Field

DEFAULT_LABELS = ["medical image", "non-medical image"]


class ImageClassifyRequest(BaseModel):
    image_base64: str = Field(..., description="Image encoded as base64 string")
    candidate_labels: list[str] | None = Field(
        default=None,
        description="Optional candidate labels. Defaults to medical vs non-medical.",
    )


class ImageClassifyScore(BaseModel):
    label: str
    score: float


class ImageClassifyResponse(BaseModel):
    top_label: str
    is_medical: bool
    scores: list[ImageClassifyScore]
