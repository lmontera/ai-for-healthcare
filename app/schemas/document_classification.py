from pydantic import BaseModel, Field


class DocumentCategory(BaseModel):
    key: str = Field(..., description="Identifier of the category, e.g. 'lab_report'")
    label: str = Field(..., description="Human-readable label, e.g. 'Referto di laboratorio'")
    description: str | None = Field(
        default=None,
        description="Short description guiding the classifier on what this category contains.",
    )


class DocumentClassifyRequest(BaseModel):
    image_base64: str = Field(..., description="Document image encoded as base64 string")
    categories: list[DocumentCategory] | None = Field(
        default=None,
        description="Custom category list. If null, the server default is used.",
    )
    max_new_tokens: int = Field(default=1024, ge=64, le=8192)


class DocumentClassifyResponse(BaseModel):
    ocr_text: str
    category: str
    label: str
    confidence: float | None = None
    reasoning: str | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    raw: str
