from pydantic import BaseModel, Field


class LabResult(BaseModel):
    name: str
    value: float | None = None
    unit: str | None = None
    min_range_value: float | None = None
    max_range_value: float | None = None


class LabResultsRequest(BaseModel):
    image_base64: str = Field(..., description="Document image encoded as base64 string")
    max_new_tokens: int = Field(default=4096, ge=64, le=16384)


class LabResultsResponse(BaseModel):
    ocr_text: str
    results: list[LabResult]
    raw: str
