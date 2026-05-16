from pydantic import BaseModel, Field


class PIIEntity(BaseModel):
    label: str
    text: str
    start: int
    end: int
    score: float


class PIIDetectRequest(BaseModel):
    text: str = Field(..., min_length=1)


class PIIDetectResponse(BaseModel):
    entities: list[PIIEntity]
